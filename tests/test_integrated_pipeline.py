import numpy as np
import pytest

from src.pipeline import (
    EncryptedImage,
    IntegratedPipelineConfig,
    decrypt_image,
    encrypt_image,
)
from src.quantum_encryption import QuantumInspiredConfig
from src.key_derivation import validate_secret_key


TEST_SECRET_KEY = bytes(range(32))


def config(size, **kwargs):
    values = dict(image_shape=(size, size), x0=0.37, r=3.91, transient=17,
                  chaotic_seed=9, arnold_iterations=3,
                  quantum=QuantumInspiredConfig(cnot_control=2, cnot_target=6, x_bit=3))
    values.update(kwargs)
    return IntegratedPipelineConfig(**values)


@pytest.mark.parametrize("size", [4, 8, 16])
def test_integrated_round_trip_deterministic_images(size):
    image = np.arange(size * size, dtype=np.uint8).reshape(size, size)
    cfg = config(size)
    recovered = decrypt_image(encrypt_image(image, cfg, TEST_SECRET_KEY), cfg, TEST_SECRET_KEY)
    assert np.array_equal(recovered, image)


def test_integrated_round_trip_random_16x16():
    image = np.random.default_rng(123).integers(0, 256, (16, 16), dtype=np.uint8)
    cfg = config(16)
    assert np.array_equal(decrypt_image(encrypt_image(image, cfg, TEST_SECRET_KEY), cfg, TEST_SECRET_KEY), image)


def test_128x128_smoke_round_trip():
    image = np.random.default_rng(128).integers(0, 256, (128, 128), dtype=np.uint8)
    cfg = config(128)
    encrypted = encrypt_image(image, cfg, TEST_SECRET_KEY)
    assert encrypted.ciphertext.shape == image.shape
    assert np.array_equal(decrypt_image(encrypted, cfg, TEST_SECRET_KEY), image)


@pytest.mark.parametrize("label", ["A", "B", "C", "D"])
def test_all_direct_configurations_round_trip_with_secret_key(label):
    image = np.random.default_rng(770).integers(0, 256, (16, 16), dtype=np.uint8)
    cfg = config(16)
    encrypted = encrypt_image(image, cfg, TEST_SECRET_KEY, nonce=b"R" * 16, configuration=label)
    assert np.array_equal(decrypt_image(encrypted, cfg, TEST_SECRET_KEY), image)


def test_encryption_is_deterministic_for_explicit_nonce_and_metadata_has_no_key():
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    cfg = config(8)
    nonce = bytes(range(16))
    first = encrypt_image(image, cfg, TEST_SECRET_KEY, nonce=nonce)
    second = encrypt_image(image, cfg, TEST_SECRET_KEY, nonce=nonce)
    assert np.array_equal(first.ciphertext, second.ciphertext)
    assert "key" not in first.metadata
    assert first.metadata == cfg.to_dict()
    assert first.nonce == nonce
    assert first.auth_tag == second.auth_tag
    assert first.to_dict()["format_version"] == 5
    assert TEST_SECRET_KEY.hex() not in str(first.to_dict())
    assert "phase" not in first.to_dict()
    assert "control_bits" not in first.to_dict()
    assert "rotation_amounts" not in first.to_dict()
    assert "z_bit" not in first.metadata["quantum"]


def test_each_encryption_generates_a_fresh_nonce():
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    cfg = config(8)
    first = encrypt_image(image, cfg, TEST_SECRET_KEY)
    second = encrypt_image(image, cfg, TEST_SECRET_KEY)
    assert len(first.nonce) == len(second.nonce) == 16
    assert first.nonce != second.nonce
    assert not np.array_equal(first.ciphertext, second.ciphertext)


@pytest.mark.parametrize(
    "change",
    [
        {"x0": 0.38},
        {"arnold_iterations": 4},
        {"quantum": QuantumInspiredConfig(cnot_control=1, cnot_target=7, x_bit=4)},
    ],
)
def test_configuration_changes_ciphertext(change):
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    nonce = b"C" * 16
    first = encrypt_image(image, config(8), TEST_SECRET_KEY, nonce=nonce)
    changed = config(8, **change)
    second = encrypt_image(image, changed, TEST_SECRET_KEY, nonce=nonce)
    assert not np.array_equal(first.ciphertext, second.ciphertext)


def test_config_is_serializable_and_reconstructible():
    cfg = config(8)
    restored = IntegratedPipelineConfig.from_dict(cfg.to_dict())
    assert restored == cfg


@pytest.mark.parametrize(
    "kwargs",
    [
        {"image_shape": (4, 8)},
        {"image_shape": (4, 4), "x0": 0.0},
        {"image_shape": (4, 4), "r": 3.57},
        {"image_shape": (4, 4), "arnold_iterations": -1},
    ],
)
def test_invalid_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        IntegratedPipelineConfig(**kwargs)


def test_invalid_image_and_missing_encrypted_metadata_are_rejected():
    cfg = config(4)
    with pytest.raises(ValueError):
        encrypt_image(np.zeros((4, 4), dtype=np.int16), cfg, TEST_SECRET_KEY)
    with pytest.raises(ValueError):
        decrypt_image(np.zeros((4, 4), dtype=np.uint8), cfg, TEST_SECRET_KEY)


def test_wrong_config_shape_is_rejected_on_decryption():
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    encrypted = encrypt_image(image, config(4), TEST_SECRET_KEY)
    with pytest.raises(ValueError):
        decrypt_image(encrypted, config(8), TEST_SECRET_KEY)


@pytest.mark.parametrize("bad_key", [b"", b"x" * 31, b"x" * 33, "x" * 64, bytearray(b"x" * 32), None])
def test_secret_key_requires_exactly_32_bytes(bad_key):
    with pytest.raises(ValueError, match="secret_key"):
        validate_secret_key(bad_key)


def test_secret_key_is_required_and_wrong_key_is_rejected_by_authentication():
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    cfg = config(8)
    with pytest.raises(TypeError):
        encrypt_image(image, cfg)
    encrypted = encrypt_image(image, cfg, TEST_SECRET_KEY, nonce=b"K" * 16)
    with pytest.raises(ValueError, match="authentication failed"):
        decrypt_image(encrypted, cfg, b"z" * 32)
    assert np.array_equal(decrypt_image(encrypted, cfg, TEST_SECRET_KEY), image)


@pytest.mark.parametrize("label", ["A", "B", "C", "D", "E"])
def test_one_bit_key_change_changes_artifact_for_each_configuration(label):
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    cfg = config(8)
    nonce = b"Q" * 16
    changed_key = bytearray(TEST_SECRET_KEY)
    changed_key[17] ^= 0x08
    first = encrypt_image(image, cfg, TEST_SECRET_KEY, nonce=nonce, configuration=label)
    second = encrypt_image(image, cfg, bytes(changed_key), nonce=nonce, configuration=label)
    assert not np.array_equal(first.ciphertext, second.ciphertext)
    assert first.auth_tag != second.auth_tag


def test_legacy_artifact_version_is_rejected_explicitly():
    with pytest.raises(ValueError, match="version 5 is required"):
        from src.pipeline import ResearchMetadata
        ResearchMetadata.from_dict({"format_version": 4, "config": {}, "nonce": "00" * 16})
