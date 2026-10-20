"""Run Phase 6 empirical evaluation without modifying cipher or metric code."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import time

import cv2
import numpy as np
from scipy.stats import chisquare

import app as flask_app
from experiments.dataset_manifest import unique_dataset_records
from src.chaotic_key import chaotic_key_for_shape, chaotic_key_stream
from src.diffusion import (
    dense_gf256_diffusion,
    derive_chaotic_xor_key,
    derive_diffusion_material,
    derive_diffusion_scalar,
    inverse_dense_gf256_diffusion,
)
from src.key_derivation import artifact_auth_tag, derive_share_coefficients, validate_secret_key
from src.metrics import (
    calculate_image_quality_metrics,
    calculate_security_metrics,
    calculate_storage_metrics,
    entropy,
    neighboring_correlations,
    npcr,
    psnr,
    ssim,
    uaci,
)
from src.preprocessing import PREPROCESSING_VERSION, preprocess
from src.quantum_encryption import (
    arnold_scramble,
    derive_z_rotation_parameters,
    generate_random_key,
    quantum_inspired_transform,
    xor_diffusion,
)
from src.visual_cryptography import generate_shares, reconstruct_from_shares
from experiments.key_material import experiment_key_id, load_experiment_key


DEFAULT_OUTPUT = Path("experiments/results/phase6-security-v2")
DATASET_DIR = Path("experiments/real-input-7")
TARGET_SIZE = 128
REPETITIONS = 5
PLAINTEXT_DELTAS = (1, 2, 127, 128, 255)
KEY_BIT_POSITIONS = (0, 63, 127, 191, 255)
CONFIGURATIONS = [(label, None, None) for label in "ABCD"] + [
    ("E", 2, 2), ("E", 2, 3), ("E", 3, 5), ("E", 3, 6),
]


def stable_nonce(master_seed: int, content_hash: str, config_id: str, purpose="base") -> bytes:
    payload = f"phase6:{master_seed}:{content_hash}:{config_id}:{purpose}".encode("utf-8")
    return hashlib.sha256(payload).digest()[:16]


def xor_occupancy_percent(first, second) -> float:
    left, right = np.asarray(first), np.asarray(second)
    if left.shape != right.shape or left.dtype != np.uint8 or right.dtype != np.uint8:
        raise ValueError("ciphertexts must be matching uint8 arrays")
    return float(np.count_nonzero(np.bitwise_xor(left, right)) / left.size * 100.0)


def compare_ciphertexts(first, second) -> dict:
    """Return existing NPCR/UACI plus explicitly named XOR occupancy."""
    return {
        "npcr": npcr(first, second),
        "uaci": uaci(first, second),
        "xor_difference_occupancy_percent": xor_occupancy_percent(first, second),
        "numeric_inequality_percent": float(np.count_nonzero(np.asarray(first) != np.asarray(second)) / np.asarray(first).size * 100.0),
    }


def plaintext_perturbations(image, pixel_index: int) -> list[dict]:
    source = np.asarray(image)
    if source.dtype != np.uint8 or source.ndim != 2 or not 0 <= pixel_index < source.size:
        raise ValueError("expected grayscale uint8 image and a valid flat pixel index")
    rows = []
    for delta in PLAINTEXT_DELTAS:
        changed = source.copy()
        changed.flat[pixel_index] ^= np.uint8(delta)
        rows.append({"delta": delta, "image": changed})
    return rows


def key_bit_perturbations(secret_key: bytes) -> list[dict]:
    """Flip one controlled bit in the caller-supplied 256-bit secret key."""
    source = validate_secret_key(secret_key)
    rows = []
    for trial, bit_index in enumerate(KEY_BIT_POSITIONS, start=1):
        changed = bytearray(source)
        byte_index = bit_index // 8
        bit_mask = 1 << (bit_index % 8)
        changed[byte_index] ^= bit_mask
        rows.append({"trial": trial, "bit_index": bit_index, "byte_index": byte_index,
                     "bit_mask": bit_mask, "secret_key": bytes(changed)})
    return rows


def structured_plaintexts(size=128) -> dict[str, np.ndarray]:
    zero = np.zeros((size, size), dtype=np.uint8)
    maximum = np.full((size, size), 255, dtype=np.uint8)
    constant = np.full((size, size), 128, dtype=np.uint8)
    horizontal = np.tile(np.linspace(0, 255, size, dtype=np.uint8), (size, 1))
    vertical = horizontal.T.copy()
    yy, xx = np.indices((size, size))
    checkerboard = (((xx + yy) & 1) * 255).astype(np.uint8)
    sparse = zero.copy()
    sparse[size // 2, size // 2] = 1
    return {
        "all_zero": zero,
        "all_255": maximum,
        "constant_128": constant,
        "horizontal_gradient": horizontal,
        "vertical_gradient": vertical,
        "checkerboard": checkerboard,
        "sparse_single_pixel": sparse,
    }


def encrypt_current(image, label, config, nonce, secret_key, *, include_trace=False):
    """Call the production API for normal runs; expose diffusion input for audits."""
    source = np.asarray(image)
    secret_key = validate_secret_key(secret_key)
    encrypted = flask_app._api_direct_encrypt_artifact(source, label, config, secret_key, nonce=nonce)
    ciphertext = encrypted.ciphertext
    pre_diffusion = None
    if label != "A":
        mask, _, _, _ = derive_diffusion_material(
            source.shape, secret_key=secret_key, nonce=nonce, x0=config.x0, r=config.r,
            transient=config.transient, seed=config.chaotic_seed, configuration=label,
            context=config.to_dict(),
        )
        scalar = derive_diffusion_scalar(secret_key, nonce, configuration=label, context=config.to_dict())
        pre_diffusion = inverse_dense_gf256_diffusion(ciphertext, mask, scalar)
    return (ciphertext, pre_diffusion) if include_trace else ciphertext


def decrypt_current(ciphertext, label, config, nonce, secret_key):
    tag = artifact_auth_tag(secret_key, nonce, label, config.to_dict(), ciphertext)
    return flask_app._api_direct_decrypt(ciphertext, label, config, secret_key,
                                         nonce=nonce, auth_tag=tag)


def _config_id(label, k, n):
    return label if label != "E" else f"E_{k}_of_{n}"


def _csv_value(value):
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, sort_keys=True)
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    return value


def _write_csv(path: Path, rows: list[dict]):
    columns = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def _mean_std(values):
    numbers = np.asarray(values, dtype=np.float64)
    return float(numbers.mean()), float(numbers.std(ddof=0)), float(numbers.min()), float(numbers.max())


def _seeded_key_params(config):
    return {
        "chaotic_seed": config.chaotic_seed,
        "x0": config.x0,
        "r": config.r,
        "transient": config.transient,
        "arnold_iterations": config.arnold_iterations,
        "quantum_cnot_control": config.quantum.cnot_control,
        "quantum_cnot_target": config.quantum.cnot_target,
        "quantum_x_bit": config.quantum.x_bit,
    }


def _keystream_rows(secret_key, master_seed):
    sets = [
        {"parameter_set": "default", "x0": 0.5, "r": 3.99, "transient": 1000, "seed": None},
        {"parameter_set": "api-D", "x0": 0.37, "r": 3.91, "transient": 1000,
         "seed": flask_app._api_config("D").chaotic_seed},
        {"parameter_set": "alternate", "x0": 0.23, "r": 3.98, "transient": 1200, "seed": 314159},
    ]
    rows = []
    length = 100_000
    for params in sets:
        nonce = stable_nonce(master_seed, "keystream-diagnostic", params["parameter_set"])
        stream = derive_chaotic_xor_key(
            (length,), secret_key=secret_key, nonce=nonce, x0=params["x0"],
            r=params["r"], transient=params["transient"], seed=params["seed"],
            configuration="B", context={"diagnostic_parameter_set": params["parameter_set"]},
        )
        counts = np.bincount(stream, minlength=256)
        statistic, p_value = chisquare(counts)
        rows.append({
            **params, "assessment": "statistical assessment of the generated byte stream",
            "nonce_hex": nonce.hex(),
            "sequence_length": length,
            "chi_square_statistic": float(statistic), "chi_square_p_value": float(p_value),
            "byte_entropy_bits": entropy(stream.reshape(250, 400)),
            "lag1_correlation": float(np.corrcoef(stream[:-1].astype(float), stream[1:].astype(float))[0, 1]),
            "lag2_correlation": float(np.corrcoef(stream[:-2].astype(float), stream[2:].astype(float))[0, 1]),
            "lag5_correlation": float(np.corrcoef(stream[:-5].astype(float), stream[5:].astype(float))[0, 1]),
            "one_bit_proportion": float(np.unpackbits(stream).mean()),
            "byte_mean": float(stream.mean()), "byte_std_population": float(stream.std()),
            "byte_min": int(stream.min()), "byte_max": int(stream.max()),
            "histogram_counts": counts.tolist(),
        })
    return rows


def _float_bits(value):
    return int.from_bytes(np.float64(value).tobytes(), "little")


def key_space_row():
    smallest_positive = np.nextafter(np.float64(0.0), np.float64(1.0))
    x0_values = _float_bits(1.0) - _float_bits(smallest_positive)
    first_r = np.nextafter(np.float64(3.57), np.float64(np.inf))
    r_values = _float_bits(4.0) - _float_bits(first_r) + 1
    return {
        "x0_accepted_range": "0 < x0 < 1; Python binary64 representable inputs",
        "x0_binary64_values": x0_values,
        "r_accepted_range": "3.57 < r <= 4.0; Python binary64 representable inputs",
        "r_binary64_values": r_values,
        "transient": "nonnegative integer; default 1000; configurable and public metadata",
        "seed": "integer or None; Logistic warmup uses seed modulo 1000 (at most 1000 warmup classes for fixed other inputs)",
        "arnold_iterations": "nonnegative integer, but finite image permutation order for fixed dimensions; public configuration",
        "nonce": "16 bytes / 128 bits; public and used for per-encryption separation, not a secret key",
        "quantum_parameters": "8*7 control-target choices and 8 X-bit choices; public configuration",
        "sharing_seed": "deterministic configuration value stored in ResearchPipelineConfig metadata",
        "theoretical_secret_key_space": "2^256 possibilities from a 32-byte caller-supplied secret key",
        "public_nonce_space": "2^128 possibilities; nonce is public and excluded from secret-key size",
        "configuration_parameter_space": "separate reproducibility/configuration domain; not secret-key entropy",
        "effective_security_level": "not inferred from key length; depends on the complete construction and implementation",
        "security_note": "The key length does not establish an effective 256-bit security level.",
    }


def _result_readme(master_seed, dataset_count, output, key_id):
    return f"""# Phase 6 security and experimental evaluation

Output version: `{output.name}`  
Dataset: `experiments/real-input-7`; {dataset_count} unique decoded image contents, identified by the Phase-5 manifest and SHA-256 over decoded dtype/shape/pixels.  
Preprocessing: `{PREPROCESSING_VERSION}`, center square crop, `INTER_AREA`, grayscale uint8, {TARGET_SIZE}×{TARGET_SIZE}.  
Configurations: A–D and E (2,2), (2,3), (3,5), (3,6).  
Repetitions: {REPETITIONS} timing repetitions per image/configuration.  
Master experiment seed: {master_seed}.  
Nonce policy: deterministic 16-byte SHA-256-derived public nonces for reproducibility; comparisons hold secret key and configuration fixed except in nonce sensitivity. All configurations use a nonce.  
Key policy: a fixed 32-byte experiment key is loaded externally; each sensitivity trial flips exactly one controlled key bit while nonce/configuration/plaintext stay fixed. The key is never written to outputs.  
Experimental key: one fixed 32-byte key loaded externally; only identifier `{key_id}` is recorded. Preserve that key separately to reproduce this run.  
Aggregation: run `python -m experiments.aggregate_phase6 --results-dir {output.as_posix()}` to derive summaries from raw CSV files.

Metric definitions are unchanged from `src/metrics.py`. NPCR is numeric ciphertext inequality percentage; XOR-difference occupancy is reported separately by name, though for uint8 pairs the per-byte nonzero-XOR predicate is mathematically equivalent to inequality. Empirical measurements are not cryptographic proofs. Dense GF(256) single-byte propagation is a mathematical property under fixed material and a one-byte difference at its input; it is not a universal avalanche or security claim.

Threshold sharing is GF(2^8)-based secret sharing with XOR field addition. Experiment coefficient bytes use the separate HKDF sharing domain; the GF(256) sharing equations are unchanged. No information-theoretic claim is made. No published-scheme values were available in the repository, so no external numerical comparisons are asserted. Peak memory was not measured because the project has no existing memory instrumentation. Existing historical results are preserved; this run writes only inside this versioned directory.
"""


def run_phase6(*, output_dir=DEFAULT_OUTPUT, image_dir=DATASET_DIR, master_seed=20261008,
               secret_key: bytes | None = None):
    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"Phase 6 output directory already exists; refusing to overwrite: {output}")
    secret_key = load_experiment_key() if secret_key is None else validate_secret_key(secret_key)
    key_id = experiment_key_id(secret_key)
    records = unique_dataset_records(image_dir, target_size=TARGET_SIZE)
    manifest_path = Path("experiments/manifests/phase5-center-crop-v1.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    content_samples = {sample["decoded_content_sha256"]: sample for sample in manifest["samples"]}
    output.mkdir(parents=True)

    core_rows, differential_rows, dense_property_rows, key_rows, nonce_rows = [], [], [], [], []
    structured_rows, threshold_rows, performance_rows, ablation_rows = [], [], [], []

    for image_record in records:
        image = image_record["processed"]
        content_hash = image_record["content_hash"]
        dataset_sample = content_samples[content_hash]
        content_id = dataset_sample["content_id"]
        preprocess_times = []
        for _ in range(REPETITIONS):
            started = time.perf_counter_ns()
            preprocess(image_record["decoded"], size=(TARGET_SIZE, TARGET_SIZE))
            preprocess_times.append((time.perf_counter_ns() - started) / 1_000_000.0)
        for repetition, elapsed in enumerate(preprocess_times, start=1):
            performance_rows.append({"content_id": content_id, "configuration": "ALL", "operation": "preprocessing", "repetition": repetition, "value_ms": elapsed})

        for label, k, n in CONFIGURATIONS:
            config_id = _config_id(label, k, n)
            config = flask_app._api_config(label, k or 2, n or 2)
            nonce = stable_nonce(master_seed, content_hash, config_id)
            ciphertext = encrypt_current(image, label, config, nonce, secret_key)
            decrypted = decrypt_current(ciphertext, label, config, nonce, secret_key)
            round_trip_exact = bool(np.array_equal(decrypted, image))
            quality = calculate_image_quality_metrics(image, decrypted)
            security = calculate_security_metrics(image, ciphertext)
            histogram = security["histogram"]
            encoded_cipher = cv2.imencode(".png", ciphertext)[1].size

            diff_index = int.from_bytes(bytes.fromhex(content_hash[:8]), "big") % image.size
            differential_for_config = []
            baseline_cipher, pre_diffusion = encrypt_current(image, label, config, nonce, secret_key, include_trace=True)
            mask = None
            if label != "A":
                mask = derive_diffusion_material(
                    image.shape, secret_key=secret_key, nonce=nonce, x0=config.x0, r=config.r,
                    transient=config.transient, seed=config.chaotic_seed,
                    configuration=label, context=config.to_dict(),
                )[0]
                scalar = derive_diffusion_scalar(secret_key, nonce, configuration=label, context=config.to_dict())
                property_index = (diff_index + 7919) % image.size
                for property_delta in PLAINTEXT_DELTAS:
                    property_input = pre_diffusion.copy()
                    property_input.flat[property_index] ^= np.uint8(property_delta)
                    property_output = dense_gf256_diffusion(property_input, mask, scalar)
                    property_comparison = compare_ciphertexts(baseline_cipher, property_output)
                    property_xor_count = int(np.count_nonzero(np.bitwise_xor(baseline_cipher, property_output)))
                    dense_property_rows.append({
                        "content_id": content_id, "configuration": label, "config_id": config_id,
                        "threshold_k": k, "threshold_n": n, "diffusion_input_index": property_index,
                        "diffusion_input_xor_delta": property_delta,
                        "input_difference_bytes": 1,
                        "output_nonzero_xor_bytes": property_xor_count,
                        "output_total_bytes": int(property_output.size),
                        "output_xor_occupancy_percent": property_xor_count / property_output.size * 100.0,
                        "all_output_xor_differences_nonzero": property_xor_count == property_output.size,
                        **property_comparison,
                    })
            for delta_record in plaintext_perturbations(image, diff_index):
                changed = delta_record["image"]
                changed_cipher, changed_pre = encrypt_current(changed, label, config, nonce, secret_key, include_trace=True)
                comparison = compare_ciphertexts(baseline_cipher, changed_cipher)
                dense_xor_count = None
                dense_total = None
                pre_diff_count = None
                if label != "A":
                    diff_outputs = np.bitwise_xor(baseline_cipher, changed_cipher)
                    dense_xor_count = int(np.count_nonzero(diff_outputs))
                    dense_total = int(diff_outputs.size)
                    pre_diff_count = int(np.count_nonzero(pre_diffusion != changed_pre))
                row = {
                    "content_id": content_id, "configuration": label, "config_id": config_id,
                    "threshold_k": k, "threshold_n": n, "pixel_index": diff_index,
                    "xor_delta": delta_record["delta"], "nonce_hex": nonce.hex(),
                    "preprocessing_version": PREPROCESSING_VERSION,
                    "pre_diffusion_changed_bytes": pre_diff_count,
                    "dense_output_nonzero_xor_bytes": dense_xor_count,
                    "dense_output_total_bytes": dense_total,
                    "dense_output_all_xor_nonzero": (dense_xor_count == dense_total) if dense_total else None,
                    "dense_single_input_byte_property_checked": pre_diff_count == 1 if pre_diff_count is not None else None,
                    "dense_single_input_byte_property_holds": (
                        dense_xor_count == dense_total if pre_diff_count == 1 else None
                    ),
                    **comparison,
                }
                differential_rows.append(row)
                differential_for_config.append(row)

            for perturbation in key_bit_perturbations(secret_key):
                changed_cipher = encrypt_current(
                    image, label, config, nonce, perturbation["secret_key"],
                )
                key_rows.append({
                    "content_id": content_id, "configuration": label, "config_id": config_id,
                    "threshold_k": k, "threshold_n": n,
                    "trial": perturbation["trial"], "secret_key_bit_index": perturbation["bit_index"],
                    "secret_key_byte_index": perturbation["byte_index"],
                    "secret_key_bit_mask": perturbation["bit_mask"], "nonce_hex": nonce.hex(),
                    "key_policy": "exactly one bit of the 256-bit secret key changed; plaintext, nonce, and configuration fixed",
                    **compare_ciphertexts(ciphertext, changed_cipher),
                })

            repeated = encrypt_current(image, label, config, nonce, secret_key)
            nonce_b = stable_nonce(master_seed, content_hash, config_id, purpose="alternate")
            alternate = encrypt_current(image, label, config, nonce_b, secret_key)
            nonce_rows.append({
                    "content_id": content_id, "configuration": label, "config_id": config_id,
                    "nonce_applicable": True, "nonce_a_hex": nonce.hex(), "nonce_b_hex": nonce_b.hex(),
                    "same_nonce_deterministic": bool(np.array_equal(ciphertext, repeated)),
                    "different_nonce_ciphertext_differs": bool(not np.array_equal(ciphertext, alternate)),
                    **{f"different_nonce_{key}": value for key, value in compare_ciphertexts(ciphertext, alternate).items()},
                    "different_nonce_entropy_bits": entropy(alternate),
                    "purpose": "nonce separates per-encryption derived diffusion material; nonce is public and not a secret key",
                })

            differential_means = {
                metric: float(np.mean([item[metric] for item in differential_for_config]))
                for metric in ("npcr", "uaci", "xor_difference_occupancy_percent")
            }
            e_shares = None
            encoded_shares = None
            if label == "E":
                gen_samples = []
                for _ in range(REPETITIONS):
                    started = time.perf_counter_ns()
                    coefficient_count = (1 if (k, n) == (2, 2) else k - 1) * ciphertext.size
                    coefficients = derive_share_coefficients(secret_key, nonce, config.to_dict(), coefficient_count)
                    e_shares = generate_shares(ciphertext, k, n, coefficient_bytes=coefficients)
                    gen_samples.append((time.perf_counter_ns() - started) / 1_000_000.0)
                encoded_shares = [int(cv2.imencode(".png", np.asarray(share))[1].size) for share in e_shares]
                for rep, elapsed in enumerate(gen_samples, start=1):
                    performance_rows.append({"content_id": content_id, "configuration": label, "config_id": config_id, "operation": "share_generation", "repetition": rep, "value_ms": elapsed})
                one_subset = e_shares[:k]
                recon_samples = []
                for rep in range(REPETITIONS):
                    started = time.perf_counter_ns()
                    reconstructed = reconstruct_from_shares(one_subset, k, n)
                    recon_samples.append((time.perf_counter_ns() - started) / 1_000_000.0)
                    if not np.array_equal(reconstructed, ciphertext):
                        raise AssertionError(f"threshold reconstruction failed for {config_id}/{content_id}")
                for rep, elapsed in enumerate(recon_samples, start=1):
                    performance_rows.append({"content_id": content_id, "configuration": label, "config_id": config_id, "operation": "reconstruction", "repetition": rep, "value_ms": elapsed})
                storage = calculate_storage_metrics(
                    image, ciphertext, e_shares,
                    encoded_cipher_bytes=encoded_cipher,
                    encoded_share_sizes=encoded_shares,
                )
                for subset in itertools.combinations(e_shares, k):
                    indices = [int(share.index) for share in subset]
                    reconstructed = reconstruct_from_shares(subset, k, n)
                    threshold_rows.append({
                        "content_id": content_id, "configuration": label, "config_id": config_id,
                        "threshold_k": k, "threshold_n": n,
                        "test_kind": "valid_subset", "selected_share_indices": indices,
                        "selected_share_count": len(subset),
                        "exact_ciphertext_reconstruction": bool(np.array_equal(reconstructed, ciphertext)),
                        "share_bytes_each_raw": int(ciphertext.nbytes),
                        "share_bytes_each_png": encoded_shares[indices[0] - 1],
                        "total_share_bytes_raw": int(sum(np.asarray(share).nbytes for share in e_shares)),
                        "ciphertext_bytes_raw": int(ciphertext.nbytes),
                        "storage_overhead_vs_ciphertext": float(sum(np.asarray(share).nbytes for share in e_shares) / ciphertext.nbytes),
                        "total_share_bytes_png": int(sum(encoded_shares)),
                        "reconstruction_rejected": False,
                    })
                try:
                    reconstruct_from_shares(e_shares[:max(0, k - 1)], k, n)
                    rejected = False
                    failure_detail = "returned_without_exception"
                except ValueError as exc:
                    rejected = True
                    failure_detail = str(exc)
                threshold_rows.append({
                    "content_id": content_id, "configuration": label, "config_id": config_id,
                    "threshold_k": k, "threshold_n": n,
                    "test_kind": "insufficient_shares", "selected_share_indices": list(range(1, k)),
                    "selected_share_count": max(0, k - 1), "exact_ciphertext_reconstruction": False,
                    "reconstruction_rejected": rejected, "rejection_detail": failure_detail,
                    "share_bytes_each_raw": int(ciphertext.nbytes),
                    "total_share_bytes_raw": int(sum(np.asarray(share).nbytes for share in e_shares)),
                    "ciphertext_bytes_raw": int(ciphertext.nbytes),
                })
            else:
                storage = {"cipher_bytes": int(ciphertext.nbytes)}

            for repetition in range(1, REPETITIONS + 1):
                started = time.perf_counter_ns()
                repeated_cipher = encrypt_current(image, label, config, nonce, secret_key)
                encrypt_ms = (time.perf_counter_ns() - started) / 1_000_000.0
                started = time.perf_counter_ns()
                repeated_plain = decrypt_current(repeated_cipher, label, config, nonce, secret_key)
                decrypt_ms = (time.perf_counter_ns() - started) / 1_000_000.0
                exact = bool(np.array_equal(repeated_plain, image))
                perf_fields = {
                    "encryption_time_ms": encrypt_ms,
                    "decryption_time_ms": decrypt_ms,
                    "preprocessing_ms": preprocess_times[repetition - 1],
                    "ciphertext_bytes_raw": int(ciphertext.nbytes),
                    "ciphertext_bytes_png": int(encoded_cipher),
                    "round_trip_exact": exact,
                }
                if label == "E":
                    perf_fields.update({
                        "share_generation_time_ms": gen_samples[repetition - 1],
                        "reconstruction_time_ms": recon_samples[repetition - 1],
                        "bytes_per_share_raw": int(ciphertext.nbytes),
                        "total_share_bytes_raw": int(sum(np.asarray(share).nbytes for share in e_shares)),
                        "total_share_bytes_png": int(sum(encoded_shares)),
                        "storage_overhead_vs_ciphertext": float(sum(np.asarray(share).nbytes for share in e_shares) / ciphertext.nbytes),
                    })
                performance_rows.extend([
                    {"content_id": content_id, "configuration": label, "config_id": config_id, "operation": "encryption", "repetition": repetition, "value_ms": encrypt_ms},
                    {"content_id": content_id, "configuration": label, "config_id": config_id, "operation": "decryption", "repetition": repetition, "value_ms": decrypt_ms},
                ])
                core = {
                    "content_id": content_id,
                    "source_filename": dataset_sample["source_filename"],
                    "source_filenames": dataset_sample["source_filenames"],
                    "source_content_sha256": content_hash,
                    "configuration": label, "config_id": config_id,
                    "threshold_k": k, "threshold_n": n,
                    "preprocessing_version": PREPROCESSING_VERSION,
                    "repetition": repetition, "nonce_hex": nonce.hex() if nonce else None,
                    "encryption_time_ms": encrypt_ms, "decryption_time_ms": decrypt_ms,
                    "entropy": security["entropy"],
                    "correlation_horizontal": security["correlation_horizontal"],
                    "correlation_vertical": security["correlation_vertical"],
                    "correlation_diagonal": security["correlation_diagonal"],
                    "histogram_counts": histogram["counts"].tolist(),
                    "histogram_distinct_bins": int(np.count_nonzero(histogram["counts"])),
                    "npcr_mean_over_5_plaintext_deltas": differential_means["npcr"],
                    "uaci_mean_over_5_plaintext_deltas": differential_means["uaci"],
                    "xor_occupancy_mean_over_5_plaintext_deltas": differential_means["xor_difference_occupancy_percent"],
                    "ciphertext_bytes_raw": int(ciphertext.nbytes),
                    "ciphertext_bytes_png": int(encoded_cipher),
                    "round_trip_exact": round_trip_exact and exact,
                    "mse": quality["mse"], "psnr": quality["psnr"], "ssim": quality["ssim"],
                    **_seeded_key_params(config),
                    **storage,
                }
                core_rows.append(core)
                ablation_rows.append({
                    "content_id": content_id, "configuration": label, "config_id": config_id,
                    "threshold_k": k, "threshold_n": n, "repetition": repetition,
                    "entropy": security["entropy"],
                    "correlation_horizontal": security["correlation_horizontal"],
                    "correlation_vertical": security["correlation_vertical"],
                    "correlation_diagonal": security["correlation_diagonal"],
                    "npcr_mean_over_deltas": differential_means["npcr"],
                    "uaci_mean_over_deltas": differential_means["uaci"],
                    "encryption_time_ms": encrypt_ms, "decryption_time_ms": decrypt_ms,
                    "ciphertext_bytes_raw": int(ciphertext.nbytes),
                    "share_count": n if label == "E" else 0,
                    "share_bytes_total_raw": storage.get("total_share_bytes", 0),
                    "round_trip_exact": round_trip_exact and exact,
                })

    structured_rows = _run_structured_tests(master_seed, secret_key)
    stream_rows = _keystream_rows(secret_key, master_seed)
    keyspace = key_space_row()

    rows_by_file = {
        "core_metrics.csv": core_rows,
        "differential_analysis.csv": differential_rows,
        "dense_diffusion_property.csv": dense_property_rows,
        "plaintext_sensitivity.csv": differential_rows,
        "key_sensitivity.csv": key_rows,
        "nonce_sensitivity.csv": nonce_rows,
        "keystream_statistics.csv": stream_rows,
        "key_space_analysis.csv": [keyspace],
        "structured_plaintext.csv": structured_rows,
        "ablation_results.csv": ablation_rows,
        "threshold_results.csv": threshold_rows,
        "performance_results.csv": performance_rows,
        "published_comparison_template.csv": [{
            "scheme": "", "source_citation": "", "dataset": "", "image_size": "",
            "metric": "", "reported_value": "", "metric_definition": "",
            "evaluation_type": "", "comparability_notes": "No comparison dataset found in repository; populate only from sourced publications.",
        }],
    }
    for filename, rows in rows_by_file.items():
        _write_csv(output / filename, rows)
    (output / "README.md").write_text(_result_readme(master_seed, len(records), output, key_id), encoding="utf-8")
    (output / "run_metadata.json").write_text(json.dumps({
        "version": output.name, "master_seed": master_seed,
        "unique_image_count": len(records), "content_ids": [content_samples[item["content_hash"]]["content_id"] for item in records],
        "configuration_ids": [_config_id(*spec) for spec in CONFIGURATIONS],
        "repetitions": REPETITIONS, "plaintext_deltas": PLAINTEXT_DELTAS,
        "key_bit_positions": KEY_BIT_POSITIONS, "experiment_key_id_sha256": key_id,
        "preprocessing_version": PREPROCESSING_VERSION,
        "nonce_policy": "deterministic 16-byte SHA-256 derivation; separate purpose namespace for alternate nonce",
        "secrets": "Secret key omitted; only SHA-256 key identifier recorded. Preserve experiment key outside tracked source.",
    }, indent=2), encoding="utf-8")
    return {"output_dir": output, "image_count": len(records), "core_rows": len(core_rows),
            "differential_rows": len(differential_rows), "key_rows": len(key_rows),
            "threshold_rows": len(threshold_rows)}


def _run_structured_tests(master_seed, secret_key):
    patterns = structured_plaintexts(TARGET_SIZE)
    rows = []
    for label in "BCD":
        config = flask_app._api_config(label)
        content_hash = hashlib.sha256(f"structured:{label}:{master_seed}".encode()).hexdigest()
        nonce = stable_nonce(master_seed, content_hash, label)
        zero_cipher = encrypt_current(patterns["all_zero"], label, config, nonce, secret_key)
        for name, image in patterns.items():
            ciphertext = encrypt_current(image, label, config, nonce, secret_key)
            stats = calculate_security_metrics(image, ciphertext)
            comparison = compare_ciphertexts(zero_cipher, ciphertext)
            rows.append({
                "configuration": label, "structure": name, "nonce_hex": nonce.hex(),
                "entropy": stats["entropy"],
                "correlation_horizontal": stats["correlation_horizontal"],
                "correlation_vertical": stats["correlation_vertical"],
                "correlation_diagonal": stats["correlation_diagonal"],
                "histogram_counts": stats["histogram"]["counts"].tolist(),
                "npcr_vs_all_zero_ciphertext": comparison["npcr"],
                "uaci_vs_all_zero_ciphertext": comparison["uaci"],
                "xor_occupancy_vs_all_zero_ciphertext": comparison["xor_difference_occupancy_percent"],
            })
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--image-dir", type=Path, default=DATASET_DIR)
    parser.add_argument("--seed", type=int, default=20261008)
    args = parser.parse_args()
    result = run_phase6(output_dir=args.output_dir, image_dir=args.image_dir, master_seed=args.seed)
    print(json.dumps({key: str(value) if isinstance(value, Path) else value for key, value in result.items()}))


if __name__ == "__main__":
    main()
