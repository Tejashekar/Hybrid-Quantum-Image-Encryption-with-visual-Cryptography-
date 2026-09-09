from __future__ import annotations

import os
import uuid

import cv2
import numpy as np
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

from src.metrics import correlation_analysis, entropy, npcr_uaci, psnr
from src.preprocessing import load_image, preprocess
from src.visual_cryptography import generate_shares, reconstruct_from_shares

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tif", "tiff"}

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"
app.config["UPLOAD_FOLDER"] = INPUT_DIR
app.config["OUTPUT_FOLDER"] = OUTPUT_DIR
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_directories() -> None:
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def unique_name(prefix: str, suffix: str = ".png") -> str:
    return f"{prefix}_{uuid.uuid4().hex}{suffix}"


def save_gray_image(image: np.ndarray, filename: str) -> None:
    cv2.imwrite(os.path.join(OUTPUT_DIR, filename), image)


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
    return render_template("index.html", state=pipeline_state())


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
# Static file serving
# ---------------------------------------------------------------------------

@app.route("/output/<path:filename>")
def serve_output_file(filename: str):
    return send_from_directory(OUTPUT_DIR, filename)


@app.route("/input/<path:filename>")
def serve_input_file(filename: str):
    return send_from_directory(INPUT_DIR, filename)


ensure_directories()

if __name__ == "__main__":
    app.run(debug=True)