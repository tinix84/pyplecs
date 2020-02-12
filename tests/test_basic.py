# -*- coding: utf-8 -*-

from context import pyplecs

import unittest
import time
from pywinauto.application import Application
import os

from pathlib import Path

class BasicTestSuite(unittest.TestCase):
    """Basic test cases."""

    def test01_absolute_truth_and_meaning(self):
        """[summary]
        """
        assert True

    def test02_pywinauto_with_notepad(self):
        """[summary]
        """
        # Run a target application
        app = Application().start("notepad.exe")
        # Select a menu item
        app.UntitledNotepad.menu_select("Help->About Notepad")
        # Click on a button
        app.AboutNotepad.OK.click()
        # Type a text string
        app.UntitledNotepad.Edit.type_keys("pywinauto Works!", with_spaces=True)

    def test03_plecs_app_open_highpriority(self):
        """[summary]
        """
        plecs42 = pyplecs.PlecsApp()
        plecs42.kill_plecs()
        time.sleep(1)
        plecs42.open_plecs()
        time.sleep(1)
        plecs42.set_plecs_high_priority()

    def test04_pyplecs_xrpc_server(self):
        """[summary]
        """
        sim_file_path_obj = Path('../data/simple_buck.plecs')
        full_sim_name = str(sim_file_path_obj.absolute())
        plecs_mdl = pyplecs.GenericConverterPlecsMdl(full_sim_name)

        plecs42 = pyplecs.PlecsApp()
        plecs42.kill_plecs()
        plecs42.open_plecs()
        time.sleep(1)
        pyplecs.PlecsServer(plecs_mdl.folder, plecs_mdl.simulation_name)

    def test05_pyplecs_generate_variants(self):
        """[summary]
        """
        sim_file_path_obj = Path('../data/simple_buck.plecs')
        full_sim_name = str(sim_file_path_obj.absolute())
        buck_mdl = pyplecs.GenericConverterPlecsMdl(full_sim_name)

        ModelVars = dict()
        ModelVars["Vi"] = 250
        ModelVars["Ii_max"] = 250
        ModelVars["Vo_ref"] = 250
        pyplecs.generate_variant_plecs_mdl(src_mdl=buck_mdl, variant_name='01',
                                           variant_vars=ModelVars)

        ModelVars["Vi"] = 25
        ModelVars["Ii_max"] = 25
        ModelVars["Vo_ref"] = 25
        pyplecs.generate_variant_plecs_mdl(src_mdl=buck_mdl, variant_name='02',
                                           variant_vars=ModelVars)

    def test06_sequential_simulation_server_same_file(self):
        """[summary]
        """
        sim_file_path_obj = Path('../data/simple_buck.plecs')
        full_sim_name = str(sim_file_path_obj.absolute())
        plecs_mdl = pyplecs.GenericConverterPlecsMdl(full_sim_name)

        input("Press Enter to continue with next sim 00...")

        plecs42 = pyplecs.PlecsApp()
        plecs42.open_plecs()
        time.sleep(1)
        plecs_server = pyplecs.PlecsServer(plecs_mdl.folder, plecs_mdl.simulation_name)
        plecs_server.run_sim_with_datastream()

        input("Press Enter to continue with next sim 01...")

        ModelVars = dict()
        ModelVars["Vi"] = 250
        ModelVars["Ii_max"] = 25
        ModelVars["Vo_ref"] = 25

        plecs_server = pyplecs.PlecsServer(plecs_mdl.folder, plecs_mdl.simulation_name)
        plecs_server.run_sim_with_datastream(param_dict=ModelVars)

        input("Press Enter to continue with next sim 02...")

        ModelVars["Vi"] = 25
        ModelVars["Ii_max"] = 1
        ModelVars["Vo_ref"] = 5

        plecs_server = pyplecs.PlecsServer(plecs_mdl.folder, plecs_mdl.simulation_name)
        plecs_server.run_sim_with_datastream(param_dict=ModelVars)

    def test07_sequential_simulation_server_different_file(self):
        """[summary]
        """
        sim_file_path_obj = Path('../data/simple_buck.plecs')
        full_sim_name = str(sim_file_path_obj.absolute())
        buck_mdl = pyplecs.GenericConverterPlecsMdl(full_sim_name)

        ModelVars = dict()
        ModelVars["Vi"] = 250
        ModelVars["Ii_max"] = 25
        ModelVars["Vo_ref"] = 25

        buck_mdl_01 = pyplecs.generate_variant_plecs_mdl(src_mdl=buck_mdl,
                                                         variant_name='01', variant_vars=ModelVars)

        ModelVars["Vi"] = 25
        ModelVars["Ii_max"] = 1
        ModelVars["Vo_ref"] = 5

        buck_mdl_02 = pyplecs.generate_variant_plecs_mdl(src_mdl=buck_mdl,
                                                         variant_name='02', variant_vars=ModelVars)

        sim_path_buck_mdl_01 = buck_mdl_01.folder
        sim_name_buck_mdl_01 = buck_mdl_01.simulation_name
        print(sim_path_buck_mdl_01)
        print(sim_name_buck_mdl_01)

        sim_path_buck_mdl_02 = buck_mdl_02.folder
        sim_name_buck_mdl_02 = buck_mdl_02.simulation_name

        plecs42 = pyplecs.PlecsApp()
        plecs42.open_plecs()
        time.sleep(1)
        plecs_server = pyplecs.PlecsServer(sim_path_buck_mdl_01, sim_name_buck_mdl_01)
        plecs_server.run_sim_with_datastream()
        input("Press Enter to continue with next sim...")

        time.sleep(1)
        plecs_server = pyplecs.PlecsServer(sim_path_buck_mdl_02, sim_name_buck_mdl_02)
        plecs_server.run_sim_with_datastream()
        input("Press Enter to continue with next sim...")

    def test_gui_cmds(self):
        """[summary]
        """
        plecs42 = pyplecs.PlecsApp()
        plecs42.open_plecs()

    def test_gui_simulation(self):
        """[summary]
        """
        sim_file_path_obj = Path('../data/simple_buck.plecs')
        full_sim_name = str(sim_file_path_obj.absolute())
        buck_mdl = pyplecs.GenericConverterPlecsMdl(full_sim_name)

        ModelVars = dict()
        ModelVars["Vi"] = 250
        ModelVars["Ii_max"] = 25
        ModelVars["Vo_ref"] = 25

        buck_mdl_01 = pyplecs.generate_variant_plecs_mdl(src_mdl=buck_mdl,
                                                         variant_name='01', variant_vars=ModelVars)

        ModelVars["Vi"] = 25
        ModelVars["Ii_max"] = 1
        ModelVars["Vo_ref"] = 5

        buck_mdl_02 = pyplecs.generate_variant_plecs_mdl(src_mdl=buck_mdl,
                                                         variant_name='02', variant_vars=ModelVars)

        time.sleep(1)
        buck_mdl_01_server = pyplecs.PlecsServer(buck_mdl_01.folder,
                                                 buck_mdl_01.simulation_name)

        time.sleep(1)
        buck_mdl_02_server = pyplecs.PlecsServer(buck_mdl_02.folder,
                                                 buck_mdl_02.simulation_name)

        # creating processes

        plecs42 = pyplecs.PlecsApp()
        plecs42.open_plecs()

        buck_mdl_01_server.load()
        time.sleep(1)
        plecs42.run_simulation_by_gui(plecs_mdl=buck_mdl_01)

        buck_mdl_02_server.load()
        time.sleep(1)
        plecs42.run_simulation_by_gui(plecs_mdl=buck_mdl_02)

    def test_check_simulation_running(self):
        pass

    def test_set_value_plecs_server(self):
        pass


if __name__ == '__main__':
    unittest.main()
    # test=BasicTestSuite()
    # test.test04_pyplecs_xrpc_server()
