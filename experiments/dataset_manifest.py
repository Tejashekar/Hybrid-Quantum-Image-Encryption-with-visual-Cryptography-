"""Decoded-content inventory and deterministic manifests for real-image runs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from src.preprocessing import preprocessing_parameters, preprocess


def decode_image_record(path, target_size=128):
    path = Path(path)
    decoded = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if decoded is None:
        raise ValueError(f"image could not be decoded: {path.name}")
    with Image.open(path) as source:
        image_format = source.format or path.suffix.lstrip(".").upper()
        source_mode = source.mode
    height, width = decoded.shape[:2]
    channels = 1 if decoded.ndim == 2 else int(decoded.shape[2])
    digest = hashlib.sha256()
    digest.update(decoded.dtype.str.encode("ascii"))
    digest.update(repr(tuple(decoded.shape)).encode("ascii"))
    digest.update(decoded.tobytes(order="C"))
    content_hash = digest.hexdigest()
    output = preprocess(decoded, size=(target_size, target_size))
    return {
        "path": path,
        "decoded": decoded,
        "content_hash": content_hash,
        "file_format": image_format,
        "source_mode": source_mode,
        "original_width": int(width),
        "original_height": int(height),
        "original_channels": channels,
        "processed": output,
    }


def unique_dataset_records(image_dir, target_size=128):
    """Decode a directory and return one record per exact decoded pixel hash."""
    root = Path(image_dir)
    if not root.is_dir():
        raise ValueError(f"image directory does not exist: {root}")
    paths = sorted((path for path in root.iterdir() if path.is_file()), key=lambda p: p.name.casefold())
    if not paths:
        raise ValueError(f"image directory contains no image files: {root}")
    grouped = {}
    for path in paths:
        record = decode_image_record(path, target_size)
        if record["content_hash"] not in grouped:
            grouped[record["content_hash"]] = {**record, "source_filenames": []}
        grouped[record["content_hash"]]["source_filenames"].append(path.name)
    return [grouped[key] for key in sorted(grouped, key=lambda k: grouped[k]["path"].name.casefold())]


def build_dataset_manifest(image_dir, target_size=128) -> dict:
    """Create a deterministic JSON-serializable dataset and preprocessing manifest."""
    root = Path(image_dir)
    paths = sorted((path for path in root.iterdir() if path.is_file()), key=lambda p: p.name.casefold())
    records = unique_dataset_records(root, target_size=target_size)
    params = preprocessing_parameters((target_size, target_size))
    samples = []
    for content_id, record in enumerate(records, start=1):
        samples.append({
            "content_id": f"image-{content_id:03d}",
            "decoded_content_sha256": record["content_hash"],
            "source_filename": record["path"].name,
            "source_filenames": record["source_filenames"],
            "file_format": record["file_format"],
            "source_mode": record["source_mode"],
            "original_width": record["original_width"],
            "original_height": record["original_height"],
            "original_channels": record["original_channels"],
            "preprocessing_method": params["method"],
            "preprocessing_version": params["version"],
            "target_size": params["target_size"],
            "interpolation": params["interpolation"],
            "resulting_dimensions": [target_size, target_size],
            "resulting_channels": 1,
            "resulting_dtype": "uint8",
        })
    duplicate_groups = [
        {"decoded_content_sha256": sample["decoded_content_sha256"],
         "source_filenames": sample["source_filenames"]}
        for sample in samples if len(sample["source_filenames"]) > 1
    ]
    return {
        "manifest_version": 1,
        "dataset_location": root.as_posix(),
        "image_file_count": len(paths),
        "unique_decoded_content_count": len(samples),
        "independent_sample_count": len(samples),
        "content_hash_method": "SHA-256 of OpenCV decoded uint8 dtype, shape, and C-order pixel bytes",
        "decoded_channel_convention": "OpenCV native grayscale/BGR/BGRA channel order",
        "preprocessing": params,
        "samples": samples,
        "duplicate_groups": duplicate_groups,
    }


def write_dataset_manifest(image_dir, output_path, target_size=128):
    """Write the deterministic manifest without overwriting an existing report."""
    destination = Path(output_path)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite dataset manifest: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest = build_dataset_manifest(image_dir, target_size=target_size)
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
