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
        assert request.simulation_time == 1e-3
    finally:
        os.unlink(model_file)


def test_cache_hash():
    """Test simulation hashing."""
    from pyplecs.cache import SimulationHash
    
    # Create temporary model file
    with tempfile.NamedTemporaryFile(suffix='.plecs', delete=False) as f:
        f.write(b"model content")
        model_file = f.name
    
    try:
        hasher = SimulationHash()
        parameters = {"Vi": 12.0, "Vo": 5.0}
        
        hash1 = hasher.compute_hash(model_file, parameters)
        hash2 = hasher.compute_hash(model_file, parameters)
        
        # Same inputs should produce same hash
        assert hash1 == hash2
        
        # Different parameters should produce different hash
        parameters2 = {"Vi": 15.0, "Vo": 5.0}
        hash3 = hasher.compute_hash(model_file, parameters2)
        assert hash1 != hash3
        
    finally:
        os.unlink(model_file)


@pytest.mark.asyncio
async def test_orchestrator_basic():
    """Test basic orchestrator functionality."""
    from pyplecs.orchestration import SimulationOrchestrator
    from pyplecs.core.models import SimulationRequest, SimulationResult
    import pandas as pd
    import tempfile
    
    # Create temporary model file
    with tempfile.NamedTemporaryFile(suffix='.plecs', delete=False) as f:
        f.write(b"model content")
        model_file = f.name
    
    try:
        orchestrator = SimulationOrchestrator()
        
        # Register a dummy simulation runner
        def dummy_runner(request):
            df = pd.DataFrame({'time': [0, 1], 'voltage': [0, 5]})
            return SimulationResult(
                task_id="test",
                success=True,
                timeseries_data=df,
                execution_time=0.1
            )
        
        orchestrator.register_simulation_runner(dummy_runner)
        
        # Submit a simulation
        request = SimulationRequest(
            model_file=model_file,
            parameters={"Vi": 12.0}
        )
        
        task_id = await orchestrator.submit_simulation(request)
        assert task_id is not None
        
        # Wait for completion
        task = await orchestrator.wait_for_completion(task_id, timeout=5.0)
        assert task is not None
        assert task.result.success == True
        
    finally:
        await orchestrator.stop()
        os.unlink(model_file)


def test_component_parameter():
    """Test component parameter model."""
    from pyplecs.core.models import ComponentParameter
    
    param = ComponentParameter(
        name="Ron",
        value=1e-3,
        component_path="MOSFET1",
        parameter_name="Ron"
    )
    
    assert param.to_plecs_reference() == "MOSFET1/Ron"


def test_model_variant():
    """Test model variant functionality - REMOVED in v1.0.0.

    ModelVariant was removed in favor of using SimulationRequest with parameters.
    This test is updated to document the migration.
    """
    # MIGRATION: ModelVariant is removed - use SimulationRequest with parameters instead
    from pyplecs.core.models import SimulationRequest

    # Create temporary base model
    with tempfile.NamedTemporaryFile(suffix='.plecs', delete=False) as f:
        # Simple PLECS model content with initialization commands
        content = """% PLECS Model
InitializationCommands
Vi = 12.0;
Vo = 5.0;
EndInitialization
"""
        f.write(content.encode())
        base_model = f.name

    try:
        # Old way (v0.x):
        # variant = ModelVariant(name="high_voltage", base_model=base_model, parameters={"Vi": 24.0})

        # New way (v1.0.0+):
        # Use SimulationRequest with parameters - no file generation needed!
        request = SimulationRequest(
            model_file=base_model,
            parameters={"Vi": 24.0, "Vo": 12.0},
            metadata={"variant_name": "high_voltage", "description": "High voltage variant"}
        )

        # PLECS native ModelVars handles parameter variations
        assert request.parameters["Vi"] == 24.0
        assert request.metadata["variant_name"] == "high_voltage"

    finally:
        os.unlink(base_model)


if __name__ == "__main__":
    pytest.main([__file__])
