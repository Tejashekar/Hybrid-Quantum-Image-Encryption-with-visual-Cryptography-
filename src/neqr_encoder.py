def neqr_encode_qiskit(image_matrix):
    # This function builds the NEQR quantum circuit for small images (≤8×8)
    from qiskit import QuantumCircuit, Aer, transpile, assemble, execute
    import numpy as np

    # Get image dimensions
    height, width = image_matrix.shape
    num_qubits = int(np.log2(height * width))

    # Create a quantum circuit
    circuit = QuantumCircuit(num_qubits)

    # Encoding logic here (example: set qubits based on pixel values)
    for i in range(height):
        for j in range(width):
            if image_matrix[i, j] > 0:  # Assuming pixel values are > 0
                circuit.x(i * width + j)  # Apply X gate for non-zero pixels

    return circuit

def neqr_encode_numpy(image_matrix):
    # This function simulates the NEQR encoding logic using NumPy for larger images
    height, width = image_matrix.shape
    num_qubits = int(np.log2(height * width))

    # Initialize the quantum state as a zero vector
    quantum_state = np.zeros((2 ** num_qubits,), dtype=complex)

    # Encoding logic here (example: set amplitudes based on pixel values)
    for i in range(height):
        for j in range(width):
            index = i * width + j
            if image_matrix[i, j] > 0:  # Assuming pixel values are > 0
                quantum_state[index] = 1 / np.sqrt(np.sum(image_matrix > 0))  # Normalize

    return quantum_state

def neqr_decode(quantum_state):
    # This function decodes the quantum state back to a pixel matrix
    num_qubits = int(np.log2(len(quantum_state)))
    height = width = 2 ** (num_qubits // 2)  # Assuming square image for simplicity
    image_matrix = np.zeros((height, width), dtype=int)

    for index, amplitude in enumerate(quantum_state):
        if amplitude > 0:
            i = index // width
            j = index % width
            image_matrix[i, j] = 255  # Set pixel value (example)

    return image_matrix