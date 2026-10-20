import csv

import numpy as np
import pytest

from experiments import aggregate_phase6, phase6_security
from experiments.dataset_manifest import unique_dataset_records
from src.diffusion import dense_gf256_diffusion, derive_diffusion_material
from src.preprocessing import PREPROCESSING_VERSION
from src.visual_cryptography import generate_shares, reconstruct_from_shares

TEST_SECRET_KEY = bytes(range(32))


def test_phase6_nonce_is_reproducible_and_purpose_separated():
    args = (20261008, "content-hash", "D")
    first = phase6_security.stable_nonce(*args)
    assert len(first) == 16
    assert first == phase6_security.stable_nonce(*args)
    assert first != phase6_security.stable_nonce(*args, purpose="alternate")


def test_phase6_nonce_comparison_holds_key_and_plaintext_fixed():
    config = phase6_security.flask_app._api_config("B")
    image = np.arange(128 * 128, dtype=np.uint32).astype(np.uint8).reshape(128, 128)
    nonce_a = phase6_security.stable_nonce(7, "same-image", "B")
    nonce_b = phase6_security.stable_nonce(7, "same-image", "B", purpose="alternate")
    cipher_a = phase6_security.encrypt_current(image, "B", config, nonce_a, TEST_SECRET_KEY)
    repeated_a = phase6_security.encrypt_current(image, "B", config, nonce_a, TEST_SECRET_KEY)
    cipher_b = phase6_security.encrypt_current(image, "B", config, nonce_b, TEST_SECRET_KEY)
    assert np.array_equal(cipher_a, repeated_a)
    assert not np.array_equal(cipher_a, cipher_b)
    assert phase6_security.compare_ciphertexts(cipher_a, cipher_b)["npcr"] > 0


def test_phase6_ciphertext_comparison_fields_are_consistent():
    left = np.array([[0, 4, 9]], dtype=np.uint8)
    right = np.array([[0, 5, 8]], dtype=np.uint8)
    comparison = phase6_security.compare_ciphertexts(left, right)
    assert comparison["npcr"] == comparison["xor_difference_occupancy_percent"]
    assert comparison["npcr"] == comparison["numeric_inequality_percent"]
    assert comparison["uaci"] >= 0


def test_phase6_dense_stage_single_byte_xor_propagation():
    config = phase6_security.flask_app._api_config("D")
    nonce = phase6_security.stable_nonce(20261008, "sample", "D")
    mask = derive_diffusion_material(
        (16, 16), secret_key=TEST_SECRET_KEY, nonce=nonce, x0=config.x0, r=config.r,
        transient=config.transient, seed=config.chaotic_seed, configuration="D",
        context=config.to_dict(),
    )[0]
    base = np.arange(256, dtype=np.uint8).reshape(16, 16)
    reference = dense_gf256_diffusion(base, mask)
    for delta in (1, 2, 127, 128, 255):
        changed = base.copy()
        changed.flat[37] ^= np.uint8(delta)
        output = dense_gf256_diffusion(changed, mask)
        assert np.all(np.bitwise_xor(reference, output) != 0)


def test_phase6_plaintext_and_key_perturbation_helpers():
    image = np.zeros((4, 4), dtype=np.uint8)
    variants = phase6_security.plaintext_perturbations(image, 3)
    assert [row["delta"] for row in variants] == [1, 2, 127, 128, 255]
    assert all(np.count_nonzero(row["image"] != image) == 1 for row in variants)
    key = TEST_SECRET_KEY
    changed = phase6_security.key_bit_perturbations(key)
    assert len(changed) == 5
    for row in changed:
        diff = [i for i, (left, right) in enumerate(zip(key, row["secret_key"])) if left != right]
        assert diff == [row["byte_index"]]
        assert key[row["byte_index"]] ^ row["secret_key"][row["byte_index"]] == row["bit_mask"]
        assert sum((left ^ right).bit_count() for left, right in zip(key, row["secret_key"])) == 1


def test_phase6_structured_inputs_are_deterministic_uint8():
    first = phase6_security.structured_plaintexts(8)
    second = phase6_security.structured_plaintexts(8)
    assert set(first) == {
        "all_zero", "all_255", "constant_128", "horizontal_gradient",
        "vertical_gradient", "checkerboard", "sparse_single_pixel",
    }
    assert all(value.dtype == np.uint8 and value.shape == (8, 8) for value in first.values())
    assert all(np.array_equal(first[name], second[name]) for name in first)


def test_phase6_unique_real_image_count_and_preprocessing_version():
    records = unique_dataset_records("experiments/real-input-7", target_size=128)
    assert len(records) == 5
    assert all(record["processed"].shape == (128, 128) for record in records)
    assert PREPROCESSING_VERSION == "center-square-crop-resize-grayscale-v1"


def test_phase6_output_directory_protection(tmp_path):
    output = tmp_path / "already-there"
    output.mkdir()
    with pytest.raises(FileExistsError):
        phase6_security.run_phase6(output_dir=output)


def test_phase6_aggregation_is_reproducible_and_uses_population_std():
    rows = [
        {"configuration": "B", "value": "1"},
        {"configuration": "B", "value": "3"},
        {"configuration": "B", "value": "not-applicable"},
    ]
    first = aggregate_phase6.summarize_numeric(rows, ["configuration"], ["value"])
    second = aggregate_phase6.summarize_numeric(rows, ["configuration"], ["value"])
    assert first == second
    assert first[0]["n"] == 2
    assert first[0]["mean"] == 2
    assert first[0]["std_population"] == 1
    assert first[0]["minimum"] == 1
    assert first[0]["maximum"] == 3


def test_phase6_threshold_reconstruction_and_insufficient_shares():
    ciphertext = np.arange(64, dtype=np.uint8).reshape(8, 8)
    shares = generate_shares(ciphertext, 2, 3, seed=20261008)
    assert np.array_equal(reconstruct_from_shares([shares[0], shares[2]], 2, 3), ciphertext)
    with pytest.raises(ValueError, match="shares are required"):
        reconstruct_from_shares(shares[:1], 2, 3)


def test_phase6_result_schema_csv_round_trip(tmp_path):
    rows = [{
        "content_id": "image-001", "configuration": "D", "npcr": 100.0,
        "preprocessing_version": PREPROCESSING_VERSION,
    }]
    output = tmp_path / "differential_analysis.csv"
    phase6_security._write_csv(output, rows)
    with output.open(newline="", encoding="utf-8") as handle:
        loaded = list(csv.DictReader(handle))
    assert loaded == [{key: str(value) for key, value in rows[0].items()}]

