"""GUI automation test cases that require external application interaction.

These were restored from the project's git history. They require
external GUI tools (pywinauto) and may fail in headless CI. The file
below is placed under `tests/interactive/` and is marked to be skipped
in CI via an environment variable check.
"""

import os
import sys
import time
import socket
import pytest
import unittest
from pathlib import Path

# Ensure a minimal config exists so importing pyplecs during test
# collection doesn't raise FileNotFoundError. Create ./config/default.yml
# if it does not already exist.
repo_root = Path(__file__).resolve().parents[2]
config_path = repo_root / "config" / "default.yml"
if not config_path.exists():
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        "plecs:\n"
        "  xmlrpc:\n"
        "    host: localhost\n"
        "    port: 1080\n"
        "api:\n"
        "  docs:\n"
        "    enabled: false\n"
    )

# Skip GUI automation tests on CI
pytestmark = pytest.mark.skipif(
    os.environ.get("CI", "").lower() in ("1", "true", "yes"),
    reason="GUI automation tests are skipped in CI",
)

# Add project root to path for import
sys.path.insert(0, str(repo_root))

# Import project after ensuring a config exists
import pyplecs
try:
    from pywinauto.application import Application
except Exception:  # pragma: no cover - optional dependency
    Application = None


class GUIAutomationTestSuite(unittest.TestCase):
    """GUI automation test cases that require external application interaction.

    These tests use pywinauto to interact with GUI applications and may
    fail in headless environments or when the required applications are
    not available.
    """

    def test01_pywinauto_with_notepad(self):
        """Test pywinauto functionality with Windows Notepad.

        This test verifies that pywinauto can interact with external
        Windows applications by automating Notepad operations.
        """
        if sys.platform != 'win32' or Application is None:
            self.skipTest('pywinauto tests require Windows and pywinauto')

        app = Application().start("notepad.exe")
        # Select a menu item
        app.UntitledNotepad.menu_select("Help->About Notepad")
        # Click on a button
        app.AboutNotepad.OK.click()
        # Type a text string
        edit = app.UntitledNotepad.Edit
        edit.type_keys("pywinauto Works!", with_spaces=True)

    def test02_gui_simulation(self):
        """Test PLECS GUI automation for simulation execution.

        This test demonstrates automated interaction with the PLECS GUI
        to load models and run simulations through the graphical interface.
        """
        sim_file_path_obj = Path('data/simple_buck.plecs')
        full_sim_name = str(sim_file_path_obj.absolute())
        buck_mdl = pyplecs.GenericConverterPlecsMdl(full_sim_name)

        # Create simulation variants
        ModelVars = dict()
        ModelVars["Vi"] = 250
        ModelVars["Ii_max"] = 25
        ModelVars["Vo_ref"] = 25

        buck_mdl_01 = pyplecs.generate_variant_plecs_mdl(
            src_mdl=buck_mdl, variant_name='01', variant_vars=ModelVars
        )

        ModelVars["Vi"] = 25
        ModelVars["Ii_max"] = 1
        ModelVars["Vo_ref"] = 5

        buck_mdl_02 = pyplecs.generate_variant_plecs_mdl(
            src_mdl=buck_mdl, variant_name='02', variant_vars=ModelVars
        )

        # Initialize PLECS servers
        time.sleep(1)
        buck_mdl_01_server = pyplecs.PlecsServer(
            buck_mdl_01.folder, buck_mdl_01.simulation_name
        )

        time.sleep(1)
        buck_mdl_02_server = pyplecs.PlecsServer(
            buck_mdl_02.folder, buck_mdl_02.simulation_name
        )

        # Start PLECS application
        # Skip PLECS GUI automation if RPC server is not reachable
        try:
            s = socket.create_connection(('localhost', 1080), timeout=1)
            s.close()
        except Exception:
            self.skipTest('PLECS RPC not reachable; skipping GUI automation')

        plecs42 = pyplecs.PlecsApp()
        plecs42.open_plecs()

        # Run simulations via GUI
        buck_mdl_01_server.load()
        time.sleep(1)
        plecs42.run_simulation_by_gui(plecs_mdl=buck_mdl_01)

        buck_mdl_02_server.load()
        time.sleep(1)
        plecs42.run_simulation_by_gui(plecs_mdl=buck_mdl_02)


if __name__ == '__main__':
    print("external applications and may fail in headless environments.")
    print("\nThese tests should typically be run manually or in environments")
    print("with full GUI support and the required applications installed.")
    print("\nExample usage:")
    print("python -m pytest tests/interactive/test_gui_automation.py -v -s")

    unittest.main()
