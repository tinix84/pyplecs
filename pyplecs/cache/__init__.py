"""Simulation caching with whole-record lifecycle semantics."""

import hashlib
import io
import json
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


class SimulationHash:
    """Generate hash for simulation parameters and models."""

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
        """Compute the existing model-and-parameter cache identity."""
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
    """Own Cache Record persistence, expiration, invalidation, and statistics."""

    _MANIFEST_FILENAME = "record.json"

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        *,
        clock: Callable[[], float] = time.time,
    ):
        self.config = config or get_config().cache
        if self.config.type != "file":
            raise ValueError(f"Unsupported cache type: {self.config.type}")

        self.hasher = SimulationHash(
            self.config.hash_algorithm,
            config=self.config,
        )
        self._clock = clock
        self._cache_dir = Path(self.config.directory)
        self._records_dir = self._cache_dir / "records"
        self._records_dir.mkdir(parents=True, exist_ok=True)
        self._result_store = SimulationResultStore(self.config)

    def get_cached_result(
        self, model_file: str, parameters: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not self.config.enabled:
            return None

        simulation_hash = self._compute_hash(model_file, parameters)
        record_dir = self._record_dir(simulation_hash)
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

        simulation_hash = self._compute_hash(model_file, parameters)
        record_dir = self._record_dir(simulation_hash)
        temporary_dir = self._records_dir / f".{simulation_hash}.{uuid.uuid4().hex}.tmp"
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
                "simulation_hash": simulation_hash,
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

            self._delete_record(record_dir)
            temporary_dir.replace(record_dir)
        finally:
            if temporary_dir.exists():
                shutil.rmtree(temporary_dir)

        return simulation_hash

    def invalidate_cache(self, model_file: str, parameters: Dict[str, Any]) -> bool:
        return self._delete_record(self._record_dir(self._compute_hash(model_file, parameters)))

    def clear_cache(self) -> None:
        if self._records_dir.exists():
            shutil.rmtree(self._records_dir)
        self._records_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_stats(self) -> Dict[str, Any]:
        live_record_dirs = []
        for record_dir in self._records_dir.iterdir():
            if not record_dir.is_dir() or record_dir.name.startswith("."):
                continue
            if self._read_live_manifest(record_dir) is not None:
                live_record_dirs.append(record_dir)

        total_size = sum(
            path.stat().st_size
            for record_dir in live_record_dirs
            for path in record_dir.rglob("*")
            if path.is_file()
        )
        return {
            "total_entries": len(live_record_dirs),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_directory": str(self._cache_dir),
        }

    def _compute_hash(self, model_file: str, parameters: Dict[str, Any]) -> str:
        return self.hasher.compute_hash(
            model_file, parameters, self.config.include_files
        )

    def _record_dir(self, simulation_hash: str) -> Path:
        return self._records_dir / simulation_hash

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
