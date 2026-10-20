"""Classical reversible image operations inspired by selected quantum gates.

These byte operations are classical analogues. They do not simulate amplitudes,
superposition, or physical quantum hardware.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class QuantumInspiredState:
    """Compatibility wrapper for transformed grayscale pixel values only."""

    values: np.ndarray

    def __post_init__(self):
        self.values = _validate_quantum_image(self.values)

    def __array__(self, dtype=None):
        return np.asarray(self.values, dtype=dtype)


@dataclass(frozen=True)
class QuantumInspiredConfig:
    """Bit positions for reversible mixing, controlled XOR, and bit flip."""

    cnot_control: int = 0
    cnot_target: int = 1
    x_bit: int = 0

    def __post_init__(self):
        for name in ("cnot_control", "cnot_target", "x_bit"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or not 0 <= value <= 7:
                raise ValueError(f"{name} must be an integer in [0, 7]")
        if self.cnot_control == self.cnot_target:
            raise ValueError("cnot_control and cnot_target must differ")


def _validate_quantum_image(image):
    array = np.asarray(image)
    if array.ndim != 2 or array.dtype != np.uint8:
        raise ValueError("quantum-inspired transformations require a 2D uint8 grayscale image")
    return array


def _state_from(value):
    return value if isinstance(value, QuantumInspiredState) else QuantumInspiredState(value)


def _replace_bit(values, bit, new_bit):
    mask = np.uint8(1 << bit)
    return (values & np.uint8(255 ^ int(mask))) | (np.asarray(new_bit, dtype=np.uint8) * mask)


def reversible_bit_mixing_transform(image):
    """Apply the classical mapping ``(a,b) -> (a XOR b, a)`` to bit pairs.

    This is a reversible bit-mixing analogue inspired by a selected quantum
    transformation; it is not a Hadamard gate or an exact gate simulation.
    """
    state = _state_from(image)
    values = state.values.copy()
    for low in range(0, 8, 2):
        a = (values >> low) & 1
        b = (values >> (low + 1)) & 1
        values = _replace_bit(values, low, a ^ b)
        values = _replace_bit(values, low + 1, a)
    return QuantumInspiredState(values) if isinstance(image, QuantumInspiredState) else values


def inverse_reversible_bit_mixing_transform(image):
    """Invert the classical pair mapping with ``(u,v) -> (v, u XOR v)``."""
    state = _state_from(image)
    values = state.values.copy()
    for low in range(0, 8, 2):
        u = (values >> low) & 1
        v = (values >> (low + 1)) & 1
        values = _replace_bit(values, low, v)
        values = _replace_bit(values, low + 1, u ^ v)
    return QuantumInspiredState(values) if isinstance(image, QuantumInspiredState) else values


def cnot_inspired_transform(image, control=0, target=1):
    """Apply controlled XOR: target bit XORs control bit; control is unchanged."""
    config = QuantumInspiredConfig(cnot_control=control, cnot_target=target)
    state = _state_from(image)
    control_bits = (state.values >> config.cnot_control) & 1
    target_bits = ((state.values >> config.cnot_target) & 1) ^ control_bits
    values = _replace_bit(state.values, config.cnot_target, target_bits)
    return QuantumInspiredState(values) if isinstance(image, QuantumInspiredState) else values


def inverse_cnot_inspired_transform(image, control=0, target=1):
    """Controlled XOR is self-inverse."""
    return cnot_inspired_transform(image, control, target)


def x_inspired_bit_flip(image, bit=0):
    """Flip one selected classical pixel bit (computational-basis X action)."""
    config = QuantumInspiredConfig(x_bit=bit)
    state = _state_from(image)
    values = state.values ^ np.uint8(1 << config.x_bit)
    return QuantumInspiredState(values) if isinstance(image, QuantumInspiredState) else values


def inverse_x_inspired_bit_flip(image, bit=0):
    """A bit flip is self-inverse."""
    return x_inspired_bit_flip(image, bit)


def _normalize_rotation_inputs(values, control_bits, rotation_amounts):
    controls = np.asarray(control_bits)
    rotations = np.asarray(rotation_amounts)
    if controls.shape != values.shape or rotations.shape != values.shape:
        raise ValueError("control bits and rotation amounts must match the image shape")
    if not np.issubdtype(controls.dtype, np.integer) or not np.issubdtype(rotations.dtype, np.integer):
        raise ValueError("control bits and rotation amounts must be integer arrays")
    if not np.all(np.isin(controls, (0, 1))):
        raise ValueError("control bits must contain only 0 or 1")
    if not np.all(np.isin(rotations, np.arange(1, 8))):
        raise ValueError("rotation amounts must be integers in [1, 7]")
    return controls.astype(np.uint8), rotations.astype(np.uint8)


def z_inspired_reversible_bit_rotation(image, control_bits, rotation_amounts):
    """Conditionally rotate each grayscale byte left by its derived amount.

    The operation is classical and value-affecting; it does not represent
    quantum Z phase behavior. All controls/amounts are supplied by deterministic
    key-and-nonce-derived material and are never serialized.
    """
    values = _validate_quantum_image(image)
    controls, rotations = _normalize_rotation_inputs(values, control_bits, rotation_amounts)
    amounts = rotations.astype(np.uint16)
    wide = values.astype(np.uint16)
    rotated = ((wide << amounts) | (wide >> (8 - amounts))) & 0xFF
    result = np.where(controls == 1, rotated, wide).astype(np.uint8)
    return result


def inverse_z_inspired_reversible_bit_rotation(image, control_bits, rotation_amounts):
    """Undo conditional byte rotation by rotating selected values right."""
    values = _validate_quantum_image(image)
    controls, rotations = _normalize_rotation_inputs(values, control_bits, rotation_amounts)
    amounts = rotations.astype(np.uint16)
    wide = values.astype(np.uint16)
    rotated = ((wide >> amounts) | (wide << (8 - amounts))) & 0xFF
    return np.where(controls == 1, rotated, wide).astype(np.uint8)


def derive_z_rotation_parameters(key_material, rotation_material):
    """Derive one control and nonzero rotation per byte from existing key bytes.

    The low bit of k1 is the control. Rotation is ``(k2 % 7) + 1``; neither
    array is stored in artifacts, and both are regenerated from key parameters
    and the public nonce through the existing diffusion-material derivation.
    """
    controls = np.asarray(key_material)
    rotations = np.asarray(rotation_material)
    if controls.dtype != np.uint8 or rotations.dtype != np.uint8 or controls.shape != rotations.shape:
        raise ValueError("key material must be matching uint8 arrays")
    return controls & np.uint8(1), (rotations % np.uint8(7)) + np.uint8(1)


def quantum_inspired_transform(image, configuration=None, *, control_bits=None, rotation_amounts=None):
    """Apply reversible mixing, controlled XOR, bit flip, then byte rotation.

    Standalone calls default to active one-bit rotation for reproducible unit
    use. The encryption pipeline supplies control/rotation bytes derived from
    its existing key material and per-image nonce.
    """
    config = configuration if configuration is not None else QuantumInspiredConfig()
    if not isinstance(config, QuantumInspiredConfig):
        raise ValueError("configuration must be QuantumInspiredConfig")
    source = _validate_quantum_image(image)
    controls = np.ones(source.shape, dtype=np.uint8) if control_bits is None else control_bits
    rotations = np.ones(source.shape, dtype=np.uint8) if rotation_amounts is None else rotation_amounts
    values = reversible_bit_mixing_transform(source)
    values = cnot_inspired_transform(values, config.cnot_control, config.cnot_target)
    values = x_inspired_bit_flip(values, config.x_bit)
    return QuantumInspiredState(z_inspired_reversible_bit_rotation(values, controls, rotations))


def inverse_quantum_inspired_transform(transformed, configuration=None, *, control_bits=None, rotation_amounts=None):
    """Invert the classical operations in reverse order."""
    config = configuration if configuration is not None else QuantumInspiredConfig()
    if not isinstance(config, QuantumInspiredConfig):
        raise ValueError("configuration must be QuantumInspiredConfig")
    state = _state_from(transformed)
    controls = np.ones(state.values.shape, dtype=np.uint8) if control_bits is None else control_bits
    rotations = np.ones(state.values.shape, dtype=np.uint8) if rotation_amounts is None else rotation_amounts
    values = inverse_z_inspired_reversible_bit_rotation(state.values, controls, rotations)
    values = inverse_x_inspired_bit_flip(values, config.x_bit)
    values = inverse_cnot_inspired_transform(values, config.cnot_control, config.cnot_target)
    return inverse_reversible_bit_mixing_transform(values)


# Legacy prototype names retained as clearly marked compatibility aliases.
def hadamard_inspired_transform(image):
    """Legacy alias for reversible bit mixing; this does not apply a Hadamard gate."""
    return reversible_bit_mixing_transform(image)


def inverse_hadamard_inspired_transform(image):
    """Legacy inverse alias; this does not model a quantum Hadamard gate."""
    return inverse_reversible_bit_mixing_transform(image)


def _validate_arnold_input(image, iterations):
    array = np.asarray(image)
    if array.ndim != 2 or array.shape[0] != array.shape[1] or array.shape[0] == 0:
        raise ValueError("image must be a non-empty two-dimensional square array")
    if isinstance(iterations, bool) or not isinstance(iterations, (int, np.integer)) or iterations < 0:
        raise ValueError("iterations must be a non-negative integer")
    return array, int(iterations)


def _arnold_step(image):
    """Apply one forward step using x=column and y=row coordinates."""
    size = image.shape[0]
    result = np.empty_like(image)
    for y in range(size):
        for x in range(size):
            new_x = (x + y) % size
            new_y = (x + 2 * y) % size
            result[new_y, new_x] = image[y, x]
    return result


def _inverse_arnold_step(image):
    """Apply A^-1=[[2,-1],[-1,1]] modulo N to destination coordinates."""
    size = image.shape[0]
    result = np.empty_like(image)
    for y_prime in range(size):
        for x_prime in range(size):
            x = (2 * x_prime - y_prime) % size
            y = (-x_prime + y_prime) % size
            result[y, x] = image[y_prime, x_prime]
    return result


def arnold_scramble(image, iterations=1):
    """Permute an N×N image with the standard Arnold Cat Map."""
    result, count = _validate_arnold_input(image, iterations)
    for _ in range(count):
        result = _arnold_step(result)
    return result


def arnold_unscramble(image, iterations=1):
    """Reverse :func:`arnold_scramble` using the modular inverse map."""
    result, count = _validate_arnold_input(image, iterations)
    for _ in range(count):
        result = _inverse_arnold_step(result)
    return result


arnold_cat_map = arnold_scramble


def generate_random_key(shape, seed=None):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=shape, dtype=np.uint8)


def _validate(image, key):
    image_array, key_array = np.asarray(image), np.asarray(key)
    if image_array.ndim != 2 or key_array.shape != image_array.shape:
        raise ValueError("image and key must be two-dimensional arrays with equal shapes")
    if image_array.dtype != np.uint8 or key_array.dtype != np.uint8:
        raise ValueError("image and key must use dtype uint8")
    return image_array, key_array


def xor_diffusion(image, key):
    image_array, key_array = _validate(image, key)
    return np.bitwise_xor(image_array, key_array)


def encrypt(image, key=None, seed=None):
    image_array = np.asarray(image).astype(np.uint8, copy=False)
    actual_key = generate_random_key(image_array.shape, seed) if key is None else key
    return xor_diffusion(image_array, actual_key)
