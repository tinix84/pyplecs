# -*- coding: utf-8 -*-
"""
DEPRECATED: This file is being reorganized into separate test files.

New test file organization:
- test_automated.py: Tests that run without user interaction
- test_interactive.py: Tests that require manual user input
- test_gui_automation.py: Tests that require GUI automation with external apps

Please use the appropriate test file for your testing needs:

For automated CI/CD testing:
    python -m pytest tests/test_automated.py -v

For interactive testing:
    python -m pytest tests/test_interactive.py -v -s

For GUI automation testing:
    python -m pytest tests/test_gui_automation.py -v -s

For backward compatibility, this file redirects to test_automated.py
"""

from .test_automated import AutomatedTestSuite

# Re-export the automated test suite for backward compatibility
BasicTestSuite = AutomatedTestSuite

if __name__ == '__main__':
    import unittest
    print("NOTICE: test_basic.py is deprecated.")
    print("Please use the new organized test files:")
    print("- tests/test_automated.py")
    print("- tests/test_interactive.py") 
    print("- tests/test_gui_automation.py")
    print("\nRunning automated tests for backward compatibility...")
    unittest.main()
