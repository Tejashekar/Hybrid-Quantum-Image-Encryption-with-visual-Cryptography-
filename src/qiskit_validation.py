"""Small-register Qiskit checks for selected classical bit-operation mappings.

This validation-only module is intentionally not imported by the production
image pipeline. It checks computational-basis behavior, not general quantum
state equivalence or quantum security.
"""
from __future__ import annotations

import qiskit
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

import numpy as np

from .quantum_encryption import (
    cnot_inspired_transform,
    inverse_cnot_inspired_transform,
    inverse_reversible_bit_mixing_transform,
    inverse_x_inspired_bit_flip,
    reversible_bit_mixing_transform,
    x_inspired_bit_flip,
    z_inspired_reversible_bit_rotation,
)


def _run_basis(circuit: QuantumCircuit, basis_value: int, qubits: int, *, inverse=False) -> tuple[int, complex]:
    """Run one basis state through a circuit and return output index/amplitude."""
    prepared = QuantumCircuit(qubits)
    for bit in range(qubits):
        if (basis_value >> bit) & 1:
            prepared.x(bit)
    operation = circuit.compose(circuit.inverse()) if inverse else circuit
    state = Statevector.from_instruction(prepared.compose(operation))
    index = int(np.argmax(np.abs(state.data)))
    return index, complex(state.data[index])


def _x_circuit(bit: int = 0, qubits: int = 1) -> QuantumCircuit:
    circuit = QuantumCircuit(qubits)
    circuit.x(bit)
    return circuit


def _cnot_circuit(control: int = 0, target: int = 1) -> QuantumCircuit:
    circuit = QuantumCircuit(2)
    circuit.cx(control, target)
    return circuit


def _bit_mixing_circuit() -> QuantumCircuit:
    """Eight-qubit permutation matching the four classical bit-pair maps."""
    circuit = QuantumCircuit(8)
    for low in range(0, 8, 2):
        # (a,b) -> (a XOR b,a), where low stores a and high stores b.
        circuit.cx(low + 1, low)
        circuit.cx(low, low + 1)
    return circuit


def validate_qiskit_correspondences() -> dict:
    """Exhaustively validate X, CNOT, and reversible bit-mixing basis maps."""
    x_circuit = _x_circuit()
    x_rows = []
    for value in range(2):
        output, amplitude = _run_basis(x_circuit, value, 1)
        expected = int(x_inspired_bit_flip(np.array([[value]], dtype=np.uint8), bit=0)[0, 0])
        classical_inverse = int(inverse_x_inspired_bit_flip(np.array([[expected]], dtype=np.uint8), bit=0)[0, 0])
        inverse_output, inverse_amplitude = _run_basis(x_circuit, value, 1, inverse=True)
        if output != expected or classical_inverse != value or inverse_output != value or amplitude != 1 or inverse_amplitude != 1:
            raise AssertionError(f"X correspondence failed for basis input {value}")
        x_rows.append({"input": value, "output": output})

    # The displayed two-bit order is conventional control, target (MSB, LSB).
    cnot_circuit = _cnot_circuit(control=1, target=0)
    cnot_rows = []
    for value in range(4):
        output, amplitude = _run_basis(cnot_circuit, value, 2)
        expected = int(cnot_inspired_transform(np.array([[value]], dtype=np.uint8), 1, 0)[0, 0])
        classical_inverse = int(inverse_cnot_inspired_transform(np.array([[expected]], dtype=np.uint8), 1, 0)[0, 0])
        inverse_output, inverse_amplitude = _run_basis(cnot_circuit, value, 2, inverse=True)
        if output != expected or classical_inverse != value or inverse_output != value or amplitude != 1 or inverse_amplitude != 1:
            raise AssertionError(f"CNOT correspondence failed for basis input {value}")
        cnot_rows.append({"input": value, "output": output})

    mix_circuit = _bit_mixing_circuit()
    mixing_rows = []
    for value in range(256):
        output, amplitude = _run_basis(mix_circuit, value, 8)
        expected = int(reversible_bit_mixing_transform(np.array([[value]], dtype=np.uint8))[0, 0])
        classical_inverse = int(inverse_reversible_bit_mixing_transform(np.array([[expected]], dtype=np.uint8))[0, 0])
        inverse_output, inverse_amplitude = _run_basis(mix_circuit, value, 8, inverse=True)
        if output != expected or classical_inverse != value or inverse_output != value or amplitude != 1 or inverse_amplitude != 1:
            raise AssertionError(f"bit-mixing correspondence failed for basis input {value}")
        mixing_rows.append({"input": value, "output": output})

    return {
        "qiskit_version": qiskit.__version__,
        "x": {"qubits": 1, "basis_states_checked": len(x_rows), "rows": x_rows},
        "cnot": {"qubits": 2, "basis_states_checked": len(cnot_rows), "rows": cnot_rows},
        "reversible_bit_mixing": {
            "qubits": 8, "basis_states_checked": len(mixing_rows), "rows": mixing_rows,
        },
    }


def demonstrate_z_distinction() -> dict:
    """Return genuine Z-gate phase behavior and separate classical rotation data."""
    z = QuantumCircuit(1)
    z.z(0)
    z_basis = []
    for value in range(2):
        prepared = QuantumCircuit(1)
        if value:
            prepared.x(0)
        state = Statevector.from_instruction(prepared.compose(z))
        z_basis.append([complex(amplitude) for amplitude in state.data])

    plus = QuantumCircuit(1)
    plus.h(0)
    plus_z_state = Statevector.from_instruction(plus.compose(z))

    # This is the repository's classical operation, deliberately not a Qiskit Z.
    source = np.array([[1]], dtype=np.uint8)
    controls = np.array([[1]], dtype=np.uint8)
    rotations = np.array([[1]], dtype=np.uint8)
    classical_rotated = int(z_inspired_reversible_bit_rotation(source, controls, rotations)[0, 0])
    return {
        "qiskit_z_basis_statevectors": z_basis,
        "qiskit_z_on_plus_statevector": [complex(value) for value in plus_z_state.data],
        "classical_conditional_rotation": {"input_byte": 1, "control": 1, "rotation": 1,
                                           "output_byte": classical_rotated},
        "same_transformation": False,
    }
