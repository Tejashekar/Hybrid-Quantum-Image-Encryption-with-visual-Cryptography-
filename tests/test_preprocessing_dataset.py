import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from experiments.dataset_manifest import build_dataset_manifest, unique_dataset_records
from experiments.run_experiments import load_experiment_images, run_experiments
from src.preprocessing import PREPROCESSING_VERSION, preprocess, preprocessing_parameters


DATASET_DIR = Path("experiments/real-input-7")
TEST_EXPERIMENT_KEY = bytes(range(32))


def test_center_crop_is_applied_before_resize_for_landscape_portrait_and_square():
    landscape = np.tile(np.arange(80, dtype=np.uint8), (40, 1))
    landscape_crop = landscape[:, 20:60]
    assert np.array_equal(
        preprocess(landscape, size=16),
        cv2.resize(landscape_crop, (16, 16), interpolation=cv2.INTER_AREA),
    )

    portrait = np.tile(np.arange(80, dtype=np.uint8)[:, None], (1, 40))
    portrait_crop = portrait[20:60, :]
    assert np.array_equal(
        preprocess(portrait, size=16),
        cv2.resize(portrait_crop, (16, 16), interpolation=cv2.INTER_AREA),
    )

    square = np.arange(40 * 40, dtype=np.uint8).reshape(40, 40)
    assert np.array_equal(
        preprocess(square, size=16),
        cv2.resize(square, (16, 16), interpolation=cv2.INTER_AREA),
    )


def test_grayscale_rgb_and_already_128_inputs_are_deterministic_uint8_gray():
    rng = np.random.default_rng(1285)
    gray = rng.integers(0, 256, (35, 57), dtype=np.uint8)
    first = preprocess(gray)
    second = preprocess(gray.copy())
    assert first.shape == (128, 128) and first.dtype == np.uint8
    assert np.array_equal(first, second)

    bgr = rng.integers(0, 256, (49, 33, 3), dtype=np.uint8)
    side = 33
    top = (49 - side) // 2
    resized = cv2.resize(bgr[top:top + side], (128, 128), interpolation=cv2.INTER_AREA)
    expected = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    assert np.array_equal(preprocess(bgr), expected)
    assert preprocess(bgr).shape == (128, 128)

    already = rng.integers(0, 256, (128, 128), dtype=np.uint8)
    assert np.array_equal(preprocess(already), already)


def test_preprocessing_rejects_non_square_target_and_unsupported_channels():
    image = np.zeros((10, 20), dtype=np.uint8)
    with pytest.raises(ValueError, match="square"):
        preprocess(image, size=(128, 64))
    with pytest.raises(ValueError, match="BGR"):
        preprocess(np.zeros((10, 20, 2), dtype=np.uint8))


def test_manifest_reports_five_unique_decoded_contents_and_exact_duplicate_groups():
    manifest = build_dataset_manifest(DATASET_DIR, target_size=128)
    assert manifest["image_file_count"] == 7
    assert manifest["unique_decoded_content_count"] == 5
    assert manifest["independent_sample_count"] == 5
    assert manifest["preprocessing"]["version"] == PREPROCESSING_VERSION
    alias_groups = {tuple(group["source_filenames"]) for group in manifest["duplicate_groups"]}
    assert alias_groups == {
        ("20240519_121151.jpg", "original_d9e21b27e5d84c0bb09ddd92d688ac2f.jpg"),
        ("original_3796b5dfeba745a2846c9fa9f24923c1.jpg", "original_f948e6b8f4e04c6b9ca68b93512d2e2a.jpg"),
    }
    assert all(sample["resulting_dimensions"] == [128, 128] for sample in manifest["samples"])
    assert all(sample["resulting_channels"] == 1 for sample in manifest["samples"])
    assert all(sample["original_channels"] == 3 for sample in manifest["samples"])
    assert all(len(sample["decoded_content_sha256"]) == 64 for sample in manifest["samples"])


def test_duplicate_files_share_hash_and_runner_loads_each_unique_content_once():
    records = unique_dataset_records(DATASET_DIR, target_size=16)
    assert len(records) == 5
    hashes_by_filename = {
        filename: record["content_hash"]
        for record in records
        for filename in record["source_filenames"]
    }
    assert hashes_by_filename["20240519_121151.jpg"] == hashes_by_filename[
        "original_d9e21b27e5d84c0bb09ddd92d688ac2f.jpg"
    ]
    assert hashes_by_filename["original_3796b5dfeba745a2846c9fa9f24923c1.jpg"] == hashes_by_filename[
        "original_f948e6b8f4e04c6b9ca68b93512d2e2a.jpg"
    ]
    loaded = load_experiment_images(image_dir=DATASET_DIR, size=16)
    assert len(loaded) == 5
    assert all(item["image"].shape == (16, 16) and item["image"].dtype == np.uint8 for item in loaded)
    assert all(item["preprocessing"]["version"] == PREPROCESSING_VERSION for item in loaded)


def test_experiment_rows_record_source_aliases_hash_and_preprocessing(tmp_path):
    rows = run_experiments(image_dir=DATASET_DIR, size=4, seed=514, secret_key=TEST_EXPERIMENT_KEY, output_dir=tmp_path / "phase5")
    assert len(rows) == 5 * 8
    assert len({row["source_content_sha256"] for row in rows}) == 5
    assert all(row["preprocessing"]["version"] == PREPROCESSING_VERSION for row in rows)
    duplicate_row = next(row for row in rows if len(row["source_filenames"]) == 2)
    assert duplicate_row["configuration"] in {"A", "B", "C", "D", "E"}
    assert duplicate_row["original_channels"] == 3
    assert duplicate_row["preprocessing"]["target_size"] == [4, 4]


def test_committed_manifest_matches_deterministic_builder():
    path = Path("experiments/manifests/phase5-center-crop-v1.json")
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert committed == build_dataset_manifest(DATASET_DIR, target_size=128)


def test_preprocessing_metadata_records_interpolation_and_channels():
    config = preprocessing_parameters((128, 128))
    assert config["interpolation"] == "INTER_AREA"
    assert config["output_color_space"] == "grayscale"
    assert config["output_channels"] == 1
    assert config["output_dtype"] == "uint8"
