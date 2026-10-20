# Q-CRYPT Research Interface

Q-CRYPT presents a configurable hybrid image encryption and threshold sharing research pipeline with measurements for recovery, security properties, and storage costs.

The active application architecture is a **Flask backend/API with a Next.js frontend**. The 128×128 large-image workflow is a **classical simulation of quantum-inspired transformations**; it does not execute on physical quantum hardware and is not post-quantum cryptography. Threshold sharing is GF(2^8)-based, with XOR as field addition; it is computational image sharing rather than optical visual cryptography.

## Research configurations

- **A** — Classical XOR baseline
- **B** — Logistic chaotic material + XOR + dense GF(256) diffusion
- **C** — Quantum-inspired reversible transformations + XOR + dense GF(256) diffusion
- **D** — Logistic material + Arnold scrambling + quantum-inspired transformations + XOR + dense GF(256) diffusion
- **E** — D followed by GF(256)-based k-of-n threshold secret sharing

Supported E thresholds are (2,2), (2,3), (3,5), and (3,6). The validated research API is implemented in `src/pipeline.py`; the web interface calls those research primitives and the metric functions in `src/metrics.py`. The experiment runner and result files remain independent of the web interface.

The quantum-inspired layer applies a reversible bit-mixing analogue `(a,b) → (a XOR b,a)`, CNOT-inspired controlled XOR, an X-inspired bit flip, and a nonce-derived Z-inspired conditional bit rotation. These are classical reversible operations; the byte rotation is not a quantum Z phase operation.

Qiskit 2.3.0 is used only for small-scale validation of selected computational-basis correspondences between the classical reversible operations and explicitly constructed quantum circuits. The X-inspired bit flip, CNOT-inspired controlled XOR, and reversible bit-mixing analogue are exhaustively checked over their selected basis states. The genuine quantum Z gate is demonstrated separately as a phase operation; it is not the same transformation as the repository's conditional byte rotation. These checks do not establish equivalence for arbitrary superpositions. See [the Qiskit validation note](docs/research/QISKIT_VALIDATION.md) for scope and test details.

The main 128×128 workflow remains a classical simulation of quantum-inspired transformations. Qiskit does not execute the complete image pipeline, no quantum hardware execution or quantum advantage is claimed, and no post-quantum security claim is made.

For A–E, each encryption generates a fresh 16-byte public nonce. Key-separated HKDF material supplies each configuration's required keyed bytes; B–E also use nonce-bound Logistic material for the dense GF(256) diffusion and transformations. The dense transform uses polynomial `0x11B`. Ciphertext artifacts do not store masks, scalars, controls, or key streams. Configuration A remains the classical XOR baseline.

## Secret-key model (artifact format 5)

The active A–E research API requires a caller-supplied **32-byte (256-bit) secret key**. It is combined with a separate public 16-byte nonce through HKDF-SHA-256 (RFC 5869). Key separation uses the domain labels `QCRYPT diffusion`, `QCRYPT chaotic`, `QCRYPT scalar`, `QCRYPT xor`, `QCRYPT sharing`, and `QCRYPT authentication`; public configuration and dimensions are included as derivation context. Candidate-3's `c` is derived from the scalar domain as `2 + (byte mod 254)`. The active dense diffusion does not require an IV. The key, KDF outputs, masks, and generated streams are never serialized. Version-5 artifacts carry the nonce, public configuration/version metadata, and an HMAC-SHA-256 integrity tag; versions without this authenticated metadata are explicitly rejected by the new API.

The theoretical secret-key input space is 2^256 possibilities; the public nonce space is 2^128 and is not added to the secret-key size. Key length alone does not establish an effective security level, and the complete construction has not been established as conventional secure encryption. Reusing a nonce with the same key is undesirable. To reproduce experiments, set `QCRYPT_EXPERIMENT_KEY_HEX` to a fixed 64-character hex key held outside tracked files, or use the ignored `.env.phase7.local`; result metadata records only a SHA-256 key identifier. The browser UI currently has no secret-key entry, so keyed operations must use the API client or research API until the UI is extended. Never persist the key in browser storage.

For Flask JSON endpoints, provide `secret_key_hex` (64 hex characters) on both `/api/encrypt` and `/api/reconstruct`; an optional `nonce_hex` (32 hex characters) is accepted for reproducible encryption. The key is not retained in Flask session state or returned in responses.

## Current real-image experiment

The preserved prior real-image result archive contains **56 successful result rows**. Its source directory contains seven filenames, but two pairs decode to duplicate image contents, leaving **five unique decoded image contents**. These results must not be described as seven independent images; this is a limitation of the current repository dataset. Corrected input handling and the center-crop preprocessing protocol are documented in [DATASET_PROTOCOL.md](docs/research/DATASET_PROTOCOL.md); new runs use a versioned output directory and do not overwrite this historical archive by default.

## Run the application

Start Flask first, then start the Next.js development server in a second terminal. Visiting `http://localhost:5000` redirects to the frontend at `http://localhost:3000`.

Install Python dependencies from the repository root:

```powershell
pip install -r requirements.txt
```

Install the existing Next.js dependencies:

```powershell
cd frontend
npm ci
```

Start Flask from a terminal at the repository root:

```powershell
python app.py
```

In another terminal, start the frontend:

```powershell
cd frontend
npm run dev
```

Open `http://localhost:5000`. Flask redirects the browser to the Q-CRYPT frontend at `http://localhost:3000`. The Next.js development server proxies `/api`, `/input`, and `/output` requests to Flask on port 5000, so Flask must remain running while using the frontend. The older server-rendered templates remain in the repository but are no longer served as the home page.

To use a different frontend address, set `FRONTEND_URL` before starting Flask. For example, in PowerShell: `$env:FRONTEND_URL = "http://localhost:3000"`.

For local development, the app starts without additional secret configuration; it generates a temporary runtime session key when `FLASK_SECRET_KEY` is not provided. You may set `FLASK_SECRET_KEY` in the process environment to use a consistent local session key. Debug mode is off by default and can be explicitly enabled for development with `FLASK_DEBUG=true`.

For network deployment, configure a strong `FLASK_SECRET_KEY`, keep Flask debug mode disabled, and serve the application through a production WSGI server. Do not use Flask's development server for deployment.

## API

- `GET /api/state` — current browser session state
- `POST /api/upload` — preprocess an explicitly supplied image to grayscale uint8 128×128
- `POST /api/encrypt` — run A–E with the selected configuration and threshold
- `POST /api/reconstruct` — decrypt A–D, or reconstruct and decrypt E from selected share indices
- `GET /api/experiment-results` — read the existing real-image JSON results

Uploads must decode as supported image formats. Invalid images and unsupported thresholds return errors; the upload endpoint does not fall back to synthetic input. API images and derived outputs use the ignored `input/` and `output/` working directories for the active browser session. A successful replacement upload clears that session's prior artifacts, and startup prunes API artifacts older than 24 hours.

## Validation

Run the existing research suite:

```powershell
python -m pytest -q
```

Build the frontend:

```powershell
cd frontend
npm run build
npm run lint
```

## Project structure

```text
app.py                         Flask pages and research JSON API
src/                           Encryption, sharing, preprocessing, and metrics
tests/                         Research and integration tests
experiments/run_experiments.py Reproducible experiment runner
experiments/results/           Existing JSON and CSV experiment outputs
frontend/                      Next.js research interface
templates/                     Retained Flask templates
```
