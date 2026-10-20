"""XOR-based threshold image secret sharing over GF(2^8).

This is computational image secret sharing, not optical visual cryptography
and does not use pixel expansion. Field addition is byte XOR; multiplication
is the standard Rijndael GF(256) multiplication.
"""
from __future__ import annotations

import numbers
import numpy as np


class ImageShare(np.ndarray):
    """A uint8 image share carrying its non-secret field x-coordinate."""

    def __new__(cls, array, index):
        obj = np.asarray(array, dtype=np.uint8).view(cls)
        obj.index = int(index)
        return obj

    def __array_finalize__(self, obj):
        if obj is not None:
            self.index = getattr(obj, "index", None)


def _validate_threshold(k, n):
    if isinstance(k, bool) or isinstance(n, bool) or not isinstance(k, numbers.Integral) or not isinstance(n, numbers.Integral):
        raise ValueError("k and n must be integers")
    if not 1 <= int(k) <= int(n) <= 255:
        raise ValueError("threshold must satisfy 1 <= k <= n <= 255")
    return int(k), int(n)


def _validate_secret(secret_image):
    secret = np.asarray(secret_image)
    if secret.ndim != 2 or secret.dtype != np.uint8:
        raise ValueError("secret_image must be a two-dimensional uint8 array")
    return secret


def _gf_mul(left, right):
    """Multiply uint8 arrays/scalars in GF(2^8), with XOR as addition."""
    a = np.asarray(left, dtype=np.uint8)
    b = np.asarray(right, dtype=np.uint8)
    result = np.zeros(np.broadcast_shapes(a.shape, b.shape), dtype=np.uint8)
    a, b = (array.copy() for array in np.broadcast_arrays(a, b))
    for _ in range(8):
        result ^= np.where((b & 1) != 0, a, 0).astype(np.uint8)
        a = (((a.astype(np.uint16) << 1) ^ np.where((a & 0x80) != 0, 0x11B, 0)) & 0xFF).astype(np.uint8)
        b >>= 1
    return result


def _gf_pow(value, exponent):
    result = np.uint8(1)
    base = np.uint8(value)
    while exponent:
        if exponent & 1:
            result = _gf_mul(result, base).item()
        base = _gf_mul(base, base).item()
        exponent >>= 1
    return np.uint8(result)


def _gf_inv(value):
    value = int(value)
    if value == 0:
        raise ValueError("zero has no multiplicative inverse in GF(2^8)")
    return _gf_pow(value, 254)


def generate_shares(secret_image, k=2, n=2, seed=None, *, coefficient_bytes=None):
    """Generate n image shares; any k shares reconstruct the secret.

    For backwards compatibility, the `(2,2)` case uses the original
    `share2 = secret XOR share1` construction. Other configurations use a
    degree `k-1` random polynomial independently at each image pixel over
    GF(2^8), with the secret as the constant term.
    """
    secret = _validate_secret(secret_image)
    k, n = _validate_threshold(k, n)
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, numbers.Integral)):
        raise ValueError("seed must be an integer or None")
    rng = np.random.default_rng(seed) if coefficient_bytes is None else None
    coefficients = None
    if coefficient_bytes is not None:
        coefficients = np.asarray(coefficient_bytes)
        expected = (1 if (k, n) == (2, 2) else k - 1) * secret.size
        if coefficients.dtype != np.uint8 or coefficients.size != expected:
            raise ValueError("coefficient_bytes must be uint8 material of the exact required length")
        coefficients = coefficients.reshape((1, *secret.shape) if (k, n) == (2, 2) else (k - 1, *secret.shape))
    if (k, n) == (2, 2):
        first_values = (rng.integers(0, 256, secret.shape, dtype=np.uint8)
                        if coefficients is None else coefficients[0])
        first = ImageShare(first_values.copy(), 1)
        return [first, ImageShare(np.bitwise_xor(secret, first), 2)]

    if coefficients is None:
        coefficients = rng.integers(0, 256, size=(k - 1, *secret.shape), dtype=np.uint8)
    shares = []
    for x in range(1, n + 1):
        value = secret.copy()
        power = np.uint8(x)
        for degree in range(1, k):
            value ^= _gf_mul(coefficients[degree - 1], power)
            power = _gf_mul(power, np.uint8(x)).item()
        shares.append(ImageShare(value, x))
    return shares


def _normalise_shares(shares):
    if isinstance(shares, np.ndarray) and shares.ndim == 3:
        return list(shares)
    try:
        values = list(shares)
    except TypeError as exc:
        raise ValueError("shares must be an iterable of image arrays") from exc
    if not values:
        raise ValueError("at least one share is required")
    return values


def reconstruct_from_shares(shares, k=2, n=2):
    """Reconstruct from at least k compatible shares using GF(2^8) Lagrange interpolation.

    The legacy call `reconstruct_from_shares(share1, share2)` remains valid
    and performs the original XOR pair reconstruction.
    """
    # Legacy two-array API.
    if isinstance(shares, np.ndarray) and isinstance(k, np.ndarray) and n == 2:
        first, second = np.asarray(shares), np.asarray(k)
        if first.shape != second.shape or first.ndim != 2 or first.dtype != np.uint8 or second.dtype != np.uint8:
            raise ValueError("shares must be matching two-dimensional uint8 arrays")
        return np.bitwise_xor(first, second)

    k, n = _validate_threshold(k, n)
    values = _normalise_shares(shares)
    if len(values) < k:
        raise ValueError(f"at least {k} shares are required for reconstruction")
    selected = values[:k]
    arrays = []
    indices = []
    for position, share in enumerate(selected, start=1):
        array = np.asarray(share)
        if array.ndim != 2 or array.dtype != np.uint8:
            raise ValueError("each share must be a two-dimensional uint8 array")
        index = getattr(share, "index", None) or position
        if not 1 <= int(index) <= n or int(index) in indices:
            raise ValueError("share indices must be unique values in the configured range")
        arrays.append(array)
        indices.append(int(index))
    shape = arrays[0].shape
    if any(array.shape != shape for array in arrays):
        raise ValueError("all shares must have identical shapes")
    if (k, n) == (2, 2):
        return np.bitwise_xor(arrays[0], arrays[1])

    secret = np.zeros(shape, dtype=np.uint8)
    for i, (array, index_i) in enumerate(zip(arrays, indices)):
        coefficient = np.uint8(1)
        for j, index_j in enumerate(indices):
            if i == j:
                continue
            numerator = np.uint8(index_j)
            denominator = np.uint8(index_j ^ index_i)
            coefficient = _gf_mul(coefficient, _gf_mul(numerator, _gf_inv(denominator))).item()
        secret ^= _gf_mul(array, coefficient)
    return secret
