from pathlib import Path

import pandas as pd
import pytest

from pyplecs.cache import SimulationCache, SimulationHash
from pyplecs.config import CacheConfig


def _cache(tmp_path: Path, **overrides) -> SimulationCache:
    config = CacheConfig(
        directory=str(tmp_path / "cache"),
        timeseries_format=overrides.pop("timeseries_format", "parquet"),
        metadata_format=overrides.pop("metadata_format", "json"),
        **overrides,
    )
    return SimulationCache(config)


def _result() -> pd.DataFrame:
    return pd.DataFrame({"Time": [0.0, 0.5, 1.0], "Vo": [0.0, 6.0, 12.0]})


def test_hash_preserves_public_algorithm_argument(tmp_path):
    model = tmp_path / "model.plecs"
    model.write_text("model", encoding="utf-8")

    assert len(SimulationHash("md5").compute_hash(str(model), {})) == 32


@pytest.mark.parametrize("timeseries_format", ["parquet", "csv"])
@pytest.mark.parametrize("metadata_format", ["json", "yaml"])
def test_cache_record_round_trip_in_supported_core_formats(tmp_path, timeseries_format, metadata_format):
    cache = _cache(
        tmp_path,
        timeseries_format=timeseries_format,
        metadata_format=metadata_format,
    )

    simulation_hash = cache.cache_result("model.plecs", {"Vi": 24}, _result(), {"model": "buck"})
    cached = cache.get_cached_result("model.plecs", {"Vi": 24})

    assert simulation_hash
    pd.testing.assert_frame_equal(cached["timeseries"], _result())
    assert cached["metadata"] == {"model": "buck"}


def test_hdf5_cache_record_round_trip_when_cache_extra_is_installed(tmp_path):
    pytest.importorskip("h5py")
    cache = _cache(tmp_path, timeseries_format="hdf5")

    cache.cache_result("model.plecs", {}, _result(), {"format": "hdf5"})
    cached = cache.get_cached_result("model.plecs", {})

    pd.testing.assert_frame_equal(cached["timeseries"], _result())
    assert cached["metadata"] == {"format": "hdf5"}


def test_expiration_removes_the_whole_cache_record(tmp_path):
    now = [100.0]
    config = CacheConfig(directory=str(tmp_path / "cache"), ttl=10)
    cache = SimulationCache(config, clock=lambda: now[0])
    simulation_hash = cache.cache_result("model.plecs", {}, _result(), {})
    record_dir = Path(config.directory) / "records" / simulation_hash

    now[0] = 111.0

    assert cache.get_cached_result("model.plecs", {}) is None
    assert not record_dir.exists()
    assert cache.get_cache_stats()["total_entries"] == 0


def test_invalidation_removes_the_whole_cache_record(tmp_path):
    cache = _cache(tmp_path)
    simulation_hash = cache.cache_result("model.plecs", {}, _result(), {})
    record_dir = Path(cache.config.directory) / "records" / simulation_hash

    assert cache.invalidate_cache("model.plecs", {}) is True
    assert not record_dir.exists()
    assert cache.get_cached_result("model.plecs", {}) is None
    assert cache.invalidate_cache("model.plecs", {}) is False


def test_clear_removes_every_cache_record(tmp_path):
    cache = _cache(tmp_path)
    cache.cache_result("one.plecs", {}, _result(), {})
    cache.cache_result("two.plecs", {}, _result(), {})

    cache.clear_cache()

    assert cache.get_cache_stats()["total_entries"] == 0
    assert list((Path(cache.config.directory) / "records").iterdir()) == []


def test_statistics_describe_live_cache_records_only(tmp_path):
    now = [100.0]
    config = CacheConfig(directory=str(tmp_path / "cache"), ttl=10)
    cache = SimulationCache(config, clock=lambda: now[0])
    cache.cache_result("live.plecs", {}, _result(), {})
    now[0] = 105.0
    cache.cache_result("newer.plecs", {}, _result(), {})

    stats = cache.get_cache_stats()
    assert stats["total_entries"] == 2
    assert stats["total_size_bytes"] > 0

    now[0] = 111.0
    stats = cache.get_cache_stats()
    assert stats["total_entries"] == 1
    assert stats["total_size_bytes"] > 0


def test_incomplete_record_is_not_read_or_counted(tmp_path):
    cache = _cache(tmp_path)
    simulation_hash = cache.cache_result("model.plecs", {}, _result(), {})
    record_dir = Path(cache.config.directory) / "records" / simulation_hash
    (record_dir / "timeseries.parquet").unlink()

    assert cache.get_cached_result("model.plecs", {}) is None
    assert not record_dir.exists()
    assert cache.get_cache_stats()["total_entries"] == 0
