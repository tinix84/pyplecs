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


def test_run_sim_single_timeout(monkeypatch):
    # simulate a slow RPC by making rpc_call_wrapper sleep
    def slow_rpc(proxy, method_name, *args, **kwargs):
        import time as _t
        _t.sleep(0.5)
        return {'Time': [0, 1], 'Values': [[0], [1]]}

    monkeypatch.setattr('pyplecs.pyplecs.rpc_call_wrapper', slow_rpc)
    server = PlecsServer(sim_path='.', sim_name='slow.plecs', port='1080', load=False)
    with pytest.raises(SimulationError):
        server.run_sim_single({'Vi': 1}, timeout=0.01)


def test_get_model_variables_uses_rpc_then_parser(monkeypatch, tmp_path):
    # First, test RPC path
    class FakeProxy:
        class plecs:
            @staticmethod
            def getModelVariables():
                return ['A', 'B']

    monkeypatch.setattr('pyplecs.pyplecs.xmlrpc.client.Server', lambda url: FakeProxy())
    ps = PlecsServer(sim_path='.', sim_name='model.plecs', port='1080', load=False)
    mv = ps.get_model_variables()
    assert 'A' in mv

    # Next, simulate RPC lacking the method so parser fallback triggers
    class ProxyNoMethod:
        class plecs:
            pass

    monkeypatch.setattr('pyplecs.pyplecs.xmlrpc.client.Server', lambda url: ProxyNoMethod())
    # point to a real sample plecs file present in repo data
    ps2 = PlecsServer(sim_path='.', sim_name='simple_buck.plecs', port='1080', load=False)
    mv2 = ps2.get_model_variables()
    assert isinstance(mv2, list)
