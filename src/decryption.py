"""Inverse operations for the Phase 1 classical XOR baseline."""
from __future__ import annotations
import numpy as np
from .quantum_encryption import xor_diffusion

def decrypt(encrypted_image: np.ndarray, key: np.ndarray) -> np.ndarray:
    return xor_diffusion(encrypted_image, key)
