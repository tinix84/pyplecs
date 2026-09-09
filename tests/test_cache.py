import logging
from pathlib import Path

import pandas as pd
import pytest

from pyplecs.cache import PlecsEnvironment, SimulationCache, SimulationHash
from pyplecs.config import CacheConfig

DATA_DIR = Path(__file__).parent.parent / "data"
ENVIRONMENT = PlecsEnvironment("4.7-test")


def _cache(tmp_path: Path, environment: PlecsEnvironment = ENVIRONMENT, **overrides) -> SimulationCache:
    config = CacheConfig(
        directory=str(tmp_path / "cache"),
        timeseries_format=overrides.pop("timeseries_format", "parquet"),
        metadata_format=overrides.pop("metadata_format", "json"),
        **overrides,
    )
    return SimulationCache(config, environment=environment)


def _result() -> pd.DataFrame:
    return pd.DataFrame({"Time": [0.0, 0.5, 1.0], "Vo": [0.0, 6.0, 12.0]})


def _record_dir(cache: SimulationCache, model_file: str, parameters: dict) -> Path:
    key = cache.cache_key(model_file, parameters)
    return Path(cache.config.directory) / "v2" / "records" / key.topology_id / key.record_id


def _buck(tmp_path: Path, name: str = "buck.plecs") -> str:
    target = tmp_path / name
    target.write_text((DATA_DIR / "simple_buck_prb.plecs").read_text(encoding="utf-8"), encoding="utf-8")
    return str(target)


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
    model = _buck(tmp_path)

    record_id = cache.cache_result(model, {"Vi": 24}, _result(), {"model": "buck"})
    cached = cache.get_cached_result(model, {"Vi": 24})

    assert record_id == cache.cache_key(model, {"Vi": 24}).record_id
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
    cache = SimulationCache(config, environment=ENVIRONMENT, clock=lambda: now[0])
    cache.cache_result("model.plecs", {}, _result(), {})
    record_dir = _record_dir(cache, "model.plecs", {})
    assert record_dir.is_dir()

    now[0] = 111.0

    assert cache.get_cached_result("model.plecs", {}) is None
    assert not record_dir.exists()
    assert cache.get_cache_stats()["total_entries"] == 0


def test_invalidation_removes_the_whole_cache_record(tmp_path):
    cache = _cache(tmp_path)
    cache.cache_result("model.plecs", {}, _result(), {})
    record_dir = _record_dir(cache, "model.plecs", {})

    assert cache.invalidate_cache("model.plecs", {}) is True
    assert not record_dir.exists()
    assert cache.get_cached_result("model.plecs", {}) is None
    assert cache.invalidate_cache("model.plecs", {}) is False


def test_clear_removes_every_cache_record_and_the_legacy_layout(tmp_path):
    cache = _cache(tmp_path)
    cache.cache_result("one.plecs", {}, _result(), {})
    cache.cache_result("two.plecs", {}, _result(), {})
    legacy = Path(cache.config.directory) / "records" / "deadbeef"
    legacy.mkdir(parents=True)

    cache.clear_cache()

    assert cache.get_cache_stats()["total_entries"] == 0
    assert list((Path(cache.config.directory) / "v2" / "records").iterdir()) == []
    assert not legacy.exists()


def test_statistics_describe_live_cache_records_only(tmp_path):
    now = [100.0]
    config = CacheConfig(directory=str(tmp_path / "cache"), ttl=10)
    cache = SimulationCache(config, environment=ENVIRONMENT, clock=lambda: now[0])
    cache.cache_result("live.plecs", {}, _result(), {})
    now[0] = 105.0
    cache.cache_result("newer.plecs", {}, _result(), {})

    stats = cache.get_cache_stats()
    assert stats["total_entries"] == 2
    assert stats["total_size_bytes"] > 0
    assert stats["environment"] == {"plecs_version": "4.7-test", "source": "explicit"}

    now[0] = 111.0
    stats = cache.get_cache_stats()
    assert stats["total_entries"] == 1
    assert stats["total_size_bytes"] > 0


def test_incomplete_record_is_not_read_or_counted(tmp_path):
    cache = _cache(tmp_path)
    cache.cache_result("model.plecs", {}, _result(), {})
    record_dir = _record_dir(cache, "model.plecs", {})
    (record_dir / "timeseries.parquet").unlink()

    assert cache.get_cached_result("model.plecs", {}) is None
    assert not record_dir.exists()
    assert cache.get_cache_stats()["total_entries"] == 0


def test_cosmetic_edit_of_the_model_still_hits(tmp_path):
    cache = _cache(tmp_path)
    model = _buck(tmp_path)
    cache.cache_result(model, {"Vi": 24}, _result(), {"run": 1})

    text = Path(model).read_text(encoding="utf-8")
    moved = text.replace("Position      [85, 95]", "Position      [185, 195]").replace(
        "Location      [915, 288; 1725, 613]", "Location      [0, 0; 800, 600]"
    )
    assert moved != text
    Path(model).write_text(moved, encoding="utf-8")

    cached = cache.get_cached_result(model, {"Vi": 24})
    assert cached is not None and cached["metadata"] == {"run": 1}


def test_topology_document_is_stored_once_and_shared_by_parameter_points(tmp_path):
    cache = _cache(tmp_path)
    model = _buck(tmp_path)
    cache.cache_result(model, {"Vi": 24}, _result(), {})
    cache.cache_result(model, {"Vi": 48}, _result(), {})

    key = cache.cache_key(model, {"Vi": 24})
    topologies = list((Path(cache.config.directory) / "v2" / "topologies").iterdir())
    assert [path.name for path in topologies] == [f"{key.topology_id}.json"]
    assert cache.get_cache_stats() == {**cache.get_cache_stats(), "total_entries": 2, "total_topologies": 1}
    assert cache.topology_document(model).topology_id == key.topology_id


def test_explain_miss_names_the_dimension_that_differs(tmp_path):
    cache = _cache(tmp_path)
    model = _buck(tmp_path)

    assert cache.explain_miss(model, {"Vi": 24})["differences"] == ["topology"]
    cache.cache_result(model, {"Vi": 24}, _result(), {})

    assert cache.explain_miss(model, {"Vi": 24}) == {
        **cache.explain_miss(model, {"Vi": 24}),
        "hit": True,
        "differences": [],
        "candidates": 1,
    }
    assert cache.explain_miss(model, {"Vi": 48})["differences"] == ["params"]

    text = Path(model).read_text(encoding="utf-8")
    Path(model).write_text(text.replace('RelTol        "1e-3"', 'RelTol        "1e-6"'), encoding="utf-8")
    assert cache.explain_miss(model, {"Vi": 24})["differences"] == ["solver"]

    other = _cache(tmp_path, environment=PlecsEnvironment("4.9-test"))
    Path(model).write_text(text, encoding="utf-8")
    assert other.explain_miss(model, {"Vi": 24})["differences"] == ["environment"]
    assert other.get_cached_result(model, {"Vi": 24}) is None


def test_unknown_environment_disables_caching_with_one_warning(tmp_path, caplog):
    cache = _cache(tmp_path, environment=PlecsEnvironment(None, "unknown"))
    model = _buck(tmp_path)

    with caplog.at_level(logging.WARNING, logger="pyplecs.cache"):
        assert cache.cache_result(model, {}, _result(), {}) == ""
        assert cache.get_cached_result(model, {}) is None
        assert cache.invalidate_cache(model, {}) is False
        assert cache.explain_miss(model, {})["differences"] == ["environment"]

    assert sum("caching is disabled" in record.message for record in caplog.records) == 1
    assert cache.get_cache_stats()["total_entries"] == 0
