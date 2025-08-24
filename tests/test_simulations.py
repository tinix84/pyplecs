
import unittest
import itertools
from pathlib import Path
from pyplecs.core.simulations import SimulationPlan
from tests.integration_utils import (
    start_plecs_app, load_and_validate_model, start_xrpc_server, filter_sweep_params
)

class TestSimulationPlanUnit(unittest.TestCase):
    def test_parameter_sweep_generation(self):
        plan = SimulationPlan()
        plan.set_parameter_sweep('voltage', [12, 24])
        plan.set_parameter_sweep('current', [1, 2])
        sweeps = plan.generate_parameter_sweeps()
        self.assertEqual(len(sweeps), 4)
        self.assertIn({'voltage': 12, 'current': 1}, sweeps)
        self.assertIn({'voltage': 24, 'current': 2}, sweeps)

# --- Integration test for real PLECS XRPC server (no mocks) ---

class TestBatchParameterSweepIntegration(unittest.TestCase):
    def test_batch_parameter_sweep_real_xrpc(self):
        # Standardized integration test using shared utilities
        start_plecs_app()
        model_path = 'data/simple_buck.plecs'
        parser, allowed_vars = load_and_validate_model(model_path)
        model_folder = str(Path(model_path).parent)
        model_name = Path(model_path).name

        sweep_params = {
            'Vin': [100, 200],
            'Load': [1, 2],
            'NotInModel': [999]  # This will be ignored
        }
        sweep_keys = [k for k in sweep_params if k in allowed_vars]
        sweep_values = [sweep_params[k] for k in sweep_keys]
        combos = [dict(zip(sweep_keys, vals)) for vals in itertools.product(*sweep_values)]

        server = start_xrpc_server(model_folder, model_name)
        results = []
        for param_set in combos:
            filtered_params = filter_sweep_params(param_set, allowed_vars)
            result = server.run_sim_single(filtered_params)
            print(f"Sweep {filtered_params} result: {result}")
            results.append(result)
        self.assertEqual(len(results), len(combos))
        for res in results:
            self.assertTrue(res['success'])

if __name__ == '__main__':
    unittest.main()
