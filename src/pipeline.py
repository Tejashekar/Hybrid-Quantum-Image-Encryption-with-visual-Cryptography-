"""Classical baseline and integrated Phase 5 encryption pipelines."""
from __future__ import annotations

from dataclasses import dataclass, field
import numbers

import numpy as np

from .chaotic_key import chaotic_key_for_shape
from .diffusion import (
    derive_chaotic_xor_key,
    derive_diffusion_material,
    derive_diffusion_scalar,
    derive_xor_key,
    dense_gf256_diffusion,
    inverse_dense_gf256_diffusion,
    normalize_nonce,
)
from .key_derivation import (artifact_auth_tag as make_artifact_auth_tag,
                             derive_share_coefficients, validate_secret_key,
                             verify_artifact_auth_tag)
from .decryption import decrypt as baseline_decrypt
from .metrics import psnr
from .preprocessing import load_image, preprocess
from .quantum_encryption import (
    QuantumInspiredConfig,
    arnold_scramble,
    arnold_unscramble,
    encrypt as baseline_encrypt,
    quantum_inspired_transform,
    inverse_quantum_inspired_transform,
    generate_random_key,
    derive_z_rotation_parameters,
    xor_diffusion,
)
from .visual_cryptography import generate_shares, reconstruct_from_shares


@dataclass(frozen=True)
class IntegratedPipelineConfig:
    """All parameters needed to reproduce and invert integrated encryption."""

    image_shape: tuple[int, int]
    x0: float = 0.5
    r: float = 3.99
    transient: int = 1000
    chaotic_seed: int | None = None
    arnold_iterations: int = 5
    quantum: QuantumInspiredConfig = field(default_factory=QuantumInspiredConfig)
    algorithm_version: str = "hybrid-classical-v5"

    def __post_init__(self):
        shape = tuple(self.image_shape)
        if len(shape) != 2 or shape[0] != shape[1] or any(
            isinstance(value, bool) or not isinstance(value, numbers.Integral) or value <= 0 for value in shape
        ):
            raise ValueError("image_shape must contain two equal positive integer dimensions")
        if not isinstance(self.x0, numbers.Real) or not 0.0 < float(self.x0) < 1.0:
            raise ValueError("x0 must satisfy 0 < x0 < 1")
        if not isinstance(self.r, numbers.Real) or not 3.57 < float(self.r) <= 4.0:
            raise ValueError("r must satisfy 3.57 < r <= 4.0")
        if isinstance(self.transient, bool) or not isinstance(self.transient, numbers.Integral) or self.transient < 0:
            raise ValueError("transient must be a non-negative integer")
        if self.chaotic_seed is not None and (isinstance(self.chaotic_seed, bool) or not isinstance(self.chaotic_seed, numbers.Integral)):
            raise ValueError("chaotic_seed must be an integer or None")
        if isinstance(self.arnold_iterations, bool) or not isinstance(self.arnold_iterations, numbers.Integral) or self.arnold_iterations < 0:
            raise ValueError("arnold_iterations must be a non-negative integer")
        if not isinstance(self.quantum, QuantumInspiredConfig):
            raise ValueError("quantum must be QuantumInspiredConfig")
        object.__setattr__(self, "image_shape", (int(shape[0]), int(shape[1])))
        object.__setattr__(self, "transient", int(self.transient))
        object.__setattr__(self, "arnold_iterations", int(self.arnold_iterations))

    def to_dict(self) -> dict:
        """Return JSON-serializable metadata; no raw key is stored."""
        return {
            "algorithm_version": self.algorithm_version,
            "image_shape": list(self.image_shape),
            "x0": float(self.x0),
            "r": float(self.r),
            "transient": self.transient,
            "chaotic_seed": self.chaotic_seed,
            "arnold_iterations": self.arnold_iterations,
            "quantum": {
                "cnot_control": self.quantum.cnot_control,
                "cnot_target": self.quantum.cnot_target,
                "x_bit": self.quantum.x_bit,
            },
        }

    @classmethod
    def from_dict(cls, data: dict):
        quantum_data = dict(data.get("quantum", {}))
        # Old archived configs may still contain the retired phase bit.
        quantum_data.pop("z_bit", None)
        return cls(
            image_shape=tuple(data["image_shape"]),
            x0=data["x0"],
            r=data["r"],
            transient=data["transient"],
            chaotic_seed=data.get("chaotic_seed"),
            arnold_iterations=data["arnold_iterations"],
            quantum=QuantumInspiredConfig(**quantum_data),
            algorithm_version=data.get("algorithm_version", "hybrid-classical-v5"),
        )


@dataclass
class EncryptedImage:
    """Cipher pixels plus public nonce and non-secret configuration."""

    ciphertext: np.ndarray
    metadata: dict
    nonce: bytes | None = None
    auth_tag: bytes | None = None
    configuration: str = "D"

    def __post_init__(self):
        self.ciphertext = np.asarray(self.ciphertext)
        if self.ciphertext.ndim != 2 or self.ciphertext.dtype != np.uint8:
            raise ValueError("ciphertext must be a two-dimensional uint8 array")
        if self.nonce is None:
            raise ValueError("ciphertext nonce is required for decryption")
        self.nonce = normalize_nonce(self.nonce)
        if not isinstance(self.auth_tag, bytes) or len(self.auth_tag) != 32:
            raise ValueError("ciphertext authentication tag is required; legacy formats are unsupported")
        if self.configuration not in {"A", "B", "C", "D", "E"}:
            raise ValueError("unsupported encrypted-image configuration")

    def to_dict(self) -> dict:
        return {
            "ciphertext": self.ciphertext.tolist(),
            "metadata": self.metadata,
            "format_version": 5,
            "nonce": self.nonce.hex(),
            "auth_tag": self.auth_tag.hex(),
            "configuration": self.configuration,
        }


def encrypt_image(image, config: IntegratedPipelineConfig, secret_key: bytes, *, nonce: bytes | None = None,
                  configuration: str = "D", public_config: dict | None = None) -> EncryptedImage:
    """Encrypt using caller-supplied 256-bit key and a public per-artifact nonce."""
    secret_key = validate_secret_key(secret_key)
    if configuration not in {"A", "B", "C", "D", "E"}:
        raise ValueError("unsupported configuration")
    image_array = np.asarray(image)
    if image_array.shape != config.image_shape or image_array.dtype != np.uint8 or image_array.ndim != 2:
        raise ValueError("image must be a uint8 grayscale array matching config.image_shape")
    nonce = normalize_nonce(nonce)
    context = public_config if public_config is not None else config.to_dict()
    if configuration == "A":
        ciphertext = xor_diffusion(image_array, derive_xor_key(
            image_array.shape, secret_key=secret_key, nonce=nonce,
            configuration=configuration, context=context,
        ))
    else:
        mask, k2, _, _ = derive_diffusion_material(
            image_array.shape, secret_key=secret_key, nonce=nonce, x0=config.x0, r=config.r,
            transient=config.transient, seed=config.chaotic_seed,
            configuration=configuration, context=context,
        )
        if configuration == "B":
            transformed_values = image_array
            xor_key = derive_chaotic_xor_key(
                image_array.shape, secret_key=secret_key, nonce=nonce, x0=config.x0,
                r=config.r, transient=config.transient, seed=config.chaotic_seed,
                configuration=configuration, context=context,
            )
        elif configuration == "C":
            controls, rotations = derive_z_rotation_parameters(mask, k2)
            transformed_values = quantum_inspired_transform(
                image_array, config.quantum,
                control_bits=controls.reshape(image_array.shape),
                rotation_amounts=rotations.reshape(image_array.shape),
            ).values
            xor_key = derive_xor_key(
                image_array.shape, secret_key=secret_key, nonce=nonce,
                configuration=configuration, context=context,
            )
        else:
            controls, rotations = derive_z_rotation_parameters(mask, k2)
            scrambled = arnold_scramble(image_array, config.arnold_iterations)
            transformed_values = quantum_inspired_transform(
                scrambled, config.quantum,
                control_bits=controls.reshape(image_array.shape),
                rotation_amounts=rotations.reshape(image_array.shape),
            ).values
            xor_key = derive_chaotic_xor_key(
                image_array.shape, secret_key=secret_key, nonce=nonce, x0=config.x0,
                r=config.r, transient=config.transient, seed=config.chaotic_seed,
                configuration=configuration, context=context,
            )
        xor_ciphertext = xor_diffusion(transformed_values, xor_key)
        scalar = derive_diffusion_scalar(secret_key, nonce, configuration=configuration, context=context)
        ciphertext = dense_gf256_diffusion(xor_ciphertext, mask, scalar)
    metadata = dict(context)
    tag = make_artifact_auth_tag(secret_key, nonce, configuration, metadata, ciphertext)
    return EncryptedImage(ciphertext, metadata, nonce, tag, configuration)


def decrypt_image(encrypted: EncryptedImage, config: IntegratedPipelineConfig, secret_key: bytes) -> np.ndarray:
    """Authenticate, then invert the configured classical pipeline."""
    secret_key = validate_secret_key(secret_key)
    if not isinstance(encrypted, EncryptedImage):
        raise ValueError("encrypted must be EncryptedImage with nonce metadata")
    if encrypted.ciphertext.shape != config.image_shape:
        raise ValueError("ciphertext shape does not match config.image_shape")
    verify_artifact_auth_tag(secret_key, encrypted.nonce, encrypted.configuration,
                             encrypted.metadata, encrypted.ciphertext, encrypted.auth_tag)
    context = encrypted.metadata
    if encrypted.configuration == "A":
        xor_key = derive_xor_key(
            encrypted.ciphertext.shape, secret_key=secret_key, nonce=encrypted.nonce,
            configuration="A", context=context,
        )
        return xor_diffusion(encrypted.ciphertext, xor_key)
    mask, k2, _, _ = derive_diffusion_material(
        config.image_shape, secret_key=secret_key, nonce=encrypted.nonce, x0=config.x0,
        r=config.r, transient=config.transient, seed=config.chaotic_seed,
        configuration=encrypted.configuration, context=context,
    )
    scalar = derive_diffusion_scalar(secret_key, encrypted.nonce,
                                     configuration=encrypted.configuration, context=context)
    xor_ciphertext = inverse_dense_gf256_diffusion(encrypted.ciphertext, mask, scalar)
    if encrypted.configuration == "B":
        xor_key = derive_chaotic_xor_key(
            config.image_shape, secret_key=secret_key, nonce=encrypted.nonce, x0=config.x0,
            r=config.r, transient=config.transient, seed=config.chaotic_seed,
            configuration="B", context=context,
        )
        return xor_diffusion(xor_ciphertext, xor_key)
    if encrypted.configuration == "C":
        xor_key = derive_xor_key(
            config.image_shape, secret_key=secret_key, nonce=encrypted.nonce,
            configuration="C", context=context,
        )
        transformed_values = xor_diffusion(xor_ciphertext, xor_key)
        controls, rotations = derive_z_rotation_parameters(mask, k2)
        return inverse_quantum_inspired_transform(
            transformed_values, config.quantum,
            control_bits=controls.reshape(config.image_shape),
            rotation_amounts=rotations.reshape(config.image_shape),
        )
    xor_key = derive_chaotic_xor_key(
        config.image_shape, secret_key=secret_key, nonce=encrypted.nonce, x0=config.x0,
        r=config.r, transient=config.transient, seed=config.chaotic_seed,
        configuration=encrypted.configuration, context=context,
    )
    transformed_values = xor_diffusion(xor_ciphertext, xor_key)
    controls, rotations = derive_z_rotation_parameters(mask, k2)
    scrambled = inverse_quantum_inspired_transform(
        transformed_values, config.quantum,
        control_bits=controls.reshape(config.image_shape),
        rotation_amounts=rotations.reshape(config.image_shape),
    )
    return arnold_unscramble(scrambled, config.arnold_iterations)


def run_pipeline(image_path, *, size=(128, 128), seed=None):
    """Existing Phase 1 random-key baseline pipeline, preserved for comparison."""
    image = load_image(image_path)
    if image is None:
        raise FileNotFoundError(f"could not load image: {image_path}")
    original = preprocess(image, size=size)
    key = generate_random_key(original.shape, seed=seed)
    encrypted = baseline_encrypt(original, key=key)
    share1, share2 = generate_shares(encrypted, seed=seed)
    reconstructed = reconstruct_from_shares(share1, share2)
    decrypted = baseline_decrypt(reconstructed, key)
    return {"original": original, "encrypted": encrypted, "share1": share1,
            "share2": share2, "reconstructed": reconstructed, "decrypted": decrypted,
            "psnr": psnr(original, decrypted)}


@dataclass(frozen=True)
class ResearchPipelineConfig:
    """Serializable configuration for encryption plus threshold sharing."""

    image_shape: tuple[int, int]
    x0: float = 0.5
    r: float = 3.99
    transient: int = 1000
    chaotic_seed: int | None = None
    arnold_iterations: int = 5
    quantum: QuantumInspiredConfig = field(default_factory=QuantumInspiredConfig)
    threshold_k: int = 2
    threshold_n: int = 2
    sharing_seed: int | None = None
    algorithm_version: str = "research-hybrid-v5"

    def __post_init__(self):
        encryption = IntegratedPipelineConfig(
            image_shape=self.image_shape, x0=self.x0, r=self.r,
            transient=self.transient, chaotic_seed=self.chaotic_seed,
            arnold_iterations=self.arnold_iterations, quantum=self.quantum,
            algorithm_version=self.algorithm_version,
        )
        if not isinstance(self.threshold_k, numbers.Integral) or not isinstance(self.threshold_n, numbers.Integral):
            raise ValueError("threshold_k and threshold_n must be integers")
        if not 1 <= int(self.threshold_k) <= int(self.threshold_n) <= 255:
            raise ValueError("threshold must satisfy 1 <= k <= n <= 255")
        for name, value in (("chaotic_seed", self.chaotic_seed), ("sharing_seed", self.sharing_seed)):
            if value is not None and (isinstance(value, bool) or not isinstance(value, numbers.Integral)):
                raise ValueError(f"{name} must be an integer or None")
        object.__setattr__(self, "image_shape", encryption.image_shape)
        object.__setattr__(self, "threshold_k", int(self.threshold_k))
        object.__setattr__(self, "threshold_n", int(self.threshold_n))
        object.__setattr__(self, "transient", encryption.transient)
        object.__setattr__(self, "arnold_iterations", encryption.arnold_iterations)

    def encryption_config(self) -> IntegratedPipelineConfig:
        return IntegratedPipelineConfig(
            image_shape=self.image_shape, x0=self.x0, r=self.r,
            transient=self.transient, chaotic_seed=self.chaotic_seed,
            arnold_iterations=self.arnold_iterations, quantum=self.quantum,
            algorithm_version=self.algorithm_version,
        )

    def to_dict(self) -> dict:
        return {
            **self.encryption_config().to_dict(),
            "threshold": {"k": self.threshold_k, "n": self.threshold_n},
        }

    @classmethod
    def from_dict(cls, data: dict):
        threshold = data.get("threshold", {})
        quantum_data = dict(data["quantum"])
        # Archived configurations used z_bit only for retired clear phase metadata.
        quantum_data.pop("z_bit", None)
        return cls(
            image_shape=tuple(data["image_shape"]), x0=data["x0"], r=data["r"],
            transient=data["transient"], chaotic_seed=data.get("chaotic_seed"),
            arnold_iterations=data["arnold_iterations"],
            quantum=QuantumInspiredConfig(**quantum_data),
            threshold_k=threshold["k"], threshold_n=threshold["n"],
            sharing_seed=data.get("sharing_seed"),
            algorithm_version=data.get("algorithm_version", "research-hybrid-v5"),
        )


def supported_research_configurations(size=128, **kwargs):
    """Return ready-to-use A-D configurations with identical encryption parameters."""
    return {
        "A_2_of_2": ResearchPipelineConfig(image_shape=(size, size), threshold_k=2, threshold_n=2, **kwargs),
        "B_2_of_3": ResearchPipelineConfig(image_shape=(size, size), threshold_k=2, threshold_n=3, **kwargs),
        "C_3_of_5": ResearchPipelineConfig(image_shape=(size, size), threshold_k=3, threshold_n=5, **kwargs),
        "D_3_of_6": ResearchPipelineConfig(image_shape=(size, size), threshold_k=3, threshold_n=6, **kwargs),
    }


@dataclass
class ResearchMetadata:
    """Serializable public configuration and nonce needed for inversion."""

    config: dict
    nonce: bytes | None = None
    auth_tag: bytes | None = None

    def to_dict(self) -> dict:
        return {
            "config": self.config,
            "format_version": 5,
            "nonce": self.nonce.hex() if self.nonce is not None else None,
            "auth_tag": self.auth_tag.hex() if self.auth_tag is not None else None,
        }

    @classmethod
    def from_dict(cls, data: dict):
        if data.get("format_version") != 5:
            raise ValueError("unsupported encrypted artifact format; version 5 is required and legacy formats are not implicitly decrypted")
        nonce_hex = data.get("nonce")
        auth_tag_hex = data.get("auth_tag")
        try:
            nonce = bytes.fromhex(nonce_hex) if nonce_hex is not None else None
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata nonce must be hexadecimal") from exc
        if nonce is not None:
            nonce = normalize_nonce(nonce)
        try:
            auth_tag = bytes.fromhex(auth_tag_hex) if auth_tag_hex is not None else None
        except (TypeError, ValueError) as exc:
            raise ValueError("metadata authentication tag must be hexadecimal") from exc
        if auth_tag is not None and len(auth_tag) != 32:
            raise ValueError("metadata authentication tag must be 32 bytes")
        config = dict(data["config"])
        quantum_data = dict(config.get("quantum", {}))
        # Legacy phase arrays are intentionally ignored; v3 regenerates controls from nonce-derived keys.
        quantum_data.pop("z_bit", None)
        config["quantum"] = quantum_data
        return cls(config=config, nonce=nonce, auth_tag=auth_tag)


@dataclass
class ResearchShareBundle:
    shares: list
    metadata: ResearchMetadata

    def to_dict(self) -> dict:
        return {
            "shares": [np.asarray(share, dtype=np.uint8).tolist() for share in self.shares],
            "share_indices": [int(getattr(share, "index", position + 1)) for position, share in enumerate(self.shares)],
            "metadata": self.metadata.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict):
        from .visual_cryptography import ImageShare
        shares = [ImageShare(np.asarray(values, dtype=np.uint8), index)
                  for values, index in zip(data["shares"], data["share_indices"])]
        return cls(shares=shares, metadata=ResearchMetadata.from_dict(data["metadata"]))


def _preprocess_for_config(image, config):
    array = np.asarray(image)
    if array.ndim == 2 and array.dtype == np.uint8:
        processed = array.copy()
    elif array.ndim == 2:
        raise ValueError("grayscale input must use dtype uint8")
    else:
        processed = preprocess(image, size=(config.image_shape[1], config.image_shape[0]))
    if processed.shape != config.image_shape or processed.dtype != np.uint8:
        raise ValueError("preprocessed image does not match configured square uint8 dimensions")
    return processed


def encrypt_and_share(image, config: ResearchPipelineConfig, secret_key: bytes, *, nonce: bytes | None = None) -> ResearchShareBundle:
    """Preprocess, encrypt, and generate configured XOR-based threshold shares."""
    if not isinstance(config, ResearchPipelineConfig):
        raise ValueError("config must be ResearchPipelineConfig")
    processed = _preprocess_for_config(image, config)
    encrypted = encrypt_image(processed, config.encryption_config(), secret_key, nonce=nonce,
                              configuration="E", public_config=config.to_dict())
    coefficient_count = (1 if (config.threshold_k, config.threshold_n) == (2, 2)
                         else config.threshold_k - 1) * encrypted.ciphertext.size
    coefficients = derive_share_coefficients(
        secret_key, encrypted.nonce, config.to_dict(), coefficient_count,
    )
    shares = generate_shares(encrypted.ciphertext, config.threshold_k, config.threshold_n,
                             coefficient_bytes=coefficients)
    metadata = ResearchMetadata(config=config.to_dict(), nonce=encrypted.nonce, auth_tag=encrypted.auth_tag)
    return ResearchShareBundle(shares=shares, metadata=metadata)


def reconstruct_and_decrypt(shares_or_bundle, config: ResearchPipelineConfig, secret_key: bytes, metadata=None) -> np.ndarray:
    """Validate metadata, reconstruct with k shares, and decrypt the image."""
    if not isinstance(config, ResearchPipelineConfig):
        raise ValueError("config must be ResearchPipelineConfig")
    if isinstance(shares_or_bundle, ResearchShareBundle):
        shares, bundle_metadata = shares_or_bundle.shares, shares_or_bundle.metadata
        if metadata is not None:
            raise ValueError("metadata must not be supplied separately with ResearchShareBundle")
        metadata = bundle_metadata
    else:
        shares = shares_or_bundle
    if isinstance(metadata, dict):
        metadata = ResearchMetadata.from_dict(metadata)
    if not isinstance(metadata, ResearchMetadata):
        raise ValueError("ResearchMetadata is required for reconstruction")
    if metadata.config != config.to_dict():
        raise ValueError("metadata configuration does not match supplied configuration")
    if metadata.nonce is None:
        raise ValueError("metadata nonce is required for reconstruction")
    ciphertext = reconstruct_from_shares(shares, config.threshold_k, config.threshold_n)
    if metadata.auth_tag is None:
        raise ValueError("artifact authentication tag is required; legacy formats are unsupported")
    encrypted = EncryptedImage(ciphertext, metadata.config, metadata.nonce,
                               metadata.auth_tag, "E")
    return decrypt_image(encrypted, config.encryption_config(), secret_key)
