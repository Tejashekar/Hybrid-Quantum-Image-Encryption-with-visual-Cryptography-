import numpy as np
import pytest

from src.metrics import (
    calculate_differential_metrics,
    calculate_image_quality_metrics,
    calculate_performance_metrics,
    calculate_security_metrics,
    calculate_storage_metrics,
    entropy,
    histogram_statistics,
    mse,
    neighboring_correlations,
    npcr,
    plaintext_sensitivity,
    psnr,
    ssim,
    uaci,
)


def test_entropy_known_cases():
    assert entropy(np.zeros((8, 8), dtype=np.uint8)) == 0.0
    values = np.indices((16, 16)).sum(axis=0).astype(np.uint8) % 2
    assert entropy(values) == pytest.approx(1.0)


def test_neighboring_correlations_and_degenerate_case():
    constant = np.full((8, 8), 7, dtype=np.uint8)
    assert neighboring_correlations(constant) == {"horizontal": 0.0, "vertical": 0.0, "diagonal": 0.0}
    gradient = np.tile(np.arange(8, dtype=np.uint8), (8, 1))
    correlations = neighboring_correlations(gradient)
    assert correlations["horizontal"] == pytest.approx(1.0)
    assert correlations["vertical"] == pytest.approx(1.0)
    random_image = np.random.default_rng(4).integers(0, 256, (32, 32), dtype=np.uint8)
    assert all(-1.0 <= value <= 1.0 for value in neighboring_correlations(random_image).values())


def test_npcr_uaci_ciphertext_definitions():
    first = np.zeros((4, 4), dtype=np.uint8)
    second = first.copy()
    assert npcr(first, second) == 0.0
    assert uaci(first, second) == 0.0
    second[:, :] = 255
    assert npcr(first, second) == 100.0
    assert uaci(first, second) == 100.0
    assert calculate_differential_metrics(first, second)["npcr"] == 100.0


def test_differential_experiment_changes_one_plaintext_pixel_outside_metric():
    plaintext = np.zeros((8, 8), dtype=np.uint8)
    changed = plaintext.copy()
    changed[3, 4] ^= 1
    key = np.full_like(plaintext, 91)
    ciphertext1 = np.bitwise_xor(plaintext, key)
    ciphertext2 = np.bitwise_xor(changed, key)
    result = plaintext_sensitivity(ciphertext1, ciphertext2)
    assert result["npcr"] == pytest.approx(100.0 / 64.0)
    assert result["uaci"] == pytest.approx(100.0 / 255.0 / 64.0)


def test_histogram_statistics_and_distance():
    image = np.arange(256, dtype=np.uint8).reshape(16, 16)
    stats = histogram_statistics(image, np.zeros_like(image))
    assert stats["counts"].shape == (256,)
    assert stats["normalized"].sum() == pytest.approx(1.0)
    assert stats["l1_distance"] == pytest.approx(2.0 - 2.0 / 256.0)


def test_quality_metrics():
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    assert mse(image, image) == 0.0
    assert psnr(image, image) == float("inf")
    assert ssim(image, image) == pytest.approx(1.0)
    altered = image.copy()
    altered[0, 0] += 1
    assert mse(image, altered) > 0
    assert psnr(image, altered) < float("inf")
    assert 0.0 < ssim(image, altered) < 1.0


def test_shape_validation_and_ssim_small_image():
    with pytest.raises(ValueError):
        npcr(np.zeros((4, 4), dtype=np.uint8), np.zeros((4, 5), dtype=np.uint8))
    with pytest.raises(ValueError):
        ssim(np.zeros((2, 2), dtype=np.uint8), np.zeros((2, 2), dtype=np.uint8))


def test_security_quality_performance_and_storage_apis():
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    security = calculate_security_metrics(image, image)
    quality = calculate_image_quality_metrics(image, image)
    performance = calculate_performance_metrics(encryption=lambda: image, decryption=lambda: image)
    storage = calculate_storage_metrics(image, image, [image, image])
    assert "entropy" in security and "correlation_horizontal" in security
    assert quality["mse"] == 0.0 and quality["ssim"] == pytest.approx(1.0)
    assert performance["encryption_time_ms"] >= 0.0
    assert performance["decryption_time_ms"] >= 0.0
    assert storage["number_of_shares"] == 2
    assert storage["total_share_bytes"] == 2 * image.nbytes
    assert storage["storage_overhead_ratio"] == pytest.approx(2.0)


def test_histogram_and_storage_reject_invalid_inputs():
    with pytest.raises(ValueError):
        histogram_statistics(np.array([[256]], dtype=np.int16))
    with pytest.raises(ValueError):
        calculate_storage_metrics(np.zeros((2, 2), dtype=np.uint8), np.zeros((2, 2), dtype=np.uint8), [np.zeros((2, 3), dtype=np.uint8)])
