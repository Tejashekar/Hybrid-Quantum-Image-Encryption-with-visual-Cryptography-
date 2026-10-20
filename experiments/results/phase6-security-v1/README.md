# Phase 6 security and experimental evaluation

> **Historical / superseded result set.** This archive predates the independent 256-bit secret-key model and uses public parameter/key-array sensitivity. Use `phase6-security-v2` for the current key-model evaluation. Preserved as research history; do not cite as the final key-sensitivity methodology.

Output version: `phase6-security-v1`  
Dataset: `experiments/real-input-7`; 5 unique decoded image contents, identified by the Phase-5 manifest and SHA-256 over decoded dtype/shape/pixels.  
Preprocessing: `center-square-crop-resize-grayscale-v1`, center square crop, `INTER_AREA`, grayscale uint8, 128×128.  
Configurations: A–D and E (2,2), (2,3), (3,5), (3,6).  
Repetitions: 5 timing repetitions per image/configuration.  
Master experiment seed: 20261008.  
Nonce policy: deterministic 16-byte SHA-256-derived nonces for reproducibility; comparisons hold key parameters and nonce fixed except in nonce sensitivity. A does not use a nonce.  
Key policy: API-derived config is fixed per label/threshold; one XOR-key byte is changed per sensitivity trial. These configurations/seeds are public metadata, not a claimed secret key.  
Aggregation: run `python -m experiments.aggregate_phase6 --results-dir experiments/results/phase6-security-v1` to derive summaries from raw CSV files.

Metric definitions are unchanged from `src/metrics.py`. NPCR is numeric ciphertext inequality percentage; XOR-difference occupancy is reported separately by name, though for uint8 pairs the per-byte nonzero-XOR predicate is mathematically equivalent to inequality. Empirical measurements are not cryptographic proofs. Dense GF(256) single-byte propagation is a mathematical property under fixed material and a one-byte difference at its input; it is not a universal avalanche or security claim.

Threshold sharing is GF(2^8)-based secret sharing with XOR field addition. The implementation's deterministic NumPy sharing seed is recorded in configuration metadata; this evaluation does not claim information-theoretic secrecy. No published-scheme values were available in the repository, so no external numerical comparisons are asserted. Peak memory was not measured because the project has no existing memory instrumentation. Existing historical results are preserved; this run writes only inside this versioned directory.
