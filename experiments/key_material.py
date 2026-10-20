"""Experiment-only key loading; never embeds or writes a secret key."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from src.key_derivation import validate_secret_key


def load_experiment_key() -> bytes:
    """Load a fixed reproducibility key from environment or ignored local file."""
    value = os.environ.get("QCRYPT_EXPERIMENT_KEY_HEX")
    if value is None:
        candidate = Path(".env.phase7.local")
        if candidate.is_file():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("QCRYPT_EXPERIMENT_KEY_HEX="):
                    value = line.split("=", 1)[1].strip()
                    break
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError("set QCRYPT_EXPERIMENT_KEY_HEX to a fixed 64-character hex key for reproducible experiments")
    try:
        key = bytes.fromhex(value)
    except ValueError as exc:
        raise ValueError("QCRYPT_EXPERIMENT_KEY_HEX must be hexadecimal") from exc
    return validate_secret_key(key)


def experiment_key_id(secret_key: bytes) -> str:
    return hashlib.sha256(validate_secret_key(secret_key)).hexdigest()
