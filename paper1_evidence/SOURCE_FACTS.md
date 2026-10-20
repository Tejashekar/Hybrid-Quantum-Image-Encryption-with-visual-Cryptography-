# Paper 1 source facts

All statements below describe the checked-out source, not a security proof. Paths are relative to the repository root and line numbers refer to this working tree.

## A–D operation order and inverses

The authoritative dispatch is `src/pipeline.py:141-199` for encryption and `src/pipeline.py:202-257` for decryption. At the app boundary, configuration and public context are constructed at `app.py:417-445`.

| Configuration | Encryption order | Inverse order |
|---|---|---|
| A | Derive a 16,384-byte HKDF XOR array (`src/pipeline.py:152-156`; `src/diffusion.py:83-92`); XOR plaintext with it (`src/pipeline.py:152-156`). | Verify HMAC first; derive the same HKDF array and XOR ciphertext with it (`src/pipeline.py:202-217`). |
| B | Derive dense-stage mask/control material; leave plaintext values unchanged; XOR with the logistic-map byte stream; apply dense GF(256) diffusion (`src/pipeline.py:158-169,194-196`). | Verify HMAC; invert dense GF(256) diffusion; XOR with the regenerated logistic-map stream (`src/pipeline.py:209-232`). |
| C | Derive dense-stage material; apply reversible bit-pair mixing, controlled-XOR, selected-bit X-like flip, and conditional byte rotation; XOR with direct HKDF bytes; apply dense GF(256) diffusion (`src/pipeline.py:158-180,194-196`; `src/quantum_encryption.py:168-184`). | Verify HMAC; invert dense diffusion; undo HKDF XOR; undo byte rotation, X-like flip, controlled-XOR, and bit-pair mixing in reverse order (`src/pipeline.py:209-244`; `src/quantum_encryption.py:187-198`). |
| D | Derive dense-stage material; Arnold scramble; apply the same reversible operations as C; XOR with a logistic-map byte stream; apply dense GF(256) diffusion (`src/pipeline.py:158-196`). | Verify HMAC; invert dense diffusion; undo logistic XOR; inverse quantum-inspired operations; inverse Arnold map (`src/pipeline.py:209-257`). The configured API uses three Arnold iterations (`app.py:422-430`); the integrated configuration default is five (`src/pipeline.py:43-50`). |

`xor_diffusion` is the project’s elementwise XOR operation (`src/quantum_encryption.py:113-125`; call sites in `src/pipeline.py:153-196`). C/D byte operations are classical reversible byte transforms inspired by gates, not a quantum encryption operation: `src/quantum_encryption.py:58-63,86-111,128-134,168-184`.

## Dense GF(256) diffusion

For flattened input bytes `x_i` and mask bytes `k_i`, source forms `z_i = x_i XOR k_i`, `s = XOR_i z_i`, then `y_i = (c · z_i) XOR s`, where multiplication is in GF(256) (`src/diffusion.py:111-128`). The field uses XOR as addition and the Rijndael reduction polynomial `x^8+x^4+x^3+x+1` (hex `0x11B`): the shift/reduce loop is `src/visual_cryptography.py:41-51`, and the diffusion module names the polynomial at `src/diffusion.py:111-128`.

`c` is derived from one byte `r` of the `QCRYPT scalar` HKDF output: `c = 2 + (r mod 254)`, so `c` is in [2,255] (`src/diffusion.py:74-80,149-157`). Thus `r mod 254` is first in [0,253], then 2 is added.

For `m` elements, let `p = m mod 2` and `Y = XOR_i y_i`. From the forward equation, `Y = (c XOR p) · s`; therefore `s = (c XOR p)^(-1) · Y`, `z_i = c^(-1) · (y_i XOR s)`, and `x_i = z_i XOR k_i`. The implementation follows this inverse at `src/diffusion.py:131-146`. **Invertibility does not depend on the number of elements being even.** If `m` is even, `p=0` and `c XOR p=c`, nonzero because `c>=2`; if odd, `p=1` and `c XOR 1` is nonzero because `c` can never equal 1. Both cases have a field inverse.

## HKDF, context, labels, lengths

The project documents RFC 5869 HKDF-SHA-256 and a 32-byte input key / 16-byte nonce at `src/key_derivation.py:1-16,19-22`. Extract is `PRK = HMAC-SHA256(key=nonce, message=secret_key)` (`src/key_derivation.py:32-43`). The Expand info is `b"QCRYPT/phase7/" + ASCII(domain) + b"\\x00" + context_json`; context JSON is UTF-8 `json.dumps(context, sort_keys=True, separators=(",", ":"), allow_nan=False)` (`src/key_derivation.py:25-29,42-44`).

Expand uses the RFC recurrence `T(i)=HMAC(PRK,T(i-1)||info||counter)` (`src/key_derivation.py:46-54`). A single call is limited to 255 SHA-256 blocks = 8,160 bytes. Longer outputs are composed from repeated Expand calls whose info adds a zero byte, `QCRYPT expand chunk ` and a four-byte big-endian zero-based chunk index (`src/key_derivation.py:56-67`). For 16,384 bytes, chunk lengths are 8,160 + 8,160 + 64 bytes.

Canonical JSON top-level context fields are caller-specific, not one universal fixed schema. The call sites construct these fields:

- Direct XOR: `configuration`, `shape`, `public_config` (`src/diffusion.py:83-92`).
- Dense logistic initialization: `configuration`, `parameters`, `shape`, `x0`, `r`, `transient`, `public_seed` (`src/diffusion.py:32-71`).
- Logistic XOR initialization: `configuration`, `parameters`, `shape`, `r`, `transient`, `public_seed` (`src/diffusion.py:95-108`).
- Scalar: `configuration`, `public_config` (`src/diffusion.py:74-80`).
- Authentication: `configuration`, `public_config` (`src/key_derivation.py:81-97`).
- Sharing: caller-supplied configuration context (`src/key_derivation.py:108-116`).

Exact domain-label strings present in the implementation are `QCRYPT xor`, `QCRYPT chaotic`, `QCRYPT diffusion`, `QCRYPT scalar`, `QCRYPT iv`, `QCRYPT authentication`, and `QCRYPT sharing` (`src/diffusion.py:46-47,62,69,77,89,101`; `src/key_derivation.py:88-89,114-115`). Active A/C XOR arrays and B/D logistic initialization use the labels described below. `QCRYPT iv` is still derived as two legacy bytes in `derive_diffusion_material`, but the active pipeline discards those values (`src/diffusion.py:44-49,69-71`; `src/pipeline.py:158-196`).

## Generation of 16,384-byte arrays/streams

- **A XOR mask:** direct `QCRYPT xor` HKDF output of `H*W` bytes; NumPy interprets the byte sequence as `uint8` and reshapes it to the requested array shape (`src/diffusion.py:83-92`; called by A at `src/pipeline.py:152-156`). At 128×128, the request is 16,384 bytes and is emitted using three indexed chunks as described above.
- **Dense-stage mask and rotation material:** derive 16 bytes using `QCRYPT diffusion`; `keyed_logistic_parameters` interprets the first eight bytes as a big-endian integer and maps it to `x0=(integer+1)/(2^64+1)`, and the last eight bytes as a big-endian seed (`src/key_derivation.py:70-78`; `src/diffusion.py:56-65`). Generate `2*H*W+2` logistic states, convert each state `q` to `floor(q*2^40)` then take its low byte with `& 0xff`; first `H*W` bytes are `k1`, next `H*W` are `k2`; the final two generated stream bytes are unused (`src/chaotic_key.py:63-77`; `src/diffusion.py:64-71`). The separately HKDF-derived `QCRYPT iv` bytes are not the source of these masks.
- **B/D XOR stream:** derive 16 bytes under `QCRYPT chaotic`; use the same first-eight/last-eight conversion to initial condition and seed, generate `H*W` logistic states, apply the same fixed-point/low-byte quantization, then reshape in C order as `uint8` (`src/diffusion.py:95-108`; `src/key_derivation.py:70-78`; `src/chaotic_key.py:63-77`).

The Logistic map is `x[n+1]=r*x[n]*(1-x[n])`; defaults are `x0=0.5`, `r=3.99`, transient 1000, and valid `r` is greater than 3.57 and at most 4 (`src/chaotic_key.py:15-17,20-28,31-60`). In the API A–D configs, `x0=0.37`, `r=3.91`, transient 1000, and a deterministic public config seed are used (`app.py:417-430`). **The logistic stream is not a cryptographic PRG** (`src/chaotic_key.py:1-5`; `src/key_derivation.py:1-5`). HKDF is a cryptographic KDF, but the logistic postprocessing is not a CSPRNG construction. Source documentation at `src/chaotic_key.py:71` says “bits 32–39”; the implementation at `:73-77` actually takes the low 8 bits after 40-bit fixed-point scaling. This docstring/code discrepancy should be corrected in the source or described according to the code in the paper.

## Logistic, Arnold, byte rotation, reversible bit operations

The map, parameters, transient and seed warm-up are specified at `src/chaotic_key.py:15-60`. Each optional integer seed adds `seed mod 1000` iterations to the transient warm-up (`src/chaotic_key.py:41-59`). Byte quantization is described above (`src/chaotic_key.py:71-77`).

Arnold forward step, with `x=column`, `y=row`, is `x'=(x+y) mod N`, `y'=(x+2y) mod N` (`src/quantum_encryption.py:221-230`). The inverse is `x=(2x'-y') mod N`, `y=(-x'+y') mod N` (`src/quantum_encryption.py:233-242`). The app defaults to three iterations (`app.py:422-430`).

For each adjacent bit pair `(a,b)`, bit mixing maps `(a,b)->(a XOR b,a)`; inverse maps `(u,v)->(v,u XOR v)` (`src/quantum_encryption.py:58-83`). The CNOT-like operation XORs the selected control bit into the target and is self-inverse (`src/quantum_encryption.py:86-98`). X-like operation XORs `1<<x_bit` and is self-inverse (`src/quantum_encryption.py:101-111`). Byte rotation uses control `k1&1`, amount `(k2 mod 7)+1`; if control is one, rotate the byte left by that many bits, otherwise leave it unchanged. Inverse rotates right (`src/quantum_encryption.py:128-165`). API bit controls default to CNOT control=2,target=6 and X bit=3 (`app.py:426-430`).

## HMAC, nonce and artifacts

The authentication key is a 32-byte HKDF-SHA-256 output with label `QCRYPT authentication` and context containing `configuration` and `public_config` (`src/key_derivation.py:81-90`). The HMAC-SHA-256 message is compact, sorted, UTF-8 JSON header plus `0x00` plus the ciphertext `uint8` bytes in C order. Header fields and order-independent serialization are `format_version=5`, `configuration`, `public_config`, `shape`, and nonce hex (`src/key_derivation.py:90-97`). The resulting tag is 32 bytes. Verification checks length and uses `hmac.compare_digest` (`src/key_derivation.py:100-105`). Decryption verifies the tag before any inverse operation (`src/pipeline.py:202-225`).

When omitted, nonce is generated with `secrets.token_bytes(16)`; supplied values are validated for 16-byte length (`src/diffusion.py:20-29`). There is no nonce uniqueness store/check in this path: encryption normalizes the nonce and proceeds (`src/pipeline.py:141-151`); repository search for nonce tracking found only validation/generation, deterministic experiment nonce functions, and same-nonce tests. Reusing a caller-supplied key/nonce/configuration is not prevented by the implementation.

Version-5 serialization depends on artifact type:

- `EncryptedImage.to_dict()` serializes `ciphertext` as nested lists, `metadata`, `format_version`, nonce hex, authentication-tag hex, and configuration (`src/pipeline.py:130-138`). Its metadata is the public configuration context (`src/pipeline.py:197-199`).
- PNG ciphertext stores the ciphertext as pixel data and PNG text fields `qcrypt_format_version`, `qcrypt_nonce`, `qcrypt_auth_tag`, and `qcrypt_configuration` (`app.py:128-138`).
- Research share-bundle metadata serializes `config`, version, nonce and tag; the share arrays and indices are serialized separately (`src/pipeline.py:353-367,395-405`).

The secret key and derived mask/stream/scalar/authentication key are not serialized by these methods (`src/pipeline.py:74-89,130-138,361-367`; `app.py:128-138`). The nonce and tag are public serialized fields; no plaintext is added to the ciphertext artifact.

## Metrics and timing

- Entropy is empirical plug-in Shannon entropy in bits per pixel, computed from observed byte frequencies (`src/metrics.py:25-30`).
- Horizontal correlation uses all `(row,col)`/`(row,col+1)` pairs; vertical uses all `(row,col)`/`(row+1,col)` pairs; diagonal uses all down-right `(row,col)`/`(row+1,col+1)` pairs. It is Pearson correlation on centered flattened arrays, not a random sample (`src/metrics.py:33-55`). A zero-variance neighborhood returns 0.0 (`src/metrics.py:38-42`).
- NPCR is the percent of unequal corresponding bytes (`src/metrics.py:64-68`). UACI is mean absolute byte difference divided by 255, as percent (`src/metrics.py:70-73`).
- XOR-difference occupancy is calculated by the Phase 6 runner as nonzero XOR bytes divided by byte count and multiplied by 100 (`experiments/phase6_security.py:66-80`). For `uint8`, this equals NPCR for the same arrays, since XOR is nonzero exactly when values differ.
- `src.metrics.measure_operation` times one callable with `perf_counter_ns` and converts to milliseconds (`src/metrics.py:148-153`). Phase 6 wraps encryption and decryption separately for each of five repetitions (`experiments/phase6_security.py:52-55,472-484`). Aggregator summaries use arithmetic mean and **population** standard deviation `ddof=0`, plus min/max (`experiments/aggregate_phase6.py:35-53`). The T5 evidence in this folder reports the specifically requested **sample** standard deviation `ddof=1`; do not confuse the two aggregations.

