import os
import pytest
from unittest.mock import MagicMock

import xmlrpc.client

from pyplecs.pyplecs import PlecsServer


def test_simulate_batch_no_callback():
    ps = PlecsServer(sim_path='.', sim_name='mymodel.plecs', load=False)
    # mock remote simulate to return a list of results
    ps.server = MagicMock()
    ps.server.plecs = MagicMock()
    ps.server.plecs.simulate = MagicMock(return_value=[
        {'Time': [0, 1], 'Values': [[0], [1]]},
        'ERROR'
    ])

    optStructs = [{'ModelVars': {'x': 1}}, {'ModelVars': {'x': 2}}]
    results = ps.simulate_batch(optStructs)

    assert results == [
        {'Time': [0, 1], 'Values': [[0], [1]]},
        'ERROR'
    ]


def test_simulate_batch_with_callback():
    ps = PlecsServer(sim_path='.', sim_name='mymodel.plecs', load=False)
    ps.server = MagicMock()
    ps.server.plecs = MagicMock()
    ps.server.plecs.simulate = MagicMock(return_value=[
        {'Time': [0, 1], 'Values': [[0], [1]]},
        {'Time': [0, 1], 'Values': [[2], [3]]}
    ])

    def cb(idx, res):
        # aggregate: return max of first output signal
        if isinstance(res, dict) and 'Values' in res:
            vals = res['Values']
            # Values is m x n; take first column
            col0 = [row[0] for row in vals]
            return max(col0)
        return None

    outputs = ps.simulate_batch([{}, {}], callback=cb)
    assert outputs == [1, 3]


def test_simulate_batch_integration_real_call():
    """
    Integration test that tries to start the PLECS application locally via
    `PlecsApp` if `PLECS_RPC_URL` is not set. If PLECS cannot be started or
    no RPC server becomes available, the test is skipped.
    """
    # If a specific RPC URL is provided use it
    url = os.environ.get('PLECS_RPC_URL')

    # use a real plecs model from the repo data folder
    from pathlib import Path

    model_path = Path(__file__).parent.parent / 'data' / 'simple_buck.plecs'
    if not model_path.exists():
        pytest.skip(
            "Repo sample model data/simple_buck.plecs not found; "
            "skip integration test"
        )

    sim_folder = str(model_path.parent)
    sim_name = model_path.name

    # If no URL supplied try to start local PLECS app and let PlecsServer
    # load the model
    if not url:
        try:
            from pyplecs.pyplecs import PlecsApp

            app = PlecsApp()
            app.open_plecs()
            import time

            time.sleep(1)
        except Exception as exc:  # pragma: no cover - environment-dependent
            pytest.skip(f"Could not start local PLECS: {exc}")

        # instantiate PlecsServer which will call load(...) when load=True
        try:
            ps = PlecsServer(sim_path=sim_folder, sim_name=sim_name, load=True)
        except Exception as exc:  # pragma: no cover - env dependent
            pytest.skip(f"Could not create PlecsServer and load model: {exc}")
    else:
        # connect to provided RPC URL and explicitly load the model
        try:
            ps = PlecsServer(sim_path='.', sim_name=sim_name, load=False)
            ps.server = xmlrpc.client.ServerProxy(url)
            ps.server.plecs.load(sim_folder + '//' + sim_name)
        except Exception as exc:  # pragma: no cover - env dependent
            pytest.skip(
                f"Could not connect to PLECS RPC at {url} or load model: {exc}"
            )

    # Query available model variables from PLECS
    try:
        model_vars = ps.server.plecs.getModelVariables()
    except Exception as exc:
        pytest.skip(f"Could not query model variables: {exc}")

    # Use the first available variable for demonstration
    if not model_vars:
        pytest.skip("No model variables found in the loaded PLECS model.")

    var_name = model_vars[0]
    optStructs = [{'ModelVars': {var_name: 1}}, {'ModelVars': {var_name: 1000}}]
    results = ps.simulate_batch(optStructs)

    assert isinstance(results, list)
    assert len(results) == 2
    for res in results:
        assert isinstance(res, dict)
        assert 'Time' in res and 'Values' in res
        assert isinstance(res['Time'], list)
        assert isinstance(res['Values'], list)
        t = res['Time']
        vals = res['Values']
        if len(vals) == 0:
            # nothing to assert about lengths
            continue
        # flat list of scalars (one signal): length must match Time
        if all(not isinstance(v, list) for v in vals):
            assert len(t) == len(vals)
            continue
        # now vals is a list of lists. PLECS may return either:
        # - time-major: vals is a list of rows (len == len(Time)).
        #   each row is a list of signal values
        # - signal-major: vals is a list of signals. Each signal is a list
        #   whose len == len(Time)
        if len(vals) == len(t) and all(isinstance(row, list) for row in vals):
            # time-major: each row should have a consistent column count
            row_lens = [len(r) for r in vals]
            first_len = row_lens[0]
            assert all(x == first_len for x in row_lens)
        elif all(isinstance(trace, list) and len(trace) == len(t)
                 for trace in vals):
            # signal-major: each trace length matches Time -> OK
            pass
        else:
            # try to find at least one inner list that matches Time length
            if not any(isinstance(v, list) and len(v) == len(t) for v in vals):
                pytest.fail(
                    "Values shape doesn't match Time length in any orientation"
                )

    # Optionally plot waveforms if matplotlib is available. Not required
    # for the test to pass.
    try:
        import matplotlib.pyplot as plt
        for idx, res in enumerate(results):
            vals = res['Values']
            t = res['Time']
            # build y as the first trace in a defensive way
            if all(not isinstance(v, list) for v in vals):
                y = vals
            elif len(vals) == len(t) and \
                    all(isinstance(row, list) for row in vals):
                # time-major: take first column from rows
                y = [row[0] for row in vals]
            elif all(isinstance(trace, list) and len(trace) == len(t)
                     for trace in vals):
                # signal-major: take first signal
                y = vals[0]
            else:
                # fallback: pick first inner list matching Time length
                candidate = None
                for v in vals:
                    if isinstance(v, list) and len(v) == len(t):
                        candidate = v
                        break
                if candidate is None:
                    # nothing sensible to plot for this run
                    continue
                y = candidate
            plt.plot(t, y, label=f'Run {idx+1}')
        plt.xlabel('Time')
        plt.ylabel('Output')
        plt.title('PLECS Simulation Results')
        plt.legend()
        plt.show()
    except ImportError:
        pass
