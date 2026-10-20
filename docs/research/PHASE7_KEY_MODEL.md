# Phase 7 key-management model

## Key flow

The active A–E research API requires an independent 32-byte secret key. The caller supplies it; it is not derived from public parameters, the image, or the nonce. A fresh 16-byte nonce is generated with `secrets.token_bytes` unless a caller explicitly supplies one for reproducible experiments.

HKDF-SHA-256 (RFC 5869) uses `salt=nonce` and `IKM=secret_key`. Each expansion has an explicit domain label and canonical JSON context:

| Domain | Use |
|---|---|
| `QCRYPT diffusion` | Logistic initialization for the dense-diffusion mask |
| `QCRYPT chaotic` | Logistic initialization for the B/D/E chaotic XOR stream |
| `QCRYPT scalar` | Candidate-3 scalar `c = 2 + (derived_byte mod 254)` |
| `QCRYPT xor` | XOR stream for A/C and other keyed XOR use |
| `QCRYPT sharing` | Coefficient bytes supplied to unchanged GF(2^8) sharing equations |
| `QCRYPT authentication` | HMAC-SHA-256 artifact authentication key |

Each label is prefixed with `QCRYPT/phase7/` and separated from its serialized context. The chaotic map remains a deterministic research transform, not a cryptographic KDF or cryptographically secure PRNG. Candidate 3 has no active IV; the old IV compatibility bytes returned by the diffusion-material helper are not used by the active pipeline.

## Artifact fields and secret handling

Public artifact information includes format version 5, configuration identifier and reproducibility parameters, image dimensions, nonce, and an HMAC-SHA-256 tag over the public metadata and ciphertext. It excludes the secret key, KDF outputs, masks, scalar, key streams, share coefficients, and secret seeds. A missing/invalid tag or wrong key is rejected before inversion. Legacy formats are rejected explicitly rather than silently interpreted as version 5.

The HMAC detects wrong keys and artifact modification; it does not make the underlying reversible construction a standardized authenticated-encryption scheme. No cryptographic-security conclusion follows from this architecture change alone.

## Experiment key handling

Set `QCRYPT_EXPERIMENT_KEY_HEX` in the process environment, or put the setting in the ignored local `.env.phase7.local`. Keep the 32-byte key outside tracked source and result archives. Experiment outputs record only a SHA-256 key identifier and the nonce policy. A deterministic nonce may be supplied for repeatability; nonce reuse with the same key is undesirable in deployment.

The Flask endpoints accept `secret_key_hex` as 64 hex characters on each encryption and reconstruction request. Optional `nonce_hex` is exactly 32 hex characters. Flask does not put the secret key in session state, responses, or artifact metadata. The current Next.js UI has no key-entry control and does not persist a key; keyed API operations require an API caller until the UI supports secure transient key entry.

## Key-space interpretation

The caller-supplied key has 2^256 theoretical values. The nonce has 2^128 public values and is not part of secret-key size. Configuration parameters form a separate public reproducibility domain. Key length is not an effective-security estimate; the complete construction and implementation have not been established as conventional secure encryption.
