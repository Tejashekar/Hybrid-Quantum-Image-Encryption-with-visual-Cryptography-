c# Table IV/V revision notes

Date: 2026-10-14 (Asia/Calcutta)

## Source search and scope

Read `docs/research/TABLE_IV_V_EVIDENCE_AUDIT.md` as the evidence baseline. Searched the repository for `main.tex`, all `*.tex`, `*.cls`, `*.sty`, `*.bib`, `*.pdf`, a `sources/` directory, included table files, and prior revision notes. None are present. No actual IEEE manuscript or table rows could be opened, so **no manuscript or table row has been changed**. This avoids fabricating a paper or silently replacing its content.

LaTeX compilation was **not run**: there is no LaTeX source to compile. Because the tables are unavailable, it is not possible to verify existing row-by-row wording, IEEE two-column layout, or whether the paper already contains correct evidence.

## Row-level disposition

The items below are the audit's evidence rows, not a claim that these are the literal rows in the absent manuscript. Once `main.tex` and its included table files are restored, map each actual row to the corresponding evidence and revise only Tables IV and V.

### Table IV — Experimental Protocol

| Audit evidence row | Disposition for paper | Evidence / reason |
|---|---|---|
| Current implementation / algorithm | Do not claim archived results are tied to this exact source version; mark source binding not verifiable. | Audit: v2 metadata has no source commit/tree hash; checkout is dirty. |
| Dataset inventory / independent samples | If the paper states sample count, supported wording is 7 files representing 5 unique decoded contents; disclose the five-sample limitation. | `experiments/manifests/phase5-center-crop-v1.json`; v2 core metrics. |
| Preprocessing protocol | Evidence supports center-square crop, INTER_AREA resize, grayscale uint8, 128×128. | Dataset manifest, `experiments/dataset_manifest.py`, v2 CSV metadata. Original OpenCV version is not recorded. |
| Configurations / thresholds | Supported as A–D and E thresholds (2,2), (2,3), (3,5), (3,6) in v2. | `run_metadata.json`, `experiments/phase6_security.py`. Archive-to-source binding remains not verifiable. |
| Seed / nonce policy | Supported as recorded v2 protocol: seed 20261008 and deterministic public 16-byte nonce derivation. | v2 `run_metadata.json`, `nonce_sensitivity.csv`. This is protocol evidence, not a nonce security claim. |
| Secret-key policy / sensitivity | Supported as key-ID-only archive and five controlled key-bit positions. Do not state effective security from sensitivity results. | v2 metadata and `key_sensitivity.csv`; reproduce is blocked without the separately held key. |
| Repetitions / sampling | Supported: five images × five timing repetitions, n=25/config; five plaintext deltas. Do not call these 25 independent images. | v2 metadata, `core_metrics.csv`, runner. |
| Ciphertext entropy | Use only the v2 aggregate range 7.9880–7.9889 bits/byte, n=25/config, if relevant to an existing Table IV row. | `aggregates/configuration_summary.csv`. Empirical statistic only. |
| Neighbor correlation | Use only measured aggregate means, near zero; the audit reports absolute means below 0.006. | `aggregates/configuration_summary.csv`. Not a security proof. |
| Plaintext NPCR/UACI | Supported v2 figures: NPCR B–E mean 100%, A 0.00610%; reported UACI means as recorded in the audit. | v2 aggregate; five controlled deltas. Do not substitute v1/v1.1. |
| Dense one-byte diffusion | Supported archived controlled-input property: 100% output XOR occupancy in recorded B–E trials; property scope must be stated. | v2 `dense_diffusion_property.csv` and aggregate. Not universal end-to-end avalanche. |
| Runtime | Archived means may be quoted only with explicit note that source version and original timing environment are missing. | v2 `aggregates/performance_summary.csv`; audit reports n=25/config. No original CPU/OS/software timing environment is available. |
| Threshold reconstruction / insufficient-share rejection | Supported archive counts: valid subsets 5/5, 15/15, 50/50, 100/100; insufficient-share rejection 5/5 for each threshold. | v2 threshold summary and raw results. This is not an information-theoretic claim. |
| Peak memory | Mark **Not implemented**; do not provide a number. | v2 README states no memory instrumentation. |
| Published scheme comparison | Mark **Not run / not verifiable**; no comparison values. | Empty `published_comparison_template.csv`; no sourced comparison in archive. |
| Original command/environment/source version | Mark **Not verifiable**. | Intended commands in notes do not prove the archived run used them; there is no execution log, source hash, lock snapshot, or host/CPU metadata. |

### Table V — Functional Verification

| Audit evidence row | Disposition for paper | Evidence / reason |
|---|---|---|
| Key validation / KDF domains | Local audit tests **Pass**; identify this as the 113-test focused local run, not an archived Phase 6 measurement. | Test source files listed in evidence audit. |
| Fixed-key/fixed-nonce deterministic encryption | Local audit tests **Pass**; do not imply production nonce reuse is recommended. | `tests/test_integrated_pipeline.py`, `tests/test_phase6_security.py`, included in 113 passing tests. |
| Authenticated decryption / wrong-key rejection | Local audit tests **Pass**, with scope limited to implementation behavior. | `src/key_derivation.py`, `src/pipeline.py`, test run. Not a formal AEAD security proof. |
| Exact A–E round trips | Local tests **Pass**; archived v2 core rows also record exact round-trip flags. Keep the evidence types distinct. | Integration tests and v2 `core_metrics.csv`. |
| Threshold reconstruction and rejection | Local tests **Pass**; archived counts separately supported by v2 threshold outputs. | Test run and v2 threshold CSVs. GF(256) shares, not optical shares. |
| Duplicate handling / preprocessing | Local tests **Pass**; manifest supports 7 files / 5 unique samples. | `tests/test_preprocessing_dataset.py`, manifest and local test run. |
| Dense diffusion property | Local tests **Pass**; archived property outputs separately support the recorded v2 result. | `tests/test_dense_gf256_diffusion.py`, `tests/test_phase6_security.py`, v2 property CSV. |
| Qiskit basis validation | Mark **Not run in this audit**; prior project-note assertion is **not verifiable** without its log. | Test source exists, but no prior log was found. This does not mean large-image quantum execution. |
| Full 263-case suite / frontend checks | Mark **Not verifiable** pending retained logs; the audit only executed a focused 113-test subset. | Prior implementation status note is not itself a test log. |
| Literal Table V rows | **Not verifiable** until the manuscript source is available. | No paper/table source found. |

## Local test evidence to preserve

The evidence baseline records this exact command, run from the repository directory:

```powershell
..\.venv\Scripts\python.exe -m pytest -q tests/test_phase6_security.py tests/test_integrated_pipeline.py tests/test_threshold_pipeline_integration.py tests/test_preprocessing_dataset.py tests/test_dense_gf256_diffusion.py
```

Result: exit 0, **113 passed in 15.76s**. Environment: Windows PowerShell, Python 3.11.9, NumPy 2.4.6, OpenCV 5.0.0, pytest 9.1.1. These are local tests, not Phase 6 archive measurements. No Phase 6 archive was modified. v1/v1.1 were not used as substitutes.

## Remaining gaps before editing/compiling the paper

1. Restore/provide the IEEE `main.tex` and all included table files (or the paper PDF if source cannot be recovered).
2. Match literal Table IV/V rows against the dispositions above; do not assume audit labels equal manuscript row labels.
3. For timing or code-specific claims, resolve the v2 source-version and original timing-environment provenance gap; do not re-run into or overwrite existing archives.
4. Retain exact logs before asserting the full 263-test suite, Qiskit test, or frontend checks.
5. Compile with the repository's intended IEEE class and included source once available, and inspect the two-column layout.

## Files changed in this request

- Added `docs/research/TABLE_IV_V_REVISION_NOTES.md`.
- No manuscript, LaTeX table, experiment archive, or other project file was changed.
