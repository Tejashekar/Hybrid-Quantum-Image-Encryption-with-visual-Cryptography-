"""Empirical statistical assessment of Logistic-derived byte streams.

The reported chi-square and serial-correlation values are diagnostics, not
evidence of cryptographic security or proof of randomness.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.stats import chi2, chisquare

from src.chaotic_key import chaotic_key_stream


SEQUENCE_LENGTH = 100_000


def _chi_square_log10_p_value(statistic: float, degrees_of_freedom: int) -> float:
    """Return log10 survival probability without double-precision underflow."""
    shape = degrees_of_freedom / 2.0
    value = statistic / 2.0
    if value <= shape + 1.0:
        return float(chi2.logsf(statistic, degrees_of_freedom) / np.log(10.0))

    # Continued fraction for the regularized upper incomplete gamma Q(a, x).
    b = value + 1.0 - shape
    c = 1.0e300
    d = 1.0 / b
    fraction = d
    for iteration in range(1, 100_000):
        coefficient = -iteration * (iteration - shape)
        b += 2.0
        d = coefficient * d + b
        if abs(d) < 1.0e-300:
            d = 1.0e-300
        c = b + coefficient / c
        if abs(c) < 1.0e-300:
            c = 1.0e-300
        d = 1.0 / d
        delta = d * c
        fraction *= delta
        if abs(delta - 1.0) < 1.0e-14:
            break
    log_probability = -value + shape * np.log(value) - math.lgamma(shape) + np.log(fraction)
    return float(log_probability / np.log(10.0))


def diagnostic_parameter_sets(*, corrected: bool = False) -> list[dict]:
    api_seed = int.from_bytes(hashlib.sha256(b"q-crypt:D:2:2").digest()[:4], "big")
    values = [
        {"name": "module-default", "x0": 0.5, "r": 3.99, "transient": 100, "seed": None},
        {"name": "current-api-D", "x0": 0.37, "r": 3.91, "transient": 17, "seed": api_seed},
        {"name": "alternate-deterministic", "x0": 0.23, "r": 3.98, "transient": 50, "seed": 314159},
    ]
    if corrected:
        for config in values:
            config["transient"] = max(1000, config["transient"])
    return values


def analyze_parameter_set(parameters: dict, *, length: int = SEQUENCE_LENGTH) -> dict:
    stream = chaotic_key_stream(length, **{key: value for key, value in parameters.items() if key != "name"})
    counts = np.bincount(stream, minlength=256)
    statistic, p_value = chisquare(counts)
    log10_p_value = _chi_square_log10_p_value(float(statistic), 255)
    left = stream[:-1].astype(np.float64)
    right = stream[1:].astype(np.float64)
    correlation = float(np.corrcoef(left, right)[0, 1])
    return {
        **parameters,
        "sequence_length": int(stream.size),
        "nonce": None,
        "quantization": "current chaotic_key_stream byte extraction",
        "histogram_counts_0_to_255": counts.astype(int).tolist(),
        "mean": float(np.mean(stream)),
        "standard_deviation_population": float(np.std(stream)),
        "minimum": int(np.min(stream)),
        "maximum": int(np.max(stream)),
        "chi_square_statistic": float(statistic),
        "chi_square_p_value": float(p_value),
        "chi_square_log10_p_value": log10_p_value,
        "serial_correlation_lag_1": correlation,
        "one_bit_proportion": float(np.unpackbits(stream).mean()),
    }


def run_diagnostics(*, corrected: bool, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(f"refusing to overwrite diagnostic output: {output}")
    result = {
        "assessment": "empirical keystream randomness diagnostics; not a cryptographic security proof",
        "stage": "after" if corrected else "before",
        "sequence_length_per_parameter_set": SEQUENCE_LENGTH,
        "parameter_sets": [
            analyze_parameter_set(parameters)
            for parameters in diagnostic_parameter_sets(corrected=corrected)
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corrected", action="store_true", help="use >=1000 transient iterations")
    parser.add_argument("--output", required=True, type=Path, help="new JSON output path; existing files are not overwritten")
    args = parser.parse_args()
    result = run_diagnostics(corrected=args.corrected, output=args.output)
    for row in result["parameter_sets"]:
        print(json.dumps({key: row[key] for key in (
            "name", "x0", "r", "transient", "sequence_length", "seed",
            "chi_square_statistic", "chi_square_p_value", "serial_correlation_lag_1",
            "chi_square_log10_p_value", "one_bit_proportion", "mean",
            "standard_deviation_population", "minimum", "maximum",
        )}))
    print(f"diagnostic saved: {args.output}")


if __name__ == "__main__":
    main()
