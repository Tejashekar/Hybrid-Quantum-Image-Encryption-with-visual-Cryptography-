import numpy as np
import pytest

from src.quantum_encryption import arnold_scramble, arnold_unscramble


@pytest.mark.parametrize("size", [4, 8, 16])
@pytest.mark.parametrize("iterations", [0, 1, 2, 5, 11])
def test_arnold_round_trip(size, iterations):
    image = np.arange(size * size, dtype=np.uint8).reshape(size, size)
    scrambled = arnold_scramble(image, iterations)
    recovered = arnold_unscramble(scrambled, iterations)
    assert np.array_equal(recovered, image)


def test_random_image_round_trip_and_preservation():
    rng = np.random.default_rng(42)
    image = rng.integers(0, 256, size=(16, 16), dtype=np.uint8)
    scrambled = arnold_scramble(image, iterations=7)
    assert scrambled.shape == image.shape
    assert scrambled.dtype == image.dtype
    assert np.array_equal(np.sort(scrambled.ravel()), np.sort(image.ravel()))
    assert np.array_equal(arnold_unscramble(scrambled, 7), image)


def test_scrambling_changes_nonsymmetric_pixel_positions():
    image = np.zeros((8, 8), dtype=np.uint8)
    image[1, 2] = 255
    scrambled = arnold_scramble(image, 1)
    assert not np.array_equal(scrambled, image)
    assert scrambled[4, 3] == 255


@pytest.mark.parametrize(
    "image, iterations",
    [
        (np.zeros((4, 5), dtype=np.uint8), 1),
        (np.zeros((4, 4, 1), dtype=np.uint8), 1),
        (np.zeros((4, 4), dtype=np.uint8), -1),
        (np.zeros((4, 4), dtype=np.uint8), 1.5),
    ],
)
def test_invalid_inputs_raise_value_error(image, iterations):
    with pytest.raises(ValueError):
        arnold_scramble(image, iterations)


def test_zero_iterations_preserves_object_values_and_dtype():
    image = np.arange(16, dtype=np.int16).reshape(4, 4)
    result = arnold_scramble(image, 0)
    assert np.array_equal(result, image)
    assert result.dtype == image.dtype
