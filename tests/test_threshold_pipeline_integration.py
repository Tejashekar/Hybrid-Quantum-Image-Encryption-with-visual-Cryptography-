from itertools import combinations

import numpy as np
import pytest

from src.pipeline import EncryptedImage, IntegratedPipelineConfig, decrypt_image, encrypt_image
from src.quantum_encryption import QuantumInspiredConfig
from src.visual_cryptography import generate_shares, reconstruct_from_shares

TEST_SECRET_KEY = bytes(range(32))


def make_config(size):
    return IntegratedPipelineConfig(
        image_shape=(size, size), x0=0.37, r=3.91, transient=17,
        chaotic_seed=9, arnold_iterations=3,
        quantum=QuantumInspiredConfig(cnot_control=2, cnot_target=6, x_bit=3),
    )


@pytest.mark.parametrize("k,n", [(2, 2), (2, 3), (3, 5), (3, 6)])
def test_encrypt_share_reconstruct_decrypt_round_trip(k, n):
    image = np.random.default_rng(k * 10 + n).integers(0, 256, (8, 8), dtype=np.uint8)
    config = make_config(8)
    encrypted = encrypt_image(image, config, TEST_SECRET_KEY)
    shares = generate_shares(encrypted.ciphertext, k, n, seed=21)
    for indices in combinations(range(n), k):
        reconstructed = reconstruct_from_shares([shares[i] for i in indices], k, n)
        recovered = decrypt_image(EncryptedImage(reconstructed, encrypted.metadata, encrypted.nonce,
                                                  encrypted.auth_tag, encrypted.configuration),
                                  config, TEST_SECRET_KEY)
        assert np.array_equal(recovered, image)


@pytest.mark.parametrize("k,n", [(2, 3), (3, 5), (3, 6)])
def test_integrated_pipeline_rejects_fewer_than_k_shares(k, n):
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    config = make_config(8)
    encrypted = encrypt_image(image, config, TEST_SECRET_KEY)
    shares = generate_shares(encrypted.ciphertext, k, n, seed=22)
    with pytest.raises(ValueError):
        reconstruct_from_shares(shares[: k - 1], k, n)
