import numpy as np
import pytest

import app as flask_app
from src.diffusion import (
    dense_gf256_diffusion,
    derive_diffusion_material,
    derive_diffusion_scalar,
    inverse_dense_gf256_diffusion,
)
from src.pipeline import ResearchPipelineConfig, encrypt_and_share, reconstruct_and_decrypt
from src.quantum_encryption import QuantumInspiredConfig
from src.visual_cryptography import _gf_inv, _gf_mul

TEST_SECRET_KEY = bytes(range(32))


@pytest.mark.parametrize("shape", [(1,), (2,), (3,), (2, 2), (1, 5), (32, 32), (4, 4, 3)])
@pytest.mark.parametrize("kind", ["random", "zero", "max", "constant"])
def test_dense_diffusion_round_trip_shapes_and_values(shape, kind):
    rng = np.random.default_rng(713 + int(np.prod(shape)))
    if kind == "random":
        image = rng.integers(0, 256, shape, dtype=np.uint8)
    elif kind == "zero":
        image = np.zeros(shape, dtype=np.uint8)
    elif kind == "max":
        image = np.full(shape, 255, dtype=np.uint8)
    else:
        image = np.full(shape, 128, dtype=np.uint8)
    mask = rng.integers(0, 256, image.size, dtype=np.uint8)
    encrypted = dense_gf256_diffusion(image, mask)
    recovered = inverse_dense_gf256_diffusion(encrypted, mask)
    assert encrypted.dtype == np.uint8
    assert encrypted.shape == image.shape
    assert np.array_equal(recovered, image)


@pytest.mark.parametrize("c", [2, 3, 127, 254, 255])
def test_dense_diffusion_round_trip_for_boundary_scalar_values(c):
    rng = np.random.default_rng(124 + c)
    image = rng.integers(0, 256, (3, 5), dtype=np.uint8)
    mask = rng.integers(0, 256, image.size, dtype=np.uint8)
    encrypted = dense_gf256_diffusion(image, mask, c=c)
    assert np.array_equal(inverse_dense_gf256_diffusion(encrypted, mask, c=c), image)


@pytest.mark.parametrize("value", [1, 2, 3, 17, 127, 254, 255])
def test_reused_gf256_arithmetic_has_multiplicative_inverses(value):
    inverse = _gf_inv(value)
    product = _gf_mul(np.uint8(value), np.uint8(inverse))
    assert np.asarray(product).dtype == np.uint8
    assert int(product) == 1
    assert int(_gf_mul(np.uint8(value), np.uint8(1))) == value


@pytest.mark.parametrize("delta", [1, 2, 127, 128, 255])
def test_single_byte_xor_change_changes_every_diffusion_output_byte(delta):
    rng = np.random.default_rng(9001)
    original = rng.integers(0, 256, 17, dtype=np.uint8)
    changed = original.copy()
    changed[8] ^= np.uint8(delta)
    mask = derive_diffusion_material(
        original.shape, secret_key=TEST_SECRET_KEY, nonce=b"d" * 16,
        x0=0.37, r=3.91, transient=1000, seed=42,
    )[0]
    first = dense_gf256_diffusion(original, mask)
    second = dense_gf256_diffusion(changed, mask)
    assert np.all(np.bitwise_xor(first, second) != 0)


@pytest.mark.parametrize("label", ["A", "B", "C", "D", "E"])
def test_api_configuration_round_trips_exactly_with_dense_diffusion(label):
    image = np.random.default_rng(81).integers(0, 256, (128, 128), dtype=np.uint8)
    config = flask_app._api_config(label)
    nonce = b"R" * 16 if label != "A" else None
    artifact = flask_app._api_direct_encrypt_artifact(image, label, config, TEST_SECRET_KEY, nonce=nonce)
    recovered = flask_app._api_direct_decrypt(artifact.ciphertext, label, config, TEST_SECRET_KEY,
                                             nonce=artifact.nonce, auth_tag=artifact.auth_tag)
    assert np.array_equal(recovered, image)


def test_dense_material_derivation_and_scalar_are_nonce_deterministic():
    arguments = dict(shape=(8, 8), secret_key=TEST_SECRET_KEY, x0=0.37, r=3.91,
                     transient=1000, seed=9281, configuration="D", context={"config": "test"})
    first_mask = derive_diffusion_material(nonce=b"A" * 16, **arguments)[0]
    repeated_mask = derive_diffusion_material(nonce=b"A" * 16, **arguments)[0]
    other_mask = derive_diffusion_material(nonce=b"B" * 16, **arguments)[0]
    scalar = derive_diffusion_scalar(TEST_SECRET_KEY, b"A" * 16, configuration="D", context={"config": "test"})
    other_scalar = derive_diffusion_scalar(TEST_SECRET_KEY, b"B" * 16, configuration="D", context={"config": "test"})
    assert np.array_equal(first_mask, repeated_mask)
    assert 2 <= scalar <= 255
    assert 2 <= other_scalar <= 255
    assert not np.array_equal(first_mask, other_mask)


@pytest.mark.parametrize("indices", [[0, 2], [1, 2]])
def test_threshold_e_reconstructs_from_arbitrary_two_of_three_shares(indices):
    image = np.random.default_rng(101).integers(0, 256, (8, 8), dtype=np.uint8)
    config = ResearchPipelineConfig(
        image_shape=(8, 8), x0=0.37, r=3.91, transient=1000,
        chaotic_seed=9281, arnold_iterations=2,
        quantum=QuantumInspiredConfig(2, 6, 3),
        threshold_k=2, threshold_n=3, sharing_seed=48,
    )
    bundle = encrypt_and_share(image, config, TEST_SECRET_KEY, nonce=b"E" * 16)
    recovered = reconstruct_and_decrypt([bundle.shares[index] for index in indices], config, TEST_SECRET_KEY, bundle.metadata)
    assert np.array_equal(recovered, image)
    with pytest.raises(ValueError, match="at least|shares|threshold"):
        reconstruct_and_decrypt(bundle.shares[:1], config, TEST_SECRET_KEY, bundle.metadata)

