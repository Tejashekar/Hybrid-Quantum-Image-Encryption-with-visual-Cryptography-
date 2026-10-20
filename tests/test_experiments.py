import json

import cv2
import numpy as np
import pytest

import experiments.run_experiments as experiment_runner
from experiments.run_experiments import (
    ExperimentConfig,
    build_experiment_matrix,
    derive_seed,
    generate_synthetic_images,
    run_experiments,
)
from src.visual_cryptography import generate_shares, reconstruct_from_shares

TEST_EXPERIMENT_KEY = bytes(range(32))


def test_experiment_matrix_and_configuration_validation():
    matrix = build_experiment_matrix(size=4, seed=7)
    assert [config.label for config in matrix] == ["A", "B", "C", "D", "E", "E", "E", "E"]
    assert [(config.threshold_k, config.threshold_n) for config in matrix if config.label == "E"] == [(2, 2), (2, 3), (3, 5), (3, 6)]
    with pytest.raises(ValueError):
        ExperimentConfig("E", "bad", (4, 4), 1, 2, 3, threshold_k=4, threshold_n=3)


def test_synthetic_images_are_reproducible_and_typed():
    first = generate_synthetic_images(size=8, seed=3)
    second = generate_synthetic_images(size=8, seed=3)
    assert [item["name"] for item in first] == [item["name"] for item in second]
    assert "synthetic_random" in [item["name"] for item in first]
    assert "random" in [item["type"] for item in first]
    assert all(np.array_equal(a["image"], b["image"]) for a, b in zip(first, second))
    assert all(item["image"].shape == (8, 8) and item["image"].dtype == np.uint8 for item in first)


def test_experiment_results_are_deterministic_except_run_identity_and_timestamp(tmp_path):
    first = run_experiments(size=4, seed=11, secret_key=TEST_EXPERIMENT_KEY, output_dir=tmp_path / "first")
    second = run_experiments(size=4, seed=11, secret_key=TEST_EXPERIMENT_KEY, output_dir=tmp_path / "second")
    assert len(first) == len(second) == 32
    for left, right in zip(first, second):
        assert left["configuration"] == right["configuration"]
        assert left["image_name"] == right["image_name"]
        assert left["status"] == right["status"]
        assert left.get("entropy") == right.get("entropy")
        assert left.get("npcr") == right.get("npcr")
        assert left.get("threshold_k") == right.get("threshold_k")


def test_result_schema_and_failure_recording(tmp_path):
    image = np.zeros((4, 4), dtype=np.uint8)
    rows = run_experiments(image=image, size=4, seed=4, secret_key=TEST_EXPERIMENT_KEY, output_dir=tmp_path / "results")
    assert len(rows) == 8
    assert all({"experiment_id", "timestamp_utc", "image_id", "image_name", "image_shape", "configuration", "status"} <= set(row) for row in rows)
    assert all("python" in row["software_version"] and "numpy" in row["software_version"] for row in rows)
    assert (tmp_path / "results" / "results.json").exists()
    assert (tmp_path / "results" / "results.csv").exists()
    json.loads((tmp_path / "results" / "results.json").read_text(encoding="utf-8"))


def test_invalid_image_is_recorded_without_abort(tmp_path):
    rows = run_experiments(image=np.zeros((3, 4, 2), dtype=np.uint8), size=4, seed=4, secret_key=TEST_EXPERIMENT_KEY, output_dir=tmp_path / "failed")
    assert len(rows) == 8
    assert all(row["status"] == "failed" for row in rows)
    assert all("error_type" in row and "error_message" in row for row in rows)
    assert all(row["image_shape"] == [3, 4, 2] and row["image_dtype"] == "uint8" for row in rows)


def test_explicit_empty_dataset_directory_fails(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        experiment_runner.load_experiment_images(image_dir=tmp_path / "empty", size=4)
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match="no valid supported images"):
        experiment_runner.load_experiment_images(image_dir=tmp_path / "empty", size=4)


def test_real_images_are_grayscale_uint8_and_deterministically_center_cropped(tmp_path):
    source = np.arange(6 * 10, dtype=np.uint8).reshape(6, 10)
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), source)
    first = experiment_runner.load_experiment_images(image_path=path, size=4)[0]["image"]
    second = experiment_runner.load_experiment_images(image_path=path, size=4)[0]["image"]
    assert first.shape == (4, 4)
    assert first.dtype == np.uint8
    assert np.array_equal(first, second)
    square = source[:, 2:8]
    assert np.array_equal(first, cv2.resize(square, (4, 4), interpolation=cv2.INTER_AREA))
    assert not np.array_equal(first, cv2.resize(source, (4, 4), interpolation=cv2.INTER_AREA))


def test_explicit_directory_unreadable_file_is_not_silently_ignored(tmp_path):
    valid = np.arange(16, dtype=np.uint8).reshape(4, 4)
    assert cv2.imwrite(str(tmp_path / "valid.png"), valid)
    (tmp_path / "broken.dat").write_text("not an image", encoding="utf-8")
    with pytest.raises(ValueError, match="unreadable or unsupported"):
        experiment_runner.load_experiment_images(image_dir=tmp_path, size=4)


def test_explicit_invalid_image_does_not_fall_back_to_synthetic(tmp_path):
    invalid = tmp_path / "missing.png"
    with pytest.raises(ValueError, match="could not be decoded"):
        experiment_runner.load_experiment_images(image_path=invalid, size=4)


def test_real_image_identity_uses_preprocessed_array(tmp_path):
    source = np.arange(8 * 12, dtype=np.uint8).reshape(8, 12)
    path = tmp_path / "source.png"
    assert cv2.imwrite(str(path), source)
    record = experiment_runner.load_experiment_images(image_path=path, size=4)[0]
    assert experiment_runner._image_identity(record["image"]) == experiment_runner._image_identity(
        cv2.resize(source[:, 2:10], (4, 4), interpolation=cv2.INTER_AREA)
    )


def test_results_refuse_to_overwrite_existing_archive_without_explicit_flag(tmp_path):
    destination = tmp_path / "archive"
    destination.mkdir()
    (destination / "results.json").write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError, match="already exists"):
        run_experiments(image=np.zeros((4, 4), dtype=np.uint8), size=4, secret_key=TEST_EXPERIMENT_KEY, output_dir=destination)
    assert (destination / "results.json").read_text(encoding="utf-8") == "preserve"


def test_image_hash_is_stable():
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    assert experiment_runner._image_identity(image) == experiment_runner._image_identity(image.copy())
    changed = image.copy(); changed[0, 0] ^= 1
    assert experiment_runner._image_identity(image) != experiment_runner._image_identity(changed)


def test_c_minimal_key_perturbation_changes_ciphertext_after_diffusion():
    config = build_experiment_matrix(size=4, seed=17)[2]
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    encrypt_for = experiment_runner._encryptor(config, TEST_EXPERIMENT_KEY)
    base = encrypt_for(image)
    modified = encrypt_for(image, "minimal_key")
    assert np.count_nonzero(base[0] != modified[0]) > 0
    seed_changed = encrypt_for(image, "seed_perturbed")
    assert np.count_nonzero(base[0] != seed_changed[0]) > 1


def test_synthetic_random_and_configuration_a_key_use_independent_seeds():
    master_seed = 20261001
    random_image = [item for item in generate_synthetic_images(size=32, seed=master_seed) if item["name"] == "synthetic_random"][0]["image"]
    config_a = build_experiment_matrix(size=32, seed=master_seed)[0]
    key = experiment_runner.generate_random_key(config_a.image_shape, config_a.seed)
    ciphertext = experiment_runner._encryptor(config_a, TEST_EXPERIMENT_KEY)(random_image)
    assert derive_seed(master_seed, "synthetic-image-random") != config_a.seed
    assert not np.array_equal(random_image, key)
    assert np.count_nonzero(ciphertext) > 0


def test_e_records_first_k_coordinates_and_share_bytes(tmp_path):
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    rows = run_experiments(image=image, size=4, seed=5, secret_key=TEST_EXPERIMENT_KEY, output_dir=tmp_path / "e")
    e_rows = [row for row in rows if row["configuration"] == "E"]
    assert all(row["share_selection_strategy"] == "first_k" for row in e_rows)
    assert all(row["selected_share_coordinates"] == list(range(1, row["threshold_k"] + 1)) for row in e_rows)
    assert all(row["bytes_per_share"] * row["number_of_shares"] == row["total_share_bytes"] for row in e_rows)
    assert all(row["decryption_time_ms"] >= 0 and "mse" in row and "ssim" in row for row in e_rows)


def test_e_quality_and_decryption_use_reconstructed_ciphertext(monkeypatch, tmp_path):
    image = np.arange(16, dtype=np.uint8).reshape(4, 4)
    observed = []
    original_decrypt = experiment_runner.decrypt_image

    def spy(encrypted, config, secret_key):
        observed.append(encrypted.ciphertext.copy())
        return original_decrypt(encrypted, config, secret_key)

    monkeypatch.setattr(experiment_runner, "decrypt_image", spy)
    run_experiments(image=image, size=4, seed=8, secret_key=TEST_EXPERIMENT_KEY, output_dir=tmp_path / "e-path")
    e_ciphertexts = []
    for config in [config for config in build_experiment_matrix(size=4, seed=8) if config.label == "E"]:
        direct = experiment_runner._encryptor(config, TEST_EXPERIMENT_KEY)(image)[0]
        shares = generate_shares(direct, config.threshold_k, config.threshold_n, config.sharing_seed)
        e_ciphertexts.append(reconstruct_from_shares(shares[:config.threshold_k], config.threshold_k, config.threshold_n))
    assert all(np.array_equal(actual, expected) for actual, expected in zip(observed[1:], e_ciphertexts))
