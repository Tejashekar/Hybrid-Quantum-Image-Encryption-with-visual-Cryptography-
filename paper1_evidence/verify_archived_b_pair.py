"""Verify a retained Phase 6 v2 B all-zero/all-255 ciphertext pair.

This helper reads only the supplied JSON manifest and ciphertext arrays. It
never loads a key. A PASS verifies consistency of the supplied files and
metadata; it cannot prove that a hand-created manifest is contemporaneous.

Manifest format (all artifact metadata must have been retained with the run):
{
  "run_id": "...",
  "configuration": "B",
  "nonce_hex": "...",
  "artifacts": {
    "all_zero": {"path": "relative.npy", "run_id": "...",
                  "configuration": "B", "nonce_hex": "...",
                  "input": "all_zero", "shape": [128, 128],
                  "dtype": "uint8", "sha256": "..."},
    "all_255": { ... same fields, input="all_255" ... }
  }
}

Run with: python verify_archived_b_pair.py MANIFEST.json
Run its synthetic validator checks with: python verify_archived_b_pair.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


EXPECTED_SHAPE = (128, 128)
EXPECTED_DTYPE = "uint8"
INPUT_LABELS = ("all_zero", "all_255")


class EvidenceError(ValueError):
    """Raised when array or manifest evidence fails validation."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    run_id = manifest.get("run_id")
    nonce = manifest.get("nonce_hex")
    if not isinstance(run_id, str) or not run_id.strip():
        raise EvidenceError("manifest needs a nonempty run_id")
    if not isinstance(nonce, str) or not nonce.strip():
        raise EvidenceError("manifest needs a nonempty nonce_hex")
    if manifest.get("configuration") != "B":
        raise EvidenceError("manifest configuration must be B")

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise EvidenceError("manifest needs an artifacts object")

    validated = []
    for input_label in INPUT_LABELS:
        item = artifacts.get(input_label)
        if not isinstance(item, dict):
            raise EvidenceError(f"missing artifact metadata for {input_label}")
        checks = {
            "run_id": run_id,
            "configuration": "B",
            "nonce_hex": nonce,
            "input": input_label,
            "shape": list(EXPECTED_SHAPE),
            "dtype": EXPECTED_DTYPE,
        }
        for field, expected in checks.items():
            if item.get(field) != expected:
                raise EvidenceError(f"{input_label} metadata mismatch: {field}")
        rel_path = item.get("path")
        expected_hash = item.get("sha256")
        if not isinstance(rel_path, str) or not rel_path:
            raise EvidenceError(f"{input_label} needs a relative array path")
        if Path(rel_path).is_absolute():
            raise EvidenceError(f"{input_label} array path must be relative")
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise EvidenceError(f"{input_label} needs a 64-character SHA-256")
        try:
            int(expected_hash, 16)
        except ValueError as exc:
            raise EvidenceError(f"{input_label} SHA-256 is not hexadecimal") from exc
        validated.append(item)
    return validated


def verify_pair(manifest_path: Path) -> dict[str, Any]:
    """Validate manifest and arrays; return safe summary without nonce values."""
    import numpy as np

    manifest_path = manifest_path.resolve(strict=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise EvidenceError("manifest root must be a JSON object")
    artifacts = _validate_manifest(manifest)
    arrays = []
    artifact_summaries = []
    manifest_dir = manifest_path.parent

    for item in artifacts:
        path = (manifest_dir / item["path"]).resolve(strict=True)
        if not path.is_relative_to(manifest_dir):
            raise EvidenceError("array path resolves outside the manifest directory")
        actual_hash = sha256_file(path)
        if actual_hash.lower() != item["sha256"].lower():
            raise EvidenceError(f"SHA-256 mismatch for {item['input']} array")
        array = np.load(path, allow_pickle=False)
        if array.shape != EXPECTED_SHAPE:
            raise EvidenceError(f"{item['input']} array has unexpected shape")
        if array.dtype != np.dtype(EXPECTED_DTYPE):
            raise EvidenceError(f"{item['input']} array has unexpected dtype")
        arrays.append(array)
        artifact_summaries.append(
            {"input": item["input"], "path": item["path"], "sha256": actual_hash}
        )

    xor_values, xor_counts = np.unique(np.bitwise_xor(arrays[0], arrays[1]), return_counts=True)
    return {
        "status": "PAIR_VALIDATED",
        "run_id": manifest["run_id"],
        "configuration": "B",
        "nonce_match": True,
        "shape": list(EXPECTED_SHAPE),
        "dtype": EXPECTED_DTYPE,
        "arrays": artifact_summaries,
        "distinct_xor_values": int(xor_values.size),
        "xor_value_counts": {
            f"0x{int(value):02x}": int(count)
            for value, count in zip(xor_values, xor_counts)
        },
        "provenance_caveat": "File/metadata consistency does not authenticate when or by whom the manifest was created.",
    }


def self_test() -> None:
    """Exercise validation only with synthetic arrays in a temporary folder."""
    import numpy as np

    with tempfile.TemporaryDirectory(prefix="paper1_pair_validator_") as temp_dir:
        root = Path(temp_dir)
        left = np.zeros(EXPECTED_SHAPE, dtype=np.uint8)
        right = np.zeros(EXPECTED_SHAPE, dtype=np.uint8)
        right.flat[0] = 1
        np.save(root / "left.npy", left, allow_pickle=False)
        np.save(root / "right.npy", right, allow_pickle=False)
        manifest = {
            "run_id": "synthetic-self-test-only",
            "configuration": "B",
            "nonce_hex": "synthetic-self-test-only",
            "artifacts": {},
        }
        for label, filename in zip(INPUT_LABELS, ("left.npy", "right.npy")):
            path = root / filename
            manifest["artifacts"][label] = {
                "path": filename,
                "run_id": manifest["run_id"],
                "configuration": "B",
                "nonce_hex": manifest["nonce_hex"],
                "input": label,
                "shape": list(EXPECTED_SHAPE),
                "dtype": EXPECTED_DTYPE,
                "sha256": sha256_file(path),
            }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        result = verify_pair(manifest_path)
        assert result["status"] == "PAIR_VALIDATED"
        assert result["nonce_match"] is True
        assert result["distinct_xor_values"] == 2
        assert result["xor_value_counts"] == {"0x00": 16383, "0x01": 1}

        manifest["artifacts"]["all_255"]["nonce_hex"] = "mismatch"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        try:
            verify_pair(manifest_path)
        except EvidenceError:
            pass
        else:
            raise AssertionError("nonce mismatch was not rejected")

    print("self-test PASS (synthetic fixtures only; no Q-CRYPT result produced)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.self_test:
            self_test()
            return 0
        if args.manifest is None:
            parser.error("provide a manifest or use --self-test")
        result = verify_pair(args.manifest)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (EvidenceError, OSError, json.JSONDecodeError) as exc:
        print(f"verification failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
