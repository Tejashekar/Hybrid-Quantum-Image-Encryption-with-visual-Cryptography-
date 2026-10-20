"""Independent research metrics for image-encryption evaluation."""
from __future__ import annotations

import time
from collections.abc import Callable, Sequence

import numpy as np
from skimage.metrics import structural_similarity


def _image(image, name="image"):
    array = np.asarray(image)
    if array.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional grayscale image")
    return array


def _pair(first, second):
    left, right = _image(first, "first image"), _image(second, "second image")
    if left.shape != right.shape:
        raise ValueError("images must have identical shapes")
    return left, right


def entropy(image):
    """Return Shannon entropy in bits per pixel."""
    array = _image(image)
    values, counts = np.unique(array, return_counts=True)
    probabilities = counts.astype(np.float64) / array.size
    return float(-np.sum(probabilities * np.log2(probabilities)))


def _correlation(first, second):
    x = np.asarray(first, dtype=np.float64).ravel()
    y = np.asarray(second, dtype=np.float64).ravel()
    if x.size < 2:
        return 0.0
    x_centered, y_centered = x - x.mean(), y - y.mean()
    denominator = np.sqrt(np.dot(x_centered, x_centered) * np.dot(y_centered, y_centered))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(x_centered, y_centered) / denominator)


def neighboring_correlations(image):
    """Return horizontal, vertical, and diagonal Pearson correlations.

    Degenerate neighborhoods with zero variance are reported as 0.0 because
    Pearson correlation is undefined for them.
    """
    array = _image(image)
    return {
        "horizontal": _correlation(array[:, :-1], array[:, 1:]) if array.shape[1] > 1 else 0.0,
        "vertical": _correlation(array[:-1, :], array[1:, :]) if array.shape[0] > 1 else 0.0,
        "diagonal": _correlation(array[:-1, :-1], array[1:, 1:]) if min(array.shape) > 1 else 0.0,
    }


def correlation_analysis(image):
    """Backwards-compatible horizontal correlation."""
    return neighboring_correlations(image)["horizontal"]


def npcr(ciphertext1, ciphertext2):
    """Number of pixels change rate, in percent, between two ciphertexts."""
    first, second = _pair(ciphertext1, ciphertext2)
    return float(np.count_nonzero(first != second) / first.size * 100.0)


def uaci(ciphertext1, ciphertext2):
    """Unified average changing intensity, in percent, between ciphertexts."""
    first, second = _pair(ciphertext1, ciphertext2)
    return float(np.mean(np.abs(first.astype(np.float64) - second.astype(np.float64))) / 255.0 * 100.0)


def npcr_uaci(image1, image2):
    """Backwards-compatible pair returning ``(NPCR, UACI)``."""
    return npcr(image1, image2), uaci(image1, image2)


def calculate_differential_metrics(ciphertext1, ciphertext2):
    return {"npcr": npcr(ciphertext1, ciphertext2), "uaci": uaci(ciphertext1, ciphertext2)}


def key_sensitivity(ciphertext1, ciphertext2):
    """Compare ciphertexts from the same plaintext under two keys."""
    return calculate_differential_metrics(ciphertext1, ciphertext2)


def plaintext_sensitivity(ciphertext1, ciphertext2):
    """Compare ciphertexts from a one-pixel/bit plaintext perturbation."""
    return calculate_differential_metrics(ciphertext1, ciphertext2)


def histogram_statistics(image, reference=None):
    """Return 256-bin counts, normalized histogram, and optional L1 distance."""
    array = _image(image)
    if np.any(array < 0) or np.any(array > 255):
        raise ValueError("grayscale values must lie in [0, 255]")
    counts = np.bincount(array.astype(np.uint8).ravel(), minlength=256).astype(np.int64)
    result = {"counts": counts, "normalized": counts.astype(np.float64) / array.size}
    if reference is not None:
        other = histogram_statistics(reference)
        result["l1_distance"] = float(np.sum(np.abs(result["normalized"] - other["normalized"])))
    return result


def histogram_analysis(original, encrypted):
    """Backwards-compatible normalized histogram pair."""
    return histogram_statistics(original)["normalized"], histogram_statistics(encrypted)["normalized"]


def mse(original, recovered):
    first, second = _pair(original, recovered)
    difference = first.astype(np.float64) - second.astype(np.float64)
    return float(np.mean(difference * difference))


def psnr(original, decrypted):
    value = mse(original, decrypted)
    if value == 0.0:
        return float("inf")
    return float(20.0 * np.log10(255.0 / np.sqrt(value)))


def ssim(original, recovered):
    first, second = _pair(original, recovered)
    minimum = min(first.shape)
    if minimum < 3:
        raise ValueError("SSIM requires images with dimensions of at least 3")
    window = min(7, minimum if minimum % 2 else minimum - 1)
    return float(structural_similarity(first, second, data_range=255, win_size=window))


def calculate_security_metrics(original, ciphertext):
    encrypted = _image(ciphertext, "ciphertext")
    return {
        "entropy": entropy(encrypted),
        **{f"correlation_{key}": value for key, value in neighboring_correlations(encrypted).items()},
        "histogram": histogram_statistics(encrypted),
    }


def calculate_image_quality_metrics(original, recovered):
    return {"mse": mse(original, recovered), "psnr": psnr(original, recovered), "ssim": ssim(original, recovered)}


def measure_operation(operation: Callable, *args, **kwargs):
    """Run an already-prepared algorithm operation and return result, milliseconds."""
    started = time.perf_counter_ns()
    result = operation(*args, **kwargs)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0
    return result, float(elapsed_ms)


def calculate_performance_metrics(*, encryption=None, decryption=None, share_generation=None, reconstruction=None):
    operations = {
        "encryption_time_ms": encryption,
        "decryption_time_ms": decryption,
        "share_generation_time_ms": share_generation,
        "reconstruction_time_ms": reconstruction,
    }
    result = {}
    for name, operation in operations.items():
        if operation is not None:
            _, elapsed = measure_operation(operation)
            result[name] = elapsed
    return result


def calculate_storage_metrics(
    original,
    ciphertext,
    shares: Sequence,
    *,
    encoded_original_bytes=None,
    encoded_cipher_bytes=None,
    encoded_share_sizes=None,
    encoded_sizes=None,
):
    """Report raw array storage separately from optional encoded file sizes."""
    original_array, cipher_array = _image(original), _image(ciphertext)
    share_arrays = [_image(share, "share") for share in shares]
    if any(share.dtype != cipher_array.dtype for share in share_arrays):
        raise ValueError("shares must use the same dtype as the ciphertext")
    raw_original = int(original_array.nbytes)
    raw_cipher = int(cipher_array.nbytes)
    if any(share.shape != cipher_array.shape for share in share_arrays):
        raise ValueError("shares must have the same shape as the ciphertext")
    raw_total_shares = int(sum(share.nbytes for share in share_arrays))
    result = {
        "original_bytes": raw_original,
        "cipher_bytes": raw_cipher,
        "number_of_shares": len(share_arrays),
        "total_share_bytes": raw_total_shares,
        "storage_overhead_ratio": float(raw_total_shares / raw_original) if raw_original else float("inf"),
    }
    if encoded_share_sizes is None:
        encoded_share_sizes = encoded_sizes
    if encoded_share_sizes is not None:
        if len(encoded_share_sizes) != len(share_arrays):
            raise ValueError("encoded_sizes must contain one value per share")
        result["encoded_total_share_bytes"] = int(sum(encoded_share_sizes))
    if encoded_original_bytes is not None:
        result["encoded_original_bytes"] = int(encoded_original_bytes)
    if encoded_cipher_bytes is not None:
        result["encoded_cipher_bytes"] = int(encoded_cipher_bytes)
    return result
