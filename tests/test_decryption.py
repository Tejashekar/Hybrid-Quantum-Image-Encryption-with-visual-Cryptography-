import numpy as np

from src.decryption import decrypt
from src.quantum_encryption import encrypt, generate_random_key


def test_decryption_is_exact_inverse():
    image = np.arange(25, dtype=np.uint8).reshape(5, 5)
    key = generate_random_key(image.shape, seed=5)
    assert np.array_equal(decrypt(encrypt(image, key=key), key), image)
