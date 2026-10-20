# Table IV/V evidence audit — Q-CRYPT

Audit date: 2026-10-13 (Asia/Calcutta)

## Scope and verdict

The intended current archive is `experiments/results/phase6-security-v2/`. It is newer than v1 and v1.1 and matches the key model described in `docs/research/FINAL_IMPLEMENTATION_STATUS.md`: external 32-byte secret, public 16-byte nonce, HKDF domains, dense GF(256) diffusion, and artifact HMAC. v1 and v1.1 are explicitly historical, pre-independent-key archives. Their metadata lacks the v2 experiment key identifier and calls out older key-delta semantics; do not combine their values with v2.

**Critical provenance gap:** v2 metadata identifies seed 20261008, five content IDs, configurations, repetitions, preprocessing version, nonce policy, and secret-key SHA-256 identifier `0753b2ee0ced818c444fafa523b897ecadd816335cb92ef5d43a816b7e60f8a8`, but contains no source commit, code-tree hash, raw host/CPU/OS/timing environment, or retained test log. The checkout's visible Git commit is `dce17be25a472a6ec177a4001b15634740b588c3` (`Initial project import`, 2026-09-09); the working tree is heavily modified/untracked. Therefore the archived results are **not verifiably bound to this checkout**. The 2026-10-13 local rerun environment below is not evidence of the original timing environment.

The requested paper source is not present: no `sources/` directory, PDF, `.tex`, or other paper artifact was found in this repository. Thus literal row labels and paper claims for Tables IV/V cannot be inspected. Nothing under `sources/` was modified. Statuses below map documented experiment protocol and functional verification claims; exact paper-row-to-evidence mapping remains **not verifiable** until the table source is supplied.

Status meanings: **PASS** = concrete archived measurement or locally executed check; **FAIL** = concrete contrary evidence; **NOT RUN** = no execution evidence found; **NOT IMPLEMENTED** = code capability absent; **BLOCKED** = execution prevented by a stated missing prerequisite; **NOT VERIFIABLE** = evidence cannot establish the claim/provenance.

## Table IV — experimental protocol and measured outputs

| Protocol item | Status | Evidence and supported result | Limit |
|---|---|---|---|
| Current implementation / algorithm | PASS (code inspection) | `app.py`, `src/pipeline.py`, `src/key_derivation.py`, `src/diffusion.py`, `src/preprocessing.py`; current notes identify artifact format v5 and A–E configurations. | Archive-to-code version binding is NOT VERIFIABLE (no commit/hash in metadata). |
| Dataset inventory / independent samples | PASS (archived manifest + local test) | `experiments/manifests/phase5-center-crop-v1.json`: 7 files, 5 unique decoded contents; `experiments/results/phase6-security-v2/core_metrics.csv` has 5 content IDs per config and 25 rows/config. Test `test_phase6_unique_real_image_count_and_preprocessing_version` passed. | Five samples are small; not broad generalization. |
| Preprocessing protocol | PASS (source + manifest + archive fields) | `experiments/dataset_manifest.py`, `src/preprocessing.py`, manifest and v2 CSV: center-square crop, INTER_AREA to grayscale uint8 128×128; archive labels `center-square-crop-resize-grayscale-v1`. | Environment-specific OpenCV version at original run is NOT VERIFIABLE. |
| Configurations / thresholds | PASS (archived) | v2 metadata lists A–D and E_(2,2), E_(2,3), E_(3,5), E_(3,6); `experiments/phase6_security.py` defines the same set. | Archive/code hash binding NOT VERIFIABLE. |
| Fixed seed / deterministic nonce policy | PASS (recorded) | v2 metadata: seed 20261008; deterministic 16-byte SHA-256-derived nonce and separate alternate-purpose namespace; `nonce_sensitivity.csv` records same-nonce determinism True and different-nonce ciphertext differs True for each sample/config. | This is deterministic experiment policy, not proof of nonce safety under arbitrary reuse. |
| Secret-key policy / key sensitivity | PASS (recorded) | v2 metadata records key ID only; `key_sensitivity.csv` records five bit positions 0,63,127,191,255 per sample/config. One-bit key changes yield mean NPCR about 99.5% for A and 100% for B–E in the archived rows. | The key itself is intentionally absent; exact rerun is BLOCKED unless the external key matching the identifier is available. Empirical sensitivity is not key-strength proof. |
| Repetitions / metric sampling | PASS (recorded) | 5 timing repetitions × 5 images = n=25/config in `core_metrics.csv` / aggregates; plaintext deltas 1,2,127,128,255 in metadata and runner. | Do not treat repetitions on same five inputs as 25 independent images. |
| Ciphertext entropy | PASS (measured) | v2 `aggregates/configuration_summary.csv`: entropy means range 7.9880–7.9889 bits/byte across A–E configs (n=25/config). | Empirical statistic only. |
| Neighbor correlation | PASS (measured) | Same aggregate reports horizontal, vertical, diagonal means near zero (absolute values below 0.006 in the listed means). | Does not establish security. |
| Plaintext differential NPCR/UACI | PASS (measured) | Aggregate: B–E NPCR mean 100%; A NPCR mean 0.00610%. UACI means vary by config; e.g. B 25.327%, C 29.738%, D 20.955%; E configs 23.261–25.903%. | The archive labels means over five controlled plaintext deltas; not a cryptographic proof. |
| Dense diffusion one-byte property | PASS (archived property check + local tests) | `dense_diffusion_property.csv` and summary: 5 images × 5 deltas/config, output XOR occupancy 100% in recorded B–E trials; `tests/test_dense_gf256_diffusion.py`, `tests/test_phase6_security.py` exercise it. | Property is at diffusion input for a controlled one-byte difference; not universal end-to-end avalanche. |
| Runtime | PASS (archive only) | `performance_summary.csv` records 25 observations/config. Mean encryption ms: A 1.514, B 15.185, C 14.995, D 27.216, E configs 21.263–25.725. Decryption means: A 1.564, B 10.064, C 10.041, D 22.867, E 21.263–22.341. | Original hardware/software/timing environment is absent; values are not portable and cannot be reproduced from metadata alone. |
| Threshold reconstruction / rejection | PASS (archive) | `threshold_summary.csv`: valid subsets 5/5, 15/15, 50/50, 100/100 for (2,2),(2,3),(3,5),(3,6); insufficient-share rejection 5/5 each. `threshold_results.csv` contains the trial rows. | Applies to archived ciphertext/share samples, not information-theoretic security. |
| Peak memory | NOT IMPLEMENTED | v2 README explicitly says no existing memory instrumentation. | No value can be reported. |
| Published scheme comparison | NOT RUN / NOT VERIFIABLE | `published_comparison_template.csv` is an empty template; README says no sourced comparisons available. | No comparative numerical claim supported. |
| Original experiment command and environment | NOT VERIFIABLE | Notes give intended commands in `docs/research/FINAL_IMPLEMENTATION_STATUS.md`; no execution log, dependency lock snapshot, source hash, host or CPU metadata retained. | Command documentation is not evidence the archived run used that exact environment. |

## Table V — functional verification evidence

| Functional item | Status | Evidence | Limit |
|---|---|---|---|
| Key length validation / KDF domains | PASS (tests run) | `tests/test_key_derivation.py`, `tests/test_integrated_pipeline.py`; relevant test files included in the local run below. | Current checkout only; archive provenance remains unbound. |
| Deterministic encryption for fixed key/nonce | PASS (tests run) | `tests/test_integrated_pipeline.py`, `tests/test_phase6_security.py`; local run passed. | Determinism under fixed nonce does not recommend production nonce reuse. |
| Authenticated decryption / wrong key rejection | PASS (tests run) | `src/key_derivation.py`, `src/pipeline.py`, `tests/test_integrated_pipeline.py`; local run passed. | HMAC detects tampering/wrong key; not a formal proof of a standard AEAD construction. |
| Exact round trip A–E | PASS (tests run) | `tests/test_integrated_pipeline.py`, `tests/test_threshold_pipeline_integration.py`; local run passed. v2 core rows mark `round_trip_exact=True`. | `round_trip_exact` archive field supports observed experiment cases only. |
| Threshold valid subsets and insufficient-share rejection | PASS (tests run + archive) | `src/visual_cryptography.py`, `tests/test_threshold_pipeline_integration.py`, `tests/test_phase6_security.py`; archive counts above. | The data are GF(256) shares, not optical visual cryptography. |
| Dataset duplicate handling / preprocessing | PASS (tests run) | `experiments/dataset_manifest.py`, `tests/test_preprocessing_dataset.py`, Phase 5 manifest; local test passed. | No broad external dataset verification. |
| Dense diffusion property | PASS (tests run) | `src/diffusion.py`, `tests/test_dense_gf256_diffusion.py`, `tests/test_phase6_security.py`; local run passed. | Narrow controlled property only. |
| Qiskit basis validation | NOT RUN in this audit; prior claim NOT VERIFIABLE | Test source `tests/test_qiskit_validation.py`; notes describe small-register checks in `docs/research/QISKIT_VALIDATION.md`. | No prior test log found; does not indicate 128×128 quantum execution or hardware. |
| Full 263-case suite and frontend checks | NOT VERIFIABLE (prior note only) | `docs/research/FINAL_IMPLEMENTATION_STATUS.md` claims 263 pytest cases plus ESLint/TypeScript/build/diff-check, but no logs or exact commands are retained. | This audit ran a focused subset, not the complete suite or frontend checks. |
| Table V literal row mapping | NOT VERIFIABLE | Paper/table source absent from repo. | Need the paper PDF or editable source to map every printed row exactly. |

## Tests run in this audit

Command (from repository directory `quantum-image-encryption-vc/`):

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_phase6_security.py tests/test_integrated_pipeline.py tests/test_threshold_pipeline_integration.py tests/test_preprocessing_dataset.py tests/test_dense_gf256_diffusion.py
```

Exit status: **0**. Output: **113 passed in 15.76s**.

Environment: Windows PowerShell; Python **3.11.9**; NumPy **2.4.6**; OpenCV **5.0.0**; pytest **9.1.1**; venv also imported required dependencies successfully. This was a focused non-destructive run; tests use temporary output paths. No packages were installed, no experiment archive was changed, and no tests were run from or against `sources/`.

No persistent test log was present before this audit. The command/output above are recorded here. Qiskit test, full suite, frontend ESLint/TypeScript/build, and experiment regeneration were not run. Regenerating phase6 v2 is not appropriate for this audit: the original external key and timing environment are not captured in the repository, and existing results must remain unchanged.

## Discrepancies and next steps

1. Supply/restore the actual paper PDF or editable source. Then compare its exact Table IV/V rows against this report; no LaTeX was changed because none is present.
2. Before publishing timing or code-specific claims, rerun into a new versioned result directory and add a provenance sidecar: exact source commit and dirty-tree diff hash, Python/package lock versions, OS/CPU, command, manifest hash, configuration, seed, repetition policy, and key ID. Preserve raw CSVs.
3. Preserve the external experiment key securely if exact v2 reproduction is required; compare its SHA-256 identifier before running. Never add the key to tracked files.
4. Capture full pytest and frontend command logs before retaining the project note's 263-case / frontend pass statement as independently auditable test evidence.
5. Keep v1/v1.1 labeled historical; do not pool or substitute their results for v2. Keep the five-image limitation, crop information loss, and distinction between empirical metrics and security proof in any revised table caption/notes.

## Recommended LaTeX handling

No exact Table IV/V replacement is safe without their actual row text. Where the current paper says the dataset has seven independent samples, update it to **7 image files / 5 unique decoded contents**. Where it reports these timing results, cite the v2 values above and disclose that original timing hardware/software metadata and source commit binding are missing. Do not state a full-suite pass based solely on the status note; identify it as an unverified project-note claim until logs are retained. Do not invent memory or published-comparison values.
