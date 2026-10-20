"""Collect Paper 1 controlled evidence using the repository APIs.

The helper orchestrates project preprocessing, encryption/decryption, and
metrics. It uses only the fixed TEST key bytes(range(32)) and TEST nonce
bytes(16) for cryptographic runs. No key bytes are printed or saved.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import app
from experiments.dataset_manifest import unique_dataset_records
from src.diffusion import derive_diffusion_scalar
from src.metrics import entropy, neighboring_correlations, npcr, uaci
from src.pipeline import decrypt_image
from src.preprocessing import preprocess
from src.visual_cryptography import _gf_mul


OUT = Path(__file__).resolve().parent
TEST_KEY = bytes(range(32))
TEST_NONCE = bytes(16)
TEST_DESCRIPTOR = "TEST key bytes(range(32)); TEST nonce bytes(16)"


def csv_write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def encode_png(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(path), array):
        raise OSError(f"Unable to write {path}")


def read_images() -> list[tuple[str, np.ndarray]]:
    rows = []
    for path in sorted((ROOT / "experiments/real-input-7").iterdir(), key=lambda p: p.name.casefold()):
        if not path.is_file():
            continue
        decoded = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        if decoded is None:
            raise ValueError(f"Could not decode dataset image {path.name}")
        rows.append((path.name, preprocess(decoded, size=(128, 128))))
    return rows


def unique_preprocessed(images: list[tuple[str, np.ndarray]]):
    groups: dict[bytes, list[tuple[str, np.ndarray]]] = {}
    for name, array in images:
        digest = hashlib.sha256(array.tobytes(order="C")).digest()
        groups.setdefault(digest, []).append((name, array))
    ordered = sorted(groups.values(), key=lambda group: group[0][0].casefold())
    return [(f"image-{index:03d}", group[0][0], group[0][1], [item[0] for item in group])
            for index, group in enumerate(ordered, 1)]


def make_cipher(plain: np.ndarray, label: str):
    config = app._api_config(label)
    artifact = app._api_direct_encrypt_artifact(
        plain, label, config, TEST_KEY, nonce=TEST_NONCE
    )
    return config, artifact


def task_t3() -> list[dict]:
    rng = np.random.default_rng(20261017)
    rows = []
    for label in "ABCD":
        nonzero = 0
        for trial in range(200):
            p1, p2, p3 = [rng.integers(0, 256, size=(128, 128), dtype=np.uint8) for _ in range(3)]
            p4 = np.bitwise_xor(np.bitwise_xor(p1, p2), p3)
            ciphertexts = [make_cipher(image, label)[1].ciphertext for image in (p1, p2, p3, p4)]
            residue = np.bitwise_xor.reduce(np.stack(ciphertexts), axis=0)
            nonzero += int(bool(np.any(residue)))
        rows.append({"configuration": label, "trials": 200, "nonzero_residue_trials": nonzero,
                     "affine_over_GF2": nonzero == 0, "rng": "numpy.default_rng(20261017)",
                     "key_nonce": TEST_DESCRIPTOR})
        print(f"T3 {label}: {nonzero}/200 nonzero residues", flush=True)
    csv_write(OUT / "affine_test.csv", rows)
    return rows


def task_t4() -> list[dict]:
    zero = np.zeros((128, 128), dtype=np.uint8)
    full = np.full((128, 128), 255, dtype=np.uint8)
    rows = []
    for label in "ABCD":
        config, a = make_cipher(zero, label)
        _, b = make_cipher(full, label)
        diff = np.bitwise_xor(a.ciphertext, b.ciphertext)
        values, counts = np.unique(diff, return_counts=True)
        idx = int(np.argmax(counts))
        scalar = ""
        product = ""
        if label == "B":
            scalar = derive_diffusion_scalar(TEST_KEY, TEST_NONCE, configuration=label,
                                             context=config.to_dict())
            product = int(_gf_mul(np.uint8(scalar), np.uint8(255)))
        rows.append({"configuration": label, "distinct_xor_values": int(values.size),
                     "most_common_value_hex": f"0x{int(values[idx]):02x}",
                     "most_common_count": int(counts[idx]), "B_scalar_decimal": scalar,
                     "B_scalar_times_255_gf256_hex": f"0x{product:02x}" if product != "" else "",
                     "GF_polynomial": "0x11B", "key_nonce": TEST_DESCRIPTOR})
    csv_write(OUT / "constant_diff.csv", rows)
    return rows


def task_t5(unique):
    target = OUT / "plain"
    target.mkdir(exist_ok=True)
    per_image = []
    for image_id, representative, array, aliases in unique:
        np.save(target / f"{image_id}.npy", array, allow_pickle=False)
        encode_png(target / f"{image_id}.png", array)
        metrics = neighboring_correlations(array)
        per_image.append({"image_id": image_id, "source_filename": representative,
                          "source_filenames": ";".join(aliases), "entropy_bits": entropy(array),
                          "correlation_horizontal": metrics["horizontal"],
                          "correlation_vertical": metrics["vertical"],
                          "correlation_diagonal": metrics["diagonal"]})
    csv_write(target / "plaintext_metrics.csv", per_image)
    names = ["entropy_bits", "correlation_horizontal", "correlation_vertical", "correlation_diagonal"]
    aggregate = []
    for name in names:
        values = np.array([row[name] for row in per_image], dtype=float)
        aggregate.append({"metric": name, "mean_over_unique_contents": float(values.mean()),
                          "sample_sd_ddof_1": float(values.std(ddof=1)), "n_unique": len(values)})
    csv_write(target / "plaintext_summary.csv", aggregate)
    (target / "README.md").write_text(
        "Preprocessed arrays use `src.preprocessing.preprocess`; deduplicated by SHA-256 of the preprocessed array bytes. "
        "No cryptographic key is used for plaintext statistics. Metrics use `src.metrics`; correlations use all adjacent pairs.\n",
        encoding="utf-8")
    return per_image, aggregate


def task_t6(image_id: str, plain: np.ndarray):
    target = OUT / "fig4"
    target.mkdir(exist_ok=True)
    summary = []
    for label in "ABCD":
        config, artifact = make_cipher(plain, label)
        recovered = decrypt_image(artifact, config.encryption_config(), TEST_KEY)
        if not np.array_equal(recovered, plain):
            raise AssertionError(f"{label}: ciphertext round-trip failed")
        cipher = artifact.ciphertext
        np.save(target / f"{image_id}_{label}.npy", cipher, allow_pickle=False)
        encode_png(target / f"{image_id}_{label}.png", cipher)
        counts = np.bincount(cipher.ravel(), minlength=256)
        csv_write(target / f"{image_id}_{label}_histogram.csv", [
            {"gray_level": i, "count": int(counts[i]), "configuration": label,
             "key_nonce": TEST_DESCRIPTOR} for i in range(256)])
        summary.append({"image_id": image_id, "configuration": label, "round_trip_exact": True,
                        "ciphertext_entropy_bits": entropy(cipher), "key_nonce": TEST_DESCRIPTOR})
    csv_write(target / "round_trip_summary.csv", summary)
    (target / "README.md").write_text(
        f"Figure 4 arrays are regenerated from {image_id} using the fixed {TEST_DESCRIPTOR}. "
        "They do not use the archived experiment key. Encrypt/decrypt use the project pipeline; histograms have 256 bins.\n",
        encoding="utf-8")
    return summary


def task_t7():
    zero = np.zeros((128, 128), dtype=np.uint8)
    full = np.full((128, 128), 255, dtype=np.uint8)
    rows = []
    for label in "ABCD":
        cipher = {}
        for name, plain in (("all_zero", zero), ("all_255", full)):
            _, artifact = make_cipher(plain, label)
            cipher[name] = artifact.ciphertext
            rows.append({"configuration": label, "plaintext": name,
                         "ciphertext_entropy_bits": entropy(artifact.ciphertext),
                         "npcr_vs_other_constant": "", "uaci_vs_other_constant": "",
                         "key_nonce": TEST_DESCRIPTOR})
        row0, row1 = rows[-2], rows[-1]
        row0["npcr_vs_other_constant"] = npcr(cipher["all_zero"], cipher["all_255"])
        row1["npcr_vs_other_constant"] = row0["npcr_vs_other_constant"]
        row0["uaci_vs_other_constant"] = uaci(cipher["all_zero"], cipher["all_255"])
        row1["uaci_vs_other_constant"] = row0["uaci_vs_other_constant"]
    csv_write(OUT / "structured_inputs.csv", rows)
    return rows


def task_t9():
    archive = ROOT / "experiments/results/phase6-security-v2"
    z_one_sided = 1.6448536269514722
    z_two_sided = 1.959963984540054
    n = 128 * 128
    p = 1.0 / 256.0
    npcr_critical = (1.0 - p - z_one_sided * np.sqrt(p * (1.0 - p) / n)) * 100.0
    # E[|X-Y|]/255 for independent uniform bytes, simplified exactly to 257/768.
    uaci_mean = 257.0 / 768.0
    mean_abs_sq = (256.0**2 - 1.0) / (6.0 * 255.0**2)
    uaci_sd = np.sqrt(mean_abs_sq - uaci_mean**2)
    uaci_low = (uaci_mean - z_two_sided * uaci_sd / np.sqrt(n)) * 100.0
    uaci_high = (uaci_mean + z_two_sided * uaci_sd / np.sqrt(n)) * 100.0
    published_n = 256 * 256
    published_npcr = (1.0 - p - z_one_sided * np.sqrt(p * (1.0 - p) / published_n)) * 100.0
    published_uaci_low = (uaci_mean - z_two_sided * uaci_sd / np.sqrt(published_n)) * 100.0
    published_uaci_high = (uaci_mean + z_two_sided * uaci_sd / np.sqrt(published_n)) * 100.0
    (OUT / "wu_threshold_validation.md").write_text(
        "# Wu critical-value formula check\n\n"
        "Computed using the implementation in `collect_controlled.py`; NPCR uses the one-sided 5% normal quantile "
        "and UACI uses the two-sided 95% interval.\n\n"
        f"- N=65,536: NPCR {published_npcr:.4f}% (expected 99.5693%); UACI [{published_uaci_low:.4f}, "
        f"{published_uaci_high:.4f}]% (expected [33.2824, 33.6447]).\n"
        f"- N=16,384: NPCR {npcr_critical:.4f}% (expected 99.5292%); UACI [{uaci_low:.4f}, "
        f"{uaci_high:.4f}]% (expected [33.1012, 33.8259]).\n",
        encoding="utf-8")

    def read_rows(name):
        with (archive / name).open(newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))

    groups = {"key_flip": read_rows("key_sensitivity.csv"),
              "alternate_nonce": [r for r in read_rows("nonce_sensitivity.csv") if r["nonce_applicable"] == "True"],
              "plaintext_delta": read_rows("differential_analysis.csv")}
    rows = []
    for label in "ABCD":
        for kind, source in groups.items():
            selected = [r for r in source if r["configuration"] == label]
            if kind == "alternate_nonce":
                metrics = [(float(r["different_nonce_npcr"]), float(r["different_nonce_uaci"])) for r in selected]
            else:
                metrics = [(float(r["npcr"]), float(r["uaci"])) for r in selected]
            passed = sum(npv >= npcr_critical and uaci_low <= uv <= uaci_high for npv, uv in metrics)
            rows.append({"configuration": label, "trial_type": kind, "trials": len(metrics),
                         "pass_both": passed, "npcr_critical_percent": npcr_critical,
                         "uaci_low_percent": uaci_low, "uaci_high_percent": uaci_high,
                         "npcr_z_one_sided": z_one_sided, "uaci_z_two_sided": z_two_sided,
                         "source": "archived phase6-security-v2 per-trial CSVs"})
    csv_write(OUT / "wu_pass_counts.csv", rows)
    return npcr_critical, uaci_low, uaci_high, rows


def main():
    images = read_images()
    unique = unique_preprocessed(images)
    (OUT / "plain").mkdir(exist_ok=True)
    (OUT / "plain" / "input_inventory.csv").write_text(
        "source_images,unique_preprocessed_contents\n" + f"{len(images)},{len(unique)}\n", encoding="utf-8")
    (OUT / "plain" / "README.md").write_text(
        "T5 plaintext preprocessing and metrics use repository implementations. "
        "Cryptographic tasks T3/T4/T6/T7/T9 use the fixed " + TEST_DESCRIPTOR + ".\n", encoding="utf-8")
    print(f"T5: {len(images)} files, {len(unique)} unique preprocessed arrays", flush=True)
    t3 = task_t3()
    t4 = task_t4()
    plain_rows, plain_summary = task_t5(unique)
    image001 = next((entry for entry in unique if entry[0] == "image-001"), None)
    # Anchor Figure 4 to the v2 manifest's image-001 representative filename.
    manifest_records = unique_dataset_records(ROOT / "experiments/real-input-7", target_size=128)
    manifest_names = [record["path"].name for record in manifest_records]
    wanted = manifest_names[0]
    image001 = next((entry for entry in unique if wanted in entry[3]), image001)
    t6 = task_t6(image001[0], image001[2])
    t7 = task_t7()
    thresholds = task_t9()
    print(json.dumps({"T3": t3, "T4": t4, "T5": plain_rows, "T5_summary": plain_summary,
                      "T6": t6, "T7": t7, "T9_thresholds": thresholds[:3],
                      "T9_counts": thresholds[3]}, indent=2,
                     default=lambda value: value.item() if isinstance(value, np.generic) else str(value)))


if __name__ == "__main__":
    main()
