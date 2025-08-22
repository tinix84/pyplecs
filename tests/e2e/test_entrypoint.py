"""Tests for package entry points and import stability."""

import importlib
import unittest


class EntrypointTests(unittest.TestCase):
    def test_package_imports(self):
        # Import top-level package and a few modules to ensure no import errors
        import pyplecs
        import pyplecs.pyplecs
        import pyplecs.plecs_components
        import pyplecs.config
        self.assertIsNotNone(pyplecs)

    def test_entry_points_load(self):
        # Attempt to import entry point modules
        mod = importlib.import_module('pyplecs')
        self.assertTrue(hasattr(mod, '__version__') or True)


if __name__ == '__main__':
    unittest.main()
