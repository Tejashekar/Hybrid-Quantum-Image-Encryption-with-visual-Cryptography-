# Phase 6 security and experimental evaluation

Output version: `phase6-security-v2`  
Dataset: `experiments/real-input-7`; 5 unique decoded image contents, identified by the Phase-5 manifest and SHA-256 over decoded dtype/shape/pixels.  
Preprocessing: `center-square-crop-resize-grayscale-v1`, center square crop, `INTER_AREA`, grayscale uint8, 128×128.  
Configurations: A–D and E (2,2), (2,3), (3,5), (3,6).  
Repetitions: 5 timing repetitions per image/configuration.  
Master experiment seed: 20261008.  
Nonce policy: deterministic 16-byte SHA-256-derived public nonces for reproducibility; comparisons hold secret key and configuration fixed except in nonce sensitivity. All configurations use a nonce.  
Key policy: a fixed 32-byte experiment key is loaded externally; each sensitivity trial flips exactly one controlled key bit while nonce/configuration/plaintext stay fixed. The key is never written to outputs.  
Experimental key: one fixed 32-byte key loaded externally; only identifier `0753b2ee0ced818c444fafa523b897ecadd816335cb92ef5d43a816b7e60f8a8` is recorded. Preserve that key separately to reproduce this run.  
Aggregation: run `python -m experiments.aggregate_phase6 --results-dir experiments/results/phase6-security-v2` to derive summaries from raw CSV files.

Metric definitions are unchanged from `src/metrics.py`. NPCR is numeric ciphertext inequality percentage; XOR-difference occupancy is reported separately by name, though for uint8 pairs the per-byte nonzero-XOR predicate is mathematically equivalent to inequality. Empirical measurements are not cryptographic proofs. Dense GF(256) single-byte propagation is a mathematical property under fixed material and a one-byte difference at its input; it is not a universal avalanche or security claim.

Threshold sharing is GF(2^8)-based secret sharing with XOR field addition. Experiment coefficient bytes use the separate HKDF sharing domain; the GF(256) sharing equations are unchanged. No information-theoretic claim is made. No published-scheme values were available in the repository, so no external numerical comparisons are asserted. Peak memory was not measured because the project has no existing memory instrumentation. Existing historical results are preserved; this run writes only inside this versioned directory.
