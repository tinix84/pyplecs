import unittest
from pathlib import Path
from pyplecs import PlecsServer


class SimulationTestSuite(unittest.TestCase):
	"""Test cases for simulation management."""

	def test_run_sim_single(self):
		"""Test single simulation execution."""
		sim_file_path = Path('../data/simple_buck.plecs')
		try:
			plecs_server = PlecsServer(
				sim_path=str(sim_file_path.parent), sim_name=sim_file_path.name
			)
		except Exception as exc:
			import pytest

			pytest.skip(f"PLECS RPC not available: {exc}")

		inputs = {'Vi': 250, 'Ii_max': 25, 'Vo_ref': 25}
		results = plecs_server.run_sim_single(inputs)

		self.assertIsNotNone(results)
		self.assertTrue(hasattr(results, 'Time'))
		self.assertTrue(hasattr(results, 'Values'))

	def test_run_sim_with_datastream(self):
		"""Test simulation with datastream parameters."""
		sim_file_path = Path('../data/simple_buck.plecs')
		try:
			plecs_server = PlecsServer(
				sim_path=str(sim_file_path.parent), sim_name=sim_file_path.name
			)
		except Exception as exc:
			import pytest

			pytest.skip(f"PLECS RPC not available: {exc}")

		params = {'Vi': 25, 'Ii_max': 1, 'Vo_ref': 5}
		results = plecs_server.run_sim_with_datastream(param_dict=params)

		self.assertIsNotNone(results)
		self.assertTrue(hasattr(results, 'Time'))
		self.assertTrue(hasattr(results, 'Values'))


if __name__ == '__main__':
	unittest.main()
