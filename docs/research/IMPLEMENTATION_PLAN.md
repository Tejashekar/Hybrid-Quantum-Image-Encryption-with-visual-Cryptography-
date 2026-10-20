# Historical research implementation plan (superseded)

> Historical plan: some phase descriptions below preserve earlier designs and are superseded by the current implementation. The active bit-mixing, controlled-XOR, bit-flip, conditional byte-rotation, and dense GF(256) diffusion details are documented in the source and main README. Current Qiskit validation scope is documented in [QISKIT_VALIDATION.md](QISKIT_VALIDATION.md); it does not validate the complete image workflow as a quantum circuit.

## 1. Final architecture

The system will use a modular pipeline: grayscale and fixed-size preprocessing, an NEQR-inspired representation, configurable key generation, Arnold scrambling, reversible quantum-inspired transforms, XOR diffusion, and generic XOR threshold image sharing. Decryption will execute the exact inverse operations and require a valid set of shares. The Flask application will call the pipeline through a small service layer; research experiments will call the same modules directly.

Large images will use classical NumPy simulation. A separate small-image Qiskit demonstration will validate the circuit representation and report its resource limits.

## 2. Baseline definitions

- **Baseline A:** classical random byte-key XOR encryption with (2,2) XOR sharing.
- **Baseline B:** chaotic-key XOR encryption with (2,2) XOR sharing.
- **Baseline C:** quantum-inspired reversible transforms followed by XOR diffusion with (2,2) XOR sharing.
- **Proposed framework:** quantum-inspired transforms, chaotic key generation, XOR diffusion, and configurable (k,n) XOR threshold sharing.

## 3. Proposed framework

The proposed configuration will expose image size, key parameters, transform parameters, threshold `(k,n)`, random seed, and whether the Qiskit demonstration is enabled. Every operation will have a documented inverse, and experiment output will include the complete configuration.

## 4. Metrics

Security evaluation will report entropy, horizontal/vertical/diagonal neighboring-pixel correlation, differential NPCR and UACI, key sensitivity, plaintext sensitivity, histogram analysis, and key-space analysis. Reconstruction quality will report MSE, PSNR, and SSIM. Performance will report encryption, decryption, share generation, reconstruction, peak memory where practical, and storage overhead from `n` shares. The Qiskit demonstration will report qubits, gate count, depth, simulator time, and limitations.

NPCR and UACI will compare ciphertexts produced from a plaintext and an exactly one-pixel/bit modified plaintext under the same key. Key sensitivity will compare minimally modified keys on the same plaintext.

## 5. Ablation matrix

Experiments will independently remove or replace chaotic key generation, Arnold scrambling, quantum-inspired transforms, XOR diffusion, and threshold sharing. Results will be compared against Baselines A-C using the same image set and seeds.

## 6. Experiment configurations

The minimum threshold configurations are `(2,2)`, `(2,3)`, `(3,5)`, and `(3,6)`. Experiments will use small deterministic fixtures first, then fixed 128x128 grayscale images. Each result row will record image identifier, dimensions, seed, key parameters, transform parameters, threshold, timings, memory, storage, and all metrics.

## 7. Known limitations

The framework is not post-quantum, quantum-resistant, or quantum-safe. Large-image processing is classical simulation. XOR threshold sharing is computational image sharing and is not traditional optical visual cryptography with pixel expansion. Security metrics are empirical indicators and do not constitute a cryptographic security proof.

## 8. Genuine quantum vs quantum-inspired behavior

Only the explicitly separated small-image Qiskit demonstration is genuine quantum-circuit construction and simulator execution. The production-sized pipeline uses classical NumPy representations and reversible quantum-inspired transformations.

## Phase 2: Logistic Map chaotic key generation

The chaotic-key baseline uses the Logistic Map recurrence `x_(n+1) = r*x_n*(1-x_n)`. The initial condition `x0` must satisfy `0 < x0 < 1`; the control parameter `r` must satisfy `3.57 < r <= 4.0`, with `r=3.99` as the default chaotic-regime value. The requested sequence length must be positive.

The generator discards a configurable transient before collecting key values. The default transient is 100 iterations, which reduces dependence on the initial state before key material is collected. An optional integer seed adds a deterministic bounded warm-up offset (`seed % 1000`); it does not introduce random floating-point values.

Collected values are explicitly mapped to bytes with `floor(x*256)` and clipped to `[0,255]`, then stored as `uint8`. The same `x0`, `r`, length, transient, and seed always produce the same key. A stream of any positive length and a two-dimensional key matching an image shape are supported.

This is a deterministic research key-generation primitive, not a claim of cryptographic security. Logistic-map keys require later security evaluation and careful key handling; the Phase 1 random-key XOR baseline remains available for comparison.

## Phase 3: Arnold Cat Map scrambling

For an `N x N` image, coordinates use `x` as the column index and `y` as the row index. Each source pixel is moved according to the standard map:

```text
x' = (x + y) mod N
y' = (x + 2y) mod N
```

The inverse uses the modular inverse matrix of `[[1,1],[1,2]]`:

```text
x = (2x' - y') mod N
y = (-x' + y') mod N
```

`arnold_scramble(image, iterations)` applies the forward permutation repeatedly; `arnold_unscramble(image, iterations)` applies the true inverse permutation the same number of times. Zero iterations is the identity, and every iteration count preserves shape, dtype, pixel values, and the pixel histogram. Arnold scrambling is only a reversible position-permutation primitive; by itself it is not encryption.

## Phase 4: quantum-inspired transformation layer

“Quantum-inspired” in this project means a deterministic classical simulation of selected reversible bit-level effects. The production image is not encoded as a `128 x 128` quantum state vector and is not processed by quantum hardware. Each `uint8` pixel is represented as eight classical bits and reconstructed exactly after transformation.

The H-inspired operation is an explicitly classical two-bit linear mixing analogue applied to adjacent bit pairs: `(a,b) -> (a XOR b, a)`, with inverse `(u,v) -> (v, u XOR v)`. It is not a literal Hadamard gate and does not create amplitudes or superposition. CNOT-inspired transformation leaves a selected control bit unchanged and maps the target to `target XOR control`; it is self-inverse. X-inspired transformation flips one selected bit with XOR 1 and is also self-inverse.

Pauli-Z acts on phase, rather than classical bit values. The implementation therefore carries an explicit per-pixel sign array containing `+1` or `-1`; Z toggles the sign where the selected pixel bit is 1. The phase metadata is retained through the combined transform and removed only after the inverse has restored it. Treating Z as another pixel XOR would be misleading.

The combined order is H-inspired, CNOT-inspired, X-inspired, then Z-inspired. Its configuration records the selected CNOT control/target and X/Z bit indices, allowing exact reverse order during inversion. This layer is reversible and deterministic, but it is not a quantum computation, does not model full amplitude evolution, and does not establish cryptographic security. Genuine Qiskit circuit construction and small-image simulator evaluation are reserved for a later phase.

## Phase 5: integrated hybrid classical pipeline

The integrated encryption order is:

```text
image -> deterministic Logistic Map byte key -> Arnold scramble
      -> H-inspired/CNOT-inspired/X-inspired/Z-inspired transform
      -> XOR with the chaotic byte key -> cipher image
```

Decryption executes the exact reverse order: XOR with the regenerated key, restore the retained phase metadata in the quantum-inspired state, apply inverse Z/X/CNOT/H transformations, then apply inverse Arnold scrambling.

`IntegratedPipelineConfig` records the image shape, `x0`, `r`, transient length, optional deterministic chaotic seed, Arnold iteration count, quantum bit configuration, and algorithm version. It can be converted to and from a JSON-serializable dictionary. The raw chaotic key is never stored; encryption and decryption derive the same key from these parameters. Because the Pauli-Z abstraction uses explicit per-pixel signs, `EncryptedImage` carries ciphertext, phase metadata, and configuration metadata together. Discarding the phase metadata prevents exact inversion.

The existing random-key XOR API and baseline pipeline remain available for later comparison. The integrated pipeline is a research prototype: a Logistic Map is not automatically a cryptographic PRNG, Arnold scrambling is only a permutation, XOR alone is not sufficient cryptographic diffusion, and the quantum-inspired operations are classical reversible transformations. Security metrics and stronger evaluation are deferred to later phases.

## Phase 6: XOR-based (k,n) threshold image secret sharing

General thresholds use Shamir secret sharing over the finite field `GF(2^8)`. Field addition is bytewise XOR; field multiplication is standard irreducible-polynomial multiplication for eight-bit values. For each image pixel `s`, a random degree `k-1` polynomial is created independently:

```text
f(x) = s XOR a1*x XOR a2*x^2 XOR ... XOR a(k-1)*x^(k-1)
```

Share `i` contains `f(i)` at every pixel, with distinct nonzero field coordinates `i=1..n`. Any `k` shares recover `f(0)=s` using Lagrange interpolation in `GF(2^8)`; fewer than `k` shares are rejected by the API and, with independently random coefficients, provide no information-theoretic information about the secret under standard Shamir assumptions. Shares remain image-shaped `uint8` arrays and carry their coordinate as metadata so arbitrary combinations can be reconstructed.

The legacy `(2,2)` API remains compatible with the original XOR pair (`share2 = secret XOR share1`). General `(k,n)` configurations are therefore XOR-based finite-field threshold sharing rather than pure XOR-only sharing. This is computational image secret sharing, not traditional optical visual cryptography and has no pixel expansion. Storage overhead is `n` full-size shares, approximately `n` times the encrypted image storage, plus small coordinate/configuration metadata. The construction assumes secure random coefficients, protected share metadata, and a field size supporting `n <= 255`.

## Phase 7: complete research pipeline API

The research API is exposed by `encrypt_and_share(image, config)` and `reconstruct_and_decrypt(shares, config, metadata)` (or the returned `ResearchShareBundle` shortcut). Its end-to-end architecture is:

```text
input image
  -> grayscale/fixed-size preprocessing and shape validation
  -> deterministic chaotic key derivation
  -> Arnold scramble
  -> H/CNOT/X/Z-inspired classical transformation
  -> XOR diffusion with chaotic byte key
  -> encrypted image
  -> GF(2^8) XOR-based (k,n) threshold sharing
  -> n image shares + ResearchMetadata

k valid shares + ResearchMetadata
  -> threshold reconstruction of encrypted image
  -> regenerate identical chaotic key
  -> inverse XOR diffusion
  -> inverse Z/X/CNOT/H-inspired transformation
  -> inverse Arnold scramble
  -> recovered preprocessed image
```

`ResearchPipelineConfig` combines image dimensions, algorithm version, Logistic Map parameters, transient and Arnold settings, quantum-inspired bit settings, threshold `(k,n)`, and independent deterministic seeds for chaotic key derivation and share generation. `ResearchMetadata` contains the serializable configuration dictionary and the explicit phase array required by the Pauli-Z abstraction; it never stores a raw chaotic key. Metadata is compared to the supplied configuration before reconstruction.

Ready-made configurations are available for `(2,2)`, `(2,3)`, `(3,5)`, and `(3,6)`. Encryption parameters remain identical when these threshold configurations are compared. The classical random XOR baseline remains separately callable, so future experiments can distinguish Baselines A-C from the proposed configurable pipeline. Exact byte-for-byte recovery is required for every valid share combination; fewer than `k` shares are rejected.

## Research Metrics

The metrics module contains independent functions and does not perform encryption. Entropy is Shannon entropy in bits per pixel, `H=-sum(p(x)log2(p(x)))`, computed from grayscale value frequencies. Neighbor correlation is Pearson correlation of separate horizontal, vertical, and diagonal neighboring pairs; zero is returned for a zero-variance or otherwise undefined neighborhood.

NPCR compares two equal-shaped ciphertexts only: `100 * changed_pixels / N`. UACI compares the same ciphertext pair: `100/N * sum(abs(C1-C2)/255)`. The intended experiment encrypts `P` and a controlled one-pixel/one-bit variant `P'` under the same key, then computes NPCR/UACI between `C1` and `C2`. Key sensitivity uses the same plaintext with minimally changed keys and the same pairwise comparison. These metrics do not compare plaintext directly with ciphertext.

Histogram statistics provide 256-bin counts, normalized probabilities, and optional L1 histogram distance without plotting. MSE is the mean squared pixel error; PSNR is `20log10(255/sqrt(MSE))` and is infinite for identical images. SSIM uses the established `scikit-image` implementation, requires equal shapes, and does not resize inputs.

Timing helpers use high-resolution monotonic timing and report milliseconds for already-prepared encryption, decryption, share-generation, or reconstruction callables; image loading and UI/network work are excluded. Storage metrics report raw NumPy array bytes separately from optional encoded-file sizes, including original bytes, cipher bytes, number of shares, total share bytes, and share/original storage ratio.

These metrics provide evidence about specific properties and reconstruction quality. Values such as high NPCR or entropy are not standalone proofs of cryptographic security and must be interpreted with the construction, baselines, controls, and limitations.

## Experimental Protocol

The experiment runner in `experiments/run_experiments.py` labels the comparison matrix as follows: A is classical deterministic/random XOR only; B is Logistic Map chaos plus XOR; C is the quantum-inspired transform plus XOR; D is the full chaotic-key, Arnold, quantum-inspired, and XOR pipeline; E is D followed by threshold sharing. E evaluates `(2,2)`, `(2,3)`, `(3,5)`, and `(3,6)` with identical encryption parameters across thresholds. Threshold sharing is evaluated for access, reconstruction, timing, and storage rather than as a ciphertext-security improvement.

Experiments accept a single image or directory and never download data. Without external data, deterministic synthetic natural-like, gradient, random-valued, and low-texture grayscale images are generated. Synthetic-image randomness and encryption/key randomness are derived from independent labels under the same master seed. Each row records an experiment identifier, UTC timestamp, image name/type/dimensions, complete configuration, seeds, Logistic Map parameters, Arnold and quantum settings, threshold values, raw metrics, timings, storage values, and either success or a typed failure message. JSON and CSV results are written under `experiments/results` by default.

The seed policy fixes one master seed and deterministically derives independent random-key, chaotic-key, sharing, and synthetic-image seeds. Differential tests modify exactly pixel `(0,0)` by XOR 1 and compare ciphertexts using NPCR/UACI; key sensitivity changes the deterministic key material or chaotic `x0` by the runner's recorded perturbation. Timing uses the existing high-resolution operation helper and excludes loading, plotting, result serialization, and UI/network work. Failures are recorded per independent image/configuration row and do not silently stop the remaining matrix.

Experiment UUIDs and timestamps are run metadata and are allowed to vary. Ciphertexts, shares, and metric values are deterministic for fixed inputs, parameters, and seeds; timing measurements are expected to vary. Configuration C's primary key sensitivity flips exactly one deterministic key byte, while its optional seed-perturbation result is labelled separately. B, D, and E use the explicitly recorded `x0 + 1e-4` chaotic parameter sensitivity. For E, the selected share strategy is recorded as `first_k`, and decryption/quality metrics use the reconstructed ciphertext rather than the direct ciphertext.
