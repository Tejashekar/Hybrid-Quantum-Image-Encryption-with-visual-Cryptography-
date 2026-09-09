import numpy as np


def generate_shares(encrypted_image):
    height, width = encrypted_image.shape
    share1 = np.random.randint(0, 256, (height, width), dtype=np.uint8)
    share2 = np.bitwise_xor(encrypted_image, share1)
    return share1, share2


def reconstruct_from_shares(share1, share2):
    return np.bitwise_xor(share1, share2)