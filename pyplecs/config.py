"""Configuration discovery, decoding, validation, and persistence."""

import copy
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import yaml

from pyplecs.contracts import ConfigManagerBase

DEFAULT_CONFIG_DATA: Dict[str, Any] = {
    "app": {"name": "PyPLECS", "version": "0.1.0", "debug": False},
    "plecs": {
        "executable_paths": [],
        "xmlrpc": {"host": "localhost", "port": 1080, "timeout": 30},
        "priority": "HIGH_PRIORITY_CLASS",
        "auto_launch": True,
        "auto_launch_wait": 30,
        "simulation": {"timeout": 300, "auto_save": True, "save_format": "mat"},
    },
    "orchestration": {
        "max_concurrent_simulations": 4,
        "queue_size": 100,
        "retry_attempts": 3,
        "retry_delay": 5,
    },
    "cache": {
        "enabled": True,
        "type": "file",
        "directory": "./cache",
        "ttl": 3600,
        "storage": {
            "timeseries_format": "parquet",
            "metadata_format": "json",
            "compression": "snappy",
        },
        "hash": {
            "algorithm": "sha256",
            "include_files": True,
            "include_parameters": True,
            "exclude_fields": ["timestamp", "run_id"],
        },
    },
    "webgui": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8080,
        "static_files": "./static",
        "templates": "./templates",
        "auth": {"enabled": False, "secret_key": "your-secret-key-here"},
        "monitoring": {"refresh_interval": 1000, "max_history_points": 1000},
    },
    "api": {
        "enabled": True,
        "host": "0.0.0.0",
        "port": 8081,
        "prefix": "/api/v1",
        "rate_limit": {"enabled": True, "requests_per_minute": 100},
        "docs": {"enabled": True, "swagger_ui": True},
    },
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": {
            "enabled": True,
            "path": "./logs/pyplecs.log",
            "max_size": "10MB",
            "backup_count": 5,
            "rotation": "time",
        },
        "console": {"enabled": True, "level": "INFO"},
        "structured": {
            "enabled": True,
            "format": "json",
            "path": "./logs/structured.jsonl",
        },
    },
    "mcp": {
        "enabled": True,
        "name": "pyplecs-mcp",
        "version": "1.0.0",
        "server": {"transport": "stdio", "host": "localhost", "port": 3000},
        "tools": [
            "simulation_runner",
            "parameter_optimizer",
            "result_analyzer",
            "model_validator",
        ],
    },
    "database": {
        "enabled": False,
        "type": "sqlite",
        "url": "sqlite:///./pyplecs.db",
        "pool_size": 5,
        "max_overflow": 10,
        "echo": False,
    },
    "model_defaults": {
        "Vi": 0.0,
        "Vo": 0.0,
        "mosfet": {"Ron": 1e-6},
        "inductor": {"L": 1e-6, "R": 1e-3},
        "capacitor": {"C": 1e-6, "ESR": 1e-3},
        "buck_lossless": {"ron": 0.0001, "Vf_d": 0.05, "Ron_d": 0.0001},
    },
    "paths": {
        "models": "./models",
        "results": "./results",
        "cache": "./cache",
        "logs": "./logs",
        "temp": "./temp",
        "static": "./static",
        "templates": "./templates",
    },
    "development": {"auto_reload": True, "debug_mode": True, "profiling": False},
    "production": {"workers": 4, "worker_connections": 1000, "keepalive": 2},
}


@dataclass
class PlecsConfig:
    """Resolved PLECS application configuration."""

    executable_paths: list[str] = field(
        default_factory=lambda: list(DEFAULT_CONFIG_DATA["plecs"]["executable_paths"])
    )
    xmlrpc_host: str = DEFAULT_CONFIG_DATA["plecs"]["xmlrpc"]["host"]
    xmlrpc_port: int = DEFAULT_CONFIG_DATA["plecs"]["xmlrpc"]["port"]
    xmlrpc_timeout: int = DEFAULT_CONFIG_DATA["plecs"]["xmlrpc"]["timeout"]
    priority: str = DEFAULT_CONFIG_DATA["plecs"]["priority"]
    auto_launch: bool = DEFAULT_CONFIG_DATA["plecs"]["auto_launch"]
    auto_launch_wait: int = DEFAULT_CONFIG_DATA["plecs"]["auto_launch_wait"]
    simulation_timeout: int = DEFAULT_CONFIG_DATA["plecs"]["simulation"]["timeout"]
    auto_save: bool = DEFAULT_CONFIG_DATA["plecs"]["simulation"]["auto_save"]
    save_format: str = DEFAULT_CONFIG_DATA["plecs"]["simulation"]["save_format"]


@dataclass
class OrchestrationConfig:
    """Resolved Simulation Task orchestration configuration."""

    max_concurrent_simulations: int = DEFAULT_CONFIG_DATA["orchestration"][
        "max_concurrent_simulations"
    ]
    queue_size: int = DEFAULT_CONFIG_DATA["orchestration"]["queue_size"]
    retry_attempts: int = DEFAULT_CONFIG_DATA["orchestration"]["retry_attempts"]
    retry_delay: int = DEFAULT_CONFIG_DATA["orchestration"]["retry_delay"]


@dataclass
class CacheConfig:
    """Resolved cache configuration."""

    enabled: bool = DEFAULT_CONFIG_DATA["cache"]["enabled"]
    type: str = DEFAULT_CONFIG_DATA["cache"]["type"]
    directory: str = DEFAULT_CONFIG_DATA["cache"]["directory"]
    ttl: int = DEFAULT_CONFIG_DATA["cache"]["ttl"]
    timeseries_format: str = DEFAULT_CONFIG_DATA["cache"]["storage"][
        "timeseries_format"
    ]
    metadata_format: str = DEFAULT_CONFIG_DATA["cache"]["storage"]["metadata_format"]
    compression: str = DEFAULT_CONFIG_DATA["cache"]["storage"]["compression"]
    hash_algorithm: str = DEFAULT_CONFIG_DATA["cache"]["hash"]["algorithm"]
    include_files: bool = DEFAULT_CONFIG_DATA["cache"]["hash"]["include_files"]
    include_parameters: bool = DEFAULT_CONFIG_DATA["cache"]["hash"][
        "include_parameters"
    ]
    exclude_fields: list[str] = field(
        default_factory=lambda: list(
            DEFAULT_CONFIG_DATA["cache"]["hash"]["exclude_fields"]
        )
    )


@dataclass
class WebGuiConfig:
    """Resolved web GUI configuration."""

    enabled: bool = DEFAULT_CONFIG_DATA["webgui"]["enabled"]
    host: str = DEFAULT_CONFIG_DATA["webgui"]["host"]
    port: int = DEFAULT_CONFIG_DATA["webgui"]["port"]
    static_files: str = DEFAULT_CONFIG_DATA["webgui"]["static_files"]
    templates: str = DEFAULT_CONFIG_DATA["webgui"]["templates"]
    auth_enabled: bool = DEFAULT_CONFIG_DATA["webgui"]["auth"]["enabled"]
    secret_key: str = DEFAULT_CONFIG_DATA["webgui"]["auth"]["secret_key"]
    refresh_interval: int = DEFAULT_CONFIG_DATA["webgui"]["monitoring"][
        "refresh_interval"
    ]
    max_history_points: int = DEFAULT_CONFIG_DATA["webgui"]["monitoring"][
        "max_history_points"
    ]


@dataclass
class ApiConfig:
    """Resolved REST API configuration."""

    enabled: bool = DEFAULT_CONFIG_DATA["api"]["enabled"]
    host: str = DEFAULT_CONFIG_DATA["api"]["host"]
    port: int = DEFAULT_CONFIG_DATA["api"]["port"]
    prefix: str = DEFAULT_CONFIG_DATA["api"]["prefix"]
    rate_limit_enabled: bool = DEFAULT_CONFIG_DATA["api"]["rate_limit"]["enabled"]
    requests_per_minute: int = DEFAULT_CONFIG_DATA["api"]["rate_limit"][
        "requests_per_minute"
    ]
    docs_enabled: bool = DEFAULT_CONFIG_DATA["api"]["docs"]["enabled"]
    swagger_ui: bool = DEFAULT_CONFIG_DATA["api"]["docs"]["swagger_ui"]


@dataclass
class LoggingConfig:
    """Resolved logging configuration."""

    level: str = DEFAULT_CONFIG_DATA["logging"]["level"]
    format: str = DEFAULT_CONFIG_DATA["logging"]["format"]
    file_enabled: bool = DEFAULT_CONFIG_DATA["logging"]["file"]["enabled"]
    file_path: str = DEFAULT_CONFIG_DATA["logging"]["file"]["path"]
    file_max_size: str = DEFAULT_CONFIG_DATA["logging"]["file"]["max_size"]
    file_backup_count: int = DEFAULT_CONFIG_DATA["logging"]["file"]["backup_count"]
    console_enabled: bool = DEFAULT_CONFIG_DATA["logging"]["console"]["enabled"]
    console_level: str = DEFAULT_CONFIG_DATA["logging"]["console"]["level"]
    structured_enabled: bool = DEFAULT_CONFIG_DATA["logging"]["structured"]["enabled"]
    structured_format: str = DEFAULT_CONFIG_DATA["logging"]["structured"]["format"]
    structured_path: str = DEFAULT_CONFIG_DATA["logging"]["structured"]["path"]


@dataclass
class McpConfig:
    """Resolved MCP server configuration."""

    enabled: bool = DEFAULT_CONFIG_DATA["mcp"]["enabled"]
    name: str = DEFAULT_CONFIG_DATA["mcp"]["name"]
    version: str = DEFAULT_CONFIG_DATA["mcp"]["version"]
    transport: str = DEFAULT_CONFIG_DATA["mcp"]["server"]["transport"]
    host: str = DEFAULT_CONFIG_DATA["mcp"]["server"]["host"]
    port: int = DEFAULT_CONFIG_DATA["mcp"]["server"]["port"]
    tools: list[str] = field(
        default_factory=lambda: list(DEFAULT_CONFIG_DATA["mcp"]["tools"])
    )


class ConfigManager(ConfigManagerBase):
    """Own defaults, discovery, decoding, validation, update, and persistence."""

    _DISCOVERY_PATHS = (
        "./config/default.yml",
        "./config.yml",
        "~/.pyplecs/config.yml",
        "/etc/pyplecs/config.yml",
    )

    def __init__(
        self,
        config_path: Optional[str | Path] = None,
        *,
        search_paths: Optional[Iterable[str | Path]] = None,
    ):
        if config_path is not None:
            explicit_path = Path(config_path).expanduser()
            if not explicit_path.is_file():
                raise FileNotFoundError(f"Configuration file not found: {explicit_path}")
            self.config_path: Optional[str] = str(explicit_path)
        else:
            discovered = self._find_config_file(search_paths)
            self.config_path = str(discovered) if discovered is not None else None

        self._config_data: Dict[str, Any] = {}
        self.load_config()

    def _find_config_file(
        self, search_paths: Optional[Iterable[str | Path]] = None
    ) -> Optional[Path]:
        candidates = search_paths if search_paths is not None else self._DISCOVERY_PATHS
        for candidate in candidates:
            path = Path(candidate).expanduser()
            if path.is_file():
                return path
        return None

    def load_config(self) -> None:
        """Load overrides over canonical defaults and decode resolved sections."""
        overrides: Dict[str, Any] = {}
        if self.config_path is not None:
            path = Path(self.config_path)
            try:
                loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
            except (OSError, yaml.YAMLError) as error:
                raise ValueError(
                    f"Failed to parse configuration '{path}': {error}"
                ) from error
            if loaded is not None and not isinstance(loaded, dict):
                raise ValueError(
                    f"Invalid configuration '{path}': top-level value must be a mapping"
                )
            overrides = loaded or {}

        resolved = _deep_merge(copy.deepcopy(DEFAULT_CONFIG_DATA), overrides)
        decoded = self._decode(resolved)
        self._config_data = resolved
        self._apply_decoded(decoded)

    def _decode(self, data: Dict[str, Any]) -> tuple[Any, ...]:
        plecs = PlecsConfig(
            executable_paths=list(_read(data, "plecs.executable_paths", list)),
            xmlrpc_host=_read(data, "plecs.xmlrpc.host", str),
            xmlrpc_port=_read(data, "plecs.xmlrpc.port", int),
            xmlrpc_timeout=_read(data, "plecs.xmlrpc.timeout", int),
            priority=_read(data, "plecs.priority", str),
            auto_launch=_read(data, "plecs.auto_launch", bool),
            auto_launch_wait=_read(data, "plecs.auto_launch_wait", int),
            simulation_timeout=_read(data, "plecs.simulation.timeout", int),
            auto_save=_read(data, "plecs.simulation.auto_save", bool),
            save_format=_read(data, "plecs.simulation.save_format", str),
        )
        _require_string_list(plecs.executable_paths, "plecs.executable_paths")
        _require_port(plecs.xmlrpc_port, "plecs.xmlrpc.port")

        orchestration = OrchestrationConfig(
            max_concurrent_simulations=_read(
                data, "orchestration.max_concurrent_simulations", int
            ),
            queue_size=_read(data, "orchestration.queue_size", int),
            retry_attempts=_read(data, "orchestration.retry_attempts", int),
            retry_delay=_read(data, "orchestration.retry_delay", int),
        )
        for field_name in ("max_concurrent_simulations", "queue_size", "retry_attempts"):
            if getattr(orchestration, field_name) < 1:
                raise ValueError(f"Invalid configuration 'orchestration.{field_name}': must be >= 1")
        if orchestration.retry_delay < 0:
            raise ValueError("Invalid configuration 'orchestration.retry_delay': must be >= 0")

        cache = CacheConfig(
            enabled=_read(data, "cache.enabled", bool),
            type=_read(data, "cache.type", str),
            directory=_read(data, "cache.directory", str),
            ttl=_read(data, "cache.ttl", int),
            timeseries_format=_read(data, "cache.storage.timeseries_format", str),
            metadata_format=_read(data, "cache.storage.metadata_format", str),
            compression=_read(data, "cache.storage.compression", str),
            hash_algorithm=_read(data, "cache.hash.algorithm", str),
            include_files=_read(data, "cache.hash.include_files", bool),
            include_parameters=_read(data, "cache.hash.include_parameters", bool),
            exclude_fields=list(_read(data, "cache.hash.exclude_fields", list)),
        )
        _validate_cache(cache)

        webgui = WebGuiConfig(
            enabled=_read(data, "webgui.enabled", bool),
            host=_read(data, "webgui.host", str),
            port=_read(data, "webgui.port", int),
            static_files=_read(data, "webgui.static_files", str),
            templates=_read(data, "webgui.templates", str),
            auth_enabled=_read(data, "webgui.auth.enabled", bool),
            secret_key=_read(data, "webgui.auth.secret_key", str),
            refresh_interval=_read(data, "webgui.monitoring.refresh_interval", int),
            max_history_points=_read(data, "webgui.monitoring.max_history_points", int),
        )
        _require_port(webgui.port, "webgui.port")

        api = ApiConfig(
            enabled=_read(data, "api.enabled", bool),
            host=_read(data, "api.host", str),
            port=_read(data, "api.port", int),
            prefix=_read(data, "api.prefix", str),
            rate_limit_enabled=_read(data, "api.rate_limit.enabled", bool),
            requests_per_minute=_read(data, "api.rate_limit.requests_per_minute", int),
            docs_enabled=_read(data, "api.docs.enabled", bool),
            swagger_ui=_read(data, "api.docs.swagger_ui", bool),
        )
        _require_port(api.port, "api.port")

        logging_config = LoggingConfig(
            level=_read(data, "logging.level", str),
            format=_read(data, "logging.format", str),
            file_enabled=_read(data, "logging.file.enabled", bool),
            file_path=_read(data, "logging.file.path", str),
            file_max_size=_read(data, "logging.file.max_size", str),
            file_backup_count=_read(data, "logging.file.backup_count", int),
            console_enabled=_read(data, "logging.console.enabled", bool),
            console_level=_read(data, "logging.console.level", str),
            structured_enabled=_read(data, "logging.structured.enabled", bool),
            structured_format=_read(data, "logging.structured.format", str),
            structured_path=_read(data, "logging.structured.path", str),
        )
        _validate_logging(logging_config)

        mcp = McpConfig(
            enabled=_read(data, "mcp.enabled", bool),
            name=_read(data, "mcp.name", str),
            version=_read(data, "mcp.version", str),
            transport=_read(data, "mcp.server.transport", str),
            host=_read(data, "mcp.server.host", str),
            port=_read(data, "mcp.server.port", int),
            tools=list(_read(data, "mcp.tools", list)),
        )
        _require_port(mcp.port, "mcp.server.port")
        _require_string_list(mcp.tools, "mcp.tools")

        return plecs, orchestration, cache, webgui, api, logging_config, mcp

    def _apply_decoded(self, decoded: tuple[Any, ...]) -> None:
        (
            self._plecs,
            self._orchestration,
            self._cache,
            self._webgui,
            self._api,
            self._logging,
            self._mcp,
        ) = decoded

    @property
    def plecs(self) -> PlecsConfig:
        return self._plecs

    @property
    def orchestration(self) -> OrchestrationConfig:
        return self._orchestration

    @property
    def cache(self) -> CacheConfig:
        return self._cache

    @property
    def webgui(self) -> WebGuiConfig:
        return self._webgui

    @property
    def api(self) -> ApiConfig:
        return self._api

    @property
    def logging_config(self) -> LoggingConfig:
        return self._logging

    @property
    def mcp(self) -> McpConfig:
        return self._mcp

    def get(self, key: str, default: Any = None) -> Any:
        value: Any = self._config_data
        for part in key.split("."):
            if not isinstance(value, dict) or part not in value:
                return default
            value = value[part]
        return value

    def update(self, key: str, value: Any) -> None:
        candidate = copy.deepcopy(self._config_data)
        parts = key.split(".")
        if not all(parts):
            raise ValueError("Configuration key must not be empty")
        target = candidate
        for part in parts[:-1]:
            existing = target.get(part)
            if existing is None:
                existing = {}
                target[part] = existing
            if not isinstance(existing, dict):
                raise ValueError(
                    f"Cannot update configuration '{key}': '{part}' is not a mapping"
                )
            target = existing
        target[parts[-1]] = value

        decoded = self._decode(candidate)
        self._config_data = candidate
        self._apply_decoded(decoded)

    def save_config(self, path: Optional[str | Path] = None) -> None:
        destination_value = path or self.config_path
        if destination_value is None:
            raise ValueError("A destination path is required to persist default configuration")
        destination = Path(destination_value)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            yaml.safe_dump(self._config_data, default_flow_style=False, sort_keys=False),
            encoding="utf-8",
        )
        self.config_path = str(destination)

    def as_dict(self) -> Dict[str, Any]:
        """Return a defensive copy of the resolved configuration."""
        return copy.deepcopy(self._config_data)


def _deep_merge(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            base[key] = _deep_merge(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def _read(data: Dict[str, Any], path: str, expected_type: type) -> Any:
    value: Any = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ValueError(f"Missing required configuration field '{path}'")
        value = value[part]

    valid = isinstance(value, expected_type)
    if expected_type is int:
        valid = type(value) is int
    elif expected_type is bool:
        valid = type(value) is bool
    if not valid:
        raise ValueError(
            f"Invalid configuration '{path}': expected {expected_type.__name__}, "
            f"got {type(value).__name__}"
        )
    return value


def _require_string_list(value: list[Any], path: str) -> None:
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"Invalid configuration '{path}': expected non-empty strings")


def _require_port(value: int, path: str) -> None:
    if not 1 <= value <= 65535:
        raise ValueError(f"Invalid configuration '{path}': expected port 1..65535")


def _validate_cache(config: CacheConfig) -> None:
    if config.type != "file":
        raise ValueError("Invalid configuration 'cache.type': only 'file' is supported")
    if not config.directory:
        raise ValueError("Invalid configuration 'cache.directory': must not be empty")
    if config.ttl < 0:
        raise ValueError("Invalid configuration 'cache.ttl': must be >= 0")
    if config.timeseries_format not in {"parquet", "hdf5", "csv"}:
        raise ValueError(
            "Invalid configuration 'cache.storage.timeseries_format': "
            "expected parquet, hdf5, or csv"
        )
    if config.metadata_format not in {"json", "yaml"}:
        raise ValueError(
            "Invalid configuration 'cache.storage.metadata_format': expected json or yaml"
        )
    try:
        hashlib.new(config.hash_algorithm)
    except ValueError as error:
        raise ValueError(
            f"Invalid configuration 'cache.hash.algorithm': {config.hash_algorithm}"
        ) from error
    _require_string_list(config.exclude_fields, "cache.hash.exclude_fields")


def _validate_logging(config: LoggingConfig) -> None:
    for path, value in (
        ("logging.level", config.level),
        ("logging.console.level", config.console_level),
    ):
        if not isinstance(getattr(logging, value.upper(), None), int):
            raise ValueError(f"Invalid configuration '{path}': unknown level {value}")
    if config.file_backup_count < 0:
        raise ValueError("Invalid configuration 'logging.file.backup_count': must be >= 0")


_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Resolve the compatibility global configuration lazily."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def init_config(config_path: Optional[str | Path] = None) -> ConfigManager:
    """Replace the compatibility global configuration."""
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager
