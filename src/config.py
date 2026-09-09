# Configuration settings for the Quantum Image Encryption + Visual Cryptography project

# Image size constants
DEFAULT_IMAGE_SIZE = (128, 128)  # Default size for demo purposes
SUPPORTED_IMAGE_SIZES = [(64, 64), (128, 128), (256, 256)]  # Supported sizes

# Logistic map parameters for chaotic key generation
LOGISTIC_MAP_PARAMS = {
    'mu': 3.99,  # Chaotic parameter
    'x0': 0.5    # Initial value
}

# Arnold Cat Map iteration count for pixel scrambling
ARNOLD_ITERATIONS = 5

# File paths for input and output directories
INPUT_DIR = 'input/'
OUTPUT_DIR = 'output/'