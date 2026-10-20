"""RFC 5869 HKDF-SHA-256 key separation for the research pipeline.

This module derives reproducible per-artifact material from a caller-provided
32-byte key and public 16-byte nonce. The Logistic map remains a research
transform; it is not treated as a cryptographic KDF or PRNG.
"""
from __future__ import annotations

import hashlib
import hmac
import json


SECRET_KEY_SIZE = 32
NONCE_SIZE = 16
KDF_VERSION = "HKDF-SHA-256/RFC5869"


def validate_secret_key(secret_key: bytes) -> bytes:
    if not isinstance(secret_key, bytes) or len(secret_key) != SECRET_KEY_SIZE:
        raise ValueError("secret_key must be exactly 32 bytes")
    return secret_key


def _context_bytes(context) -> bytes:
    try:
        return json.dumps(context, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("key derivation context must be JSON-serializable") from exc


def hkdf_sha256(secret_key: bytes, nonce: bytes, domain: str, length: int, *, context=None) -> bytes:
    """Derive bytes using HKDF-Extract(salt=nonce) and RFC 5869 Expand."""
    key = validate_secret_key(secret_key)
    if not isinstance(nonce, bytes) or len(nonce) != NONCE_SIZE:
        raise ValueError("nonce must be exactly 16 bytes")
    if not isinstance(domain, str) or not domain.startswith("QCRYPT "):
        raise ValueError("domain must be an explicit QCRYPT domain label")
    if isinstance(length, bool) or not isinstance(length, int) or not 1 <= length <= 16 * 1024 * 1024:
        raise ValueError("HKDF output length is out of range")

    prk = hmac.new(nonce, key, hashlib.sha256).digest()
    info = b"QCRYPT/phase7/" + domain.encode("ascii") + b"\x00" + _context_bytes(context or {})
    block_limit = 255 * hashlib.sha256().digest_size

    def expand(expand_info: bytes, requested: int) -> bytes:
        output = bytearray()
        previous = b""
        counter = 1
        while len(output) < requested:
            previous = hmac.new(prk, previous + expand_info + bytes((counter,)), hashlib.sha256).digest()
            output.extend(previous)
            counter += 1
        return bytes(output[:requested])

    if length <= block_limit:
        return expand(info, length)
    # RFC 5869 caps one Expand at 255 hash blocks. Larger image masks are
    # assembled from separate HKDF-Expand invocations with indexed info.
    output = bytearray()
    chunk_index = 0
    while len(output) < length:
        requested = min(block_limit, length - len(output))
        indexed_info = info + b"\x00QCRYPT expand chunk " + chunk_index.to_bytes(4, "big")
        output.extend(expand(indexed_info, requested))
        chunk_index += 1
    return bytes(output)


def keyed_logistic_parameters(secret_key: bytes, nonce: bytes, domain: str, *, x0: float, context=None):
    """Map separated key material to Logistic-map initialization inputs."""
    material = hkdf_sha256(secret_key, nonce, domain, 16, context=context)
    integer = int.from_bytes(material[:8], "big")
    derived_x0 = (integer + 1) / ((1 << 64) + 1)
    if not 0.0 < derived_x0 < 1.0:
        derived_x0 = 0.5
    derived_seed = int.from_bytes(material[8:], "big")
    return derived_x0, derived_seed


def artifact_auth_tag(secret_key: bytes, nonce: bytes, configuration: str, context, ciphertext) -> bytes:
    """Authenticate public artifact metadata and ciphertext with a separated HMAC key."""
    import numpy as np

    array = np.asarray(ciphertext)
    if array.dtype != np.uint8 or array.ndim != 2:
        raise ValueError("ciphertext must be a two-dimensional uint8 array")
    auth_key = hkdf_sha256(secret_key, nonce, "QCRYPT authentication", 32,
                           context={"configuration": configuration, "public_config": context})
    header = json.dumps({
        "format_version": 5,
        "configuration": configuration,
        "public_config": context,
        "shape": list(array.shape),
        "nonce": nonce.hex(),
    }, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hmac.new(auth_key, header + b"\x00" + array.tobytes(order="C"), hashlib.sha256).digest()


def verify_artifact_auth_tag(secret_key: bytes, nonce: bytes, configuration: str, context, ciphertext, tag: bytes) -> None:
    if not isinstance(tag, bytes) or len(tag) != hashlib.sha256().digest_size:
        raise ValueError("ciphertext artifact is missing a valid authentication tag; legacy formats are unsupported")
    expected = artifact_auth_tag(secret_key, nonce, configuration, context, ciphertext)
    if not hmac.compare_digest(expected, tag):
        raise ValueError("ciphertext authentication failed; check the secret key and artifact metadata")


def derive_share_coefficients(secret_key: bytes, nonce: bytes, configuration_context, count: int):
    """Return domain-separated coefficient bytes for unchanged GF(256) sharing math."""
    import numpy as np

    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("coefficient byte count must be positive")
    material = hkdf_sha256(secret_key, nonce, "QCRYPT sharing", count,
                           context=configuration_context)
    return np.frombuffer(material, dtype=np.uint8).copy()
