"""Deterministic center-crop preprocessing for grayscale research images."""
from __future__ import annotations

import cv2
import numpy as np


PREPROCESSING_VERSION = "center-square-crop-resize-grayscale-v1"
INTERPOLATION_NAME = "INTER_AREA"


def load_image(path):
    """Load a color image in OpenCV BGR channel order."""
    return cv2.imread(str(path), cv2.IMREAD_COLOR)


def preprocessing_parameters(size=(128, 128)) -> dict:
    """Describe the deterministic crop, resize, and grayscale protocol."""
    width, height = _target_dimensions(size)
    return {
        "version": PREPROCESSING_VERSION,
        "method": "largest centered square crop, then resize",
        "crop": "center square with side=min(original_width, original_height)",
        "target_size": [height, width],
        "interpolation": INTERPOLATION_NAME,
        "input_color_order": "OpenCV BGR/BGRA or grayscale",
        "output_color_space": "grayscale",
        "output_channels": 1,
        "output_dtype": "uint8",
    }


def _target_dimensions(size):
    if isinstance(size, (int, np.integer)):
        width = height = int(size)
    else:
        if len(size) != 2:
            raise ValueError("size must be an integer or a square (width, height) pair")
        width, height = (int(size[0]), int(size[1]))
    if width <= 0 or height <= 0 or width != height:
        raise ValueError("target size must be a positive square")
    return width, height


def preprocess(image, size=(128, 128)):
    """Center-crop to a square, resize deterministically, and return uint8 gray.

    Color inputs use OpenCV's BGR/BGRA-to-gray conversion after resizing;
    two-dimensional inputs are treated as grayscale. No aspect-ratio stretch
    is applied because the crop is square before the resize stage.
    """
    if image is None:
        raise ValueError("image cannot be None")
    width, height = _target_dimensions(size)
    array = np.asarray(image)
    if array.ndim not in (2, 3) or (array.ndim == 3 and array.shape[2] not in (3, 4)):
        raise ValueError("image must be grayscale, BGR, or BGRA")
    if array.size == 0:
        raise ValueError("image cannot be empty")
    if array.dtype != np.uint8:
        if np.issubdtype(array.dtype, np.integer) and array.min() >= 0 and array.max() <= 255:
            array = array.astype(np.uint8)
        else:
            raise ValueError("image pixels must be representable as uint8 values")

    source_height, source_width = array.shape[:2]
    side = min(source_width, source_height)
    left = (source_width - side) // 2
    top = (source_height - side) // 2
    square = array[top:top + side, left:left + side]
    resized = cv2.resize(square, (width, height), interpolation=cv2.INTER_AREA)
    if resized.ndim == 3:
        conversion = cv2.COLOR_BGRA2GRAY if resized.shape[2] == 4 else cv2.COLOR_BGR2GRAY
        resized = cv2.cvtColor(resized, conversion)
    return np.ascontiguousarray(resized, dtype=np.uint8)


def image_to_matrix(image):
    return np.array(image)


def matrix_to_image(matrix):
    return np.uint8(matrix)
