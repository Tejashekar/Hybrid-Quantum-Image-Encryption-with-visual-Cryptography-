from itertools import combinations

import numpy as np
import pytest

from src.visual_cryptography import generate_shares, reconstruct_from_shares


@pytest.mark.parametrize("k,n", [(2, 2), (2, 3), (3, 5), (3, 6)])
def test_all_required_threshold_combinations_reconstruct(k, n):
    secret = np.random.default_rng(k * 100 + n).integers(0, 256, (4, 4), dtype=np.uint8)
    shares = generate_shares(secret, k, n, seed=12)
    assert len(shares) == n
    for indices in combinations(range(n), k):
        recovered = reconstruct_from_shares([shares[index] for index in indices], k, n)
        assert np.array_equal(recovered, secret)


@pytest.mark.parametrize("k,n", [(2, 3), (3, 5), (3, 6)])
def test_fewer_than_threshold_shares_are_rejected(k, n):
    secret = np.arange(16, dtype=np.uint8).reshape(4, 4)
    shares = generate_shares(secret, k, n, seed=3)
    with pytest.raises(ValueError, match="at least"):
        reconstruct_from_shares(shares[: k - 1], k, n)


def test_generation_is_deterministic_and_seed_sensitive():
    secret = np.arange(16, dtype=np.uint8).reshape(4, 4)
    first = generate_shares(secret, 3, 5, seed=8)
    repeat = generate_shares(secret, 3, 5, seed=8)
    different = generate_shares(secret, 3, 5, seed=9)
    assert all(np.array_equal(a, b) for a, b in zip(first, repeat))
    assert any(not np.array_equal(a, b) for a, b in zip(first, different))


def test_share_shape_and_dtype_are_preserved():
    secret = np.zeros((8, 8), dtype=np.uint8)
    shares = generate_shares(secret, 3, 6, seed=1)
    assert all(share.shape == secret.shape and share.dtype == np.uint8 for share in shares)


@pytest.mark.parametrize("k,n", [(0, 2), (3, 2), (1, 0), (2, 256)])
def test_invalid_thresholds_are_rejected(k, n):
    with pytest.raises(ValueError):
        generate_shares(np.zeros((2, 2), dtype=np.uint8), k, n)


def test_invalid_or_incompatible_shares_are_rejected():
    secret = np.zeros((4, 4), dtype=np.uint8)
    shares = generate_shares(secret, 2, 3, seed=2)
    with pytest.raises(ValueError):
        reconstruct_from_shares([shares[0], np.zeros((4, 5), dtype=np.uint8)], 2, 3)
    with pytest.raises(ValueError):
        reconstruct_from_shares([shares[0].astype(np.uint16), shares[1]], 2, 3)


def test_unauthorized_single_share_has_no_direct_reconstruction_and_uniform_marginal():
    """Empirically check the information-theoretic marginal for a 2-of-3 scheme."""
    secret_a = np.zeros((1, 1), dtype=np.uint8)
    secret_b = np.full((1, 1), 255, dtype=np.uint8)
    samples_a = [int(generate_shares(secret_a, 2, 3, seed=i)[0][0, 0]) for i in range(256)]
    samples_b = [int(generate_shares(secret_b, 2, 3, seed=i)[0][0, 0]) for i in range(256)]
    counts_a = np.bincount(samples_a, minlength=256)
    counts_b = np.bincount(samples_b, minlength=256)
    assert np.max(np.abs(counts_a - counts_b)) < 20
