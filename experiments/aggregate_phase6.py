"""Aggregate Phase 6 raw CSV measurements and generate a sourced report."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import numpy as np


CORE_METRICS = (
    "entropy", "correlation_horizontal", "correlation_vertical", "correlation_diagonal",
    "npcr_mean_over_5_plaintext_deltas", "uaci_mean_over_5_plaintext_deltas",
    "encryption_time_ms", "decryption_time_ms", "ciphertext_bytes_raw",
)


def _read_csv(path):
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _numeric(values):
    result = []
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if np.isfinite(number):
            result.append(number)
    return result


def summarize_numeric(rows, group_fields, value_fields):
    """Return grouped population mean/std/min/max summaries from raw rows."""
    groups = {}
    for row in rows:
        key = tuple(row.get(field, "") for field in group_fields)
        groups.setdefault(key, []).append(row)
    summaries = []
    for key, group in sorted(groups.items(), key=lambda item: tuple(str(x) for x in item[0])):
        group_key = dict(zip(group_fields, key))
        for field in value_fields:
            values = _numeric(row.get(field) for row in group)
            if not values:
                continue
            array = np.asarray(values, dtype=np.float64)
            summaries.append({
                **group_key, "metric": field, "n": len(values),
                "mean": float(array.mean()), "std_population": float(array.std(ddof=0)),
                "minimum": float(array.min()), "maximum": float(array.max()),
            })
    return summaries


def _write_csv(path, rows):
    columns = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _markdown_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    return "\n".join(lines)


def _fmt(value):
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if np.isinf(number):
        return "∞"
    return f"{number:.4f}"


def build_evaluation_report(results_dir, core_summary, differential_summary,
                            dense_summary, key_summary, nonce_summary, structured_summary,
                            performance_summary, threshold_summary):
    root = Path(results_dir)
    meta = json.loads((root / "run_metadata.json").read_text(encoding="utf-8"))
    keyspace = _read_csv(root / "key_space_analysis.csv")[0]
    keystream = _read_csv(root / "keystream_statistics.csv")
    core_metrics = {row["metric"]: row for row in core_summary}
    core_table = []
    for config_id in sorted({row["config_id"] for row in _read_csv(root / "core_metrics.csv")}):
        def cell(metric):
            row = next((item for item in core_summary if item.get("config_id") == config_id and item["metric"] == metric), None)
            return "N/A" if row is None else f"{_fmt(row['mean'])} ± {_fmt(row['std_population'])}"
        core_table.append({
            "Configuration": config_id,
            "Entropy": cell("entropy"),
            "H/V/D correlation": "/".join(cell(f"correlation_{axis}") for axis in ("horizontal", "vertical", "diagonal")),
            "NPCR*": cell("npcr_mean_over_5_plaintext_deltas"),
            "UACI*": cell("uaci_mean_over_5_plaintext_deltas"),
            "Encrypt ms": cell("encryption_time_ms"),
            "Decrypt ms": cell("decryption_time_ms"),
        })

    diff_lines = []
    for row in differential_summary:
        if row["metric"] == "npcr":
            uaci_row = next((item for item in differential_summary if item.get("config_id") == row.get("config_id") and item.get("xor_delta") == row.get("xor_delta") and item["metric"] == "uaci"), None)
            occupancy = next((item for item in differential_summary if item.get("config_id") == row.get("config_id") and item.get("xor_delta") == row.get("xor_delta") and item["metric"] == "xor_difference_occupancy_percent"), None)
            diff_lines.append({"Configuration": row.get("config_id"), "XOR delta": row.get("xor_delta"),
                               "NPCR mean ± SD": f"{_fmt(row['mean'])} ± {_fmt(row['std_population'])}",
                               "UACI mean ± SD": "N/A" if uaci_row is None else f"{_fmt(uaci_row['mean'])} ± {_fmt(uaci_row['std_population'])}",
                               "XOR occupancy mean ± SD": "N/A" if occupancy is None else f"{_fmt(occupancy['mean'])} ± {_fmt(occupancy['std_population'])}"})

    dense_lines = []
    for row in dense_summary:
        if row["metric"] == "output_xor_occupancy_percent":
            npcr_row = next((item for item in dense_summary if item.get("config_id") == row.get("config_id") and item.get("diffusion_input_xor_delta") == row.get("diffusion_input_xor_delta") and item["metric"] == "npcr"), None)
            dense_lines.append({
                "Configuration": row.get("config_id"),
                "Input XOR delta": row.get("diffusion_input_xor_delta"),
                "Output XOR occupancy mean +/- SD": f"{_fmt(row['mean'])} +/- {_fmt(row['std_population'])}",
                "Output NPCR mean +/- SD": "N/A" if npcr_row is None else f"{_fmt(npcr_row['mean'])} +/- {_fmt(npcr_row['std_population'])}",
            })

    key_lines = []
    for config_id in sorted({row.get("config_id") for row in key_summary}):
        npcr_row = next((r for r in key_summary if r.get("config_id") == config_id and r["metric"] == "npcr"), None)
        uaci_row = next((r for r in key_summary if r.get("config_id") == config_id and r["metric"] == "uaci"), None)
        occupancy = next((r for r in key_summary if r.get("config_id") == config_id and r["metric"] == "xor_difference_occupancy_percent"), None)
        if npcr_row:
            key_lines.append({"Configuration": config_id,
                              "NPCR mean ± SD": f"{_fmt(npcr_row['mean'])} ± {_fmt(npcr_row['std_population'])}",
                              "UACI mean ± SD": f"{_fmt(uaci_row['mean'])} ± {_fmt(uaci_row['std_population'])}",
                              "XOR occupancy": f"{_fmt(occupancy['mean'])} ± {_fmt(occupancy['std_population'])}"})

    stream_table = [{
        "Parameter set": row["parameter_set"], "x0": row["x0"], "r": row["r"],
        "transient": row["transient"], "seed": row["seed"],
        "chi-square": _fmt(row["chi_square_statistic"]), "p-value": _fmt(row["chi_square_p_value"]),
        "lag-1 corr": _fmt(row["lag1_correlation"]), "one-bit proportion": _fmt(row["one_bit_proportion"]),
    } for row in keystream]

    threshold_lines = []
    for config_id in sorted({row.get("config_id") for row in threshold_summary}):
        valid = next((r for r in threshold_summary if r.get("config_id") == config_id and r.get("test_kind") == "valid_subset"), None)
        insufficient = next((r for r in threshold_summary if r.get("config_id") == config_id and r.get("test_kind") == "insufficient_shares"), None)
        if valid:
            threshold_lines.append({"Threshold": config_id,
                                    "Subset reconstructions": f"{valid['successes']}/{valid['trials']}",
                                    "Insufficient-share rejections": "yes" if insufficient and insufficient["all_rejected"] else "no"})

    performance_lines = [{
        "Configuration": row.get("config_id") or row.get("configuration"),
        "Operation": row["operation"], "Mean ms": _fmt(row["mean"]), "SD ms": _fmt(row["std_population"]),
        "Min ms": _fmt(row["minimum"]), "Max ms": _fmt(row["maximum"]),
    } for row in performance_summary if row["operation"] in {"preprocessing", "encryption", "decryption", "share_generation", "reconstruction"}]

    return f"""# Phase 6 — Comprehensive security and experimental evaluation

## 1. Objective

Measure the current research implementation without changing cipher equations, preprocessing, or metric definitions. This evaluation is empirical and is not a security proof.

## 2. Dataset

The Phase-5 manifest supplies **{meta['unique_image_count']} unique decoded image contents** from seven filenames. Duplicate aliases are grouped; image files are not counted as independent samples.

## 3. Preprocessing

Version: `{meta['preprocessing_version']}`. The protocol uses a centered square crop, `INTER_AREA` resizing, grayscale `uint8`, and 128×128 output. Cropping and resizing lose source information; round-trip exactness is measured relative to this processed plaintext.

## 4. Experimental protocol

Configurations: A–D and E with (2,2), (2,3), (3,5), and (3,6). Timing repetitions: {meta['repetitions']}. Master seed: {meta['master_seed']}. The run uses an externally supplied 32-byte secret key (key identifier SHA-256: `{meta.get('experiment_key_id_sha256', 'not recorded')}`). Nonces are deterministic public 16-byte values for reproducibility and held fixed except in nonce comparisons. Each key-sensitivity trial flips exactly one controlled bit of the 256-bit key. Configuration parameters remain public reproducibility metadata.

Metric formulas are unchanged from `src/metrics.py`. Aggregates below are calculated by `experiments/aggregate_phase6.py` from the saved per-image/per-trial CSV rows. Standard deviation uses population `ddof=0`.

## 5. Core statistical results

Values are configuration means ± population standard deviations across raw rows; the raw file also contains per-image and per-repetition results. Entropy and correlations describe ciphertext statistics; they do not prove security. NPCR/UACI are averaged over the five tested plaintext XOR deltas per image.

{_markdown_table(['Configuration','Entropy','H/V/D correlation','NPCR*','UACI*','Encrypt ms','Decrypt ms'], core_table)}

## 6. Differential analysis

{_markdown_table(['Configuration','XOR delta','NPCR mean ± SD','UACI mean ± SD','XOR occupancy mean ± SD'], diff_lines)}

For a uint8 pair, `a XOR b != 0` and `a != b` are equivalent per element; therefore XOR-difference occupancy and NPCR have equal numeric values when computed on the same arrays. The dense diffusion's tested all-nonzero property is specifically a one-byte input-difference property under fixed material; it is not a general claim for arbitrary multi-byte differences or all security notions.

### Isolated dense diffusion single-byte check

The following rows change one byte at the dense diffusion input while holding its mask fixed. This is a construction-specific input property and is not a general security or avalanche claim.

{_markdown_table(['Configuration','Input XOR delta','Output XOR occupancy mean +/- SD','Output NPCR mean +/- SD'], dense_lines)}

## 7. Key sensitivity

Five one-bit perturbations at key bit positions 0, 63, 127, 191, and 255 were applied to the caller-supplied 256-bit key per image/configuration, holding plaintext, nonce, and configuration fixed. These are empirical measurements, not proof of a secure key schedule.

{_markdown_table(['Configuration','NPCR mean ± SD','UACI mean ± SD','XOR occupancy'], key_lines)}

## 8. Plaintext sensitivity

One preprocessed byte was XOR-modified by 1, 2, 127, 128, and 255 for each unique image and configuration, with identical key material and nonce. Per-image trials are in `plaintext_sensitivity.csv` and full propagation traces in `differential_analysis.csv`.

## 9. Nonce sensitivity

The same plaintext/key parameters with the same nonce were checked for deterministic equality; a separately derived nonce was then compared. All configurations use the public nonce in the KDF context; it is not secret key material. These measurements do not prove nonce uniqueness or cryptographic security.

## 10. Keystream statistical assessment

Assessment label: statistical assessment of the generated byte stream. Each parameter set uses 100,000 bytes.

{_markdown_table(['Parameter set','x0','r','transient','seed','chi-square','p-value','lag-1 corr','one-bit proportion'], stream_table)}

Chi-square, serial correlation, byte entropy, and bit proportion are statistical diagnostics only. They do not establish cryptographic pseudorandomness or NIST compliance.

## 11. Key-space analysis

The independent secret key has 2^256 theoretical values because it is exactly 32 bytes. The public nonce has 2^128 possible values and is not added to secret-key size. Logistic parameters, seeds, Arnold iteration count, and quantum-inspired configuration are separate public reproducibility domains. Finite-precision and equivalent parameter behaviors prevent treating their theoretical domains as additional secret entropy. Key length alone does not establish an effective 256-bit security level; practical security depends on the complete construction and implementation.

`{keyspace['security_note']}`

## 12. Structured plaintext analysis

All-zero, all-255, constant-128, horizontal/vertical gradient, checkerboard, and sparse single-pixel patterns were encrypted under B/C/D. Entropy, neighboring correlations, histogram, and comparisons against the all-zero ciphertext are recorded per structure in `structured_plaintext.csv`. These are structural robustness checks, not chosen-plaintext attack resistance tests.

## 13. Configuration ablation

The controlled A–E rows are available in `ablation_results.csv`; means/stds are represented in the core table and raw CSV. The comparison describes observed changes across configurations; it does not isolate causal effects beyond their defined component differences.

## 14. Threshold-sharing analysis

Threshold results are based on GF(2^8)-based secret sharing with XOR field addition. Every valid k-subset was reconstructed for each image and threshold; fewer-than-k attempts were expected to raise a threshold error. Exact success/rejection counts and share sizes are in `threshold_results.csv`. Storage ratios are relative to raw ciphertext bytes. Coefficient bytes are derived in the separate HKDF sharing domain; no information-theoretic secrecy claim is made.

{_markdown_table(['Threshold','Subset reconstructions','Insufficient-share rejections'], threshold_lines)}

## 15. Performance and resource analysis

Preprocessing, encryption, decryption, share-generation, and reconstruction timings are repeated and summarized below. Ciphertext/share raw and encoded byte counts are retained in raw result files. Peak memory is not available because the current project has no memory instrumentation; no throughput or memory claim is made.

{_markdown_table(['Configuration','Operation','Mean ms','SD ms','Min ms','Max ms'], performance_lines)}

## 16. Limitations

Only five independent real-image contents are available. Results are not representative of a broad image population. Timing depends on this machine and runtime conditions. The historical 56-row archive is preserved and predates corrected preprocessing. No full security proof, cryptographic key-space estimate, or external scheme comparison is claimed.

## 17. Threat-model interpretation

The repository does not accept an independently supplied secret key for the image cipher; derivation parameters and seeds are included in public configuration metadata, and the nonce is public. These results should be interpreted as research measurements of a reversible classical simulation, not evidence that the application provides secure encryption. Statistical metrics, sensitivity tests, and threshold reconstruction checks do not prove resistance to attacks.

## 18. Reproducibility information

Run raw evaluation: `python -m experiments.phase6_security --output-dir experiments/results/phase6-security-v2 --seed {meta['master_seed']}`. Aggregate: `python -m experiments.aggregate_phase6 --results-dir experiments/results/phase6-security-v2`. The exact dataset, nonce/key policy, preprocessing version, counts, and output schema are recorded in this directory's README and `run_metadata.json`. Existing result directories are never overwritten by the runner.
"""


def aggregate_results(results_dir, *, overwrite=False):
    root = Path(results_dir)
    aggregate_dir = root / "aggregates"
    report_path = Path("docs/research/PHASE6_SECURITY_EVALUATION.md")
    if aggregate_dir.exists() and not overwrite:
        raise FileExistsError(f"aggregate directory exists: {aggregate_dir}")
    if report_path.exists() and not overwrite:
        raise FileExistsError(f"evaluation report exists: {report_path}")
    aggregate_dir.mkdir(parents=True, exist_ok=True)
    core = _read_csv(root / "core_metrics.csv")
    differential = _read_csv(root / "differential_analysis.csv")
    key = _read_csv(root / "key_sensitivity.csv")
    nonce = _read_csv(root / "nonce_sensitivity.csv")
    structured = _read_csv(root / "structured_plaintext.csv")
    performance = _read_csv(root / "performance_results.csv")
    thresholds = _read_csv(root / "threshold_results.csv")

    core_summary = summarize_numeric(core, ["configuration", "config_id", "threshold_k", "threshold_n"], CORE_METRICS)
    per_image_summary = summarize_numeric(core, ["content_id", "configuration", "config_id", "threshold_k", "threshold_n"], CORE_METRICS)
    diff_summary = summarize_numeric(differential, ["configuration", "config_id", "xor_delta"], ["npcr", "uaci", "xor_difference_occupancy_percent", "numeric_inequality_percent"])
    dense = _read_csv(root / "dense_diffusion_property.csv")
    dense_summary = summarize_numeric(dense, ["configuration", "config_id", "diffusion_input_xor_delta"], ["npcr", "uaci", "xor_difference_occupancy_percent", "output_xor_occupancy_percent"])
    key_summary = summarize_numeric(key, ["configuration", "config_id", "secret_key_bit_index"], ["npcr", "uaci", "xor_difference_occupancy_percent"])
    key_summary_all_trials = summarize_numeric(key, ["configuration", "config_id"], ["npcr", "uaci", "xor_difference_occupancy_percent"])
    nonce_numeric = [row for row in nonce if row.get("nonce_applicable") == "True"]
    nonce_summary = summarize_numeric(nonce_numeric, ["configuration", "config_id"], ["different_nonce_npcr", "different_nonce_uaci", "different_nonce_xor_difference_occupancy_percent", "different_nonce_entropy_bits"])
    structured_summary = summarize_numeric(structured, ["configuration", "structure"], ["entropy", "correlation_horizontal", "correlation_vertical", "correlation_diagonal", "npcr_vs_all_zero_ciphertext", "uaci_vs_all_zero_ciphertext", "xor_occupancy_vs_all_zero_ciphertext"])
    performance_summary = summarize_numeric(performance, ["configuration", "config_id", "operation"], ["value_ms"])

    threshold_summary = []
    for config_id in sorted({row.get("config_id", "") for row in thresholds}):
        valid = [row for row in thresholds if row.get("config_id") == config_id and row.get("test_kind") == "valid_subset"]
        insufficient = [row for row in thresholds if row.get("config_id") == config_id and row.get("test_kind") == "insufficient_shares"]
        if valid:
            success = sum(row.get("exact_ciphertext_reconstruction") == "True" for row in valid)
            threshold_summary.append({"config_id": config_id, "test_kind": "valid_subset", "trials": len(valid), "successes": success, "success_rate": success / len(valid)})
        if insufficient:
            rejected = sum(row.get("reconstruction_rejected") == "True" for row in insufficient)
            threshold_summary.append({"config_id": config_id, "test_kind": "insufficient_shares", "trials": len(insufficient), "rejected": rejected, "all_rejected": rejected == len(insufficient)})

    family = []
    for family_name, rows in (("core", core_summary), ("per_image_configuration", per_image_summary),
                              ("differential", diff_summary), ("dense_diffusion_property", dense_summary), ("key_sensitivity", key_summary),
                              ("nonce_sensitivity", nonce_summary), ("structured", structured_summary),
                              ("performance", performance_summary)):
        family.extend({"family": family_name, **row} for row in rows)
    _write_csv(aggregate_dir / "configuration_summary.csv", core_summary)
    _write_csv(aggregate_dir / "per_image_configuration_summary.csv", per_image_summary)
    _write_csv(aggregate_dir / "differential_summary.csv", diff_summary)
    _write_csv(aggregate_dir / "dense_diffusion_property_summary.csv", dense_summary)
    _write_csv(aggregate_dir / "key_sensitivity_summary.csv", key_summary)
    _write_csv(aggregate_dir / "nonce_sensitivity_summary.csv", nonce_summary)
    _write_csv(aggregate_dir / "structured_plaintext_summary.csv", structured_summary)
    _write_csv(aggregate_dir / "performance_summary.csv", performance_summary)
    _write_csv(aggregate_dir / "threshold_summary.csv", threshold_summary)
    _write_csv(aggregate_dir / "family_summary.csv", family)
    payload = {
        "core": core_summary, "per_image_configuration": per_image_summary,
        "differential": diff_summary, "dense_diffusion_property": dense_summary, "key_sensitivity": key_summary,
        "nonce_sensitivity": nonce_summary, "structured_plaintext": structured_summary,
        "performance": performance_summary, "thresholds": threshold_summary,
    }
    (aggregate_dir / "summary.json").write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    report = build_evaluation_report(root, core_summary, diff_summary, dense_summary, key_summary_all_trials, nonce_summary,
                                     structured_summary, performance_summary, threshold_summary)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("experiments/results/phase6-security-v2"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    result = aggregate_results(args.results_dir, overwrite=args.overwrite)
    print(json.dumps({"families": list(result), "report": "docs/research/PHASE6_SECURITY_EVALUATION.md"}))


if __name__ == "__main__":
    main()
