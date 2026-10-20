"""Deterministic Logistic Map key generation.

This module produces classical byte keys for the chaotic-key XOR baseline.
It does not claim cryptographic security; the sequence is a research
primitive whose behavior is controlled by its explicit parameters.
"""

from __future__ import annotations

import numbers

import numpy as np


DEFAULT_X0 = 0.5
DEFAULT_R = 3.99
DEFAULT_TRANSIENT = 1000


def _validate_parameters(x0: float, r: float, length: int, transient: int) -> None:
    if not isinstance(x0, numbers.Real) or not 0.0 < float(x0) < 1.0:
        raise ValueError("x0 must satisfy 0 < x0 < 1")
    if not isinstance(r, numbers.Real) or not 3.57 < float(r) <= 4.0:
        raise ValueError("r must satisfy 3.57 < r <= 4.0")
    if isinstance(length, bool) or not isinstance(length, numbers.Integral) or length <= 0:
        raise ValueError("length must be a positive integer")
    if isinstance(transient, bool) or not isinstance(transient, numbers.Integral) or transient < 0:
        raise ValueError("transient must be a non-negative integer")


def logistic_sequence(
    length: int,
    *,
    x0: float = DEFAULT_X0,
    r: float = DEFAULT_R,
    transient: int = DEFAULT_TRANSIENT,
    seed: int | None = None,
) -> np.ndarray:
    """Return ``length`` values from ``x[n+1] = r*x[n]*(1-x[n])``.

    ``transient`` iterations are discarded before collection. When ``seed``
    is supplied, it deterministically adds ``seed % 1000`` warm-up
    iterations; this gives the API a reproducible seed without introducing
    random floating-point values or changing the requested initial condition.
    """
    _validate_parameters(x0, r, length, transient)
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, numbers.Integral)):
        raise ValueError("seed must be an integer or None")

    state = float(x0)
    control = float(r)
    warmup = int(transient) + (int(seed) % 1000 if seed is not None else 0)
    for _ in range(warmup):
        state = control * state * (1.0 - state)

    sequence = np.empty(int(length), dtype=np.float64)
    for index in range(int(length)):
        state = control * state * (1.0 - state)
        sequence[index] = state
    return sequence


def chaotic_key_stream(
    length: int,
    *,
    x0: float = DEFAULT_X0,
    r: float = DEFAULT_R,
    transient: int = DEFAULT_TRANSIENT,
    seed: int | None = None,
) -> np.ndarray:
    """Extract uint8 bytes from bits 32–39 of a 40-bit fixed-point state."""
    sequence = logistic_sequence(length, x0=x0, r=r, transient=transient, seed=seed)
    # 0 <= state <= 1, so scaling by 2**40 is bounded and fits uint64.
    # Taking the low byte of this fixed-point integer avoids direct x*255
    # quantization while remaining deterministic in the existing float map.
    fixed_point = np.floor(sequence * (1 << 40)).astype(np.uint64)
    return (fixed_point & np.uint64(0xFF)).astype(np.uint8)


def chaotic_key_for_shape(
    shape: tuple[int, int],
    *,
    x0: float = DEFAULT_X0,
    r: float = DEFAULT_R,
    transient: int = DEFAULT_TRANSIENT,
    seed: int | None = None,
) -> np.ndarray:
    """Return a 2D uint8 chaotic key matching ``(height, width)``."""
    if len(shape) != 2 or any(isinstance(value, bool) or not isinstance(value, numbers.Integral) or value <= 0 for value in shape):
        raise ValueError("shape must contain two positive integer dimensions")
    return chaotic_key_stream(int(shape[0]) * int(shape[1]), x0=x0, r=r, transient=transient, seed=seed).reshape(shape)


# Descriptive aliases for callers that prefer the research terminology.
generate_chaotic_key = chaotic_key_stream
generate_chaotic_key_2d = chaotic_key_for_shape
