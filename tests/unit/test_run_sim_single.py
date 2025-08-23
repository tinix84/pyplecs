import xmlrpc.client
import pytest
from pyplecs.pyplecs import PlecsServer, SimulationError, FileLoadError


def test_run_sim_single_with_dict(monkeypatch):
    server = PlecsServer(
        sim_path='.', sim_name='model.plecs', port='1080', load=False
    )

    # fake rpc_call_wrapper to return a simple dict result
    def fake_rpc(proxy, method_name, *args, **kwargs):
        if method_name == 'plecs.simulate':
            class R:
                Time = [0, 1]
                Values = [[0, 1], [2, 3]]
            return R()
        raise RuntimeError('unexpected')

    monkeypatch.setattr('pyplecs.pyplecs.rpc_call_wrapper', fake_rpc)

    res = server.run_sim_single({'Vi': 230})
    assert res['success'] is True
    assert 'results' in res
    assert 'execution_time' in res
    assert res['parameters_used']['Vi'] == 230.0


def test_run_sim_single_with_file_not_found():
    server = PlecsServer(
        sim_path='.', sim_name='model.plecs', port='1080', load=False
    )
    with pytest.raises(FileLoadError):
        server.run_sim_single('nonexistent_file.mat')


def test_run_sim_single_rpc_fault(monkeypatch):
    server = PlecsServer(
        sim_path='.', sim_name='model.plecs', port='1080', load=False
    )

    class FaultExc(xmlrpc.client.Fault):
        pass

    def fake_rpc_fault(proxy, method_name, *args, **kwargs):
        raise xmlrpc.client.Fault(1, 'sim fault')

    monkeypatch.setattr('pyplecs.pyplecs.rpc_call_wrapper', fake_rpc_fault)

    with pytest.raises(SimulationError):
        server.run_sim_single({'Vi': 230})
