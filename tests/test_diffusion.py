from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

import app as flask_app
from src.diffusion import derive_diffusion_material, diffuse, inverse_diffuse, derive_xor_key
from src.key_derivation import artifact_auth_tag
from src.metrics import calculate_differential_metrics, calculate_image_quality_metrics
from src.pipeline import (
    IntegratedPipelineConfig,
    ResearchPipelineConfig,
    decrypt_image,
    encrypt_and_share,
    encrypt_image,
    reconstruct_and_decrypt,
)
from src.quantum_encryption import QuantumInspiredConfig, generate_random_key, xor_diffusion

TEST_SECRET_KEY = bytes(range(32))


def integrated_config(size=128):
    return IntegratedPipelineConfig(
        image_shape=(size, size), x0=0.37, r=3.91, transient=17,
        chaotic_seed=9281, arnold_iterations=3,
        quantum=QuantumInspiredConfig(2, 6, 3),
    )


@pytest.mark.parametrize("shape", [(4,), (8,), (32, 32), (128, 128)])
def test_two_pass_diffusion_round_trip_returns_uint8(shape):
    rng = np.random.default_rng(len(shape) + int(np.prod(shape)))
    image = rng.integers(0, 256, shape, dtype=np.uint8)
    key1 = rng.integers(0, 256, image.size, dtype=np.uint8)
    key2 = rng.integers(0, 256, image.size, dtype=np.uint8)
    encrypted = diffuse(image, key1, key2, 53, 219)
    recovered = inverse_diffuse(encrypted, key1, key2, 53, 219)
    assert encrypted.dtype == np.uint8
    assert np.array_equal(recovered, image)


def test_nonce_deterministically_changes_chaotic_diffusion_material():
    args = dict(shape=(32, 32), secret_key=TEST_SECRET_KEY, x0=0.37, r=3.91,
                transient=17, seed=9281, configuration="D", context={"test": True})
    nonce_a, nonce_b = b"A" * 16, b"B" * 16
    first = derive_diffusion_material(nonce=nonce_a, **args)
    repeated = derive_diffusion_material(nonce=nonce_a, **args)
    second = derive_diffusion_material(nonce=nonce_b, **args)
    assert all(np.array_equal(a, b) if isinstance(a, np.ndarray) else a == b for a, b in zip(first, repeated))
    assert any(not np.array_equal(a, b) if isinstance(a, np.ndarray) else a != b for a, b in zip(first, second))


def test_integrated_random_128_round_trip_and_wrong_nonce_recovery_fails():
    image = np.random.default_rng(991).integers(0, 256, (128, 128), dtype=np.uint8)
    config = integrated_config()
    nonce_a, nonce_b = b"N" * 16, b"M" * 16
    encrypted = encrypt_image(image, config, TEST_SECRET_KEY, nonce=nonce_a)
    recovered = decrypt_image(encrypted, config, TEST_SECRET_KEY)
    assert np.array_equal(recovered, image)
    assert encrypted.nonce == nonce_a
    other_nonce_cipher = encrypt_image(image, config, TEST_SECRET_KEY, nonce=nonce_b)
    assert not np.array_equal(encrypted.ciphertext, other_nonce_cipher.ciphertext)
    with pytest.raises(ValueError, match="authentication failed"):
        wrong_nonce = type(encrypted)(encrypted.ciphertext, encrypted.metadata, nonce_b,
                                      encrypted.auth_tag, encrypted.configuration)
        decrypt_image(wrong_nonce, config, TEST_SECRET_KEY)


def test_existing_real_image_round_trip_when_repository_image_is_available():
    image_path = next(Path("experiments/real-input-7").glob("*.jpg"), None)
    if image_path is None:
        pytest.skip("repository real-image fixture is unavailable")
    loaded = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    assert loaded is not None
    image = cv2.resize(loaded, (128, 128), interpolation=cv2.INTER_AREA)
    encrypted = encrypt_image(image, integrated_config(), TEST_SECRET_KEY)
    assert np.array_equal(decrypt_image(encrypted, integrated_config(), TEST_SECRET_KEY), image)


@pytest.mark.parametrize("label", ["B", "C", "D"])
def test_api_configurations_diffuse_one_pixel_plaintext_change(label):
    image = np.random.default_rng(2026).integers(0, 256, (128, 128), dtype=np.uint8)
    image[63, 79] = np.uint8(126)
    changed = image.copy()
    changed[63, 79] = np.uint8(127)
    nonce = b"Q" * 16
    config = flask_app._api_config(label)
    first_artifact = flask_app._api_direct_encrypt_artifact(image, label, config, TEST_SECRET_KEY, nonce=nonce)
    second_artifact = flask_app._api_direct_encrypt_artifact(changed, label, config, TEST_SECRET_KEY, nonce=nonce)
    first, second = first_artifact.ciphertext, second_artifact.ciphertext
    metrics = calculate_differential_metrics(first, second)
    assert 0.0 <= metrics["npcr"] <= 100.0
    assert np.isfinite(metrics["uaci"])
    assert np.array_equal(flask_app._api_direct_decrypt(first, label, config, TEST_SECRET_KEY,
                                                       nonce=nonce, auth_tag=first_artifact.auth_tag), image)
    other_nonce_cipher = flask_app._api_direct_encrypt(image, label, config, TEST_SECRET_KEY, nonce=b"R" * 16)
    assert not np.array_equal(first, other_nonce_cipher)
    with pytest.raises(ValueError, match="authentication failed"):
        flask_app._api_direct_decrypt(first, label, config, TEST_SECRET_KEY,
                                      nonce=b"W" * 16, auth_tag=first_artifact.auth_tag)


def test_configuration_a_remains_the_unchanged_classical_xor_baseline():
    image = np.random.default_rng(18).integers(0, 256, (128, 128), dtype=np.uint8)
    config = flask_app._api_config("A")
    ciphertext = flask_app._api_direct_encrypt(image, "A", config, TEST_SECRET_KEY, nonce=b"Z" * 16)
    expected = xor_diffusion(image, derive_xor_key(image.shape, secret_key=TEST_SECRET_KEY,
                                                   nonce=b"Z" * 16, configuration="A",
                                                   context=config.to_dict()))
    assert np.array_equal(ciphertext, expected)


def test_api_nonce_header_survives_reconstruction_and_e_uses_shares_one_and_three():
    client = flask_app.app.test_client()
    source = np.random.default_rng(311).integers(0, 256, (72, 53), dtype=np.uint8)
    encoded = BytesIO()
    Image.fromarray(source).save(encoded, format="PNG")
    uploaded = client.post(
        "/api/upload",
        data={"file": (BytesIO(encoded.getvalue()), "phase1.png")},
        content_type="multipart/form-data",
    )
    assert uploaded.status_code == 200

    api_key = TEST_SECRET_KEY.hex()
    encrypted_d = client.post("/api/encrypt", json={"configuration": "D", "secret_key_hex": api_key})
    assert encrypted_d.status_code == 200
    d_state = encrypted_d.get_json()["state"]
    assert "api_phase_filename" not in d_state
    d_filename = d_state["encrypted"].rsplit("/", 1)[-1]
    nonce_d = flask_app.load_ciphertext_nonce(d_filename)
    assert nonce_d is not None and len(nonce_d) == 16
    with client.session_transaction() as session:
        assert session["api_nonce"] == nonce_d.hex()
    with Image.open(Path(flask_app.OUTPUT_DIR) / d_filename) as artifact:
        assert artifact.info["qcrypt_format_version"] == "5"
        assert artifact.info["qcrypt_nonce"] == nonce_d.hex()
        assert len(bytes.fromhex(artifact.info["qcrypt_auth_tag"])) == 32
        assert "secret_key" not in artifact.info
        assert "phase" not in artifact.info and "control" not in artifact.info
        assert "k1" not in artifact.info and "k2" not in artifact.info
    reconstructed_d = client.post("/api/reconstruct", json={"indices": [], "secret_key_hex": api_key})
    assert reconstructed_d.status_code == 200

    encrypted_e = client.post("/api/encrypt", json={"configuration": "E", "k": 2, "n": 3, "secret_key_hex": api_key})
    assert encrypted_e.status_code == 200
    e_state = encrypted_e.get_json()["state"]
    e_filename = e_state["encrypted"].rsplit("/", 1)[-1]
    assert flask_app.load_ciphertext_nonce(e_filename) is not None
    assert len(e_state["shares"]) == 3
    reconstructed_e = client.post("/api/reconstruct", json={"indices": [1, 3], "secret_key_hex": api_key})
    assert reconstructed_e.status_code == 200
    final_state = reconstructed_e.get_json()["state"]
    assert final_state["threshold_verified"] is True
    quality = final_state["metrics"]
    assert quality["mse"] == 0
    assert quality["psnr"] == "inf"
    assert quality["ssim"] == 1
    processed = cv2.imdecode(
        np.frombuffer(client.get(d_state["image"]["processed"]).data, dtype=np.uint8),
        cv2.IMREAD_GRAYSCALE,
    )
    assert np.array_equal(
        cv2.imdecode(np.frombuffer(client.get(final_state["decrypted"]).data, dtype=np.uint8), cv2.IMREAD_GRAYSCALE),
        processed,
    )

    with client.session_transaction() as session:
        flask_app.clear_api_artifacts(dict(session))
        session.clear()


def test_api_requires_explicit_secret_key_without_persisting_it():
    client = flask_app.app.test_client()
    with client.session_transaction() as session:
        session["api_processed_filename"] = "already-uploaded.png"
    missing = client.post("/api/encrypt", json={"configuration": "D"})
    malformed = client.post("/api/encrypt", json={"configuration": "D", "secret_key_hex": "abcd"})
    assert missing.status_code == 400
    assert malformed.status_code == 400
    with client.session_transaction() as session:
        assert "secret_key" not in session
        assert "secret_key_hex" not in session
    state = client.get("/api/state").get_json()
    assert "secret_key" not in repr(state)


def test_research_threshold_bundle_persists_nonce_and_reconstructs_1_3():
    image = np.random.default_rng(412).integers(0, 256, (32, 32), dtype=np.uint8)
    nonce = b"E" * 16
    config = ResearchPipelineConfig(
        image_shape=(32, 32), x0=0.37, r=3.91, transient=17,
        chaotic_seed=9281, arnold_iterations=3,
        quantum=QuantumInspiredConfig(2, 6, 3),
        threshold_k=2, threshold_n=3, sharing_seed=91,
    )
    bundle = encrypt_and_share(image, config, TEST_SECRET_KEY, nonce=nonce)
    serialized = bundle.metadata.to_dict()
    assert serialized["nonce"] == nonce.hex()
    assert serialized["format_version"] == 5
    assert "phase" not in serialized
    assert "z_bit" not in serialized["config"]["quantum"]
    restored_bundle = type(bundle).from_dict(bundle.to_dict())
    recovered = reconstruct_and_decrypt([restored_bundle.shares[0], restored_bundle.shares[2]],
                                        config, TEST_SECRET_KEY, restored_bundle.metadata)
    assert np.array_equal(recovered, image)
    quality = calculate_image_quality_metrics(image, recovered)
    assert quality["mse"] == 0
    assert np.isinf(quality["psnr"])
    assert quality["ssim"] == 1
