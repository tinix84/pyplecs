# -*- coding: utf-8 -*-

from context import pyplecs

import unittest
import time
from pywinauto.application import Application
from pathlib import Path


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
        # Run a target application
        app = Application().start("notepad.exe")
        # Select a menu item
        app.UntitledNotepad.menu_select("Help->About Notepad")
        # Click on a button
        app.AboutNotepad.OK.click()
        # Type a text string
        app.UntitledNotepad.Edit.type_keys("pywinauto Works!", 
                                          with_spaces=True)

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
            src_mdl=buck_mdl, variant_name='01', variant_vars=ModelVars)

        ModelVars["Vi"] = 25
        ModelVars["Ii_max"] = 1
        ModelVars["Vo_ref"] = 5

        buck_mdl_02 = pyplecs.generate_variant_plecs_mdl(
            src_mdl=buck_mdl, variant_name='02', variant_vars=ModelVars)

        # Initialize PLECS servers
        time.sleep(1)
        buck_mdl_01_server = pyplecs.PlecsServer(buck_mdl_01.folder,
                                               buck_mdl_01.simulation_name)

        time.sleep(1)
        buck_mdl_02_server = pyplecs.PlecsServer(buck_mdl_02.folder,
                                               buck_mdl_02.simulation_name)

        # Start PLECS application
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
    print("WARNING: This test suite contains GUI automation tests that require")
    print("external applications and may fail in headless environments.")
    print("\nThese tests should typically be run manually or in environments")
    print("with full GUI support and the required applications installed.")
    print("\nExample usage:")
    print("python -m pytest tests/test_gui_automation.py -v -s")
    
    unittest.main()
