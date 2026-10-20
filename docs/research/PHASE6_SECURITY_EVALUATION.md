# Phase 6 — Comprehensive security and experimental evaluation

## 1. Objective

Measure the current research implementation without changing cipher equations, preprocessing, or metric definitions. This evaluation is empirical and is not a security proof.

## 2. Dataset

The Phase-5 manifest supplies **5 unique decoded image contents** from seven filenames. Duplicate aliases are grouped; image files are not counted as independent samples.

## 3. Preprocessing

Version: `center-square-crop-resize-grayscale-v1`. The protocol uses a centered square crop, `INTER_AREA` resizing, grayscale `uint8`, and 128×128 output. Cropping and resizing lose source information; round-trip exactness is measured relative to this processed plaintext.

## 4. Experimental protocol

Configurations: A–D and E with (2,2), (2,3), (3,5), and (3,6). Timing repetitions: 5. Master seed: 20261008. The run uses an externally supplied 32-byte secret key (key identifier SHA-256: `0753b2ee0ced818c444fafa523b897ecadd816335cb92ef5d43a816b7e60f8a8`). Nonces are deterministic public 16-byte values for reproducibility and held fixed except in nonce comparisons. Each key-sensitivity trial flips exactly one controlled bit of the 256-bit key. Configuration parameters remain public reproducibility metadata.

Metric formulas are unchanged from `src/metrics.py`. Aggregates below are calculated by `experiments/aggregate_phase6.py` from the saved per-image/per-trial CSV rows. Standard deviation uses population `ddof=0`.

## 5. Core statistical results

Values are configuration means ± population standard deviations across raw rows; the raw file also contains per-image and per-repetition results. Entropy and correlations describe ciphertext statistics; they do not prove security. NPCR/UACI are averaged over the five tested plaintext XOR deltas per image.

| Configuration | Entropy | H/V/D correlation | NPCR* | UACI* | Encrypt ms | Decrypt ms |
|---|---|---|---|---|---|---|
| A | 7.9883 ± 0.0009 | 0.0015 ± 0.0061/-0.0001 ± 0.0094/-0.0002 ± 0.0090 | 0.0061 ± 0.0000 | 0.0018 ± 0.0004 | 1.5136 ± 0.2187 | 1.5637 ± 0.2535 |
| B | 7.9880 ± 0.0013 | -0.0036 ± 0.0068/0.0028 ± 0.0054/-0.0002 ± 0.0083 | 100.0000 ± 0.0000 | 25.3274 ± 0.0572 | 15.1846 ± 7.2682 | 10.0638 ± 5.0384 |
| C | 7.9882 ± 0.0007 | 0.0026 ± 0.0057/0.0012 ± 0.0049/-0.0058 ± 0.0066 | 100.0000 ± 0.0000 | 29.7378 ± 5.4403 | 14.9947 ± 2.8258 | 10.0411 ± 1.5398 |
| D | 7.9889 ± 0.0012 | -0.0014 ± 0.0056/-0.0010 ± 0.0075/0.0050 ± 0.0036 | 100.0000 ± 0.0000 | 20.9552 ± 4.8085 | 27.2160 ± 5.9507 | 22.8668 ± 4.1824 |
| E_2_of_2 | 7.9887 ± 0.0005 | -0.0029 ± 0.0061/-0.0032 ± 0.0089/-0.0024 ± 0.0039 | 100.0000 ± 0.0000 | 24.7121 ± 6.6666 | 25.7250 ± 3.2161 | 22.3410 ± 3.9521 |
| E_2_of_3 | 7.9887 ± 0.0004 | 0.0046 ± 0.0027/0.0045 ± 0.0036/-0.0043 ± 0.0045 | 100.0000 ± 0.0000 | 24.5684 ± 4.8711 | 24.9987 ± 1.3391 | 21.8101 ± 1.6743 |
| E_3_of_5 | 7.9887 ± 0.0010 | 0.0016 ± 0.0055/-0.0056 ± 0.0043/-0.0060 ± 0.0059 | 100.0000 ± 0.0000 | 23.2605 ± 8.1046 | 25.1641 ± 1.8265 | 21.2629 ± 1.3976 |
| E_3_of_6 | 7.9885 ± 0.0009 | -0.0012 ± 0.0105/0.0002 ± 0.0128/-0.0003 ± 0.0040 | 100.0000 ± 0.0000 | 25.9031 ± 3.7387 | 25.1210 ± 1.1279 | 21.4950 ± 1.3156 |

## 6. Differential analysis

| Configuration | XOR delta | NPCR mean ± SD | UACI mean ± SD | XOR occupancy mean ± SD |
|---|---|---|---|---|
| A | 1 | 0.0061 ± 0.0000 | 0.0000 ± 0.0000 | 0.0061 ± 0.0000 |
| A | 127 | 0.0061 ± 0.0000 | 0.0016 ± 0.0008 | 0.0061 ± 0.0000 |
| A | 128 | 0.0061 ± 0.0000 | 0.0031 ± 0.0000 | 0.0061 ± 0.0000 |
| A | 2 | 0.0061 ± 0.0000 | 0.0000 ± 0.0000 | 0.0061 ± 0.0000 |
| A | 255 | 0.0061 ± 0.0000 | 0.0042 ± 0.0014 | 0.0061 ± 0.0000 |
| B | 1 | 100.0000 ± 0.0000 | 0.3950 ± 0.0007 | 100.0000 ± 0.0000 |
| B | 127 | 100.0000 ± 0.0000 | 25.0462 ± 0.1122 | 100.0000 ± 0.0000 |
| B | 128 | 100.0000 ± 0.0000 | 50.1955 ± 0.0012 | 100.0000 ± 0.0000 |
| B | 2 | 100.0000 ± 0.0000 | 0.7852 ± 0.0013 | 100.0000 ± 0.0000 |
| B | 255 | 100.0000 ± 0.0000 | 50.2152 ± 0.2837 | 100.0000 ± 0.0000 |
| C | 1 | 100.0000 ± 0.0000 | 20.5096 ± 24.1594 | 100.0000 ± 0.0000 |
| C | 127 | 100.0000 ± 0.0000 | 50.1060 ± 0.1963 | 100.0000 ± 0.0000 |
| C | 128 | 100.0000 ± 0.0000 | 17.5698 ± 9.2203 | 100.0000 ± 0.0000 |
| C | 2 | 100.0000 ± 0.0000 | 10.2762 ± 12.1029 | 100.0000 ± 0.0000 |
| C | 255 | 100.0000 ± 0.0000 | 50.2274 ± 0.1248 | 100.0000 ± 0.0000 |
| D | 1 | 100.0000 ± 0.0000 | 2.8310 ± 2.0377 | 100.0000 ± 0.0000 |
| D | 127 | 100.0000 ± 0.0000 | 45.0161 ± 9.9770 | 100.0000 ± 0.0000 |
| D | 128 | 100.0000 ± 0.0000 | 10.3537 ± 12.0390 | 100.0000 ± 0.0000 |
| D | 2 | 100.0000 ± 0.0000 | 1.4133 ± 1.0100 | 100.0000 ± 0.0000 |
| D | 255 | 100.0000 ± 0.0000 | 45.1620 ± 10.0448 | 100.0000 ± 0.0000 |
| E_2_of_2 | 1 | 100.0000 ± 0.0000 | 20.3939 ± 18.4336 | 100.0000 ± 0.0000 |
| E_2_of_2 | 127 | 100.0000 ± 0.0000 | 40.2251 ± 12.3578 | 100.0000 ± 0.0000 |
| E_2_of_2 | 128 | 100.0000 ± 0.0000 | 12.5504 ± 10.3099 | 100.0000 ± 0.0000 |
| E_2_of_2 | 2 | 100.0000 ± 0.0000 | 10.1981 ± 9.2226 | 100.0000 ± 0.0000 |
| E_2_of_2 | 255 | 100.0000 ± 0.0000 | 40.1930 ± 12.3318 | 100.0000 ± 0.0000 |
| E_2_of_3 | 1 | 100.0000 ± 0.0000 | 16.1681 ± 19.2815 | 100.0000 ± 0.0000 |
| E_2_of_3 | 127 | 100.0000 ± 0.0000 | 40.1391 ± 12.2597 | 100.0000 ± 0.0000 |
| E_2_of_3 | 128 | 100.0000 ± 0.0000 | 18.2755 ± 18.1487 | 100.0000 ± 0.0000 |
| E_2_of_3 | 2 | 100.0000 ± 0.0000 | 13.0988 ± 19.0913 | 100.0000 ± 0.0000 |
| E_2_of_3 | 255 | 100.0000 ± 0.0000 | 35.1603 ± 12.3030 | 100.0000 ± 0.0000 |
| E_3_of_5 | 1 | 100.0000 ± 0.0000 | 19.0002 ± 17.6246 | 100.0000 ± 0.0000 |
| E_3_of_5 | 127 | 100.0000 ± 0.0000 | 40.2371 ± 12.3515 | 100.0000 ± 0.0000 |
| E_3_of_5 | 128 | 100.0000 ± 0.0000 | 7.3736 ± 9.0589 | 100.0000 ± 0.0000 |
| E_3_of_5 | 2 | 100.0000 ± 0.0000 | 9.4924 ± 8.7896 | 100.0000 ± 0.0000 |
| E_3_of_5 | 255 | 100.0000 ± 0.0000 | 40.1993 ± 12.3183 | 100.0000 ± 0.0000 |
| E_3_of_6 | 1 | 100.0000 ± 0.0000 | 11.1439 ± 19.5497 | 100.0000 ± 0.0000 |
| E_3_of_6 | 127 | 100.0000 ± 0.0000 | 44.9694 ± 9.9407 | 100.0000 ± 0.0000 |
| E_3_of_6 | 128 | 100.0000 ± 0.0000 | 17.6482 ± 9.9022 | 100.0000 ± 0.0000 |
| E_3_of_6 | 2 | 100.0000 ± 0.0000 | 10.5892 ± 19.8082 | 100.0000 ± 0.0000 |
| E_3_of_6 | 255 | 100.0000 ± 0.0000 | 45.1646 ± 10.0171 | 100.0000 ± 0.0000 |

For a uint8 pair, `a XOR b != 0` and `a != b` are equivalent per element; therefore XOR-difference occupancy and NPCR have equal numeric values when computed on the same arrays. The dense diffusion's tested all-nonzero property is specifically a one-byte input-difference property under fixed material; it is not a general claim for arbitrary multi-byte differences or all security notions.

### Isolated dense diffusion single-byte check

The following rows change one byte at the dense diffusion input while holding its mask fixed. This is a construction-specific input property and is not a general security or avalanche claim.

| Configuration | Input XOR delta | Output XOR occupancy mean +/- SD | Output NPCR mean +/- SD |
|---|---|---|---|
| B | 1 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| B | 127 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| B | 128 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| B | 2 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| B | 255 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| C | 1 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| C | 127 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| C | 128 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| C | 2 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| C | 255 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| D | 1 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| D | 127 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| D | 128 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| D | 2 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| D | 255 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_2_of_2 | 1 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_2_of_2 | 127 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_2_of_2 | 128 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_2_of_2 | 2 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_2_of_2 | 255 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_2_of_3 | 1 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_2_of_3 | 127 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_2_of_3 | 128 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_2_of_3 | 2 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_2_of_3 | 255 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_3_of_5 | 1 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_3_of_5 | 127 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_3_of_5 | 128 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_3_of_5 | 2 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_3_of_5 | 255 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_3_of_6 | 1 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_3_of_6 | 127 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_3_of_6 | 128 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_3_of_6 | 2 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |
| E_3_of_6 | 255 | 100.0000 +/- 0.0000 | 100.0000 +/- 0.0000 |

## 7. Key sensitivity

Five one-bit perturbations at key bit positions 0, 63, 127, 191, and 255 were applied to the caller-supplied 256-bit key per image/configuration, holding plaintext, nonce, and configuration fixed. These are empirical measurements, not proof of a secure key schedule.

| Configuration | NPCR mean ± SD | UACI mean ± SD | XOR occupancy |
|---|---|---|---|
| A | 99.6184 ± 0.0358 | 33.4345 ± 0.1334 | 99.6184 ± 0.0358 |
| B | 99.5923 ± 0.0477 | 33.4431 ± 0.1817 | 99.5923 ± 0.0477 |
| C | 99.5945 ± 0.0437 | 33.3594 ± 0.1467 | 99.5945 ± 0.0437 |
| D | 99.6187 ± 0.0523 | 33.4039 ± 0.2010 | 99.6187 ± 0.0523 |
| E_2_of_2 | 99.5930 ± 0.0541 | 33.4965 ± 0.1874 | 99.5930 ± 0.0541 |
| E_2_of_3 | 99.6284 ± 0.0610 | 33.5104 ± 0.1970 | 99.6284 ± 0.0610 |
| E_3_of_5 | 99.6047 ± 0.0552 | 33.4998 ± 0.1733 | 99.6047 ± 0.0552 |
| E_3_of_6 | 99.6077 ± 0.0447 | 33.3970 ± 0.1742 | 99.6077 ± 0.0447 |

## 8. Plaintext sensitivity

One preprocessed byte was XOR-modified by 1, 2, 127, 128, and 255 for each unique image and configuration, with identical key material and nonce. Per-image trials are in `plaintext_sensitivity.csv` and full propagation traces in `differential_analysis.csv`.

## 9. Nonce sensitivity

The same plaintext/key parameters with the same nonce were checked for deterministic equality; a separately derived nonce was then compared. All configurations use the public nonce in the KDF context; it is not secret key material. These measurements do not prove nonce uniqueness or cryptographic security.

## 10. Keystream statistical assessment

Assessment label: statistical assessment of the generated byte stream. Each parameter set uses 100,000 bytes.

| Parameter set | x0 | r | transient | seed | chi-square | p-value | lag-1 corr | one-bit proportion |
|---|---|---|---|---|---|---|---|---|
| default | 0.5 | 3.99 | 1000 |  | 261.5706 | 0.3753 | 0.0015 | 0.4991 |
| api-D | 0.37 | 3.91 | 1000 | 3526811466 | 211.8605 | 0.9773 | -0.0024 | 0.4993 |
| alternate | 0.23 | 3.98 | 1200 | 314159 | 254.2694 | 0.5011 | -0.0029 | 0.4999 |

Chi-square, serial correlation, byte entropy, and bit proportion are statistical diagnostics only. They do not establish cryptographic pseudorandomness or NIST compliance.

## 11. Key-space analysis

The independent secret key has 2^256 theoretical values because it is exactly 32 bytes. The public nonce has 2^128 possible values and is not added to secret-key size. Logistic parameters, seeds, Arnold iteration count, and quantum-inspired configuration are separate public reproducibility domains. Finite-precision and equivalent parameter behaviors prevent treating their theoretical domains as additional secret entropy. Key length alone does not establish an effective 256-bit security level; practical security depends on the complete construction and implementation.

`The key length does not establish an effective 256-bit security level.`

## 12. Structured plaintext analysis

All-zero, all-255, constant-128, horizontal/vertical gradient, checkerboard, and sparse single-pixel patterns were encrypted under B/C/D. Entropy, neighboring correlations, histogram, and comparisons against the all-zero ciphertext are recorded per structure in `structured_plaintext.csv`. These are structural robustness checks, not chosen-plaintext attack resistance tests.

## 13. Configuration ablation

The controlled A–E rows are available in `ablation_results.csv`; means/stds are represented in the core table and raw CSV. The comparison describes observed changes across configurations; it does not isolate causal effects beyond their defined component differences.

## 14. Threshold-sharing analysis

Threshold results are based on GF(2^8)-based secret sharing with XOR field addition. Every valid k-subset was reconstructed for each image and threshold; fewer-than-k attempts were expected to raise a threshold error. Exact success/rejection counts and share sizes are in `threshold_results.csv`. Storage ratios are relative to raw ciphertext bytes. Coefficient bytes are derived in the separate HKDF sharing domain; no information-theoretic secrecy claim is made.

| Threshold | Subset reconstructions | Insufficient-share rejections |
|---|---|---|
| E_2_of_2 | 5/5 | yes |
| E_2_of_3 | 15/15 | yes |
| E_3_of_5 | 50/50 | yes |
| E_3_of_6 | 100/100 | yes |

## 15. Performance and resource analysis

Preprocessing, encryption, decryption, share-generation, and reconstruction timings are repeated and summarized below. Ciphertext/share raw and encoded byte counts are retained in raw result files. Peak memory is not available because the current project has no memory instrumentation; no throughput or memory claim is made.

| Configuration | Operation | Mean ms | SD ms | Min ms | Max ms |
|---|---|---|---|---|---|
| A | decryption | 1.5637 | 0.2535 | 1.3677 | 2.4724 |
| A | encryption | 1.5136 | 0.2187 | 1.3320 | 2.4143 |
| ALL | preprocessing | 32.5457 | 11.4950 | 22.4856 | 56.9926 |
| B | decryption | 10.0638 | 5.0384 | 8.1602 | 34.2350 |
| B | encryption | 15.1846 | 7.2682 | 12.1158 | 45.8461 |
| C | decryption | 10.0411 | 1.5398 | 8.3974 | 16.0805 |
| C | encryption | 14.9947 | 2.8258 | 12.2980 | 24.1509 |
| D | decryption | 22.8668 | 4.1824 | 19.7105 | 38.1150 |
| D | encryption | 27.2160 | 5.9507 | 22.6218 | 52.9657 |
| E_2_of_2 | decryption | 22.3410 | 3.9521 | 19.6513 | 39.8388 |
| E_2_of_2 | encryption | 25.7250 | 3.2161 | 22.9123 | 37.1374 |
| E_2_of_2 | reconstruction | 0.0146 | 0.0037 | 0.0103 | 0.0215 |
| E_2_of_2 | share_generation | 1.4349 | 0.1815 | 1.2657 | 1.9425 |
| E_2_of_3 | decryption | 21.8101 | 1.6743 | 19.9064 | 26.0301 |
| E_2_of_3 | encryption | 24.9987 | 1.3391 | 22.9353 | 28.0747 |
| E_2_of_3 | reconstruction | 4.8075 | 0.5121 | 4.2271 | 6.7271 |
| E_2_of_3 | share_generation | 4.6488 | 0.5317 | 4.0401 | 6.1999 |
| E_3_of_5 | decryption | 21.2629 | 1.3976 | 19.6355 | 25.4157 |
| E_3_of_5 | encryption | 25.1641 | 1.8265 | 23.0230 | 29.6727 |
| E_3_of_5 | reconstruction | 12.0214 | 1.2184 | 10.4491 | 14.3557 |
| E_3_of_5 | share_generation | 12.7175 | 0.9017 | 11.1784 | 14.7930 |
| E_3_of_6 | decryption | 21.4950 | 1.3156 | 19.9094 | 24.2023 |
| E_3_of_6 | encryption | 25.1210 | 1.1279 | 23.2415 | 27.7762 |
| E_3_of_6 | reconstruction | 11.9353 | 1.2441 | 10.4454 | 14.1750 |
| E_3_of_6 | share_generation | 16.0282 | 2.3301 | 13.4115 | 20.2850 |

## 16. Limitations

Only five independent real-image contents are available. Results are not representative of a broad image population. Timing depends on this machine and runtime conditions. The historical 56-row archive is preserved and predates corrected preprocessing. No full security proof, cryptographic key-space estimate, or external scheme comparison is claimed.

## 17. Threat-model interpretation

The repository does not accept an independently supplied secret key for the image cipher; derivation parameters and seeds are included in public configuration metadata, and the nonce is public. These results should be interpreted as research measurements of a reversible classical simulation, not evidence that the application provides secure encryption. Statistical metrics, sensitivity tests, and threshold reconstruction checks do not prove resistance to attacks.

## 18. Reproducibility information

Run raw evaluation: `python -m experiments.phase6_security --output-dir experiments/results/phase6-security-v2 --seed 20261008`. Aggregate: `python -m experiments.aggregate_phase6 --results-dir experiments/results/phase6-security-v2`. The exact dataset, nonce/key policy, preprocessing version, counts, and output schema are recorded in this directory's README and `run_metadata.json`. Existing result directories are never overwritten by the runner.
