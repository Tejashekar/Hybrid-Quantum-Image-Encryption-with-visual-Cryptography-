import pytest
import numpy as np
from src.metrics import histogram_analysis, correlation_analysis, entropy, npcr_uaci, psnr

def test_histogram_analysis():
    original = np.array([[0, 0, 0], [255, 255, 255]])
    encrypted = np.array([[128, 128, 128], [128, 128, 128]])
    
    hist_original = histogram_analysis(original, encrypted)
    assert hist_original is not None

def test_correlation_analysis():
    image = np.array([[0, 0, 0], [255, 255, 255]])
    correlation = correlation_analysis(image)
    assert correlation >= 0.0 and correlation <= 1.0

def test_entropy():
    image = np.array([[0, 0, 0], [255, 255, 255]])
    calculated_entropy = entropy(image)
    assert calculated_entropy >= 0.0

def test_npcr_uaci():
    image1 = np.array([[0, 0, 0], [255, 255, 255]])
    image2 = np.array([[255, 255, 255], [0, 0, 0]])
    
    npcr, uaci = npcr_uaci(image1, image2)
    assert npcr >= 0.0 and npcr <= 100.0
    assert uaci >= 0.0 and uaci <= 100.0

def test_psnr():
    original = np.array([[0, 0, 0], [255, 255, 255]])
    decrypted = np.array([[0, 0, 0], [255, 255, 255]])
    
    calculated_psnr = psnr(original, decrypted)
    assert calculated_psnr == float('inf')  # Lossless should yield infinite PSNR