"""Reproducible A-E baseline, threshold, and ablation experiment runner."""
from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import uuid

import cv2
import numpy as np

from src.chaotic_key import chaotic_key_for_shape
from src.metrics import (
    calculate_differential_metrics,
    calculate_image_quality_metrics,
    calculate_security_metrics,
    calculate_storage_metrics,
    measure_operation,
)
from src.pipeline import (
    EncryptedImage,
    IntegratedPipelineConfig,
    decrypt_image,
    encrypt_image,
)
from src.diffusion import derive_diffusion_material, diffuse, inverse_diffuse
from src.key_derivation import derive_share_coefficients
from experiments.key_material import experiment_key_id, load_experiment_key
from src.quantum_encryption import (
    QuantumInspiredConfig,
    encrypt as baseline_encrypt,
    generate_random_key,
    inverse_quantum_inspired_transform,
    quantum_inspired_transform,
    xor_diffusion,
    derive_z_rotation_parameters,
)
from src.decryption import decrypt as baseline_decrypt
from src.visual_cryptography import generate_shares, reconstruct_from_shares
from src.preprocessing import PREPROCESSING_VERSION, preprocessing_parameters, preprocess
from experiments.dataset_manifest import decode_image_record, unique_dataset_records


def derive_seed(master_seed, purpose):
    """Derive independent reproducible uint32 seeds from one experiment seed."""
    payload = f"{int(master_seed)}:{purpose}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:4], "big")


@dataclass(frozen=True)
class ExperimentConfig:
    label: str
    description: str
    image_shape: tuple[int, int]
    seed: int
    chaotic_seed: int
    sharing_seed: int
    x0: float = 0.37
    r: float = 3.91
    transient: int = 1000
    arnold_iterations: int = 3
    threshold_k: int | None = None
    threshold_n: int | None = None
    quantum: QuantumInspiredConfig = QuantumInspiredConfig(2, 6, 3)

    def __post_init__(self):
        if self.label not in {"A", "B", "C", "D", "E"}:
            raise ValueError("label must be one of A, B, C, D, E")
        if len(self.image_shape) != 2 or self.image_shape[0] != self.image_shape[1] or min(self.image_shape) <= 0:
            raise ValueError("image_shape must be a positive square shape")
        if self.label == "E":
            if self.threshold_k is None or self.threshold_n is None or not 1 <= self.threshold_k <= self.threshold_n <= 255:
                raise ValueError("E requires a valid threshold k,n")
        elif self.threshold_k is not None or self.threshold_n is not None:
            raise ValueError("thresholds are only valid for configuration E")

    def encryption_config(self):
        return IntegratedPipelineConfig(
            image_shape=self.image_shape, x0=self.x0, r=self.r, transient=self.transient,
            chaotic_seed=self.chaotic_seed, arnold_iterations=self.arnold_iterations,
            quantum=self.quantum,
        )

    def to_dict(self):
        value = asdict(self)
        value["image_shape"] = list(self.image_shape)
        value["quantum"] = asdict(self.quantum)
        return value


def build_experiment_matrix(size=16, seed=2026):
    """Return A-D plus all required E threshold configurations."""
    common = dict(
        image_shape=(size, size),
        seed=derive_seed(seed, "classical-key"),
        chaotic_seed=derive_seed(seed, "chaotic-key"),
        sharing_seed=derive_seed(seed, "threshold-sharing"),
    )
    return [
        ExperimentConfig("A", "XOR only", **common),
        ExperimentConfig("B", "Chaos + XOR", **common),
        ExperimentConfig("C", "Quantum-inspired + XOR", **common),
        ExperimentConfig("D", "Chaos + Arnold + quantum-inspired + XOR", **common),
        *[ExperimentConfig("E", "D + threshold sharing", threshold_k=k, threshold_n=n, **common)
          for k, n in ((2, 2), (2, 3), (3, 5), (3, 6))],
    ]


def generate_synthetic_images(size=16, seed=2026):
    """Generate deterministic natural-like, gradient, random, and low-texture images."""
    rng = np.random.default_rng(derive_seed(seed, "synthetic-image-random"))
    y, x = np.mgrid[0:size, 0:size]
    natural = ((x * 9 + y * 5 + 35 * np.sin(x / 2.7) + 24 * np.cos(y / 3.1)) % 256).astype(np.uint8)
    gradient = np.tile(np.linspace(0, 255, size, dtype=np.uint8), (size, 1))
    random_image = rng.integers(0, 256, (size, size), dtype=np.uint8)
    low_texture = np.full((size, size), 96, dtype=np.uint8)
    return [
        {"name": "synthetic_natural", "type": "natural/grayscale", "image": natural},
        {"name": "synthetic_gradient", "type": "gradient", "image": gradient},
        {"name": "synthetic_random", "type": "random", "image": random_image},
        {"name": "synthetic_low_texture", "type": "low-texture", "image": low_texture},
    ]


def preprocess_real_image(image, size):
    """Apply the shared center-crop/resize/grayscale preprocessing protocol."""
    return preprocess(image, size=(size, size))


def _record_from_decoded(record, image_type="natural/grayscale"):
    return {
        "name": record["path"].name,
        "type": image_type,
        "image": record["processed"],
        "source_filenames": record.get("source_filenames", [record["path"].name]),
        "source_content_sha256": record["content_hash"],
        "file_format": record["file_format"],
        "original_width": record["original_width"],
        "original_height": record["original_height"],
        "original_channels": record["original_channels"],
        "preprocessing": preprocessing_parameters((record["processed"].shape[1], record["processed"].shape[0])),
    }


def load_experiment_images(image=None, image_dir=None, image_path=None, size=16, seed=2026):
    if image_path is not None:
        path = Path(image_path)
        try:
            decoded = decode_image_record(path, size)
        except (ValueError, OSError):
            raise ValueError(f"explicit image could not be decoded as a supported image: {path}")
        return [_record_from_decoded(decoded)]
    if image is not None:
        array = np.asarray(image)
        try:
            processed = preprocess_real_image(array, size)
        except ValueError:
            # Preserve row-level failure reporting for explicitly invalid arrays.
            processed = array
        digest = _image_identity(array)
        return [{
            "name": "supplied", "type": "natural/grayscale", "image": processed,
            "source_filenames": [], "source_content_sha256": digest,
            "original_width": int(array.shape[1]), "original_height": int(array.shape[0]),
            "original_channels": 1 if array.ndim == 2 else int(array.shape[2]),
            "preprocessing": preprocessing_parameters((size, size)),
        }]
    if image_dir is not None:
        directory = Path(image_dir)
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"explicit image directory does not exist or is not a directory: {directory}")
        files = sorted((path for path in directory.iterdir() if path.is_file()), key=lambda p: p.name.casefold())
        non_files = [path.name for path in directory.iterdir() if not path.is_file()]
        if non_files:
            raise ValueError(
                "explicit image directory contains unreadable or unsupported entries: "
                + ", ".join(sorted(non_files, key=str.casefold))
            )
        if not files:
            raise ValueError(f"explicit image directory contains no valid supported images: {directory}")
        try:
            unique_records = unique_dataset_records(directory, target_size=size)
        except ValueError as exc:
            raise ValueError(f"explicit image directory contains unreadable or unsupported entries: {exc}") from exc
        return [_record_from_decoded(record) for record in unique_records]
    return generate_synthetic_images(size=size, seed=seed)


def _prepare(image, shape):
    array = np.asarray(image)
    if array.ndim != 2 or array.dtype != np.uint8 or array.shape != shape:
        raise ValueError(f"image must be uint8 grayscale with shape {shape}")
    return array


def _encryptor(config, secret_key):
    shape = config.image_shape
    key_a = generate_random_key(shape, config.seed)
    key_c_minimal = key_a.copy()
    key_c_minimal[0, 0] ^= np.uint8(1)
    key_c_seed_perturbed = generate_random_key(shape, config.seed + 1)
    key_b = chaotic_key_for_shape(shape, x0=config.x0, r=config.r, transient=config.transient, seed=config.chaotic_seed)
    integrated = config.encryption_config()
    experiment_nonce = hashlib.sha256(f"{config.seed}:{config.label}:nonce".encode()).digest()[:16]

    def encrypt_for(image, variant="base"):
        if config.label == "A":
            return baseline_encrypt(image, key=key_a)
        if config.label == "B":
            key = key_b if variant == "base" else chaotic_key_for_shape(shape, x0=config.x0 + 1e-4, r=config.r, transient=config.transient, seed=config.chaotic_seed)
            return xor_diffusion(image, key)
        if config.label == "C":
            key = key_a if variant == "base" else key_c_minimal if variant == "minimal_key" else key_c_seed_perturbed
            k1, k2, iv, iv2 = derive_diffusion_material(
                shape, secret_key=secret_key, nonce=experiment_nonce, x0=config.x0, r=config.r,
                transient=config.transient, seed=config.chaotic_seed,
            )
            controls, rotations = derive_z_rotation_parameters(k1.reshape(shape), k2.reshape(shape))
            transformed = quantum_inspired_transform(
                image, config.quantum, control_bits=controls, rotation_amounts=rotations,
            )
            return diffuse(xor_diffusion(transformed.values, key), k1, k2, iv, iv2), experiment_nonce
        transformed_config = integrated if variant == "base" else IntegratedPipelineConfig(
            image_shape=shape, x0=config.x0 + 1e-4, r=config.r, transient=config.transient,
            chaotic_seed=config.chaotic_seed, arnold_iterations=config.arnold_iterations,
            quantum=config.quantum)
        encrypted = encrypt_image(image, transformed_config, secret_key, nonce=experiment_nonce,
                                  configuration=config.label, public_config=config.to_dict())
        return encrypted.ciphertext, experiment_nonce, transformed_config, encrypted.auth_tag, encrypted.metadata

    return encrypt_for


def _image_identity(image):
    array = np.asarray(image)
    digest = hashlib.sha256()
    digest.update(str(array.dtype).encode("ascii"))
    digest.update(repr(array.shape).encode("ascii"))
    digest.update(array.tobytes())
    return digest.hexdigest()


def _environment_versions():
    versions = {"python": platform.python_version()}
    for package in ("numpy", "scipy", "scikit-image", "opencv-python", "qiskit"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    return versions


def _run_one(image_record, config, master_seed=None, secret_key=None):
    secret_key = load_experiment_key() if secret_key is None else secret_key
    raw_image = np.asarray(image_record["image"])
    row = {
        "experiment_id": uuid.uuid4().hex,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "image_name": image_record["name"], "image_type": image_record["type"],
        "image_id": _image_identity(raw_image), "image_shape": list(raw_image.shape),
        "configured_shape": list(config.image_shape), "image_dtype": str(raw_image.dtype),
        "configuration": config.label,
        "configuration_description": config.description, "configuration_parameters": config.to_dict(),
        "master_seed": master_seed,
        "software_version": _environment_versions(),
        "status": "success",
        "experiment_key_id_sha256": experiment_key_id(secret_key) if secret_key is not None else None,
    }
    row.update({
        "source_filename": image_record.get("name"),
        "source_filenames": image_record.get("source_filenames", [image_record.get("name")] if image_record.get("name") else []),
        "source_content_sha256": image_record.get("source_content_sha256", _image_identity(raw_image)),
        "original_width": image_record.get("original_width", int(raw_image.shape[1]) if raw_image.ndim >= 2 else None),
        "original_height": image_record.get("original_height", int(raw_image.shape[0]) if raw_image.ndim >= 2 else None),
        "original_channels": image_record.get("original_channels", 1 if raw_image.ndim == 2 else (int(raw_image.shape[2]) if raw_image.ndim == 3 else None)),
        "preprocessing": image_record.get("preprocessing", {
            "version": PREPROCESSING_VERSION,
            "method": "synthetic input already generated at target dimensions",
            "target_size": list(raw_image.shape[:2]),
            "interpolation": "N/A",
            "output_color_space": "grayscale",
            "output_channels": 1,
            "output_dtype": str(raw_image.dtype),
        }),
    })
    try:
        image = _prepare(image_record["image"], config.image_shape)
        encrypt_for = _encryptor(config, secret_key)
        if config.label in {"A", "B"}:
            encrypted, encryption_ms = measure_operation(encrypt_for, image)
            ciphertext = encrypted
        else:
            encrypted_result, encryption_ms = measure_operation(encrypt_for, image)
            ciphertext = encrypted_result[0]
            experiment_nonce = encrypted_result[1]
            encrypted_config = encrypted_result[2] if config.label in {"D", "E"} else config.encryption_config()
            artifact_tag = encrypted_result[3] if len(encrypted_result) > 3 else None
            artifact_metadata = encrypted_result[4] if len(encrypted_result) > 4 else None
        security = calculate_security_metrics(image, ciphertext)
        row.update({"entropy": security["entropy"], "correlation_horizontal": security["correlation_horizontal"],
                    "correlation_vertical": security["correlation_vertical"], "correlation_diagonal": security["correlation_diagonal"],
                    "histogram": {key: value.tolist() if isinstance(value, np.ndarray) else value for key, value in security["histogram"].items()},
                    "encryption_time_ms": encryption_ms})
        if config.label != "A":
            changed = image.copy(); changed[0, 0] ^= 1
            differential, _ = measure_operation(encrypt_for, changed)
            diff_cipher = differential[0] if isinstance(differential, tuple) else differential
            row.update(calculate_differential_metrics(ciphertext, diff_cipher))
            sensitivity_variant = "minimal_key" if config.label == "C" else "modified"
            changed_key, _ = measure_operation(lambda: encrypt_for(image, sensitivity_variant))
            changed_key_cipher = changed_key[0] if isinstance(changed_key, tuple) else changed_key
            row.update({f"key_sensitivity_{key}": value for key, value in calculate_differential_metrics(ciphertext, changed_key_cipher).items()})
            row["plaintext_perturbation"] = "pixel (0,0) XOR 1"
            row["key_perturbation"] = "one byte XOR 1 at (0,0)" if config.label == "C" else "chaotic parameter x0 + 1e-4"
            if config.label == "C":
                seed_changed, _ = measure_operation(lambda: encrypt_for(image, "seed_perturbed"))
                seed_changed_cipher = seed_changed[0] if isinstance(seed_changed, tuple) else seed_changed
                row.update({f"seed_perturbation_sensitivity_{key}": value for key, value in calculate_differential_metrics(ciphertext, seed_changed_cipher).items()})
                row["seed_perturbation"] = "random key seed + 1"
        if config.label == "D":
            enc_obj = EncryptedImage(ciphertext, artifact_metadata, experiment_nonce, artifact_tag, config.label)
            recovered, decryption_ms = measure_operation(lambda: decrypt_image(enc_obj, config.encryption_config(), secret_key))
            row.update(calculate_image_quality_metrics(image, recovered))
            row["decryption_time_ms"] = decryption_ms
        elif config.label == "B":
            key = chaotic_key_for_shape(config.image_shape, x0=config.x0, r=config.r,
                                        transient=config.transient, seed=config.chaotic_seed)
            _, decryption_ms = measure_operation(lambda: baseline_decrypt(ciphertext, key))
            row["decryption_time_ms"] = decryption_ms
        elif config.label == "C":
            k1, k2, iv, iv2 = derive_diffusion_material(
                config.image_shape, secret_key=secret_key, nonce=experiment_nonce, x0=encrypted_config.x0,
                r=encrypted_config.r, transient=encrypted_config.transient,
                seed=encrypted_config.chaotic_seed,
            )
            controls, rotations = derive_z_rotation_parameters(k1.reshape(config.image_shape), k2.reshape(config.image_shape))
            undistributed = inverse_diffuse(ciphertext, k1, k2, iv, iv2)
            _, decryption_ms = measure_operation(
                lambda: inverse_quantum_inspired_transform(
                    xor_diffusion(undistributed, generate_random_key(config.image_shape, config.seed)),
                    config.quantum, control_bits=controls, rotation_amounts=rotations))
            row["decryption_time_ms"] = decryption_ms
        if config.label == "E":
            coefficients = derive_share_coefficients(
                secret_key, experiment_nonce, config.to_dict(),
                (1 if (config.threshold_k, config.threshold_n) == (2, 2) else config.threshold_k - 1) * ciphertext.size,
            )
            shares, share_ms = measure_operation(lambda: generate_shares(
                ciphertext, config.threshold_k, config.threshold_n, coefficient_bytes=coefficients))
            reconstructed, reconstruction_ms = measure_operation(lambda: reconstruct_from_shares(shares[:config.threshold_k], config.threshold_k, config.threshold_n))
            enc_obj = EncryptedImage(reconstructed, artifact_metadata, experiment_nonce, artifact_tag, config.label)
            recovered, decryption_ms = measure_operation(lambda: decrypt_image(enc_obj, config.encryption_config(), secret_key))
            row.update(calculate_image_quality_metrics(image, recovered))
            row["decryption_time_ms"] = decryption_ms
            row["complete_round_trip_time_ms"] = encryption_ms + share_ms + reconstruction_ms + decryption_ms
            row["share_generation_time_ms"] = share_ms; row["reconstruction_time_ms"] = reconstruction_ms
            row["share_selection_strategy"] = "first_k"
            row["selected_share_coordinates"] = [int(getattr(share, "index", position + 1)) for position, share in enumerate(shares[:config.threshold_k])]
            row.update(calculate_storage_metrics(image, ciphertext, shares))
            row["bytes_per_share"] = row["total_share_bytes"] / row["number_of_shares"]
            row["threshold_k"] = config.threshold_k; row["threshold_n"] = config.threshold_n
            row["threshold_verified"] = bool(np.array_equal(reconstructed, ciphertext))
        return row
    except Exception as exc:
        row.update({"status": "failed", "error_type": type(exc).__name__, "error_message": str(exc)})
        return row


def run_experiments(*, image=None, image_dir=None, image_path=None, secret_key=None,
                    output_dir="experiments/results/phase5-center-crop-v1",
                    size=16, seed=2026, overwrite=False):
    """Run the deterministic matrix without replacing an existing result archive."""
    destination = Path(output_dir)
    existing_outputs = [destination / "results.json", destination / "results.csv"]
    if not overwrite and any(path.exists() for path in existing_outputs):
        raise FileExistsError(f"experiment output already exists: {destination}; choose a new output directory or pass overwrite=True")
    secret_key = load_experiment_key() if secret_key is None else secret_key
    images = load_experiment_images(image=image, image_dir=image_dir, image_path=image_path, size=size, seed=seed)
    configs = build_experiment_matrix(size=size, seed=seed)
    rows = []
    for image_record in images:
        for config in configs:
            rows.append(_run_one(image_record, config, master_seed=seed, secret_key=secret_key))
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "results.json").write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    columns = sorted({key for row in rows for key in row})
    with (destination / "results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns); writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(value, default=str) if isinstance(value, (dict, list)) else value for key, value in row.items()})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=Path); parser.add_argument("--image-dir", type=Path)
    parser.add_argument("--size", type=int, default=16); parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output-dir", type=Path, default=Path("experiments/results/phase5-center-crop-v1"))
    parser.add_argument("--overwrite", action="store_true", help="replace result files in the selected output directory")
    args = parser.parse_args()
    if args.image is not None and args.image_dir is not None:
        parser.error("--image and --image-dir are mutually exclusive")
    rows = run_experiments(image_path=args.image, image_dir=args.image_dir, size=args.size,
                           seed=args.seed, output_dir=args.output_dir, overwrite=args.overwrite)
    print(json.dumps({"rows": len(rows), "failed": sum(row["status"] == "failed" for row in rows)}))


if __name__ == "__main__":
    main()
