import pytest
import numpy as np
from src.visual_cryptography import generate_shares, reconstruct_from_shares

def test_generate_shares():
    # Test for a simple 2x2 encrypted image
    encrypted_image = np.array([[1, 0], [0, 1]])
    share1, share2 = generate_shares(encrypted_image)

    # Check that the shares are of the same shape as the encrypted image
    assert share1.shape == encrypted_image.shape
    assert share2.shape == encrypted_image.shape

    # Check that the XOR of the shares equals the encrypted image
    assert np.array_equal(encrypted_image, np.bitwise_xor(share1, share2))

def test_reconstruct_from_shares():
    # Test for a simple 2x2 shares
    share1 = np.array([[1, 0], [0, 1]])
    share2 = np.array([[0, 1], [1, 0]])
    reconstructed_image = reconstruct_from_shares(share1, share2)

    # Check that the reconstructed image equals the original encrypted image
    original_encrypted_image = np.bitwise_xor(share1, share2)
    assert np.array_equal(reconstructed_image, original_encrypted_image)

def test_share_security():
    # Test that individual shares reveal no information
    encrypted_image = np.array([[1, 0], [0, 1]])
    share1, share2 = generate_shares(encrypted_image)

    # Check that the shares do not reveal the original encrypted image
    assert not np.array_equal(share1, encrypted_image)
    assert not np.array_equal(share2, encrypted_image)