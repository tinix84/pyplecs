#!/usr/bin/env python3
"""
Lightweight smoke test for PyPLECS installation validation.

This test checks that the core modules can be imported and basic functionality
works without requiring GUI automation or external PLECS installation.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path for import
sys.path.insert(0, str(Path(__file__).parent.parent))

class SmokeTestSuite(unittest.TestCase):
    """Lightweight tests to validate PyPLECS installation."""

    def test01_basic_imports(self):
        """Test that core modules can be imported."""
        try:
            import pyplecs
            import pyplecs.config
            import pyplecs.core.models
            # Test that lazy imports don't fail immediately
            from pyplecs.cache import SimulationCache
            from pyplecs.orchestration import SimulationOrchestrator
        except ImportError as e:
            self.fail(f"Failed to import core modules: {e}")

    def test02_config_loading(self):
        """Test that configuration can be loaded."""
        try:
            from pyplecs.config import get_config
            config = get_config()
            # Basic validation - config should be a dict-like object
            self.assertIsNotNone(config)
        except Exception as e:
            self.fail(f"Failed to load configuration: {e}")

    def test03_models_import(self):
        """Test that core models can be imported."""
        try:
            from pyplecs.core.models import (
                SimulationRequest, SimulationResult, SimulationStatus
            )
            
            # Test that classes are available
            self.assertTrue(callable(SimulationRequest))
            self.assertTrue(callable(SimulationResult))
            
            # Test that enum values are accessible
            self.assertEqual(SimulationStatus.COMPLETED.value, "completed")
            self.assertEqual(SimulationStatus.FAILED.value, "failed")
            
        except Exception as e:
            self.fail(f"Failed to import core models: {e}")

    def test04_webgui_import(self):
        """Test that web GUI components can be imported."""
        try:
            from pyplecs.webgui import create_web_app
            # Don't actually create the app to avoid dependency issues
            self.assertTrue(callable(create_web_app))
        except ImportError as e:
            self.fail(f"Failed to import web GUI components: {e}")

    def test05_cli_installer_import(self):
        """Test that CLI installer can be imported and has main function."""
        try:
            from pyplecs.cli.installer import main
            self.assertTrue(callable(main))
        except ImportError as e:
            self.fail(f"Failed to import CLI installer: {e}")

    def test06_package_version(self):
        """Test that package version is accessible."""
        try:
            import pyplecs
            # Basic check that version info exists
            self.assertTrue(hasattr(pyplecs, '__version__') or 
                          hasattr(pyplecs, 'VERSION') or 
                          'version' in dir(pyplecs))
        except Exception as e:
            # Version info is optional, so just warn
            print(f"Warning: Could not access version info: {e}")

if __name__ == '__main__':
    print("Running PyPLECS installation smoke tests...")
    print("=" * 60)
    
    # Run tests with verbose output
    unittest.main(verbosity=2, exit=False)
    
    print("\n" + "=" * 60)
    print("Smoke tests completed. If all tests passed, PyPLECS is properly installed.")
    print("For full functionality testing, ensure PLECS is installed and run test_basic.py")
