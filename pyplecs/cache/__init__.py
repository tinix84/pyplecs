"""Simulation caching with whole-record lifecycle semantics and composite identity."""

import hashlib
import io
import json
import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from pyplecs.contracts import SimulationCacheBase

from ..config import CacheConfig, get_config
from .identity import CacheKey, ModelIdentity, PlecsEnvironment, identify
from .topology import TopologyDocument

logger = logging.getLogger(__name__)


class SimulationHash:
    """Legacy path-and-bytes identity, kept for callers that still address it."""

    def __init__(
        self,
        algorithm: str = "sha256",
        *,
        config: Optional[CacheConfig] = None,
    ):
        self.algorithm = algorithm
        self.config = config or get_config().cache

    def compute_hash(
        self,
        model_file: str,
        parameters: Dict[str, Any],
        include_file_content: bool = True,
    ) -> str:
        """Compute the legacy model-and-parameter cache identity."""
        hasher = hashlib.new(self.algorithm)
        hasher.update(str(model_file).encode())

        if include_file_content and os.path.exists(model_file):
            with open(model_file, "rb") as file:
                hasher.update(file.read())

        filtered_params = self._filter_parameters(parameters)
        hasher.update(json.dumps(filtered_params, sort_keys=True).encode())
        return hasher.hexdigest()

    def _filter_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        exclude_fields = self.config.exclude_fields
        return {key: value for key, value in parameters.items() if key not in exclude_fields}


class SimulationResultStore:
    """Internal storage-format adapter for one Cache Record directory."""

    _TIMESERIES_FILENAMES = {
        "parquet": "timeseries.parquet",
        "hdf5": "timeseries.h5",
        "csv": "timeseries.csv",
    }
    _METADATA_FILENAMES = {
        "json": "metadata.json",
        "yaml": "metadata.yml",
    }

    def __init__(self, config: CacheConfig):
        self.config = config

    def store_results(
        self,
        record_dir: Path,
        timeseries_data: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> tuple[str, str]:
        timeseries_format = self.config.timeseries_format.lower()
        metadata_format = self.config.metadata_format.lower()

        try:
            timeseries_filename = self._TIMESERIES_FILENAMES[timeseries_format]
        except KeyError as error:
            raise ValueError(
                f"Unsupported timeseries format: {timeseries_format}"
            ) from error
        try:
            metadata_filename = self._METADATA_FILENAMES[metadata_format]
        except KeyError as error:
            raise ValueError(f"Unsupported metadata format: {metadata_format}") from error

        timeseries_path = record_dir / timeseries_filename
        metadata_path = record_dir / metadata_filename

        if timeseries_format == "parquet":
            self._store_parquet(timeseries_path, timeseries_data)
        elif timeseries_format == "hdf5":
            self._store_hdf5(timeseries_path, timeseries_data)
        else:
            self._store_csv(timeseries_path, timeseries_data)

        if metadata_format == "json":
            metadata_path.write_text(
                json.dumps(metadata, indent=2, default=str), encoding="utf-8"
            )
        else:
            metadata_path.write_text(
                yaml.safe_dump(metadata, default_flow_style=False), encoding="utf-8"
            )

        return timeseries_filename, metadata_filename

    def load_results(
        self,
        record_dir: Path,
        timeseries_format: str,
        metadata_format: str,
    ) -> Dict[str, Any]:
        try:
            timeseries_filename = self._TIMESERIES_FILENAMES[timeseries_format]
            metadata_filename = self._METADATA_FILENAMES[metadata_format]
        except KeyError as error:
            raise ValueError(f"Cache Record declares unsupported format: {error.args[0]}") from error

        timeseries_path = record_dir / timeseries_filename
        metadata_path = record_dir / metadata_filename
        if not timeseries_path.is_file() or not metadata_path.is_file():
            raise ValueError("Cache Record is incomplete")

        if timeseries_format == "parquet":
            timeseries = self._load_parquet(timeseries_path)
        elif timeseries_format == "hdf5":
            timeseries = self._load_hdf5(timeseries_path)
        else:
            timeseries = pd.read_csv(timeseries_path)

        if metadata_format == "json":
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        else:
            metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))

        if not isinstance(metadata, dict):
            raise ValueError("Cache Record metadata must be a mapping")
        return {"timeseries": timeseries, "metadata": metadata}

    def _store_parquet(self, path: Path, data: pd.DataFrame) -> None:
        table = pa.Table.from_pandas(data)
        pq.write_table(table, path, compression=self.config.compression)

    @staticmethod
    def _load_parquet(path: Path) -> pd.DataFrame:
        return pq.read_table(path).to_pandas()

    @staticmethod
    def _store_hdf5(path: Path, data: pd.DataFrame) -> None:
        try:
            import h5py
        except ImportError as error:
            raise RuntimeError(
                "HDF5 cache storage requires the 'cache' optional dependencies"
            ) from error

        payload = data.to_json(orient="table").encode("utf-8")
        with h5py.File(path, "w") as file:
            file.create_dataset("timeseries", data=payload)

    @staticmethod
    def _load_hdf5(path: Path) -> pd.DataFrame:
        try:
            import h5py
        except ImportError as error:
            raise RuntimeError(
                "HDF5 cache storage requires the 'cache' optional dependencies"
            ) from error

        with h5py.File(path, "r") as file:
            payload = bytes(file["timeseries"][()]).decode("utf-8")
        return pd.read_json(io.StringIO(payload), orient="table")

    @staticmethod
    def _store_csv(path: Path, data: pd.DataFrame) -> None:
        data.to_csv(path, index=False)


class SimulationCache(SimulationCacheBase):
    """Own Cache Record identity, persistence, expiration, invalidation, and statistics.

    Layout (``LAYOUT_VERSION`` makes earlier generations unreachable rather than
    misread)::

        <directory>/v2/topologies/<topology_id>.json   canonical document, shared
        <directory>/v2/records/<topology_id>/<record_id>/record.json + payload
    """

    LAYOUT_VERSION = "v2"
    _MANIFEST_FILENAME = "record.json"

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        *,
        environment: Optional[PlecsEnvironment] = None,
        clock: Callable[[], float] = time.time,
    ):
        self.config = config or get_config().cache
        if self.config.type != "file":
            raise ValueError(f"Unsupported cache type: {self.config.type}")

        self._environment = environment
        self._clock = clock
        self._cache_dir = Path(self.config.directory)
        self._layout_dir = self._cache_dir / self.LAYOUT_VERSION
        self._records_dir = self._layout_dir / "records"
        self._topologies_dir = self._layout_dir / "topologies"
        self._records_dir.mkdir(parents=True, exist_ok=True)
        self._topologies_dir.mkdir(parents=True, exist_ok=True)
        self._result_store = SimulationResultStore(self.config)
        self._warned_unknown_environment = False

    # -- identity -----------------------------------------------------------

    @property
    def environment(self) -> PlecsEnvironment:
        if self._environment is None:
            self._environment = PlecsEnvironment.detect(get_config().plecs)
        return self._environment

    def identify(self, model_file: str, parameters: Dict[str, Any]) -> Optional[ModelIdentity]:
        """Compute the composite identity, or ``None`` when the environment is unknown."""
        identity = identify(
            model_file, parameters, self.environment, tuple(self.config.exclude_fields)
        )
        if identity is None and not self._warned_unknown_environment:
            self._warned_unknown_environment = True
            logger.warning(
                "PLECS environment identity is unknown (set plecs.version or "
                "plecs.executable_paths); simulation caching is disabled"
            )
        return identity

    def cache_key(self, model_file: str, parameters: Dict[str, Any]) -> Optional[CacheKey]:
        identity = self.identify(model_file, parameters)
        return identity.key if identity is not None else None

    def topology_document(self, model_file: str) -> Optional[TopologyDocument]:
        """The canonical topology document of a model, or ``None`` if it degraded to bytes."""
        identity = identify(model_file, {}, PlecsEnvironment("probe"))
        return identity.topology if identity is not None else None

    def explain_miss(self, model_file: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Say why a lookup would miss: which of the four ids has no live record."""
        identity = self.identify(model_file, parameters)
        if identity is None:
            return {"hit": False, "reason": "environment unknown", "differences": ["environment"]}
        key = identity.key
        candidates = [
            CacheKey(**{name: manifest["key"][name] for name in CacheKey.__dataclass_fields__})
            for manifest in self._live_manifests(self._records_dir / key.topology_id)
        ]
        if not candidates:
            return {"hit": False, "key": key.to_dict(), "differences": ["topology"], "candidates": 0}
        closest = min((key.differences(candidate) for candidate in candidates), key=len)
        return {
            "hit": not closest,
            "key": key.to_dict(),
            "differences": closest,
            "candidates": len(candidates),
        }

    # -- SimulationCacheBase ---------------------------------------------------

    def get_cached_result(
        self, model_file: str, parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not self.config.enabled:
            return None

        identity = self.identify(model_file, parameters)
        if identity is None:
            return None
        record_dir = self._record_dir(identity.key)
        manifest = self._read_live_manifest(record_dir)
        if manifest is None:
            return None

        try:
            return self._result_store.load_results(
                record_dir,
                manifest["timeseries_format"],
                manifest["metadata_format"],
            )
        except (OSError, ValueError, RuntimeError, json.JSONDecodeError, yaml.YAMLError):
            self._delete_record(record_dir)
            return None

    def cache_result(
        self,
        model_file: str,
        parameters: Dict[str, Any],
        timeseries_data: pd.DataFrame,
        metadata: Dict[str, Any],
    ) -> str:
        if not self.config.enabled:
            return ""

        identity = self.identify(model_file, parameters)
        if identity is None:
            return ""
        key = identity.key
        record_dir = self._record_dir(key)
        record_dir.parent.mkdir(parents=True, exist_ok=True)
        temporary_dir = self._records_dir / f".{key.record_id}.{uuid.uuid4().hex}.tmp"
        temporary_dir.mkdir()

        try:
            timeseries_filename, metadata_filename = self._result_store.store_results(
                temporary_dir, timeseries_data, metadata
            )
            created_at = self._clock()
            expires_at = (
                created_at + self.config.ttl if self.config.ttl and self.config.ttl > 0 else None
            )
            manifest = {
                "simulation_hash": key.record_id,
                **identity.to_dict(),
                "model_file": model_file,
                "parameters": parameters,
                "created_at": created_at,
                "expires_at": expires_at,
                "timeseries_format": self.config.timeseries_format.lower(),
                "timeseries_file": timeseries_filename,
                "metadata_format": self.config.metadata_format.lower(),
                "metadata_file": metadata_filename,
            }
            (temporary_dir / self._MANIFEST_FILENAME).write_text(
                json.dumps(manifest, indent=2, default=str), encoding="utf-8"
            )

            if identity.topology is not None:
                self._store_topology(identity.topology)
            self._delete_record(record_dir)
            temporary_dir.replace(record_dir)
        finally:
            if temporary_dir.exists():
                shutil.rmtree(temporary_dir)

        return key.record_id

    def invalidate_cache(self, model_file: str, parameters: Dict[str, Any]) -> bool:
        key = self.cache_key(model_file, parameters)
        if key is None:
            return False
        return self._delete_record(self._record_dir(key))

    def clear_cache(self) -> None:
        for stale in (self._layout_dir, self._cache_dir / "records"):
            if stale.exists():
                shutil.rmtree(stale)
        self._records_dir.mkdir(parents=True, exist_ok=True)
        self._topologies_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_stats(self) -> Dict[str, Any]:
        live_record_dirs = []
        for topology_dir in self._records_dir.iterdir():
            if not topology_dir.is_dir() or topology_dir.name.startswith("."):
                continue
            for record_dir in topology_dir.iterdir():
                if record_dir.is_dir() and self._read_live_manifest(record_dir) is not None:
                    live_record_dirs.append(record_dir)

        total_size = sum(
            path.stat().st_size
            for record_dir in live_record_dirs
            for path in record_dir.rglob("*")
            if path.is_file()
        )
        return {
            "total_entries": len(live_record_dirs),
            "total_topologies": len({record_dir.parent.name for record_dir in live_record_dirs}),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_directory": str(self._cache_dir),
            "environment": self.environment.to_dict(),
        }

    # -- internals -----------------------------------------------------------

    def _record_dir(self, key: CacheKey) -> Path:
        return self._records_dir / key.topology_id / key.record_id

    def _store_topology(self, topology: TopologyDocument) -> None:
        path = self._topologies_dir / f"{topology.topology_id}.json"
        if not path.exists():
            path.write_text(topology.to_json(), encoding="utf-8")

    def _live_manifests(self, topology_dir: Path) -> list[Dict[str, Any]]:
        if not topology_dir.is_dir():
            return []
        manifests = []
        for record_dir in topology_dir.iterdir():
            if record_dir.is_dir():
                manifest = self._read_live_manifest(record_dir)
                if manifest is not None:
                    manifests.append(manifest)
        return manifests

    def _read_live_manifest(self, record_dir: Path) -> Optional[Dict[str, Any]]:
        manifest_path = record_dir / self._MANIFEST_FILENAME
        if not manifest_path.is_file():
            self._delete_record(record_dir)
            return None

        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            expires_at = manifest.get("expires_at")
            if expires_at is not None and self._clock() >= expires_at:
                self._delete_record(record_dir)
                return None
            if manifest.get("simulation_hash") != record_dir.name:
                raise ValueError("Cache Record identity does not match its directory")
            return manifest
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            self._delete_record(record_dir)
            return None

    @staticmethod
    def _delete_record(record_dir: Path) -> bool:
        if not record_dir.exists():
            return False
        if record_dir.is_dir():
            shutil.rmtree(record_dir)
        else:
            record_dir.unlink()
        return True


__all__ = [
    "CacheKey",
    "ModelIdentity",
    "PlecsEnvironment",
    "SimulationCache",
    "SimulationHash",
    "SimulationResultStore",
    "TopologyDocument",
]
