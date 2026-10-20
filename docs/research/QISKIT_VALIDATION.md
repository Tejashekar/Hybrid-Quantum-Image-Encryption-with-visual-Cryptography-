# Small-scale Qiskit validation

The production image workflow remains a classical simulation of quantum-inspired reversible operations. This validation uses Qiskit **2.3.0** only in the isolated `src/qiskit_validation.py` module and its tests; the Flask image pipeline does not import or invoke that module.

The validator constructs explicit circuits and compares basis-state outputs against the classical operations:

- X-inspired bit flip: both one-qubit computational-basis states.
- CNOT-inspired controlled XOR: all four two-qubit computational-basis states, with the conventional control/target order.
- Reversible bit-mixing analogue `(a,b) -> (a XOR b,a)`: all 256 eight-bit basis states, implemented as four pairs of CNOT operations.

For each mapping, the tests also check exact return to the input basis state after the inverse circuit and verify the corresponding classical inverse.

The Z comparison is intentionally separate. A genuine Qiskit Z gate leaves `|0>` unchanged and applies a negative phase to `|1>`; on `|+>` it produces `|->`. The production Z-inspired operation is instead a key-controlled reversible rotation of a classical byte. The two transformations are not equivalent.

These checks establish only the tested computational-basis correspondences. They do not establish equivalence on arbitrary superpositions, validate the full image-encryption pipeline as a quantum circuit, demonstrate quantum hardware execution or advantage, or establish cryptographic security. The 128×128 workflow remains classical; there is no post-quantum security claim.

Run the validation with:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_qiskit_validation.py
```
