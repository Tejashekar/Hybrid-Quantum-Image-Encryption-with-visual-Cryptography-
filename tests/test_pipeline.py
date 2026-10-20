import cv2
import numpy as np

from src.pipeline import run_pipeline


def test_pipeline_round_trip(tmp_path):
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    path = tmp_path / "sample.png"
    cv2.imwrite(str(path), image)
    result = run_pipeline(str(path), size=(8, 8), seed=7)
    assert np.array_equal(result["original"], result["decrypted"])
    assert np.array_equal(result["encrypted"], result["reconstructed"])
    assert result["psnr"] == float("inf")
