"""Updated tests for the refactored PyPLECS."""

import pytest
import tempfile
import os
from pathlib import Path

# Test the new configuration system
def test_config_loading():
    """Test configuration loading."""
    from pyplecs.config import ConfigManager
    
    # Create a temporary config file
    config_content = """
app:
  name: "TestPyPLECS"
  version: "0.1.0"

plecs:
  xmlrpc:
    host: "localhost"
    port: 1080

cache:
  enabled: true
  directory: "./test_cache"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
        f.write(config_content)
        config_path = f.name
    
    try:
        config = ConfigManager(config_path)
        assert config.plecs.xmlrpc_host == "localhost"
        assert config.plecs.xmlrpc_port == 1080
        assert config.cache.enabled == True
        assert config.cache.directory == "./test_cache"
    finally:
        os.unlink(config_path)


def test_simulation_request():
    """Test simulation request model."""
    from pyplecs.core.models import SimulationRequest
    
    # Create a temporary PLECS file
    with tempfile.NamedTemporaryFile(suffix='.plecs', delete=False) as f:
        f.write(b"dummy plecs content")
        model_file = f.name
    
    try:
        request = SimulationRequest(
            model_file=model_file,
            parameters={"Vi": 12.0, "Vo": 5.0},
            simulation_time=1e-3
        )
        
        assert Path(request.model_file).exists()
        assert request.parameters["Vi"] == 12.0
    finally:
        os.unlink(model_file)
