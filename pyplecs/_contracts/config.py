# Vendored from tinix84/pycircuitsim@a065438297155d73469ebce83ef6ecb051aec8aa
# Source: packages/pycircuitsim-core/pycircuitsim_core/config.py
# DO NOT EDIT — re-sync via tools/SYNC_PYCIRCUITSIM_CORE.md.

"""Abstract base class for configuration management."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml


@dataclass
class CacheConfig:
    """Cache configuration (shared across tools)."""

    enabled: bool = True
    type: str = "file"
    directory: str = "./cache"
    ttl: int = 3600
    timeseries_format: str = "parquet"
    metadata_format: str = "json"
    compression: str = "snappy"
    hash_algorithm: str = "sha256"
    include_files: bool = True
    exclude_fields: list = field(default_factory=lambda: ["timestamp", "run_id"])


@dataclass
class ApiConfig:
    """REST API configuration (shared across tools)."""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8081
    prefix: str = "/api/v1"
    rate_limit_enabled: bool = True
    requests_per_minute: int = 100
    docs_enabled: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration (shared across tools)."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "./logs/app.log"
    file_max_size: str = "10MB"
    file_backup_count: int = 5
    console_enabled: bool = True
    console_level: str = "INFO"
    structured_enabled: bool = True
    structured_path: str = "./logs/structured.jsonl"


class ConfigManagerBase(ABC):
    """Abstract config manager that loads YAML and provides typed sections."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self._config_data: dict[str, Any] = {}
        self.load_config()

    @abstractmethod
    def _find_config_file(self) -> str:
        """Find config file in standard locations. Tool-specific."""

    def load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                self._config_data = yaml.safe_load(f) or {}
        except FileNotFoundError:
            self._config_data = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dot-notation key path."""
        keys = key.split(".")
        value = self._config_data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def update(self, key: str, value: Any) -> None:
        """Update config value by dot-notation key path."""
        keys = key.split(".")
        d = self._config_data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    def save_config(self, path: Optional[str] = None) -> None:
        """Save current configuration to YAML file."""
        save_path = path or self.config_path
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w") as f:
            yaml.dump(self._config_data, f, default_flow_style=False, sort_keys=False)

    @property
    def raw(self) -> dict[str, Any]:
        """Access the raw config dict."""
        return self._config_data
