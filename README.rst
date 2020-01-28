Python Plecs Repository
========================

.. image:: https://api.codacy.com/project/badge/Grade/af9810b2dc32406b93312e5dfcbebd8a
   :alt: Codacy Badge
   :target: https://app.codacy.com/manual/tinix84/pyplecs?utm_source=github.com&utm_medium=referral&utm_content=tinix84/pyplecs&utm_campaign=Badge_Grade_Settings

For python lovers and not, 

I wrote a python package to automatize the python simulations

In the test_basic.py you can find all the unit test where every test case show a different function of the package pyPlecs

Just short summary of capabilities:

1. test03_plecs_app_open_highpriority: python open plecs as process in highpriority to execure faster simulations

2. test04_pyplecs_xrpc_server: python use the normal remote control to execute plecs with xrpc server

3. test07_sequential_simulation_server_different_file: pyPlecs generate different plecs file for every variant request and launch them sequentially with normal xrpc simulations

4. test09_gui_simulation: pyPlecs generate different plecs file for every variant request and open them all at the same time and execute them in parallel with just one user (interacting with plecs GUI)

Next development steps are:

1. creation of requirement.txt and setup.py to automatize installation

2. creation of a pool of simulation to manage multiprocessing or multithreading

3. new example for more complex simulation with gui in Ipython

4. generation montecarlo variants in python and then analysis in plecs 

If you want to use but you find bugs please let me know...


---------------



✨🍰✨
