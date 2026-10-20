import numpy as np
import pytest

from src.key_derivation import (
    artifact_auth_tag,
    hkdf_sha256,
    validate_secret_key,
    verify_artifact_auth_tag,
)


KEY = bytes(range(32))
NONCE = b"N" * 16
CONTEXT = {"configuration": "D", "shape": [4, 4]}


@pytest.mark.parametrize("key", [b"", b"x" * 31, b"x" * 33, "x" * 32, bytearray(32), None])
def test_secret_key_requires_exactly_32_bytes(key):
    with pytest.raises(ValueError, match="secret_key"):
        validate_secret_key(key)


def test_hkdf_is_repeatable_and_separates_domains_and_nonce():
    baseline = hkdf_sha256(KEY, NONCE, "QCRYPT diffusion", 64, context=CONTEXT)
    assert baseline == hkdf_sha256(KEY, NONCE, "QCRYPT diffusion", 64, context=CONTEXT)
    assert baseline != hkdf_sha256(KEY, NONCE, "QCRYPT scalar", 64, context=CONTEXT)
    assert baseline != hkdf_sha256(KEY, b"M" * 16, "QCRYPT diffusion", 64, context=CONTEXT)
    changed = bytearray(KEY)
    changed[7] ^= 0x04
    assert baseline != hkdf_sha256(bytes(changed), NONCE, "QCRYPT diffusion", 64, context=CONTEXT)


def test_artifact_tag_authenticates_key_ciphertext_and_public_metadata():
    ciphertext = np.arange(16, dtype=np.uint8).reshape(4, 4)
    tag = artifact_auth_tag(KEY, NONCE, "D", CONTEXT, ciphertext)
    verify_artifact_auth_tag(KEY, NONCE, "D", CONTEXT, ciphertext, tag)
    for args in [
        (b"X" * 32, NONCE, "D", CONTEXT, ciphertext, tag),
        (KEY, NONCE, "D", {**CONTEXT, "shape": [16, 1]}, ciphertext, tag),
        (KEY, NONCE, "D", CONTEXT, ciphertext ^ np.uint8(1), tag),
    ]:
        with pytest.raises(ValueError, match="authentication failed"):
            verify_artifact_auth_tag(*args)


@pytest.mark.parametrize("tag", [None, b"", b"short", "not-bytes"])
def test_missing_or_malformed_authentication_tag_is_rejected(tag):
    ciphertext = np.arange(16, dtype=np.uint8).reshape(4, 4)
    with pytest.raises(ValueError, match="authentication tag"):
        verify_artifact_auth_tag(KEY, NONCE, "D", CONTEXT, ciphertext, tag)


def test_artifact_metadata_does_not_contain_key_or_derived_stream():
    ciphertext = np.arange(16, dtype=np.uint8).reshape(4, 4)
    tag = artifact_auth_tag(KEY, NONCE, "D", CONTEXT, ciphertext)
    public_record = repr({"nonce": NONCE.hex(), "context": CONTEXT, "tag": tag.hex()})
    assert KEY.hex() not in public_record
    assert "QCRYPT scalar" not in public_record
    assert "keystream" not in public_record
