"""Simulation caching system with hash-based storage."""

import hashlib
import json
import os
import pickle
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
# pyarrow/parquet are optional; import them lazily when parquet operations are used

from ..config import get_config


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache."""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        pass


class FileCacheBackend(CacheBackend):
    """File-based cache backend using the filesystem."""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir = self.cache_dir / "metadata"
        self.metadata_dir.mkdir(exist_ok=True)
    
    def _get_file_path(self, key: str) -> Path:
        """Get file path for cache key."""
        return self.cache_dir / f"{key}.cache"
    
    def _get_metadata_path(self, key: str) -> Path:
        """Get metadata file path for cache key."""
        return self.metadata_dir / f"{key}.meta"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from file cache."""
        file_path = self._get_file_path(key)
        metadata_path = self._get_metadata_path(key)
        
        if not file_path.exists() or not metadata_path.exists():
            return None
        
        # Check TTL
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                
            if metadata.get('ttl') and time.time() > metadata['expires_at']:
                self.delete(key)
                return None
        except (json.JSONDecodeError, KeyError):
            return None
        
        # Load cached data
        try:
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in file cache."""
        file_path = self._get_file_path(key)
        metadata_path = self._get_metadata_path(key)
        
        # Save data
        with open(file_path, 'wb') as f:
            pickle.dump(value, f)
        
        # Save metadata
        metadata = {
            'created_at': time.time(),
            'ttl': ttl,
            'expires_at': time.time() + ttl if ttl else None
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)
    
    def delete(self, key: str) -> bool:
        """Delete key from file cache."""
        file_path = self._get_file_path(key)
        metadata_path = self._get_metadata_path(key)
        
        deleted = False
        if file_path.exists():
            file_path.unlink()
            deleted = True
        
        if metadata_path.exists():
            metadata_path.unlink()
            deleted = True
        
        return deleted
    
    def exists(self, key: str) -> bool:
        """Check if key exists in file cache."""
        return self._get_file_path(key).exists()
    
    def clear(self) -> None:
        """Clear all cache entries."""
        for file_path in self.cache_dir.glob("*.cache"):
            file_path.unlink()
        for file_path in self.metadata_dir.glob("*.meta"):
            file_path.unlink()


class SimulationHash:
    """Generate hash for simulation parameters and models."""
    
    def __init__(self, algorithm: str = "sha256"):
        self.algorithm = algorithm
        self.config = get_config()
    
    def compute_hash(self, 
                    model_file: str,
                    parameters: Dict[str, Any],
                    include_file_content: bool = True) -> str:
        """Compute hash for simulation configuration.
        
        Args:
            model_file: Path to PLECS model file
            parameters: Simulation parameters
            include_file_content: Whether to include file content in hash
            
        Returns:
            Hexadecimal hash string
        """
        hasher = hashlib.new(self.algorithm)
        
        # Hash model file path
        hasher.update(str(model_file).encode())
        
        # Hash file content if requested
        if include_file_content and os.path.exists(model_file):
            with open(model_file, 'rb') as f:
                hasher.update(f.read())
        
        # Hash parameters (excluding configured fields)
        filtered_params = self._filter_parameters(parameters)
        param_str = json.dumps(filtered_params, sort_keys=True)
        hasher.update(param_str.encode())
        
        return hasher.hexdigest()
    
    def _filter_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Filter out parameters that should not affect the hash."""
        exclude_fields = self.config.cache.exclude_fields
        return {k: v for k, v in parameters.items() if k not in exclude_fields}


class SimulationResultStore:
    """Store and retrieve simulation results in optimized formats."""
    
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.config = get_config()
    
    def store_results(self, 
                     simulation_hash: str,
                     timeseries_data: pd.DataFrame,
                     metadata: Dict[str, Any]) -> None:
        """Store simulation results.
        
        Args:
            simulation_hash: Unique hash for this simulation
            timeseries_data: Time series simulation data
            metadata: Simulation metadata and parameters
        """
        # Store timeseries data
        ts_format = self.config.cache.timeseries_format.lower()
        
        if ts_format == "parquet":
            self._store_parquet(simulation_hash, timeseries_data)
        elif ts_format == "hdf5":
            self._store_hdf5(simulation_hash, timeseries_data)
        elif ts_format == "csv":
            self._store_csv(simulation_hash, timeseries_data)
        else:
            raise ValueError(f"Unsupported timeseries format: {ts_format}")
        
        # Store metadata
        metadata_format = self.config.cache.metadata_format.lower()
        if metadata_format == "json":
            self._store_json_metadata(simulation_hash, metadata)
        elif metadata_format == "yaml":
            self._store_yaml_metadata(simulation_hash, metadata)
        else:
            raise ValueError(f"Unsupported metadata format: {metadata_format}")
    
    def load_results(self, simulation_hash: str) -> Optional[Dict[str, Any]]:
        """Load simulation results.
        
        Args:
            simulation_hash: Unique hash for this simulation
            
        Returns:
            Dictionary with 'timeseries' and 'metadata' keys, or None if not found
        """
        # Load timeseries data
        ts_format = self.config.cache.timeseries_format.lower()
        
        if ts_format == "parquet":
            timeseries = self._load_parquet(simulation_hash)
        elif ts_format == "hdf5":
            timeseries = self._load_hdf5(simulation_hash)
        elif ts_format == "csv":
            timeseries = self._load_csv(simulation_hash)
        else:
            return None
        
        if timeseries is None:
            return None
        
        # Load metadata
        metadata_format = self.config.cache.metadata_format.lower()
        if metadata_format == "json":
            metadata = self._load_json_metadata(simulation_hash)
        elif metadata_format == "yaml":
            metadata = self._load_yaml_metadata(simulation_hash)
        else:
            metadata = {}
        
        return {
            'timeseries': timeseries,
            'metadata': metadata or {}
        }
    
    def _store_parquet(self, simulation_hash: str, data: pd.DataFrame) -> None:
        """Store data in Parquet format."""
        file_path = self.storage_dir / f"{simulation_hash}.parquet"
        compression = self.config.cache.compression
        try:
            import pyarrow as pa
            import pyarrow.parquet as pq
        except Exception as e:
            raise RuntimeError("pyarrow is required to store parquet files. Install pyarrow in your environment.") from e

        table = pa.Table.from_pandas(data)
        pq.write_table(table, file_path, compression=compression)
    
    def _load_parquet(self, simulation_hash: str) -> Optional[pd.DataFrame]:
        """Load data from Parquet format."""
        file_path = self.storage_dir / f"{simulation_hash}.parquet"
        if not file_path.exists():
            return None
        
        try:
            import pyarrow.parquet as pq
            table = pq.read_table(file_path)
            return table.to_pandas()
        except Exception:
            # If pyarrow is not installed or read fails, return None and let caller handle missing data
            return None
    
    def _store_hdf5(self, simulation_hash: str, data: pd.DataFrame) -> None:
        """Store data in HDF5 format."""
        file_path = self.storage_dir / f"{simulation_hash}.h5"
        data.to_hdf(file_path, key='timeseries', mode='w', complevel=9)
    
    def _load_hdf5(self, simulation_hash: str) -> Optional[pd.DataFrame]:
        """Load data from HDF5 format."""
        file_path = self.storage_dir / f"{simulation_hash}.h5"
        if not file_path.exists():
            return None
        
        try:
            return pd.read_hdf(file_path, key='timeseries')
        except Exception:
            return None
    
    def _store_csv(self, simulation_hash: str, data: pd.DataFrame) -> None:
        """Store data in CSV format."""
        file_path = self.storage_dir / f"{simulation_hash}.csv"
        data.to_csv(file_path, index=False)
    
    def _load_csv(self, simulation_hash: str) -> Optional[pd.DataFrame]:
        """Load data from CSV format."""
        file_path = self.storage_dir / f"{simulation_hash}.csv"
        if not file_path.exists():
            return None
        
        try:
            return pd.read_csv(file_path)
        except Exception:
            return None
    
    def _store_json_metadata(self, simulation_hash: str, metadata: Dict[str, Any]) -> None:
        """Store metadata in JSON format."""
        file_path = self.storage_dir / f"{simulation_hash}_metadata.json"
        with open(file_path, 'w') as f:
            json.dump(metadata, f, indent=2, default=str)
    
    def _load_json_metadata(self, simulation_hash: str) -> Optional[Dict[str, Any]]:
        """Load metadata from JSON format."""
        file_path = self.storage_dir / f"{simulation_hash}_metadata.json"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _store_yaml_metadata(self, simulation_hash: str, metadata: Dict[str, Any]) -> None:
        """Store metadata in YAML format."""
        import yaml
        file_path = self.storage_dir / f"{simulation_hash}_metadata.yml"
        with open(file_path, 'w') as f:
            yaml.dump(metadata, f, default_flow_style=False)
    
    def _load_yaml_metadata(self, simulation_hash: str) -> Optional[Dict[str, Any]]:
        """Load metadata from YAML format."""
        import yaml
        file_path = self.storage_dir / f"{simulation_hash}_metadata.yml"
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception:
            return None


class SimulationCache:
    """High-level simulation caching interface."""
    
    def __init__(self):
        self.config = get_config()
        self.hasher = SimulationHash(self.config.cache.hash_algorithm)
        
        # Initialize cache backend
        if self.config.cache.type == "file":
            self.backend = FileCacheBackend(self.config.cache.directory)
        else:
            raise ValueError(f"Unsupported cache type: {self.config.cache.type}")
        
        # Initialize result store
        self.result_store = SimulationResultStore(
            os.path.join(self.config.cache.directory, "results")
        )
    
    def get_cached_result(self, 
                         model_file: str,
                         parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get cached simulation result if available.
        
        Args:
            model_file: Path to PLECS model file
            parameters: Simulation parameters
            
        Returns:
            Cached result or None if not found
        """
        if not self.config.cache.enabled:
            return None
        
        simulation_hash = self.hasher.compute_hash(
            model_file, 
            parameters, 
            self.config.cache.include_files
        )
        
        # Check if result exists in store
        return self.result_store.load_results(simulation_hash)
    
    def cache_result(self,
                    model_file: str,
                    parameters: Dict[str, Any],
                    timeseries_data: pd.DataFrame,
                    metadata: Dict[str, Any]) -> str:
        """Cache simulation result.
        
        Args:
            model_file: Path to PLECS model file
            parameters: Simulation parameters
            timeseries_data: Time series simulation data
            metadata: Simulation metadata
            
        Returns:
            Simulation hash for this cached result
        """
        if not self.config.cache.enabled:
            return ""
        
        simulation_hash = self.hasher.compute_hash(
            model_file,
            parameters,
            self.config.cache.include_files
        )
        
        # Store in result store
        self.result_store.store_results(simulation_hash, timeseries_data, metadata)
        
        # Store hash in cache backend for quick lookup
        cache_entry = {
            'model_file': model_file,
            'parameters': parameters,
            'simulation_hash': simulation_hash,
            'cached_at': time.time()
        }
        
        self.backend.set(simulation_hash, cache_entry, self.config.cache.ttl)
        
        return simulation_hash
    
    def invalidate_cache(self, model_file: str, parameters: Dict[str, Any]) -> bool:
        """Invalidate cached result for specific model and parameters.
        
        Args:
            model_file: Path to PLECS model file  
            parameters: Simulation parameters
            
        Returns:
            True if cache entry was found and deleted
        """
        simulation_hash = self.hasher.compute_hash(
            model_file,
            parameters,
            self.config.cache.include_files
        )
        
        return self.backend.delete(simulation_hash)
    
    def clear_cache(self) -> None:
        """Clear all cached results."""
        self.backend.clear()
        
        # Also clear result store
        for file_path in self.result_store.storage_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache usage statistics."""
        cache_dir = Path(self.config.cache.directory)
        
        if not cache_dir.exists():
            return {'total_entries': 0, 'total_size_bytes': 0}
        
        total_entries = len(list(cache_dir.glob("*.cache")))
        total_size = sum(f.stat().st_size for f in cache_dir.rglob("*") if f.is_file())
        
        return {
            'total_entries': total_entries,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_directory': str(cache_dir)
        }
