# Q-CRYPT final implementation status

## 1. Project overview

Q-CRYPT is a configurable image-encryption and threshold-sharing research prototype. Its active application uses a Flask backend/API and a Next.js frontend. It is not a claim of conventional secure encryption, post-quantum security, or quantum advantage.

## 2. Final architecture

The 128×128 image path is a classical simulation of quantum-inspired reversible transformations. The active cipher uses a caller-supplied 32-byte key, a separate public 16-byte nonce, domain-separated HKDF-SHA-256 material, dense GF(256) diffusion for B–E, and HMAC-SHA-256 artifact authentication. The algorithm identifier and artifact format are version 5. Authentication detects a wrong key or modified artifact; it does not provide confidentiality by itself or establish a formally analyzed authenticated-encryption construction.

## 3. Security and key model

- **Secret:** caller-supplied 32-byte / 256-bit key.
- **Public:** 16-byte / 128-bit nonce, configuration identifier, algorithm/artifact version, image dimensions, and required preprocessing metadata.
- **Derived:** HKDF outputs, chaotic initialization material, masks, scalar `c`, XOR material, authentication key, and threshold-sharing coefficients.

The key and derived secret material are not serialized. Candidate-3 `c` is derived from the key-controlled scalar domain. The nonce is public and is not added to key length. A theoretical 2^256 key-input space is not evidence of 256-bit effective security. Do not reuse a nonce with the same key in deployment.

The Flask JSON endpoints accept `secret_key_hex` with exactly 64 hex characters; reconstruction requires the same key. An optional `nonce_hex` is available for deterministic experiment runs. The current browser interface does not have a key-entry control and does not persist keys; use a direct API/research caller for keyed operations.

## 4. Configurations A–E

- **A:** classical XOR baseline.
- **B:** Logistic chaotic material + XOR + dense GF(256) diffusion.
- **C:** quantum-inspired reversible transformations + XOR + dense GF(256) diffusion.
- **D:** Logistic material + Arnold scrambling + quantum-inspired transformations + XOR + dense GF(256) diffusion.
- **E:** D followed by GF(256)-based threshold secret sharing.

Supported E thresholds are (2,2), (2,3), (3,5), and (3,6). Sharing uses GF(2^8) with XOR field addition; it is not optical visual cryptography.

## 5. Dataset and preprocessing

The available real-image directory has seven filenames but only five unique decoded image contents. The Phase-5 manifest is [phase5-center-crop-v1.json](../../experiments/manifests/phase5-center-crop-v1.json), and the protocol is [DATASET_PROTOCOL.md](DATASET_PROTOCOL.md). Preprocessing uses the largest centered square crop, OpenCV `INTER_AREA` resize, grayscale `uint8`, and 128×128 output. Cropping discards content outside the crop and resizing changes resolution. Encryption/decryption is lossless relative to the preprocessed plaintext, not the full-resolution source.

## 6. Qiskit validation

Qiskit 2.3.0 is used only for small-register validation of selected computational-basis correspondences. It does not execute the 128×128 pipeline, demonstrate quantum hardware execution, or establish arbitrary-superposition equivalence. See [QISKIT_VALIDATION.md](QISKIT_VALIDATION.md).

## 7. Experimental result versions

- `experiments/results/phase6-security-v1/` and `phase6-security-v1.1/` are preserved historical archives from before the independent secret-key model.
- `experiments/results/phase6-security-v2/` is the current key-model evaluation and records only a non-secret SHA-256 key identifier. It used five unique images and five timing repetitions; key sensitivity flips one controlled key bit at each of five positions.
- Older Phase-5 and other experiment outputs remain historical evidence. They have not been deleted or silently regenerated.

The current dataset is small. Entropy, correlation, NPCR/UACI, keystream statistics, and key sensitivity are empirical measurements, not cryptographic security proofs. The chaotic-generator statistics do not prove cryptographic randomness. There is no formal end-to-end security proof. Timing depends on the hardware and software environment.

## 8. Reproducibility procedure

1. Install Python dependencies from `requirements.txt` and frontend dependencies with `npm ci` in `frontend/`.
2. Provide a fixed 32-byte experiment-only key through `QCRYPT_EXPERIMENT_KEY_HEX` (64 hexadecimal characters) or the ignored local `.env.phase7.local`. Keep the actual value outside tracked files. Outputs record only its SHA-256 identifier.
3. Run the security evaluation from the repository root:

   ```powershell
   .venv\Scripts\python.exe -m experiments.phase6_security --output-dir experiments/results/phase6-security-v2 --seed 20261008
   .venv\Scripts\python.exe -m experiments.aggregate_phase6 --results-dir experiments/results/phase6-security-v2
   ```

   Choose a new output directory if the target already exists; the runner protects existing result archives. The dataset manifest, preprocessing version, fixed seed, deterministic public nonce policy, five-image count, repetitions, and metric implementation are recorded in the result README and metadata.
4. For the application, start Flask with `python app.py`, then run `npm run dev` from `frontend/`. The Next.js development server proxies its requests to Flask on port 5000.

## 9. Known limitations

1. Only five unique real-image contents are available; broad statistical generalization is unsupported.
2. Large-image quantum processing is not performed; the workflow is classical simulation.
3. Qiskit validation is small-scale and computational-basis based.
4. Chaotic-generator statistics do not prove cryptographic randomness.
5. NPCR/UACI and other empirical metrics do not prove cryptographic security.
6. The complete construction has no formal end-to-end cryptographic security proof.
7. Timing measurements vary with hardware and software environment.
8. Center cropping discards information outside the crop.
9. Exact decryption applies to the preprocessed plaintext representation.
10. The theoretical 2^256 key-input space is not a proof of 256-bit security.
11. The browser UI currently has no secure transient key-entry control.

## 10. Test status

The final Phase 8 audit run passed **263 pytest cases**. ESLint, TypeScript, the Next.js production build, and `git diff --check` passed. Tests cover key-size validation, KDF domain separation, deterministic encryption with fixed key/nonce, nonce and key sensitivity, HMAC failure handling, exact A–E reconstruction, threshold rejection, dense-diffusion properties, Qiskit basis checks, deterministic preprocessing, and duplicate-content handling.

## 11. Deployment and historical components

For deployment, supply a strong `FLASK_SECRET_KEY`, keep Flask debug mode disabled, and run Flask behind a production WSGI server. The default Flask server is for local development. Historical Jinja templates, the earlier UI documentation, and older experiment result archives are intentionally retained. `docs/implementation/04_encryption_pipeline.md` and `docs/research/IMPLEMENTATION_PLAN.md` are labeled historical/superseded; `docs/implementation/07_ui_integration.md` describes the earlier UI.