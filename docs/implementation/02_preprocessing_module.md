# Preprocessing Module Documentation

## Overview

The preprocessing module is a crucial component of the Quantum Image Encryption + Visual Cryptography project. It is responsible for preparing images for further processing in the encryption pipeline. This module includes functions for loading images, resizing them, converting them to grayscale, and transforming them into NumPy matrices.

## Functions

### 1. `load_image(path)`

- **Description**: Loads an image from the specified file path.
- **Parameters**:
  - `path` (str): The file path of the image to be loaded.
- **Returns**: The loaded image in its original format.

### 2. `preprocess(image, size)`

- **Description**: Resizes the input image to the specified dimensions and converts it to grayscale.
- **Parameters**:
  - `image`: The input image to be processed.
  - `size` (tuple): The desired dimensions for the output image (width, height).
- **Returns**: The preprocessed image in grayscale.

### 3. `image_to_matrix(image)`

- **Description**: Converts the preprocessed image into a NumPy matrix representation.
- **Parameters**:
  - `image`: The preprocessed image to be converted.
- **Returns**: A NumPy array representing the pixel values of the image.

### 4. `matrix_to_image(matrix)`

- **Description**: Converts a NumPy matrix back into an image format.
- **Parameters**:
  - `matrix`: The NumPy array representing the pixel values of the image.
- **Returns**: The reconstructed image from the NumPy matrix.

## Usage

To utilize the preprocessing module, you can import the functions as follows:

```python
from src.preprocessing import load_image, preprocess, image_to_matrix, matrix_to_image

# Example usage
image_path = 'path/to/image.png'
image = load_image(image_path)
preprocessed_image = preprocess(image, (128, 128))
image_matrix = image_to_matrix(preprocessed_image)
reconstructed_image = matrix_to_image(image_matrix)
```

## Conclusion

The preprocessing module is essential for ensuring that images are in the correct format and size for the subsequent encryption and visual cryptography processes. Proper preprocessing enhances the overall effectiveness and efficiency of the quantum image encryption system.