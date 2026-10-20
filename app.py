from __future__ import annotations

import os
import uuid
import hashlib
import json
import secrets
import time

import cv2
import numpy as np
from PIL import Image, PngImagePlugin
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from src.metrics import (
    calculate_differential_metrics,
    calculate_image_quality_metrics,
    calculate_security_metrics,
    calculate_storage_metrics,
    correlation_analysis,
    entropy,
    npcr_uaci,
    psnr,
)
from src.pipeline import (
    EncryptedImage,
    ResearchMetadata,
    ResearchPipelineConfig,
    ResearchShareBundle,
    decrypt_image,
    encrypt_and_share,
    encrypt_image,
    reconstruct_and_decrypt,
    IntegratedPipelineConfig,
)
from src.key_derivation import artifact_auth_tag, validate_secret_key
from src.chaotic_key import chaotic_key_for_shape
from src.diffusion import (
    derive_diffusion_material,
    dense_gf256_diffusion,
    inverse_dense_gf256_diffusion,
    normalize_nonce,
)
from src.quantum_encryption import (
    QuantumInspiredConfig,
    derive_z_rotation_parameters,
    generate_random_key,
    inverse_quantum_inspired_transform,
    quantum_inspired_transform,
    xor_diffusion,
)
from src.preprocessing import load_image, preprocess
from src.visual_cryptography import ImageShare, generate_shares, reconstruct_from_shares

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tif", "tiff"}

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["DEBUG"] = os.environ.get("FLASK_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
app.config["UPLOAD_FOLDER"] = INPUT_DIR
app.config["OUTPUT_FOLDER"] = OUTPUT_DIR
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_directories() -> None:
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def clear_api_artifacts(state: dict | None = None, *, older_than_seconds: int | None = None) -> None:
    """Remove this session's transient API files, or expired API files at startup."""
    directories = {"input": INPUT_DIR, "output": OUTPUT_DIR}
    names = []
    if state is not None:
        names.append(("input", state.get("api_original_filename")))
        for key in ("api_processed_filename", "api_encrypted_filename", "api_phase_filename",
                    "api_reconstructed_filename", "api_decrypted_filename"):
            names.append(("output", state.get(key)))
        names.extend(("output", name) for name in state.get("api_share_filenames", []))
    else:
        cutoff = time.time() - int(older_than_seconds or 0)
        for directory_name, directory in directories.items():
            if not os.path.isdir(directory):
                continue
            for name in os.listdir(directory):
                if name.startswith("api-"):
                    path = os.path.join(directory, name)
                    if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                        names.append((directory_name, name))
    for directory_name, name in names:
        if not name or os.path.basename(name) != name or not name.startswith("api-"):
            continue
        path = os.path.join(directories[directory_name], name)
        if os.path.isfile(path):
            os.remove(path)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def unique_name(prefix: str, suffix: str = ".png") -> str:
    return f"{prefix}_{uuid.uuid4().hex}{suffix}"


def save_gray_image(image: np.ndarray, filename: str) -> None:
    cv2.imwrite(os.path.join(OUTPUT_DIR, filename), image)


def save_ciphertext_artifact(image: np.ndarray, filename: str, nonce: bytes,
                             auth_tag: bytes, configuration: str) -> None:
    """Write v5 ciphertext with public nonce/config and keyed integrity tag."""
    info = PngImagePlugin.PngInfo()
    info.add_text("qcrypt_format_version", "5")
    info.add_text("qcrypt_nonce", normalize_nonce(nonce).hex())
    info.add_text("qcrypt_auth_tag", bytes(auth_tag).hex())
    info.add_text("qcrypt_configuration", configuration)
    Image.fromarray(np.asarray(image, dtype=np.uint8)).save(
        os.path.join(OUTPUT_DIR, filename), format="PNG", pnginfo=info
    )


def load_ciphertext_nonce(filename: str) -> bytes | None:
    """Read version-5 public metadata; reject old artifacts explicitly."""
    path = os.path.join(OUTPUT_DIR, filename)
    with Image.open(path) as artifact:
        nonce_hex = artifact.info.get("qcrypt_nonce")
        version = artifact.info.get("qcrypt_format_version")
    if version != "5":
        raise ValueError("unsupported ciphertext artifact format; version 5 is required and legacy formats are not implicitly decrypted")
    if nonce_hex is None:
        raise ValueError("ciphertext artifact is missing its public nonce")
    try:
        nonce = bytes.fromhex(nonce_hex)
    except (TypeError, ValueError) as exc:
        raise ValueError("ciphertext artifact contains an invalid nonce") from exc
    return normalize_nonce(nonce)


def load_ciphertext_auth_metadata(filename: str) -> tuple[bytes, bytes, str]:
    path = os.path.join(OUTPUT_DIR, filename)
    with Image.open(path) as artifact:
        if artifact.info.get("qcrypt_format_version") != "5":
            raise ValueError("unsupported ciphertext artifact format; version 5 is required")
        nonce_hex = artifact.info.get("qcrypt_nonce")
        tag_hex = artifact.info.get("qcrypt_auth_tag")
        configuration = artifact.info.get("qcrypt_configuration")
    nonce = normalize_nonce(bytes.fromhex(nonce_hex)) if isinstance(nonce_hex, str) else None
    if nonce is None:
        raise ValueError("ciphertext artifact is missing its nonce")
    try:
        tag = bytes.fromhex(tag_hex) if isinstance(tag_hex, str) else b""
    except ValueError as exc:
        raise ValueError("ciphertext artifact contains invalid authentication metadata") from exc
    if len(tag) != 32 or configuration not in {"A", "B", "C", "D", "E"}:
        raise ValueError("ciphertext artifact contains invalid authentication metadata")
    return nonce, tag, configuration


def load_gray_from_output(filename: str | None) -> np.ndarray | None:
    if not filename:
        return None
    path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(path):
        return None
    return cv2.imread(path, cv2.IMREAD_GRAYSCALE)


def xor_encrypt(image: np.ndarray, key: np.ndarray) -> np.ndarray:
    return np.bitwise_xor(image, key)


def pipeline_state() -> dict[str, str | None]:
    original_url = _api_url("input", session.get("api_original_filename"))
    processed_url = _api_url("output", session.get("api_processed_filename"))
    encrypted_url = _api_url("output", session.get("api_encrypted_filename"))
    reconstructed_url = _api_url("output", session.get("api_reconstructed_filename"))
    decrypted_url = _api_url("output", session.get("api_decrypted_filename"))
    return {
        "original": session.get("original_filename"),
        "processed": session.get("processed_filename"),
        "encrypted": session.get("encrypted_filename"),
        "share1": session.get("share1_filename"),
        "share2": session.get("share2_filename"),
        "reconstructed": session.get("reconstructed_filename"),
        "decrypted": session.get("decrypted_filename"),
    }


# ---------------------------------------------------------------------------
# Routes  –  single-page app served via Jinja2
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return redirect(FRONTEND_URL)


@app.route("/upload", methods=["POST"])
def upload_preprocess():
    file = request.files.get("file")
    if file is None or file.filename == "":
        flash("Select an image before uploading.", "error")
        return redirect(url_for("home") + "#upload")
    if not allowed_file(file.filename):
        flash("Unsupported file format. Use PNG/JPG/BMP/TIFF.", "error")
        return redirect(url_for("home") + "#upload")

    original_name = unique_name(
        "original",
        os.path.splitext(secure_filename(file.filename))[1] or ".png",
    )
    original_path = os.path.join(INPUT_DIR, original_name)
    file.save(original_path)

    image = load_image(original_path)
    if image is None:
        flash("Could not read the uploaded image.", "error")
        return redirect(url_for("home") + "#upload")

    processed = preprocess(image, size=(128, 128))
    processed_name = unique_name("processed")
    save_gray_image(processed, processed_name)

    session["original_filename"] = original_name
    session["processed_filename"] = processed_name
    for key in (
        "encrypted_filename",
        "share1_filename",
        "share2_filename",
        "reconstructed_filename",
        "decrypted_filename",
        "key_filename",
    ):
        session.pop(key, None)

    flash("Image uploaded and preprocessed successfully.", "success")
    return redirect(url_for("home") + "#encrypt")


@app.route("/encrypt", methods=["POST"])
def encrypt_split():
    processed_name = session.get("processed_filename")
    if not processed_name:
        flash("Upload an image first.", "error")
        return redirect(url_for("home") + "#upload")

    processed = load_gray_from_output(processed_name)
    if processed is None:
        flash("Processed image is missing. Please re-upload.", "error")
        return redirect(url_for("home") + "#upload")

    key = np.random.randint(0, 256, size=processed.shape, dtype=np.uint8)
    encrypted = xor_encrypt(processed, key)
    share1, share2 = generate_shares(encrypted)

    encrypted_name = unique_name("encrypted")
    share1_name = unique_name("share1")
    share2_name = unique_name("share2")
    key_name = unique_name("key", ".npy")

    save_gray_image(encrypted, encrypted_name)
    save_gray_image(share1, share1_name)
    save_gray_image(share2, share2_name)
    np.save(os.path.join(OUTPUT_DIR, key_name), key)

    session["encrypted_filename"] = encrypted_name
    session["share1_filename"] = share1_name
    session["share2_filename"] = share2_name
    session["key_filename"] = key_name
    session.pop("reconstructed_filename", None)
    session.pop("decrypted_filename", None)

    flash("Encryption and share generation completed.", "success")
    return redirect(url_for("home") + "#reconstruct")


@app.route("/reconstruct", methods=["POST"])
def reconstruct_decrypt():
    share1_upload = request.files.get("share1")
    share2_upload = request.files.get("share2")

    share1 = None
    share2 = None

    if share1_upload and share1_upload.filename and share2_upload and share2_upload.filename:
        share1_bytes = np.frombuffer(share1_upload.read(), np.uint8)
        share2_bytes = np.frombuffer(share2_upload.read(), np.uint8)
        share1 = cv2.imdecode(share1_bytes, cv2.IMREAD_GRAYSCALE)
        share2 = cv2.imdecode(share2_bytes, cv2.IMREAD_GRAYSCALE)
    else:
        share1 = load_gray_from_output(session.get("share1_filename"))
        share2 = load_gray_from_output(session.get("share2_filename"))

    if share1 is None or share2 is None:
        flash("Both shares are required.", "error")
        return redirect(url_for("home") + "#reconstruct")

    key_name = session.get("key_filename")
    key_path = os.path.join(OUTPUT_DIR, key_name) if key_name else ""
    if not key_name or not os.path.exists(key_path):
        flash("Encryption key not found. Run encryption again.", "error")
        return redirect(url_for("home") + "#encrypt")

    key = np.load(key_path)
    reconstructed = reconstruct_from_shares(share1, share2)
    decrypted = xor_encrypt(reconstructed, key)

    reconstructed_name = unique_name("reconstructed")
    decrypted_name = unique_name("decrypted")
    save_gray_image(reconstructed, reconstructed_name)
    save_gray_image(decrypted, decrypted_name)

    session["reconstructed_filename"] = reconstructed_name
    session["decrypted_filename"] = decrypted_name

    flash("Reconstruction and decryption completed.", "success")
    return redirect(url_for("home") + "#metrics")


@app.route("/metrics")
def metrics_dashboard():
    processed = load_gray_from_output(session.get("processed_filename"))
    encrypted = load_gray_from_output(session.get("encrypted_filename"))
    decrypted = load_gray_from_output(session.get("decrypted_filename"))

    metrics = None
    if processed is not None and encrypted is not None:
        npcr_value, uaci_value = npcr_uaci(processed, encrypted)
        metrics = {
            "entropy_encrypted": round(float(entropy(encrypted)), 4),
            "correlation_encrypted": round(float(correlation_analysis(encrypted)), 4),
            "npcr": round(float(npcr_value), 4),
            "uaci": round(float(uaci_value), 4),
            "psnr_original_vs_decrypted": (
                round(float(psnr(processed, decrypted)), 4)
                if decrypted is not None
                else "N/A"
            ),
        }
    return jsonify({"metrics": metrics, "state": pipeline_state()})


# ---------------------------------------------------------------------------
# Research JSON API used by the Next.js laboratory
# ---------------------------------------------------------------------------

def _api_url(kind: str, filename: str | None):
    if not filename:
        return None
    return url_for("serve_input_file" if kind == "input" else "serve_output_file", filename=filename)


def _api_json_safe(value):
    if isinstance(value, dict):
        return {key: _api_json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_api_json_safe(item) for item in value]
    if isinstance(value, (float, np.floating)) and not np.isfinite(value):
        return "inf" if value > 0 else ("-inf" if value < 0 else None)
    if isinstance(value, np.integer):
        return int(value)
    return value


def _api_state():
    config = session.get("api_config")
    original_url = _api_url("input", session.get("api_original_filename"))
    processed_url = _api_url("output", session.get("api_processed_filename"))
    encrypted_url = _api_url("output", session.get("api_encrypted_filename"))
    reconstructed_url = _api_url("output", session.get("api_reconstructed_filename"))
    decrypted_url = _api_url("output", session.get("api_decrypted_filename"))
    return {
        "stage": session.get("api_stage", "idle"),
        "label": session.get("api_label"),
        "config": config,
        "image": {
            "original": original_url,
            "processed": processed_url,
            "original_filename": session.get("api_original_filename"),
            "processed_shape": session.get("api_shape"),
            "original_dimensions": session.get("api_original_dimensions"),
            "dtype": "uint8" if session.get("api_processed_filename") else None,
        },
        "encrypted": encrypted_url,
        "reconstructed": reconstructed_url,
        "decrypted": decrypted_url,
        "original": original_url, "processed": processed_url, "encrypted_legacy": encrypted_url,
        "share1": None, "share2": None, "reconstructed_legacy": reconstructed_url, "decrypted_legacy": decrypted_url,
        "shares": [
            {"index": index, "url": _api_url("output", filename), "selected": False}
            for index, filename in enumerate(session.get("api_share_filenames", []), start=1)
        ],
        "metrics": _api_json_safe(session.get("api_metrics")),
        "threshold_verified": session.get("api_threshold_verified"),
    }


def _api_config(label: str, k: int = 2, n: int = 2):
    if label not in {"A", "B", "C", "D", "E"}:
        raise ValueError("unsupported configuration")
    if label == "E" and (k, n) not in {(2, 2), (2, 3), (3, 5), (3, 6)}:
        raise ValueError("unsupported threshold configuration")
    shape = (128, 128)
    seed_material = hashlib.sha256(f"q-crypt:{label}:{k}:{n}".encode()).digest()
    chaotic_seed = int.from_bytes(seed_material[:4], "big")
    sharing_seed = int.from_bytes(seed_material[4:8], "big")
    return ResearchPipelineConfig(
        image_shape=shape, x0=0.37, r=3.91, transient=1000,
        chaotic_seed=chaotic_seed, arnold_iterations=3,
        quantum=QuantumInspiredConfig(2, 6, 3),
        threshold_k=k, threshold_n=n, sharing_seed=sharing_seed,
    )


def _api_public_config(config):
    return config.to_dict()


def _api_direct_encrypt_artifact(image, label, config, secret_key: bytes, *, nonce: bytes | None = None):
    integrated = config.encryption_config() if isinstance(config, ResearchPipelineConfig) else config
    return encrypt_image(image, integrated, secret_key, nonce=nonce, configuration=label,
                         public_config=_api_public_config(config))


def _api_direct_encrypt(image, label, config, secret_key: bytes, *, nonce: bytes | None = None):
    return _api_direct_encrypt_artifact(image, label, config, secret_key, nonce=nonce).ciphertext


def _api_direct_decrypt(ciphertext, label, config, secret_key: bytes, *, nonce: bytes,
                        auth_tag: bytes):
    integrated = config.encryption_config() if isinstance(config, ResearchPipelineConfig) else config
    artifact = EncryptedImage(ciphertext, _api_public_config(config), nonce, auth_tag, label)
    return decrypt_image(artifact, integrated, secret_key)


def _api_secret_key(body):
    encoded = body.get("secret_key_hex") if isinstance(body, dict) else None
    if not isinstance(encoded, str) or len(encoded) != 64:
        raise ValueError("secret_key_hex is required as exactly 64 hexadecimal characters (32 bytes)")
    try:
        key = bytes.fromhex(encoded)
    except ValueError as exc:
        raise ValueError("secret_key_hex must contain only hexadecimal characters") from exc
    return validate_secret_key(key)


def _api_metrics(original, ciphertext, recovered=None, differential=None):
    security = calculate_security_metrics(original, ciphertext)
    result = {
        "entropy": security["entropy"],
        "correlation_horizontal": security["correlation_horizontal"],
        "correlation_vertical": security["correlation_vertical"],
        "correlation_diagonal": security["correlation_diagonal"],
    }
    if differential is not None:
        result.update(calculate_differential_metrics(ciphertext, differential))
    if recovered is not None:
        result.update(calculate_image_quality_metrics(original, recovered))
    return result


@app.get("/api/state")
def api_state():
    return jsonify(_api_state())


@app.post("/api/upload")
def api_upload():
    file = request.files.get("file")
    if file is None or not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Unable to decode image. Upload a PNG, JPG, BMP, or TIFF file."}), 400
    ensure_directories()
    original_filename = unique_name("api-original", os.path.splitext(secure_filename(file.filename))[1] or ".png")
    original_path = os.path.join(INPUT_DIR, original_filename)
    file.save(original_path)
    image = load_image(original_path)
    if image is None:
        if os.path.isfile(original_path):
            os.remove(original_path)
        return jsonify({"error": "Unable to decode image."}), 400
    try:
        processed = preprocess(image, size=(128, 128)).astype(np.uint8, copy=False)
    except Exception as exc:
        if os.path.isfile(original_path):
            os.remove(original_path)
        return jsonify({"error": f"Image preprocessing failed: {exc}"}), 400
    processed_filename = unique_name("api-processed")
    save_gray_image(processed, processed_filename)
    clear_api_artifacts(dict(session))
    session.clear()
    session.update({
        "api_original_filename": original_filename,
        "api_processed_filename": processed_filename,
        "api_original_dimensions": [int(image.shape[1]), int(image.shape[0])],
        "api_shape": [128, 128], "api_stage": "processed",
    })
    return jsonify({"message": "Image processed.", "state": _api_state()})


@app.post("/api/encrypt")
def api_encrypt():
    if not session.get("api_processed_filename"):
        return jsonify({"error": "Upload an image first."}), 400
    body = request.get_json(silent=True) or {}
    label = str(body.get("configuration", "D")).upper()
    try:
        secret_key = _api_secret_key(body)
        k, n = int(body.get("k", 2)), int(body.get("n", 2))
        config = _api_config(label, k, n)
        original = load_gray_from_output(session["api_processed_filename"])
        if original is None:
            raise ValueError("processed image is missing")
        nonce_hex = body.get("nonce_hex")
        if nonce_hex is not None:
            if not isinstance(nonce_hex, str):
                raise ValueError("nonce_hex must be a 32-character hexadecimal string")
            try:
                nonce = normalize_nonce(bytes.fromhex(nonce_hex))
            except ValueError as exc:
                raise ValueError("nonce_hex must encode exactly 16 bytes") from exc
        else:
            nonce = None
        old_artifacts = {
            "api_encrypted_filename": session.get("api_encrypted_filename"),
            # Clean phase sidecars created by the previous artifact format.
            "api_phase_filename": session.get("api_phase_filename"),
            "api_reconstructed_filename": session.get("api_reconstructed_filename"),
            "api_decrypted_filename": session.get("api_decrypted_filename"),
            "api_share_filenames": list(session.get("api_share_filenames", [])),
        }
        if label == "E":
            pipeline_started = time.perf_counter_ns()
            bundle = encrypt_and_share(original, config, secret_key, nonce=nonce)
            pipeline_ms = (time.perf_counter_ns() - pipeline_started) / 1_000_000
            shares = bundle.shares
            config_dict = bundle.metadata.config
            nonce = bundle.metadata.nonce
            auth_tag = bundle.metadata.auth_tag
            reconstruction_started = time.perf_counter_ns()
            ciphertext = reconstruct_from_shares(shares[:k], k, n)
            reconstruction_ms = (time.perf_counter_ns() - reconstruction_started) / 1_000_000
            encryption_ms = None
            share_ms = None
            share_files = []
            for position, share in enumerate(shares, start=1):
                name = unique_name(f"api-share-{position}")
                save_gray_image(np.asarray(share, dtype=np.uint8), name)
                share_files.append(name)
            threshold_verified = True
        else:
            encryption_started = time.perf_counter_ns()
            encrypted_artifact = _api_direct_encrypt_artifact(original, label, config, secret_key, nonce=nonce)
            ciphertext = encrypted_artifact.ciphertext
            nonce = encrypted_artifact.nonce
            auth_tag = encrypted_artifact.auth_tag
            encryption_ms = (time.perf_counter_ns() - encryption_started) / 1_000_000
            share_ms = reconstruction_ms = None
            config_dict = config.to_dict()
            share_files = []
            threshold_verified = None
        encrypted_filename = unique_name("api-encrypted")
        save_ciphertext_artifact(ciphertext, encrypted_filename, nonce, auth_tag, label)
        differential = None
        if label != "A":
            changed = original.copy(); changed[0, 0] ^= np.uint8(1)
            differential = _api_direct_encrypt(changed, label, config, secret_key, nonce=nonce)
        metrics = _api_metrics(original, ciphertext, differential=differential)
        metrics["encryption_time_ms"] = encryption_ms
        if label == "E":
            metrics.update(calculate_storage_metrics(original, ciphertext, shares))
            metrics["bytes_per_share"] = metrics["total_share_bytes"] / metrics["number_of_shares"]
            metrics["share_generation_time_ms"] = share_ms
            metrics["threshold_pipeline_time_ms"] = pipeline_ms
            metrics["reconstruction_time_ms"] = None
        clear_api_artifacts(old_artifacts)
        # Retire the old session-only phase sidecar reference after cleanup.
        session.pop("api_phase_filename", None)
        session.update({
            "api_label": label, "api_config": config_dict,
            "api_nonce": nonce.hex() if nonce is not None else None,
            "api_encrypted_filename": encrypted_filename,
            "api_share_filenames": share_files,
            "api_threshold_verified": threshold_verified,
            "api_metrics": metrics, "api_stage": "encrypted",
            "api_reconstructed_filename": None, "api_decrypted_filename": None,
        })
        return jsonify({"message": "Research encryption completed.", "state": _api_state()})
    except Exception as exc:
        return jsonify({"error": f"Encryption failed: {exc}"}), 400


@app.post("/api/reconstruct")
def api_reconstruct():
    if session.get("api_label") not in {"A", "B", "C", "D", "E"}:
        return jsonify({"error": "Run encryption before reconstruction."}), 400
    try:
        body = request.get_json(silent=True) or {}
        secret_key = _api_secret_key(body)
        label = session["api_label"]
        config_data = session["api_config"]
        nonce, auth_tag, artifact_configuration = load_ciphertext_auth_metadata(session["api_encrypted_filename"])
        if artifact_configuration != label:
            raise ValueError("ciphertext artifact configuration does not match the active session")
        session_nonce_hex = session.get("api_nonce")
        if session_nonce_hex is not None and nonce != normalize_nonce(bytes.fromhex(session_nonce_hex)):
            raise ValueError("ciphertext nonce does not match the active session")
        original = load_gray_from_output(session["api_processed_filename"])
        ciphertext = load_gray_from_output(session["api_encrypted_filename"])
        if original is None or ciphertext is None:
            raise ValueError("encrypted state is missing")
        if label == "E":
            indices = [int(value) for value in body.get("indices", [])]
            k, n = config_data["threshold"]["k"], config_data["threshold"]["n"]
            if len(indices) < k:
                return jsonify({"error": f"{k} shares are required for reconstruction."}), 400
            all_files = session.get("api_share_filenames", [])
            if len(set(indices)) != len(indices) or any(index < 1 or index > len(all_files) for index in indices):
                return jsonify({"error": "Select distinct shares from this encrypted image."}), 400
            shares = [ImageShare(cv2.imread(os.path.join(OUTPUT_DIR, all_files[index - 1]), cv2.IMREAD_GRAYSCALE), index) for index in indices]
            cfg = ResearchPipelineConfig.from_dict(config_data)
            reconstruction_started = time.perf_counter_ns()
            metadata = ResearchMetadata(config=config_data, nonce=nonce, auth_tag=auth_tag)
            recovered = reconstruct_and_decrypt(shares, cfg, secret_key, metadata)
            reconstruction_decryption_ms = (time.perf_counter_ns() - reconstruction_started) / 1_000_000
            reconstructed = reconstruct_from_shares(shares, k, n)
            reconstruction_ms = None
            decryption_ms = None
            verified = bool(np.array_equal(reconstructed, ciphertext))
        else:
            cfg = ResearchPipelineConfig.from_dict({**config_data, "threshold": {"k": 2, "n": 2}, "sharing_seed": None})
            reconstruction_ms = None
            decrypt_started = time.perf_counter_ns()
            recovered = _api_direct_decrypt(ciphertext, label, cfg, secret_key,
                                            nonce=nonce, auth_tag=auth_tag)
            decryption_ms = (time.perf_counter_ns() - decrypt_started) / 1_000_000
            reconstructed, verified = ciphertext, True
        if label != "E":
            reconstructed = ciphertext.copy()
            reconstruction_ms = None
            reconstruction_decryption_ms = None
        reconstructed_filename = unique_name("api-reconstructed")
        decrypted_filename = unique_name("api-decrypted")
        save_gray_image(reconstructed, reconstructed_filename)
        save_gray_image(recovered, decrypted_filename)
        clear_api_artifacts({
            "api_reconstructed_filename": session.get("api_reconstructed_filename"),
            "api_decrypted_filename": session.get("api_decrypted_filename"),
        })
        session.update({
            "api_reconstructed_filename": reconstructed_filename,
            "api_decrypted_filename": decrypted_filename,
            "api_threshold_verified": verified,
            "api_stage": "reconstructed",
            "api_metrics": {
                **(session.get("api_metrics") or {}),
                **calculate_image_quality_metrics(original, recovered),
                "reconstruction_time_ms": reconstruction_ms,
                "decryption_time_ms": decryption_ms,
                "reconstruction_decryption_time_ms": reconstruction_decryption_ms,
            },
        })
        return jsonify({"message": "Reconstruction and decryption completed.", "state": _api_state()})
    except Exception as exc:
        return jsonify({"error": f"Reconstruction failed: {exc}"}), 400


@app.get("/api/experiment-results")
def api_experiment_results():
    path = os.path.join(BASE_DIR, "experiments", "results", "real-128", "results.json")
    if not os.path.exists(path):
        return jsonify({"rows": [], "count": 0})
    with open(path, encoding="utf-8") as handle:
        rows = json.load(handle)
    return jsonify({"rows": rows, "count": len(rows)})


# ---------------------------------------------------------------------------
# Static file serving
# ---------------------------------------------------------------------------

@app.route("/output/<path:filename>")
def serve_output_file(filename: str):
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/input/<path:filename>")
def serve_input_file(filename: str):
    return send_from_directory(INPUT_DIR, filename)


ensure_directories()
clear_api_artifacts(older_than_seconds=24 * 60 * 60)

if __name__ == "__main__":
    app.run(debug=app.config["DEBUG"])
