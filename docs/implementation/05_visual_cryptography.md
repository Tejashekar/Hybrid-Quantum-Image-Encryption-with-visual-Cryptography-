# Visual Cryptography Techniques in Quantum Image Encryption

## Overview

Visual Cryptography (VC) is a cryptographic method that allows for the encryption of visual information (images) in such a way that decryption can be performed visually without complex computations. In this project, we implement a (2,2) visual cryptography scheme, where an image is divided into two shares. Each share individually reveals no information about the original image, but when combined, they reconstruct the original image.

## Visual Cryptography Process

### 1. Share Generation

The process begins with the generation of two shares from the encrypted image. The shares are created using an XOR-based method, where one share is a random noise matrix, and the second share is derived from the encrypted image.

#### Steps:
- Generate a random noise matrix of the same dimensions as the encrypted image.
- Compute the second share by performing an XOR operation between the random noise matrix and the encrypted image.

### 2. Share Reconstruction

To reconstruct the original encrypted image, the two shares are combined using the XOR operation. This process ensures that the original encrypted image can be retrieved only when both shares are available.

#### Steps:
- Perform an XOR operation between the two shares to recover the encrypted image.

## Implementation in Code

The visual cryptography logic is implemented in the `visual_cryptography.py` module. Below are the key functions:

### Function: `generate_shares(encrypted_image)`

This function generates two shares from the encrypted image.

```python
import numpy as np

def generate_shares(encrypted_image):
    # Generate a random noise matrix
    noise_matrix = np.random.randint(0, 256, encrypted_image.shape, dtype=np.uint8)
    # Create the second share
    share2 = np.bitwise_xor(encrypted_image, noise_matrix)
    return noise_matrix, share2
```

### Function: `reconstruct_from_shares(share1, share2)`

This function reconstructs the encrypted image from the two shares.

```python
def reconstruct_from_shares(share1, share2):
    # Recover the encrypted image by XORing the two shares
    return np.bitwise_xor(share1, share2)
```

## Conclusion

The visual cryptography techniques implemented in this project provide a robust method for securely sharing encrypted images. By utilizing a (2,2) scheme, we ensure that the original information remains hidden unless both shares are combined, enhancing the security of the quantum image encryption process. 

Future work may include exploring higher-order visual cryptography schemes and integrating additional security measures to further enhance the robustness of the encryption process.