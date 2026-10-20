"""Nonce-derived reversible byte diffusion for quantum-inspired image runs.

The Logistic Map remains the source of the byte material. The public nonce
perturbs its initial condition and seed; it does not replace the key system.
"""
from __future__ import annotations

import secrets

import numpy as np

from .chaotic_key import chaotic_key_stream
from .key_derivation import hkdf_sha256, keyed_logistic_parameters, validate_secret_key
from .visual_cryptography import _gf_inv, _gf_mul


NONCE_SIZE = 16


def normalize_nonce(nonce: bytes | bytearray | memoryview | None = None) -> bytes:
    """Return a valid public 16-byte nonce, generating one when omitted."""
    if nonce is None:
        return secrets.token_bytes(NONCE_SIZE)
    if not isinstance(nonce, (bytes, bytearray, memoryview)):
        raise ValueError("nonce must be 16 bytes")
    value = bytes(nonce)
    if len(value) != NONCE_SIZE:
        raise ValueError("nonce must be 16 bytes")
    return value


def derive_diffusion_material(
    shape: tuple[int, ...],
    *,
    secret_key: bytes,
    nonce: bytes,
    x0: float,
    r: float,
    transient: int,
    seed: int | None,
    configuration: str = "D",
    context=None,
) -> tuple[np.ndarray, np.ndarray, int, int]:
    """Derive key-controlled diffusion and rotation material.

    HKDF domain ``QCRYPT diffusion`` controls the Logistic initialization that
    emits k1/k2. The separate ``QCRYPT iv`` domain emits the legacy boundary
    bytes used by compatibility diagnostics; neither domain output is stored.
    """
    secret_key = validate_secret_key(secret_key)
    nonce = normalize_nonce(nonce)
    dimensions = tuple(int(value) for value in shape)
    if not dimensions or any(value <= 0 for value in dimensions):
        raise ValueError("shape must contain positive dimensions")
    count = int(np.prod(dimensions, dtype=np.int64))
    public_context = {
        "configuration": configuration, "parameters": context or {},
        "shape": dimensions, "x0": float(x0), "r": float(r),
        "transient": int(transient), "public_seed": seed,
    }
    mixed_x0, mixed_seed = keyed_logistic_parameters(
        secret_key, nonce, "QCRYPT diffusion", x0=x0, context=public_context,
    )
    stream = chaotic_key_stream(
        2 * count + 2, x0=mixed_x0, r=r, transient=transient, seed=mixed_seed
    )
    k1 = stream[:count].copy()
    k2 = stream[count:2 * count].copy()
    iv_material = hkdf_sha256(secret_key, nonce, "QCRYPT iv", 2, context=public_context)
    iv, iv2 = iv_material
    return k1, k2, iv, iv2


def derive_diffusion_scalar(secret_key: bytes, nonce: bytes, *, configuration: str, context=None) -> int:
    """Derive Candidate-3's c from the separated scalar HKDF domain."""
    scalar_material = hkdf_sha256(
        secret_key, nonce, "QCRYPT scalar", 1,
        context={"configuration": configuration, "public_config": context or {}},
    )
    return 2 + (scalar_material[0] % 254)


def derive_xor_key(shape, *, secret_key: bytes, nonce: bytes, configuration: str, context=None) -> np.ndarray:
    dimensions = tuple(int(value) for value in shape)
    if not dimensions or any(value <= 0 for value in dimensions):
        raise ValueError("shape must contain positive dimensions")
    count = int(np.prod(dimensions, dtype=np.int64))
    material = hkdf_sha256(
        secret_key, nonce, "QCRYPT xor", count,
        context={"configuration": configuration, "shape": dimensions, "public_config": context or {}},
    )
    return np.frombuffer(material, dtype=np.uint8).copy().reshape(dimensions)


def derive_chaotic_xor_key(shape, *, secret_key: bytes, nonce: bytes, x0: float, r: float,
                           transient: int, seed: int | None, configuration: str, context=None) -> np.ndarray:
    dimensions = tuple(int(value) for value in shape)
    if not dimensions or any(value <= 0 for value in dimensions):
        raise ValueError("shape must contain positive dimensions")
    derived_x0, derived_seed = keyed_logistic_parameters(
        secret_key, nonce, "QCRYPT chaotic", x0=x0,
        context={"configuration": configuration, "parameters": context or {},
                 "shape": dimensions, "r": float(r), "transient": int(transient), "public_seed": seed},
    )
    return chaotic_key_stream(
        int(np.prod(dimensions, dtype=np.int64)), x0=derived_x0, r=r,
        transient=transient, seed=derived_seed,
    ).reshape(dimensions)


def dense_gf256_diffusion(image, mask, c: int | None = None) -> np.ndarray:
    """Apply the active dense rank-one GF(256) reversible diffusion.

    ``mask`` is regenerated from key parameters and nonce. When ``c`` is not
    supplied, it is derived as ``2 + mask[0] % 254``. The transform uses
    Rijndael GF(256) multiplication (polynomial 0x11B).
    """
    source = np.asarray(image)
    if source.dtype != np.uint8 or source.size == 0:
        raise ValueError("image must be a non-empty uint8 array")
    key = np.asarray(mask)
    if key.dtype != np.uint8 or key.size != source.size:
        raise ValueError("mask must be uint8 with one byte per image element")
    scalar = _validate_gf_scalar(key, c)
    values = source.reshape(-1) ^ key.reshape(-1)
    total = np.bitwise_xor.reduce(values)
    output = _gf_mul(np.uint8(scalar), values) ^ total
    return output.reshape(source.shape).astype(np.uint8, copy=False)


def inverse_dense_gf256_diffusion(ciphertext, mask, c: int | None = None) -> np.ndarray:
    """Invert :func:`dense_gf256_diffusion` exactly."""
    encrypted = np.asarray(ciphertext)
    if encrypted.dtype != np.uint8 or encrypted.size == 0:
        raise ValueError("ciphertext must be a non-empty uint8 array")
    key = np.asarray(mask)
    if key.dtype != np.uint8 or key.size != encrypted.size:
        raise ValueError("mask must be uint8 with one byte per ciphertext element")
    scalar = _validate_gf_scalar(key, c)
    values = encrypted.reshape(-1)
    parity = values.size & 1
    aggregate = np.bitwise_xor.reduce(values)
    total = _gf_mul(np.uint8(_gf_inv(scalar ^ parity)), np.uint8(aggregate)).item()
    unmasked = _gf_mul(np.uint8(_gf_inv(scalar)), values ^ np.uint8(total))
    output = unmasked ^ key.reshape(-1)
    return output.reshape(encrypted.shape).astype(np.uint8, copy=False)


def _validate_gf_scalar(mask: np.ndarray, c: int | None) -> int:
    if c is None:
        scalar = 2 + int(mask.reshape(-1)[0]) % 254
    elif isinstance(c, (bool, np.bool_)) or not isinstance(c, (int, np.integer)):
        raise ValueError("c must be an integer in [2, 255]")
    else:
        scalar = int(c)
    if not 2 <= scalar <= 255:
        raise ValueError("c must be in [2, 255]")
    return scalar


def diffuse(image, k1, k2, iv: int, iv2: int) -> np.ndarray:
    """Legacy two-pass modular diffusion; retained for compatibility only."""
    source = np.asarray(image)
    if source.dtype != np.uint8 or source.size == 0:
        raise ValueError("image must be a non-empty uint8 array")
    first_key = np.asarray(k1)
    second_key = np.asarray(k2)
    if first_key.dtype != np.uint8 or second_key.dtype != np.uint8:
        raise ValueError("diffusion keys must use dtype uint8")
    if first_key.size != source.size or second_key.size != source.size:
        raise ValueError("diffusion keys must contain one byte per image element")
    if any(isinstance(value, bool) or not isinstance(value, (int, np.integer)) or not 0 <= int(value) <= 255 for value in (iv, iv2)):
        raise ValueError("iv and iv2 must be byte values")
    values = source.reshape(-1)
    key1, key2 = first_key.reshape(-1), second_key.reshape(-1)
    forward = np.empty_like(values)
    previous = int(iv)
    for index in range(values.size):
        previous = (int(values[index] ^ key1[index]) + previous) & 0xFF
        forward[index] = previous

    output = np.empty_like(values)
    following = int(iv2)
    for index in range(values.size - 1, -1, -1):
        following = (int(forward[index] ^ key2[index]) + following) & 0xFF
        output[index] = following
    return output.reshape(source.shape)


def inverse_diffuse(ciphertext, k1, k2, iv: int, iv2: int) -> np.ndarray:
    """Legacy inverse for two-pass modular diffusion; compatibility only."""
    encrypted = np.asarray(ciphertext)
    if encrypted.dtype != np.uint8 or encrypted.size == 0:
        raise ValueError("ciphertext must be a non-empty uint8 array")
    first_key = np.asarray(k1)
    second_key = np.asarray(k2)
    if first_key.dtype != np.uint8 or second_key.dtype != np.uint8:
        raise ValueError("diffusion keys must use dtype uint8")
    if first_key.size != encrypted.size or second_key.size != encrypted.size:
        raise ValueError("diffusion keys must contain one byte per ciphertext element")
    if any(isinstance(value, bool) or not isinstance(value, (int, np.integer)) or not 0 <= int(value) <= 255 for value in (iv, iv2)):
        raise ValueError("iv and iv2 must be byte values")

    values = encrypted.reshape(-1)
    key1, key2 = first_key.reshape(-1), second_key.reshape(-1)
    forward = np.empty_like(values)
    following = int(iv2)
    for index in range(values.size - 1, -1, -1):
        forward[index] = ((int(values[index]) - following) & 0xFF) ^ int(key2[index])
        following = int(values[index])

    output = np.empty_like(values)
    previous = int(iv)
    for index in range(values.size):
        output[index] = ((int(forward[index]) - previous) & 0xFF) ^ int(key1[index])
        previous = int(forward[index])
    return output.reshape(encrypted.shape)
