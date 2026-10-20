import numpy as np
import qiskit

from src.qiskit_validation import demonstrate_z_distinction, validate_qiskit_correspondences
from src.quantum_encryption import (
    inverse_z_inspired_reversible_bit_rotation,
    reversible_bit_mixing_transform,
    z_inspired_reversible_bit_rotation,
)


def test_qiskit_validation_dependency_version():
    assert qiskit.__version__ == "2.3.0"


def test_x_cnot_and_bit_mixing_exhaustive_basis_correspondence_and_inverses():
    result = validate_qiskit_correspondences()
    assert result["qiskit_version"] == qiskit.__version__
    assert result["x"]["basis_states_checked"] == 2
    assert [row["output"] for row in result["x"]["rows"]] == [1, 0]
    assert result["cnot"]["basis_states_checked"] == 4
    assert [row["output"] for row in result["cnot"]["rows"]] == [0, 1, 3, 2]
    assert result["reversible_bit_mixing"]["basis_states_checked"] == 256
    assert len({row["output"] for row in result["reversible_bit_mixing"]["rows"]}) == 256
    for row in result["reversible_bit_mixing"]["rows"]:
        assert row["output"] == int(
            reversible_bit_mixing_transform(np.array([[row["input"]]], dtype=np.uint8))[0, 0]
        )


def test_genuine_z_gate_phase_is_distinct_from_classical_conditional_rotation():
    result = demonstrate_z_distinction()
    basis = result["qiskit_z_basis_statevectors"]
    assert basis == [[1 + 0j, 0j], [0j, -1 + 0j]]
    plus_z = np.asarray(result["qiskit_z_on_plus_statevector"], dtype=np.complex128)
    assert np.allclose(plus_z, [2**-0.5, -(2**-0.5)])
    classical = result["classical_conditional_rotation"]
    assert classical == {"input_byte": 1, "control": 1, "rotation": 1, "output_byte": 2}
    assert result["same_transformation"] is False


def test_classical_conditional_byte_rotation_is_a_reversible_permutation():
    values = np.arange(256, dtype=np.uint8).reshape(16, 16)
    controls = np.ones(values.shape, dtype=np.uint8)
    rotations = np.ones(values.shape, dtype=np.uint8)
    transformed = z_inspired_reversible_bit_rotation(values, controls, rotations)
    recovered = inverse_z_inspired_reversible_bit_rotation(transformed, controls, rotations)
    assert np.any(transformed != values)
    assert np.array_equal(recovered, values)

