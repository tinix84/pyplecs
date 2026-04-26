# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/cache.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Abstract base class for simulation caching."""

from __future__ import annotations

import hashlib
import json
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

import pandas as pd


class SimulationCacheBase(ABC):
    """Abstract simulation cache interface."""

    @abstractmethod
    def get_cached_result(
        self, model_file: str, parameters: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Get cached result for a model+parameters combination."""

    @abstractmethod
    def cache_result(
        self,
        model_file: str,
        parameters: dict[str, Any],
        timeseries_data: pd.DataFrame,
        metadata: dict[str, Any],
    ) -> str:
        """Cache a simulation result. Returns the simulation hash."""

    @abstractmethod
    def invalidate_cache(self, model_file: str, parameters: dict[str, Any]) -> bool:
        """Invalidate a specific cache entry. Returns True if found and deleted."""

    @abstractmethod
    def clear_cache(self) -> None:
        """Clear all cached results."""

    @abstractmethod
    def get_cache_stats(self) -> dict[str, Any]:
        """Return cache usage statistics."""

    @staticmethod
    def compute_hash(
        model_file: str,
        parameters: dict[str, Any],
        include_file_content: bool = True,
        algorithm: str = "sha256",
    ) -> str:
        """Compute deterministic hash for a simulation configuration."""
        hasher = hashlib.new(algorithm)
        hasher.update(str(model_file).encode())
        if include_file_content and os.path.exists(model_file):
            with open(model_file, "rb") as f:
                hasher.update(f.read())
        param_str = json.dumps(parameters, sort_keys=True, default=str)
        hasher.update(param_str.encode())
        return hasher.hexdigest()
