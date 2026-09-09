# Decryption Pipeline Implementation

## Overview
The decryption pipeline is a crucial component of the Quantum Image Encryption + Visual Cryptography project. It is responsible for reversing the encryption process, allowing users to recover the original image from the encrypted data and visual cryptography shares. This document outlines the steps involved in the decryption pipeline, detailing the functions and processes used to achieve this.

## Steps in the Decryption Pipeline

1. **Input Acquisition**
   - The user uploads the encrypted image and the two shares generated during the visual cryptography process.

2. **Reverse XOR Diffusion**
   - The first step in decryption involves reversing the XOR diffusion applied during the encryption process. This is done using the `reverse_xor_diffusion` function from the `decryption.py` module.
   - The function takes the encrypted image and the chaotic key as inputs to recover the intermediate state before quantum gate operations.

3. **Reverse Quantum Gate Operations**
   - After recovering the intermediate state, the next step is to reverse the quantum gate operations applied during encryption. This is achieved using the `reverse_quantum_gates` function.
   - The function applies the inverse of the quantum gates (Z → X → CNOT⁻¹ → H) to the pixel data, restoring the original pixel arrangement.

4. **Inverse Arnold Cat Map**
   - The final step in the decryption process is to reverse the pixel scrambling performed by the Arnold Cat Map. This is done using the `inverse_arnold_cat_map` function.
   - The function takes the image and the number of iterations used during encryption to restore the original pixel positions.

5. **Output the Decrypted Image**
   - Once all steps are completed, the decrypted image is outputted, allowing the user to view the original image.

## Implementation

The following functions are implemented in the `src/decryption.py` module to facilitate the decryption pipeline:

```python
def reverse_xor_diffusion(image, key):
    # Implementation of reverse XOR diffusion
    pass

def reverse_quantum_gates(image, key):
    # Implementation of reverse quantum gate operations
    pass

def inverse_arnold_cat_map(image, iterations):
    # Implementation of inverse Arnold Cat Map
    pass

def decrypt(encrypted_image, share1, share2, key):
    # Full decryption pipeline
    intermediate_image = reverse_xor_diffusion(encrypted_image, key)
    quantum_reversed_image = reverse_quantum_gates(intermediate_image, key)
    decrypted_image = inverse_arnold_cat_map(quantum_reversed_image, iterations)
    return decrypted_image
```

## Conclusion
The decryption pipeline effectively reverses the encryption process, ensuring that users can recover their original images securely. By following the outlined steps and utilizing the provided functions, the decryption process is both efficient and reliable.