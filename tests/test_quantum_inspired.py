import numpy as np
import pytest

from src.quantum_encryption import (
    QuantumInspiredConfig,
    cnot_inspired_transform,
    derive_z_rotation_parameters,
    inverse_cnot_inspired_transform,
    inverse_quantum_inspired_transform,
    inverse_reversible_bit_mixing_transform,
    inverse_x_inspired_bit_flip,
    inverse_z_inspired_reversible_bit_rotation,
    quantum_inspired_transform,
    reversible_bit_mixing_transform,
    x_inspired_bit_flip,
    z_inspired_reversible_bit_rotation,
)


def test_reversible_bit_mixing_round_trip():
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    mixed = reversible_bit_mixing_transform(image)
    assert np.array_equal(inverse_reversible_bit_mixing_transform(mixed), image)


def test_controlled_xor_round_trip():
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    transformed = cnot_inspired_transform(image, control=2, target=7)
    assert np.array_equal(inverse_cnot_inspired_transform(transformed, 2, 7), image)


def test_x_inspired_bit_flip_round_trip():
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    assert np.array_equal(inverse_x_inspired_bit_flip(x_inspired_bit_flip(image, 5), 5), image)


@pytest.mark.parametrize("rotation", range(1, 8))
def test_byte_rotation_round_trip_for_all_256_values(rotation):
    image = np.arange(256, dtype=np.uint8).reshape(16, 16)
    controls = np.ones(image.shape, dtype=np.uint8)
    rotations = np.full(image.shape, rotation, dtype=np.uint8)
    rotated = z_inspired_reversible_bit_rotation(image, controls, rotations)
    assert rotated.dtype == np.uint8
    assert np.array_equal(
        inverse_z_inspired_reversible_bit_rotation(rotated, controls, rotations), image
    )


def test_key_derived_byte_rotation_changes_values_and_inverts_exactly():
    image = np.array([[1, 2, 4, 8]], dtype=np.uint8)
    key_controls = np.ones(image.shape, dtype=np.uint8)
    rotation_material = np.zeros(image.shape, dtype=np.uint8)
    controls, rotations = derive_z_rotation_parameters(key_controls, rotation_material)
    changed = z_inspired_reversible_bit_rotation(image, controls, rotations)
    assert np.any(changed != image)
    assert np.array_equal(
        inverse_z_inspired_reversible_bit_rotation(changed, controls, rotations), image
    )


@pytest.mark.parametrize("size", [4, 8, 16, 128])
def test_combined_transform_round_trip_on_random_images(size):
    rng = np.random.default_rng(size)
    image = rng.integers(0, 256, size=(size, size), dtype=np.uint8)
    controls = rng.integers(0, 2, size=image.shape, dtype=np.uint8)
    rotations = rng.integers(1, 8, size=image.shape, dtype=np.uint8)
    config = QuantumInspiredConfig(cnot_control=2, cnot_target=6, x_bit=3)
    transformed = quantum_inspired_transform(
        image, config, control_bits=controls, rotation_amounts=rotations,
    )
    recovered = inverse_quantum_inspired_transform(
        transformed, config, control_bits=controls, rotation_amounts=rotations,
    )
    assert np.array_equal(recovered, image)
    assert recovered.shape == image.shape
    assert recovered.dtype == image.dtype


@pytest.mark.parametrize(
    "image",
    [np.zeros((4, 4), dtype=np.int16), np.zeros((4, 4, 1), dtype=np.uint8), np.zeros((4,), dtype=np.uint8)],
)
def test_invalid_image_input_is_rejected(image):
    with pytest.raises(ValueError):
        reversible_bit_mixing_transform(image)


def test_invalid_configuration_and_rotation_inputs_are_rejected():
    with pytest.raises(ValueError):
        QuantumInspiredConfig(cnot_control=1, cnot_target=1)
    with pytest.raises(ValueError):
        QuantumInspiredConfig(x_bit=8)
    with pytest.raises(ValueError):
        quantum_inspired_transform(np.zeros((4, 4), dtype=np.uint8), {})
    with pytest.raises(ValueError):
        z_inspired_reversible_bit_rotation(np.zeros((4, 4), dtype=np.uint8), 1, 1)
