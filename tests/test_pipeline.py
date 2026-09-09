import pytest
from src.pipeline import encrypt, decrypt
from src.visual_cryptography import generate_shares, reconstruct_from_shares
from src.metrics import histogram_analysis, correlation_analysis, entropy, npcr_uaci, psnr
import numpy as np
from PIL import Image

def test_lossless_round_trip():
    original_image = Image.open("input/sample.png").convert("L")
    original_matrix = np.array(original_image)

    encrypted_image = encrypt(original_matrix)
    decrypted_image = decrypt(encrypted_image)

    assert np.array_equal(original_matrix, decrypted_image), "Decrypted image does not match the original."

def test_visual_cryptography_correctness():
    encrypted_image = np.random.randint(0, 256, (128, 128), dtype=np.uint8)
    share1, share2 = generate_shares(encrypted_image)

    reconstructed_image = reconstruct_from_shares(share1, share2)

    assert np.array_equal(encrypted_image, reconstructed_image), "Reconstructed image does not match the encrypted image."

def test_share_security():
    share1 = np.random.randint(0, 256, (128, 128), dtype=np.uint8)
    share2 = np.random.randint(0, 256, (128, 128), dtype=np.uint8)

    assert entropy(share1) >= 7.9, "Share 1 does not have sufficient entropy."
    assert entropy(share2) >= 7.9, "Share 2 does not have sufficient entropy."

def test_key_sensitivity():
    original_image = Image.open("input/sample.png").convert("L")
    original_matrix = np.array(original_image)

    encrypted_image1 = encrypt(original_matrix, key=12345)
    encrypted_image2 = encrypt(original_matrix, key=12346)

    assert not np.array_equal(encrypted_image1, encrypted_image2), "Different keys should produce different encrypted images."

def test_metrics_calculation():
    original_image = Image.open("input/sample.png").convert("L")
    original_matrix = np.array(original_image)
    encrypted_image = encrypt(original_matrix)

    assert histogram_analysis(original_matrix, encrypted_image) is not None, "Histogram analysis failed."
    assert correlation_analysis(encrypted_image) < 0.1, "Correlation analysis indicates high pixel correlation."
    assert entropy(encrypted_image) > 7.9, "Encrypted image does not have sufficient entropy."
    assert npcr_uaci(original_matrix, encrypted_image) > 99.6, "NPCR/UACI metrics indicate low sensitivity."
    assert psnr(original_matrix, encrypted_image) == float('inf'), "PSNR should be infinite for lossless encryption."