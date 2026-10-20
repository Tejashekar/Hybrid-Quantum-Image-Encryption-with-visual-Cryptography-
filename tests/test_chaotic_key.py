import numpy as np
import pytest

from src.chaotic_key import chaotic_key_for_shape, chaotic_key_stream, logistic_sequence


def test_logistic_generation_is_deterministic():
    first = logistic_sequence(20, x0=0.31, r=3.91, transient=12, seed=8)
    second = logistic_sequence(20, x0=0.31, r=3.91, transient=12, seed=8)
    assert np.array_equal(first, second)


def test_different_initial_conditions_and_control_parameters_differ():
    assert not np.array_equal(logistic_sequence(20, x0=0.31), logistic_sequence(20, x0=0.32))
    assert not np.array_equal(logistic_sequence(20, r=3.91), logistic_sequence(20, r=3.99))


def test_key_range_and_requested_length():
    key = chaotic_key_stream(37, x0=0.23, r=3.99)
    assert key.dtype == np.uint8
    assert len(key) == 37
    assert int(key.min()) >= 0
    assert int(key.max()) <= 255


def test_2d_key_matches_shape():
    key = chaotic_key_for_shape((5, 7), seed=4)
    assert key.shape == (5, 7)
    assert key.dtype == np.uint8


@pytest.mark.parametrize(
    "kwargs",
    [
        {"x0": 0.0},
        {"x0": 1.0},
        {"x0": -0.1},
        {"r": 3.57},
        {"r": 4.1},
        {"length": 0},
        {"length": -2},
        {"transient": -1},
    ],
)
def test_invalid_parameters_raise_value_error(kwargs):
    defaults = {"length": 8}
    defaults.update(kwargs)
    with pytest.raises(ValueError):
        logistic_sequence(**defaults)


def test_invalid_shape_raises_value_error():
    with pytest.raises(ValueError):
        chaotic_key_for_shape((4,))
