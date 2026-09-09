def load_image(image_path):
    # Load an image from the specified path using OpenCV
    import cv2
    image = cv2.imread(image_path)
    return image

def save_image(image, save_path):
    # Save an image to the specified path using OpenCV
    import cv2
    cv2.imwrite(save_path, image)

def display_image(image, title="Image"):
    # Display an image in a window using OpenCV
    import cv2
    cv2.imshow(title, image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def resize_image(image, size):
    # Resize the image to the specified size
    import cv2
    resized_image = cv2.resize(image, size)
    return resized_image

def convert_to_grayscale(image):
    # Convert the image to grayscale
    import cv2
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return gray_image

def image_to_matrix(image):
    # Convert the image to a NumPy matrix
    import numpy as np
    return np.array(image)

def matrix_to_image(matrix):
    # Convert a NumPy matrix back to an image
    import numpy as np
    return np.uint8(matrix)