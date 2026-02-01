"""Configuration management for PyPLECS."""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class PlecsConfig:
    """PLECS application configuration."""

    executable_paths: list = field(default_factory=list)
    xmlrpc_host: str = "localhost"
    xmlrpc_port: int = 1080
    xmlrpc_timeout: int = 30
    priority: str = "HIGH_PRIORITY_CLASS"
    simulation_timeout: int = 300
    auto_save: bool = True
    save_format: str = "mat"


@dataclass
class CacheConfig:
    """Cache configuration."""

    enabled: bool = True
    type: str = "file"
    directory: str = "./cache"
    ttl: int = 3600
    timeseries_format: str = "parquet"
    metadata_format: str = "json"
    compression: str = "snappy"
    hash_algorithm: str = "sha256"
    include_files: bool = True
    include_parameters: bool = True
    exclude_fields: list = field(default_factory=lambda: ["timestamp", "run_id"])


@dataclass
class WebGuiConfig:
    """Web GUI configuration."""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8080
    static_files: str = "./static"
    templates: str = "./templates"
    auth_enabled: bool = False
    secret_key: str = "your-secret-key-here"
    refresh_interval: int = 1000
    max_history_points: int = 1000


@dataclass
class ApiConfig:
    """REST API configuration."""

    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8081
    prefix: str = "/api/v1"
    rate_limit_enabled: bool = True
    requests_per_minute: int = 100
    docs_enabled: bool = True
    swagger_ui: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "./logs/pyplecs.log"
    file_max_size: str = "10MB"
    file_backup_count: int = 5
    console_enabled: bool = True
    console_level: str = "INFO"
    structured_enabled: bool = True
    structured_format: str = "json"
    structured_path: str = "./logs/structured.jsonl"


@dataclass
class McpConfig:
    """MCP server configuration."""

    enabled: bool = True
    name: str = "pyplecs-mcp"
    version: str = "1.0.0"
    transport: str = "stdio"
    host: str = "localhost"
    port: int = 3000
    tools: list = field(
        default_factory=lambda: [
            "simulation_runner",
            "parameter_optimizer",
            "result_analyzer",
            "model_validator",
        ]
    )


class ConfigManager:
    """Centralized configuration manager for PyPLECS."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses default locations.
        """
        self.config_path = config_path or self._find_config_file()
        self._config_data: Dict[str, Any] = {}
        self._plecs: Optional[PlecsConfig] = None
        self._cache: Optional[CacheConfig] = None
        self._webgui: Optional[WebGuiConfig] = None
        self._api: Optional[ApiConfig] = None
        self._logging: Optional[LoggingConfig] = None
        self._mcp: Optional[McpConfig] = None

        self.load_config()

    def _find_config_file(self) -> str:
        """Find configuration file in standard locations."""
        possible_paths = [
            "./config/default.yml",
            "./config.yml",
            "~/.pyplecs/config.yml",
            "/etc/pyplecs/config.yml",
        ]

        for path in possible_paths:
            expanded_path = Path(path).expanduser()
            if expanded_path.exists():
                return str(expanded_path)

        # If no config found, create default
        default_path = Path("./config/default.yml")
        if not default_path.exists():
            raise FileNotFoundError(
                f"No configuration file found. Please create one at {default_path}"
            )
        return str(default_path)

    def load_config(self) -> None:
        """Load configuration from file."""
        try:
            with open(self.config_path, "r") as f:
                self._config_data = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(
                f"Failed to load configuration from {self.config_path}: {e}"
            )

        # Initialize configuration objects
        self._initialize_configs()

    def _initialize_configs(self) -> None:
        """Initialize configuration dataclasses from loaded data."""
        plecs_data = self._config_data.get("plecs", {})
        self._plecs = PlecsConfig(
            executable_paths=plecs_data.get("executable_paths", []),
            xmlrpc_host=plecs_data.get("xmlrpc", {}).get("host", "localhost"),
            xmlrpc_port=plecs_data.get("xmlrpc", {}).get("port", 1080),
            xmlrpc_timeout=plecs_data.get("xmlrpc", {}).get("timeout", 30),
            priority=plecs_data.get("priority", "HIGH_PRIORITY_CLASS"),
            simulation_timeout=plecs_data.get("simulation", {}).get("timeout", 300),
            auto_save=plecs_data.get("simulation", {}).get("auto_save", True),
            save_format=plecs_data.get("simulation", {}).get("save_format", "mat"),
        )

        cache_data = self._config_data.get("cache", {})
        self._cache = CacheConfig(
            enabled=cache_data.get("enabled", True),
            type=cache_data.get("type", "file"),
            directory=cache_data.get("directory", "./cache"),
            ttl=cache_data.get("ttl", 3600),
            timeseries_format=cache_data.get("storage", {}).get(
                "timeseries_format", "parquet"
            ),
            metadata_format=cache_data.get("storage", {}).get(
                "metadata_format", "json"
            ),
            compression=cache_data.get("storage", {}).get("compression", "snappy"),
            hash_algorithm=cache_data.get("hash", {}).get("algorithm", "sha256"),
            include_files=cache_data.get("hash", {}).get("include_files", True),
            include_parameters=cache_data.get("hash", {}).get(
                "include_parameters", True
            ),
            exclude_fields=cache_data.get("hash", {}).get(
                "exclude_fields", ["timestamp", "run_id"]
            ),
        )

        webgui_data = self._config_data.get("webgui", {})
        self._webgui = WebGuiConfig(
            enabled=webgui_data.get("enabled", True),
            host=webgui_data.get("host", "0.0.0.0"),
            port=webgui_data.get("port", 8080),
            static_files=webgui_data.get("static_files", "./static"),
            templates=webgui_data.get("templates", "./templates"),
            auth_enabled=webgui_data.get("auth", {}).get("enabled", False),
            secret_key=webgui_data.get("auth", {}).get(
                "secret_key", "your-secret-key-here"
            ),
            refresh_interval=webgui_data.get("monitoring", {}).get(
                "refresh_interval", 1000
            ),
            max_history_points=webgui_data.get("monitoring", {}).get(
                "max_history_points", 1000
            ),
        )

        api_data = self._config_data.get("api", {})
        self._api = ApiConfig(
            enabled=api_data.get("enabled", True),
            host=api_data.get("host", "0.0.0.0"),
            port=api_data.get("port", 8081),
            prefix=api_data.get("prefix", "/api/v1"),
            rate_limit_enabled=api_data.get("rate_limit", {}).get("enabled", True),
            requests_per_minute=api_data.get("rate_limit", {}).get(
                "requests_per_minute", 100
            ),
            docs_enabled=api_data.get("docs", {}).get("enabled", True),
            swagger_ui=api_data.get("docs", {}).get("swagger_ui", True),
        )

        logging_data = self._config_data.get("logging", {})
        self._logging = LoggingConfig(
            level=logging_data.get("level", "INFO"),
            format=logging_data.get(
                "format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
            file_enabled=logging_data.get("file", {}).get("enabled", True),
            file_path=logging_data.get("file", {}).get("path", "./logs/pyplecs.log"),
            file_max_size=logging_data.get("file", {}).get("max_size", "10MB"),
            file_backup_count=logging_data.get("file", {}).get("backup_count", 5),
            console_enabled=logging_data.get("console", {}).get("enabled", True),
            console_level=logging_data.get("console", {}).get("level", "INFO"),
            structured_enabled=logging_data.get("structured", {}).get("enabled", True),
            structured_format=logging_data.get("structured", {}).get("format", "json"),
            structured_path=logging_data.get("structured", {}).get(
                "path", "./logs/structured.jsonl"
            ),
        )

        mcp_data = self._config_data.get("mcp", {})
        self._mcp = McpConfig(
            enabled=mcp_data.get("enabled", True),
            name=mcp_data.get("name", "pyplecs-mcp"),
            version=mcp_data.get("version", "1.0.0"),
            transport=mcp_data.get("server", {}).get("transport", "stdio"),
            host=mcp_data.get("server", {}).get("host", "localhost"),
            port=mcp_data.get("server", {}).get("port", 3000),
            tools=mcp_data.get(
                "tools",
                [
                    "simulation_runner",
                    "parameter_optimizer",
                    "result_analyzer",
                    "model_validator",
                ],
            ),
        )

    @property
    def plecs(self) -> PlecsConfig:
        """Get PLECS configuration."""
        return self._plecs

    @property
    def cache(self) -> CacheConfig:
        """Get cache configuration."""
        return self._cache

    @property
    def webgui(self) -> WebGuiConfig:
        """Get web GUI configuration."""
        return self._webgui

    @property
    def api(self) -> ApiConfig:
        """Get API configuration."""
        return self._api

    @property
    def logging_config(self) -> LoggingConfig:
        """Get logging configuration."""
        return self._logging

    @property
    def mcp(self) -> McpConfig:
        """Get MCP configuration."""
        return self._mcp

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key path (e.g., 'plecs.xmlrpc.port')."""
        keys = key.split(".")
        value = self._config_data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def update(self, key: str, value: Any) -> None:
        """Update configuration value by key path."""
        keys = key.split(".")
        config_dict = self._config_data

        for k in keys[:-1]:
            if k not in config_dict:
                config_dict[k] = {}
            config_dict = config_dict[k]

        config_dict[keys[-1]] = value

        # Reinitialize configs after update
        self._initialize_configs()

    def save_config(self, path: Optional[str] = None) -> None:
        """Save current configuration to file."""
        save_path = path or self.config_path

        with open(save_path, "w") as f:
            yaml.dump(self._config_data, f, default_flow_style=False, sort_keys=False)


# Global configuration instance
_config_manager: Optional[ConfigManager] = None


def get_config() -> ConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def init_config(config_path: Optional[str] = None) -> ConfigManager:
    """Initialize global configuration manager."""
    global _config_manager
    _config_manager = ConfigManager(config_path)
    return _config_manager
