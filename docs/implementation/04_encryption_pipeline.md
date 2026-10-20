# Historical documentation — this describes an earlier design and is not the active encryption pipeline.

# Encryption Pipeline Documentation

## Overview

The encryption pipeline is a critical component of the Quantum Image Encryption + Visual Cryptography project. It orchestrates the process of encrypting images using quantum techniques and visual cryptography, ensuring that the original image can be securely transformed into an encrypted format and subsequently reconstructed.

## Components of the Encryption Pipeline

1. **Image Input**: The pipeline begins with the input of an image, which can be uploaded through the user interface. The image is then preprocessed to ensure it is in the correct format for encryption.

2. **NEQR Encoding**: The image is encoded using the Novel Quantum Representation (NEQR) method. This step involves converting the image into a quantum state representation, which is essential for the subsequent quantum operations.

3. **Quantum Encryption**: The core of the pipeline involves applying quantum gates to the encoded image. This step includes:
   - Generating a chaotic key using the Logistic Map.
   - Scrambling the pixel positions using the Arnold Cat Map.
   - Applying quantum gates (Hadamard, CNOT, etc.) to enhance security.

4. **Visual Cryptography**: After encryption, the image is split into shares using a (2,2) visual cryptography scheme. This ensures that no single share reveals any information about the original image.

5. **Output Generation**: The encrypted shares are saved as separate image files, which can be transmitted securely. The pipeline also allows for the reconstruction of the original image from the shares.

## Implementation Steps

1. **Image Upload**: 
   - Users upload an image through the interface.
   - The image is validated and passed to the preprocessing module.

2. **Preprocessing**:
   - The image is resized and converted to grayscale.
   - The processed image is transformed into a NumPy matrix for further processing.

3. **NEQR Encoding**:
   - The image matrix is encoded using the NEQR method.
   - For small images, Qiskit is used to create the quantum circuit; for larger images, a NumPy simulation is employed.

4. **Key Generation**:
   - A chaotic key is generated using the Logistic Map, which serves as the encryption key.

5. **Pixel Scrambling**:
   - The Arnold Cat Map is applied to scramble the pixel positions of the encoded image.

6. **Quantum Gate Application**:
   - Quantum gates are applied to the scrambled image to enhance security.
   - The operations include Hadamard, CNOT, and other gates as defined in the quantum encryption module.

7. **Visual Cryptography**:
   - The encrypted image is split into two shares using an XOR-based method.
   - Share 1 is generated as a random noise matrix, and Share 2 is created by XORing the encrypted image with Share 1.

8. **Output**:
   - The shares are saved as separate image files in the output directory.
   - The pipeline provides options for users to download the shares.

## Conclusion

The encryption pipeline effectively combines quantum computing techniques with visual cryptography to secure images. By following the outlined steps, users can encrypt their images and ensure that they can only be reconstructed with the appropriate shares. This documentation serves as a guide for understanding and implementing the encryption pipeline within the Quantum Image Encryption + Visual Cryptography project.
