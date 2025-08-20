# -*- coding: utf-8 -*-

from context import pyplecs

import unittest
import time
from pathlib import Path


class InteractiveTestSuite(unittest.TestCase):
    """Interactive test cases that require user input or manual interaction."""

    def test01_sequential_simulation_server_same_file(self):
        """Interactive test that runs multiple simulations with user input.
        
        This test demonstrates sequential simulation execution with manual
        progression control, allowing the user to observe each simulation
        step and results.
        """
        sim_file_path_obj = Path('data/simple_buck.plecs')
        full_sim_name = str(sim_file_path_obj.absolute())
        plecs_mdl = pyplecs.GenericConverterPlecsMdl(full_sim_name)

        print("\n=== Starting Sequential Simulation Test ===")
        input("Press Enter to continue with next sim 00...")

        plecs42 = pyplecs.PlecsApp()
        plecs42.open_plecs()
        time.sleep(1)
        plecs_server = pyplecs.PlecsServer(plecs_mdl.folder, 
                                          plecs_mdl.simulation_name)
        plecs_server.run_sim_with_datastream()

        print("Simulation 00 completed")
        input("Press Enter to continue with next sim 01...")

        ModelVars = dict()
        ModelVars["Vi"] = 250
        ModelVars["Ii_max"] = 25
        ModelVars["Vo_ref"] = 25

        plecs_server = pyplecs.PlecsServer(plecs_mdl.folder, 
                                          plecs_mdl.simulation_name)
        plecs_server.run_sim_with_datastream(param_dict=ModelVars)

        print("Simulation 01 completed with Vi=250, Ii_max=25, Vo_ref=25")
        input("Press Enter to continue with next sim 02...")

        ModelVars["Vi"] = 25
        ModelVars["Ii_max"] = 1
        ModelVars["Vo_ref"] = 5

        plecs_server = pyplecs.PlecsServer(plecs_mdl.folder, 
                                          plecs_mdl.simulation_name)
        plecs_server.run_sim_with_datastream(param_dict=ModelVars)
        
        print("Simulation 02 completed with Vi=25, Ii_max=1, Vo_ref=5")
        print("=== Sequential Simulation Test Complete ===")

    def test02_sequential_simulation_server_different_file(self):
        """Interactive test using different files for each simulation.
        
        This test demonstrates creating and running simulations from
        different variant files, with manual progression control.
        """
        sim_file_path_obj = Path('data/simple_buck.plecs')
        full_sim_name = str(sim_file_path_obj.absolute())
        buck_mdl = pyplecs.GenericConverterPlecsMdl(full_sim_name)

        print("\n=== Starting Different File Simulation Test ===")
        
        # Create first variant
        ModelVars = dict()
        ModelVars["Vi"] = 250
        ModelVars["Ii_max"] = 25
        ModelVars["Vo_ref"] = 25

        buck_mdl_01 = pyplecs.generate_variant_plecs_mdl(
            src_mdl=buck_mdl, variant_name='01', variant_vars=ModelVars)

        # Create second variant
        ModelVars["Vi"] = 25
        ModelVars["Ii_max"] = 1
        ModelVars["Vo_ref"] = 5

        buck_mdl_02 = pyplecs.generate_variant_plecs_mdl(
            src_mdl=buck_mdl, variant_name='02', variant_vars=ModelVars)

        sim_path_buck_mdl_01 = buck_mdl_01.folder
        sim_name_buck_mdl_01 = buck_mdl_01.simulation_name
        print(f"Variant 01: {sim_path_buck_mdl_01}")
        print(f"File: {sim_name_buck_mdl_01}")

        sim_path_buck_mdl_02 = buck_mdl_02.folder
        sim_name_buck_mdl_02 = buck_mdl_02.simulation_name
        print(f"Variant 02: {sim_path_buck_mdl_02}")
        print(f"File: {sim_name_buck_mdl_02}")

        plecs42 = pyplecs.PlecsApp()
        plecs42.open_plecs()
        time.sleep(1)
        
        # Run first simulation
        plecs_server = pyplecs.PlecsServer(sim_path_buck_mdl_01, 
                                          sim_name_buck_mdl_01)
        plecs_server.run_sim_with_datastream()
        print("Simulation 01 completed (Vi=250, Ii_max=25, Vo_ref=25)")
        input("Press Enter to continue with next sim...")

        # Run second simulation
        time.sleep(1)
        plecs_server = pyplecs.PlecsServer(sim_path_buck_mdl_02, 
                                          sim_name_buck_mdl_02)
        plecs_server.run_sim_with_datastream()
        print("Simulation 02 completed (Vi=25, Ii_max=1, Vo_ref=5)")
        input("Press Enter to finish test...")
        
        print("=== Different File Simulation Test Complete ===")


if __name__ == '__main__':
    print("WARNING: This test suite contains interactive tests that require")
    print("manual input. Run individual tests or use pytest for better control.")
    print("\nExample usage:")
    print("python -m pytest tests/test_interactive.py::InteractiveTestSuite::test01_sequential_simulation_server_same_file -v -s")
    print("\nOr run all interactive tests:")
    print("python -m pytest tests/test_interactive.py -v -s")
    
    unittest.main()
