def load_image(path):
    import cv2
    image = cv2.imread(path)
    return image

def preprocess(image, size=(128, 128)):
    import cv2
    image_resized = cv2.resize(image, size)
    image_gray = cv2.cvtColor(image_resized, cv2.COLOR_BGR2GRAY)
    return image_gray

def image_to_matrix(image):
    import numpy as np
    return np.array(image)

def matrix_to_image(matrix):
    import numpy as np
    return np.uint8(matrix)