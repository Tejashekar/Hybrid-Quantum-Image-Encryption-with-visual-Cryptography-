# Q-CRYPT Paper 1 evidence report

## Scope and handling

Evidence was collected from the checked-out repository at commit `dce17be25a472a6ec177a4001b15634740b588c3`. The working tree was **already dirty before this evidence folder was created**. Those existing changes are listed in `run_provenance.json` and were preserved. All evidence files and the orchestration helper are under `paper1_evidence/`; `src/`, `tests/`, and the archived `experiments/results/phase6-security-v2/` were not intentionally changed.

Controlled cryptographic evidence uses only the fixed TEST key bytes(range(32)) and TEST nonce bytes(16), identified by that descriptor in each corresponding CSV/README. The key bytes and nonce bytes were not printed or stored. No `.env` contents were read. No package was installed and no network was used.

## T0 — Provenance

- **Status:** COMPLETE; dirty baseline flagged.
- **Command:** `git rev-parse HEAD`; `git branch --show-current`; `git status --porcelain`; `.venv/Scripts/python.exe` package/platform query; CPU name from the Windows processor registry.
- **Result:** commit `dce17be25a472a6ec177a4001b15634740b588c3`, branch `main`; working tree dirty with the preexisting modifications/untracked files listed in `run_provenance.json`. Python 3.11.9; Windows 10 build 26200; AMD Ryzen 5 7535U; 12 logical CPUs. NumPy 2.4.2, OpenCV 4.13.0.92, SciPy 1.17.1, Flask 3.1.3, Qiskit 2.3.0, pytest 9.0.2; `cryptography` package absent.
- **Key availability:** checked presence only; environment variable `QCRYPT_EXPERIMENT_KEY_HEX` unset and configured fallback absent. No value was read.
- **Files:** `run_provenance.json`.
- **Contradiction:** the tree is not clean, so provenance represents the already-modified checkout, not an unmodified commit-only build.

## T1 — Source facts

- **Status:** COMPLETE for code present in this checkout.
- **Command:** read-only inspection of `src/pipeline.py`, `src/diffusion.py`, `src/key_derivation.py`, `src/chaotic_key.py`, `src/quantum_encryption.py`, `src/visual_cryptography.py`, `src/metrics.py`, `src/preprocessing.py`, `app.py`, and experiment runner/aggregator sources.
- **Result:** operation/inverse order A-D, dense GF(256) equation and inverse, HKDF extract/expand/context/chunking, stream generation, reversible transforms, authentication, nonce behavior, v5 artifact fields and metrics are documented with file:line references in `SOURCE_FACTS.md`.
- **Files:** `SOURCE_FACTS.md`.
- **Corrections/contradictions:** dense diffusion remains invertible for even and odd element counts; no even-size-only condition applies because `c XOR (m mod 2)` is nonzero for `c` in [2,255]. The chaotic-stream docstring says bits 32–39, but its implementation takes the low byte of `floor(state*2^40)`. No nonce-reuse enforcement was found in the encryption path. Timing summaries use population SD (`ddof=0`); T5 plaintext summaries here use sample SD (`ddof=1`).

## T2 — Full test suite

- **Status:** COMPLETE; 263 passed, 0 failed.
- **Command:** `.venv/Scripts/python.exe -m pytest -v`.
- **Result:** `263 passed in 26.43s`.
- **Files:** `test_suite.log`.
- **Notes:** this executes the repository's own unit tests using their test fixtures; no experiment key or real image artifacts were used.

## T3 — Affine-structure test

- **Status:** COMPLETE.
- **Command:** `.venv/Scripts/python.exe paper1_evidence/collect_controlled.py` (200 trials/configuration, seeded NumPy generator; encryption through `app._api_direct_encrypt_artifact`).
- **Result:** A, B, C and D each had 0 nonzero residues in 200 trials. All tested maps satisfy the affine identity over GF(2) for these fixed settings. This matches source structure: XORs, fixed GF multiplications/reductions, fixed rotations/bit maps and the Arnold permutation are affine/linear maps when the key and nonce are held fixed. It is a finite test, not a security proof.
- **Files:** `affine_test.csv`; helper `collect_controlled.py`; `controlled_run.log`.
- **TEST descriptor:** included in CSV.

## T4 — Constant-difference test

- **Status:** COMPLETE.
- **Command:** controlled helper; project encryptor, `derive_diffusion_scalar`, and project GF(256) multiplier.
- **Result:** A produced one XOR value, `0xff`, at all 16,384 positions. B produced one constant value, `0xf4`, at all positions. Under TEST settings the project scalar was 197 and project GF(256) multiplication gave `197 · 255 = 0xf4` using polynomial `0x11B`, matching the observed B value. C and D each produced two distinct XOR values. Thus the constant-XOR part of the B hypothesis is supported; the value is TEST-key-specific and does not validate the earlier experiment-key `0x6c` observation or inferred scalar 124.
- **Files:** `constant_diff.csv`.
- **TEST descriptor:** included in each row.

## T5 — Plaintext statistics

- **Status:** COMPLETE.
- **Command:** controlled helper called `cv2.imread(..., IMREAD_UNCHANGED)`, project `src.preprocessing.preprocess`, and `src.metrics.entropy`/`neighboring_correlations`; deduplication helper hashed preprocessed C-order bytes with SHA-256.
- **Result:** 7 files yielded 5 unique preprocessed arrays. Metrics include every horizontal, vertical and down-right diagonal neighboring pair. Mean (sample SD, `ddof=1`) over the 5 unique contents: entropy 7.429446 (0.289539); horizontal correlation 0.930077 (0.040919); vertical 0.937065 (0.040463); diagonal 0.896506 (0.062684). Full per-image values are in the CSV.
- **Files:** `plain/image-001.npy` through `image-005.npy`, corresponding PNGs, `plain/plaintext_metrics.csv`, `plain/plaintext_summary.csv`, `plain/input_inventory.csv`, `plain/README.md`.
- **Notes:** plaintext-only measurements do not require a key; no content digests were saved.

## T6 — Figure 4 assets

- **Status:** COMPLETE for regenerated TEST-key rasters.
- **Command:** controlled helper selected the source content matching v2 manifest `image-001`, then used the project encryptor/decryptor and project entropy metric for A-D.
- **Result:** all four decrypted arrays exactly equal the preprocessed `image-001` array. Ciphertext entropies: A 7.989083, B 7.988050, C 7.986569, D 7.988701 bits/pixel. These are TEST-key ciphertexts, **not** ciphertexts from the archived experiment key.
- **Files:** `fig4/image-001_{A,B,C,D}.npy`, PNGs, per-configuration 256-bin histogram CSVs, `fig4/round_trip_summary.csv`, `fig4/README.md`.
- **TEST descriptor:** README, summary and histogram rows identify TEST key/nonce.

## T7 — Structured inputs

- **Status:** COMPLETE for A-D, all-zero and all-255 inputs.
- **Command:** controlled helper used the project API encryptor and `src.metrics.entropy`, `npcr`, and `uaci`.
- **Result:** detailed ciphertext entropies and pairwise NPCR/UACI are in `structured_inputs.csv`. Both constant inputs produced 100% NPCR for every A-D pair. UACI: A 50.282006%; B 49.967831%; C 10.785558%; D 50.138179%. This does not mean C failed round-trip; it is a two-input ciphertext comparison only.
- **Files:** `structured_inputs.csv`.
- **TEST descriptor:** included on each row.

## T8 — Phase 6 v2 rerun

- **Status:** BLOCKED as required; no run, no substitute key.
- **Command:** presence-only checks for `$env:QCRYPT_EXPERIMENT_KEY_HEX` and the configured fallback; loader source inspected at `experiments/key_material.py:11-27`.
- **Result:** variable unset and fallback file absent. Required to continue is the original experiment key made available through the configured `QCRYPT_EXPERIMENT_KEY_HEX` environment variable. No key value was read, printed, generated or written. The runner's current configuration list includes A-D plus four E threshold configurations, while the task says A-D; this protocol discrepancy also needs resolution for an exact A-D-only comparison.
- **Files:** `rerun_v2/README.md`, `rerun_comparison.md`. No `run.log` or rerun CSVs exist because no run occurred.
- **Archived folder:** not written to. No per-file comparisons were possible; no mismatches are claimed.

## T9 — Wu et al. critical values

- **Status:** COMPLETE; formulas sanity-checked at both image sizes.
- **Command:** controlled helper implemented normal critical values and read only per-trial archived v2 CSV metrics; no experiment key was loaded.
- **Result:** at N=65,536, computed NPCR 99.5693% and UACI [33.2824,33.6447]%, matching the specified published values. At N=16,384, NPCR 99.5292% and UACI [33.1012,33.8259]%, matching the specified values. Counts below require **both** NPCR and UACI tests to pass:

| Configuration | Key-flip trials | Alternate-nonce trials | Plaintext-delta trials |
|---|---:|---:|---:|
| A | 25/25 | 5/5 | 0/25 |
| B | 23/25 | 3/5 | 0/25 |
| C | 24/25 | 5/5 | 0/25 |
| D | 22/25 | 5/5 | 0/25 |

- **Files:** `wu_pass_counts.csv`, `wu_threshold_validation.md`; source data: per-trial rows in archived `key_sensitivity.csv`, `nonce_sensitivity.csv`, and `differential_analysis.csv`.
- **Correction:** these are individual pass counts, not pass rates inferred from means. The earlier claim that all key-flip and nonce means fall inside the limits does not imply every trial passes; A plaintext-delta trials do not pass either test combination.

## T10 — Qiskit validation

- **Status:** COMPLETE; 4 passed.
- **Command:** print installed Qiskit version, then `.venv/Scripts/python.exe -m pytest -v tests/test_qiskit_validation.py`.
- **Result:** Qiskit 2.3.0; `4 passed in 1.51s`.
- **Files:** `qiskit_validation.log`.

## T11 — Sequential-diffusion history

- **Status:** NONE FOUND for the requested earlier cancellation/differential experiment.
- **Searches:** `git log --all` commit-message search for sequential/diffusion/cancel/cancellation; `git log --all -S` searches across `src`, `experiments`, and `docs` for sequential/cancellation/cancelled/canceled; text search over source, docs and experiment documentation/diagnostics; inspection of v1.1/v2 dense-diffusion experiment CSV headers/representative values.
- **Result:** no matching historical commit or output describing sequential-diffusion cancellation was found in the available local history/files. Existing v2 dense property data records 100% output XOR occupancy for the tested single-byte differences, which supports that narrow dense-stage property only; it is not evidence of the earlier sequential cancellation experiment. No commit hash/date or measured cancellation value can be reported.
- **Files:** this report.

## T12 — Paper marker map

- **Status:** UNRESOLVED; the source manuscript is missing.
- **Command:** `Test-Path paper1_prism/qcrypt_paper1.tex` and repository file inventory/search.
- **Result:** no `paper1_prism/` directory or requested `.tex` file is present. Therefore markers could not be enumerated and exact insertion text cannot be mapped without inventing marker locations/counts.
- **Files:** `marker_map.md` records the unresolved status. No `.tex` file was edited.

## Open issues

1. **T8 reproduction requires the original experiment key** through the configured loader path; keep the value outside all reports/evidence. Resolve whether the rerun protocol is A-D only or includes the runner's four E configurations.
2. **T12 requires the Prism source file** `paper1_prism/qcrypt_paper1.tex` in the repository to enumerate every marker and give exact insertion text.
3. **Sequential-diffusion cancellation claim lacks local evidence.** Do not state its prior measured behavior until the earlier experiment output or revision is supplied.
4. The TEST-key Figure 4 assets are reproducible controlled replacements, not archived experiment-key ciphertexts. Label them as TEST-key output if used in a paper figure.
5. The current tree began dirty. Provenance findings apply to the recorded checkout state, and none of the baseline edits were cleaned or rewritten.

## Final self-check

- A content-hash comparison against the pre-test capture found no changes to files under `src/` or `tests/`. `git diff --stat -- src tests` is still nonempty because those paths already had user/project edits at baseline; the original dirty status is recorded in `run_provenance.json`.
- A content-hash comparison found `experiments/results/phase6-security-v2/` unchanged.
- A recursive scan of `paper1_evidence/` found no 64-hex-character strings and no literal private key-file name. The experiment-key environment variable was unset, and no environment-variable value or key bytes were read or recorded.
