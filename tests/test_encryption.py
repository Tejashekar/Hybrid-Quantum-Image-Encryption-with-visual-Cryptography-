import numpy as np

from src.quantum_encryption import encrypt, generate_random_key


def test_xor_encryption_is_deterministic_with_key():
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    key = generate_random_key(image.shape, seed=3)
    assert np.array_equal(encrypt(image, key=key), encrypt(image, key=key))


def test_generated_key_is_reproducible():
    assert np.array_equal(generate_random_key((4, 4), 4), generate_random_key((4, 4), 4))
