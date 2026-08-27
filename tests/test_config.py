import logging
from pathlib import Path

import pytest
import yaml

import pyplecs.api as api_module
import pyplecs.cache as cache_module
import pyplecs.logging as logging_module
import pyplecs.orchestration as orchestration_module
import pyplecs.webgui.webgui as webgui_module
from pyplecs.cache import SimulationCache
from pyplecs.config import DEFAULT_CONFIG_DATA, ConfigManager
from pyplecs.logging import StructuredLogger
from pyplecs.orchestration import SimulationOrchestrator


def test_defaults_are_available_without_a_configuration_file():
    config = ConfigManager(search_paths=[])

    assert config.config_path is None
    assert config.plecs.xmlrpc_host == "localhost"
    assert config.cache.directory == "./cache"
    assert config.orchestration.retry_attempts == 3
    assert config.api.port == 8081


def test_partial_file_overrides_canonical_defaults(tmp_path):
    path = tmp_path / "override.yml"
    path.write_text(
        "cache:\n  directory: ./temporary-cache\nplecs:\n  xmlrpc:\n    port: 2000\n",
        encoding="utf-8",
    )

    config = ConfigManager(path)

    assert config.cache.directory == "./temporary-cache"
    assert config.cache.ttl == DEFAULT_CONFIG_DATA["cache"]["ttl"]
    assert config.plecs.xmlrpc_port == 2000
    assert config.plecs.xmlrpc_host == "localhost"


def test_discovery_uses_the_first_existing_search_path(tmp_path):
    discovered = tmp_path / "config" / "default.yml"
    discovered.parent.mkdir()
    discovered.write_text("api:\n  port: 9000\n", encoding="utf-8")

    config = ConfigManager(search_paths=[tmp_path / "missing.yml", discovered, tmp_path / "later.yml"])

    assert config.config_path == str(discovered)
    assert config.api.port == 9000


def test_malformed_yaml_has_actionable_file_context(tmp_path):
    path = tmp_path / "broken.yml"
    path.write_text("cache: [unterminated", encoding="utf-8")

    with pytest.raises(ValueError, match="broken.yml"):
        ConfigManager(path)


def test_invalid_value_has_actionable_field_context(tmp_path):
    path = tmp_path / "invalid.yml"
    path.write_text("cache:\n  ttl: soon\n", encoding="utf-8")

    with pytest.raises(ValueError, match="cache.ttl"):
        ConfigManager(path)


def test_update_validates_and_refreshes_resolved_sections():
    config = ConfigManager(search_paths=[])

    config.update("cache.ttl", 42)
    config.update("plecs.xmlrpc.port", 1234)

    assert config.cache.ttl == 42
    assert config.plecs.xmlrpc_port == 1234
    with pytest.raises(ValueError, match="cache.ttl"):
        config.update("cache.ttl", "later")
    assert config.cache.ttl == 42


def test_persistence_round_trip_through_configuration_interface(tmp_path):
    path = tmp_path / "saved.yml"
    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("orchestration.retry_attempts", 7)

    config.save_config(path)
    loaded = ConfigManager(path)

    assert loaded.cache.directory == str(tmp_path / "cache")
    assert loaded.orchestration.retry_attempts == 7
    assert loaded.as_dict() == config.as_dict()


def test_installer_output_uses_the_canonical_default_data(tmp_path):
    from pyplecs.cli.installer import write_default_config

    path = Path(write_default_config(tmp_path / "config" / "default.yml"))

    assert yaml.safe_load(path.read_text(encoding="utf-8")) == DEFAULT_CONFIG_DATA


def test_runtime_composition_accepts_resolved_config_without_global_access(tmp_path, monkeypatch):
    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("logging.console.enabled", False)
    config.update("logging.file.enabled", False)
    config.update("logging.structured.enabled", False)

    def unexpected_global_access():
        raise AssertionError("global configuration fallback was used")

    monkeypatch.setattr(cache_module, "get_config", unexpected_global_access)
    monkeypatch.setattr(orchestration_module, "get_config", unexpected_global_access)
    monkeypatch.setattr(logging_module, "get_config", unexpected_global_access)
    monkeypatch.setattr(api_module, "get_config", unexpected_global_access)
    monkeypatch.setattr(webgui_module, "get_config", unexpected_global_access)

    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    try:
        cache = SimulationCache(config.cache)
        orchestrator = SimulationOrchestrator(plecs_server=object(), config=config, cache=cache)
        structured_logger = StructuredLogger(config.logging_config)
        api_app = api_module.create_api_app(config)
        web_app, _ = webgui_module.create_web_app(config, cache)
    finally:
        root_logger.handlers[:] = original_handlers
        root_logger.setLevel(original_level)

    assert orchestrator.config is config
    assert structured_logger.config is config.logging_config
    assert api_app.state.config is config
    assert web_app.title == "PyPLECS Web GUI"
