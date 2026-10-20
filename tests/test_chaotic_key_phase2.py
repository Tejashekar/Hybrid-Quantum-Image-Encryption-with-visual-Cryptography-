import numpy as np

from experiments.diagnostics.chaotic_key_diagnostic import analyze_parameter_set
from src.chaotic_key import DEFAULT_TRANSIENT, chaotic_key_stream
from src.diffusion import derive_diffusion_material


def test_corrected_generator_defaults_to_at_least_1000_transient_iterations():
    assert DEFAULT_TRANSIENT >= 1000


def test_corrected_generator_is_deterministic_and_returns_exact_uint8_length():
    parameters = dict(x0=0.37, r=3.91, transient=1000, seed=9281)
    first = chaotic_key_stream(4097, **parameters)
    second = chaotic_key_stream(4097, **parameters)
    assert first.dtype == np.uint8
    assert first.shape == (4097,)
    assert np.array_equal(first, second)


def test_nonce_changes_material_derived_from_corrected_generator():
    parameters = dict(shape=(32, 32), secret_key=bytes(range(32)), x0=0.37, r=3.91,
                      transient=1000, seed=9281, configuration="D")
    first = derive_diffusion_material(nonce=b"A" * 16, **parameters)
    second = derive_diffusion_material(nonce=b"B" * 16, **parameters)
    assert any(
        not np.array_equal(left, right) if isinstance(left, np.ndarray) else left != right
        for left, right in zip(first, second)
    )


def test_statistical_diagnostic_calculates_distribution_metrics():
    result = analyze_parameter_set(
        {"name": "test", "x0": 0.5, "r": 3.99, "transient": 1000, "seed": None},
        length=4096,
    )
    assert result["sequence_length"] == 4096
    assert len(result["histogram_counts_0_to_255"]) == 256
    assert sum(result["histogram_counts_0_to_255"]) == 4096
    assert np.isfinite(result["chi_square_statistic"])
    assert 0.0 <= result["chi_square_p_value"] <= 1.0
    assert np.isfinite(result["serial_correlation_lag_1"])
    assert 0.0 <= result["one_bit_proportion"] <= 1.0
