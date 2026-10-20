# Reproducible experiments

Run the deterministic synthetic matrix from the repository root:

```text
.venv\Scripts\python.exe -m experiments.run_experiments --size 16 --seed 2026
```

The corrected runner defaults to the versioned output directory `experiments/results/phase5-center-crop-v1`; supply `--output-dir` to select another location. Existing result files are not overwritten unless `--overwrite` is passed. Supply `--image` for one real image or `--image-dir` for a directory. Real images use the shared deterministic largest-centered-square crop, `INTER_AREA` resize, and grayscale `uint8` conversion documented in [the dataset protocol](../docs/research/DATASET_PROTOCOL.md). No datasets are downloaded. If neither real-image argument is supplied, deterministic synthetic natural-like, gradient, random-valued, and low-texture images are generated; synthetic generation is unchanged and its random-image seed is derived independently from the classical XOR key seed.

Every entry in an explicitly supplied image directory must decode successfully. Unsupported or unreadable files, including non-file entries, cause a clear directory validation error; they are never silently skipped. An explicitly supplied `--image` that cannot be decoded also raises an error and never falls back to synthetic data. Image-directory inputs with identical decoded-content hashes are grouped and processed once; experiment rows retain the canonical filename, aliases, source content hash, and preprocessing metadata. The existing `image_id` continues to identify the processed array used by the experiment.

For a 128x128 real-image run, use:

```text
.venv\Scripts\python.exe -m experiments.run_experiments --image-dir path\to\real_images --size 128 --seed 20261001
```

The repository source directory has seven filenames but only five unique decoded image contents. The previous real-image result archive contains 56 successful rows and represents those five unique contents, not seven independent images. It predates the corrected center-crop protocol and is preserved as a historical archive; see the dataset protocol for hashes and duplicate groups. Five independent contents is a limited dataset and does not by itself support broad statistical generalization.

Configurations are labelled A (XOR only), B (chaotic XOR), C (quantum-inspired plus XOR), D (full chaotic/Arnold/quantum-inspired/XOR), and E (D plus threshold sharing). E runs `(2,2)`, `(2,3)`, `(3,5)`, and `(3,6)`. Each result records configuration parameters, seeds, image identity, dimensions, metrics, timings, storage values, and failures without aborting independent rows.

The runner records raw measurements only. It does not rank configurations or generate plots.

The integrated D/E paths in `run_experiments` require an external 32-byte experiment key; its historical A–C comparison branches remain legacy experiment code. The current Phase 6 evaluation exercises keyed A–E through the current API. Set `QCRYPT_EXPERIMENT_KEY_HEX` in the process environment or keep it in the ignored `.env.phase7.local` file; neither the key nor its bytes are written to results, and metadata records only its SHA-256 identifier. Phase 6's updated one-bit secret-key sensitivity run is in `results/phase6-security-v2/`; the older Phase 6 result directories remain historical and retain their prior public-parameter sensitivity protocol. See [the Phase 7 key model](../docs/research/PHASE7_KEY_MODEL.md).

Experiment IDs and timestamps identify a run and may vary. Cryptographic outputs and metric values are reproducible when image, parameters, and seeds match; timing values are naturally variable. Configuration C reports primary minimal key sensitivity by flipping exactly one key byte and separately reports seed perturbation sensitivity. B, D, and E report chaotic parameter sensitivity using `x0 + 1e-4`. For E, quality metrics and decryption timing use ciphertext reconstructed from the recorded `first_k` share coordinates.
