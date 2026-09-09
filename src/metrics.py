import numpy as np


def histogram_analysis(original, encrypted):
    import cv2
    import matplotlib.pyplot as plt

    # Calculate histograms
    hist_original = cv2.calcHist([original], [0], None, [256], [0, 256])
    hist_encrypted = cv2.calcHist([encrypted], [0], None, [256], [0, 256])

    # Normalize histograms
    hist_original = hist_original / hist_original.sum()
    hist_encrypted = hist_encrypted / hist_encrypted.sum()

    # Plot histograms
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.title('Histogram of Original Image')
    plt.plot(hist_original, color='blue')
    plt.xlim([0, 256])

    plt.subplot(1, 2, 2)
    plt.title('Histogram of Encrypted Image')
    plt.plot(hist_encrypted, color='red')
    plt.xlim([0, 256])

    plt.show()
    return hist_original, hist_encrypted


def correlation_analysis(image):
    from scipy.stats import pearsonr

    # Flatten the image to a 1D array
    pixels = image.flatten()
    if pixels.size < 2:
        return 0.0
    if np.std(pixels[:-1]) == 0 or np.std(pixels[1:]) == 0:
        return 0.0
    # Calculate correlation coefficient with itself (should be 1)
    correlation = pearsonr(pixels[:-1], pixels[1:])[0]
    if np.isnan(correlation):
        return 0.0
    return correlation


def entropy(image):
    from skimage.measure import shannon_entropy

    # Calculate the entropy of the image
    return shannon_entropy(image)


def npcr_uaci(image1, image2):
    # Number of pixels
    total_pixels = image1.size

    # NPCR calculation
    npcr = np.sum(image1 != image2) / total_pixels * 100

    # UACI calculation
    uaci = np.mean(np.abs(image1.astype(float) - image2.astype(float))) / 255 * 100

    return npcr, uaci


def psnr(original, decrypted):
    mse = np.mean((original.astype(np.float64) - decrypted.astype(np.float64)) ** 2)
    if mse == 0:
        return float('inf')  # No noise is present in the signal
    max_pixel = 255.0
    return 20 * np.log10(max_pixel / np.sqrt(mse))