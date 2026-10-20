from itertools import combinations

import numpy as np
import pytest

from src.pipeline import (
    ResearchMetadata,
    ResearchPipelineConfig,
    ResearchShareBundle,
    encrypt_and_share,
    reconstruct_and_decrypt,
    supported_research_configurations,
)
from src.quantum_encryption import QuantumInspiredConfig

TEST_SECRET_KEY = bytes(range(32))


def make_config(size, k, n, **kwargs):
    values = dict(
        image_shape=(size, size), x0=0.37, r=3.91, transient=17,
        chaotic_seed=9, arnold_iterations=3,
        quantum=QuantumInspiredConfig(cnot_control=2, cnot_target=6, x_bit=3),
        threshold_k=k, threshold_n=n, sharing_seed=21,
    )
    values.update(kwargs)
    return ResearchPipelineConfig(**values)


@pytest.mark.parametrize("k,n", [(2, 2), (2, 3), (3, 5), (3, 6)])
def test_complete_api_round_trip_all_supported_thresholds(k, n):
    image = np.random.default_rng(k * 100 + n).integers(0, 256, (8, 8), dtype=np.uint8)
    config = make_config(8, k, n)
    bundle = encrypt_and_share(image, config, TEST_SECRET_KEY)
    for indices in combinations(range(n), k):
        selected = [bundle.shares[index] for index in indices]
        recovered = reconstruct_and_decrypt(selected, config, TEST_SECRET_KEY, bundle.metadata)
        assert np.array_equal(recovered, image)


def test_bundle_shortcut_and_serializable_metadata():
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    config = make_config(8, 2, 3)
    bundle = encrypt_and_share(image, config, TEST_SECRET_KEY)
    assert np.array_equal(reconstruct_and_decrypt(bundle, config, TEST_SECRET_KEY), image)
    restored = ResearchMetadata.from_dict(bundle.metadata.to_dict())
    assert restored.config == bundle.metadata.config
    assert "phase" not in restored.to_dict()
    assert "key" not in bundle.metadata.config


def test_deterministic_config_reproduces_cipher_shares_and_metadata():
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    config = make_config(8, 3, 5)
    nonce = bytes(range(16))
    first = encrypt_and_share(image, config, TEST_SECRET_KEY, nonce=nonce)
    second = encrypt_and_share(image, config, TEST_SECRET_KEY, nonce=nonce)
    assert all(np.array_equal(a, b) for a, b in zip(first.shares, second.shares))
    assert first.metadata.to_dict() == second.metadata.to_dict()


def test_sharing_seed_is_not_serialized_or_used_as_a_secret():
    image = np.arange(64, dtype=np.uint8).reshape(8, 8)
    first = encrypt_and_share(image, make_config(8, 2, 3, sharing_seed=1), TEST_SECRET_KEY, nonce=b"S" * 16)
    second = encrypt_and_share(image, make_config(8, 2, 3, sharing_seed=2), TEST_SECRET_KEY, nonce=b"S" * 16)
    assert all(np.array_equal(a, b) for a, b in zip(first.shares, second.shares))
    assert "sharing_seed" not in first.metadata.config


def test_ready_made_configurations_have_identical_encryption_parameters():
    configs = supported_research_configurations(size=8, x0=0.37, r=3.91, transient=17, chaotic_seed=9, sharing_seed=21)
    assert {name: (cfg.threshold_k, cfg.threshold_n) for name, cfg in configs.items()} == {
        "A_2_of_2": (2, 2), "B_2_of_3": (2, 3), "C_3_of_5": (3, 5), "D_3_of_6": (3, 6)
    }
    encryption_dicts = [
        {key: value for key, value in cfg.to_dict().items() if key not in {"threshold", "sharing_seed"}}
        for cfg in configs.values()
    ]
    assert all(item == encryption_dicts[0] for item in encryption_dicts)


def test_invalid_inputs_are_rejected():
    image = np.zeros((8, 8), dtype=np.uint8)
    config = make_config(8, 2, 3)
    with pytest.raises(ValueError):
        ResearchPipelineConfig(image_shape=(8, 8), threshold_k=4, threshold_n=3)
    with pytest.raises(ValueError):
        encrypt_and_share(np.zeros((8, 7), dtype=np.uint8), config, TEST_SECRET_KEY)
    bundle = encrypt_and_share(image, config, TEST_SECRET_KEY)
    with pytest.raises(ValueError, match="at least"):
        reconstruct_and_decrypt(bundle.shares[:1], config, TEST_SECRET_KEY, bundle.metadata)
    with pytest.raises(ValueError, match="metadata"):
        reconstruct_and_decrypt(bundle.shares[:2], make_config(8, 2, 3, x0=0.38), TEST_SECRET_KEY, bundle.metadata)
    with pytest.raises(ValueError, match="nonce"):
        reconstruct_and_decrypt(bundle.shares[:2], config, TEST_SECRET_KEY,
                                ResearchMetadata(config=bundle.metadata.config, nonce=None))


def test_128x128_smoke_test():
    image = np.random.default_rng(128).integers(0, 256, (128, 128), dtype=np.uint8)
    config = make_config(128, 3, 5)
    bundle = encrypt_and_share(image, config, TEST_SECRET_KEY)
    assert np.array_equal(reconstruct_and_decrypt(bundle.shares[:3], config, TEST_SECRET_KEY, bundle.metadata), image)
