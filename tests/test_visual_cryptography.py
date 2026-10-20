import numpy as np
import pytest

from src.visual_cryptography import generate_shares, reconstruct_from_shares


def test_shares_reconstruct_exactly_and_reproducibly():
    encrypted = np.arange(16, dtype=np.uint8).reshape(4, 4)
    share1, share2 = generate_shares(encrypted, seed=1)
    repeat1, repeat2 = generate_shares(encrypted, seed=1)
    assert np.array_equal(encrypted, reconstruct_from_shares(share1, share2))
    assert np.array_equal(share1, repeat1)
    assert np.array_equal(share2, repeat2)


def test_share_shape_mismatch_is_rejected():
    with pytest.raises(ValueError):
        reconstruct_from_shares(np.zeros((2, 2), dtype=np.uint8), np.zeros((2, 3), dtype=np.uint8))
