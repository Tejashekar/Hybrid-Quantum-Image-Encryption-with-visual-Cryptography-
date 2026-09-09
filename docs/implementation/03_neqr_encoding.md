# NEQR Encoding in Quantum Image Encryption

## Overview

The NEQR (Novel Enhanced Quantum Representation) encoding is a crucial step in the quantum image encryption process. It allows classical images to be represented in a quantum format, enabling the application of quantum algorithms for encryption and processing. This document outlines the implementation details of the NEQR encoding module, including its functions and usage.

## NEQR Encoding Process

### 1. Image Representation

NEQR encodes an image by representing its pixel values and their positions in a quantum state. For a grayscale image of size \(N \times N\), the encoding requires:

- **Intensity Encoding**: Each pixel's intensity is represented using a certain number of qubits.
- **Position Encoding**: The position of each pixel is also encoded, allowing for the reconstruction of the image later.

### 2. Functions

The `neqr_encoder.py` module contains the following key functions:

- **`neqr_encode_qiskit(image_matrix)`**: 
  - This function constructs a Qiskit circuit for encoding small images (up to 8x8 pixels). It utilizes quantum gates to create a superposition of pixel states.
  
- **`neqr_encode_numpy(image_matrix)`**: 
  - For larger images, this function simulates the NEQR encoding using NumPy. It processes the pixel values and their positions to create a quantum-like representation without actual quantum computation.

- **`neqr_decode(quantum_state)`**: 
  - This function decodes the quantum state back into a classical pixel matrix, allowing for the retrieval of the original image data.

### 3. Implementation Steps

1. **Load the Image**: Use the preprocessing module to load and convert the image into a NumPy matrix.
2. **Choose Encoding Method**: Depending on the image size, select either the Qiskit-based or NumPy-based encoding function.
3. **Execute Encoding**: Call the appropriate encoding function to generate the quantum representation of the image.
4. **Store Quantum State**: Save the resulting quantum state for further processing in the encryption pipeline.

### 4. Example Usage

```python
from src.preprocessing import load_image, image_to_matrix
from src.neqr_encoder import neqr_encode_qiskit, neqr_encode_numpy

# Load and preprocess the image
image_path = 'input/sample.png'
image = load_image(image_path)
image_matrix = image_to_matrix(image)

# Encode the image using NEQR
if image_matrix.shape[0] <= 8:  # Small image
    quantum_state = neqr_encode_qiskit(image_matrix)
else:  # Larger image
    quantum_state = neqr_encode_numpy(image_matrix)
```

## Conclusion

The NEQR encoding module is a foundational component of the quantum image encryption process. By effectively transforming classical images into quantum states, it enables the application of quantum algorithms for secure image encryption and processing. This document serves as a guide for understanding and implementing the NEQR encoding in the Quantum Image Encryption + Visual Cryptography project.