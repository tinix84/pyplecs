import pytest

import pyplecs.pyplecs as pp


class DummyProc:
    def __init__(self, name):
        self.info = {'name': name}


def test_check_if_simulation_running_server_running(monkeypatch):
    # rpc_call_wrapper returns a dict with running True for plecs.status
    def fake_rpc(proxy, method_name, *args, **kwargs):
        if method_name == 'plecs.status':
            return {'running': True}
        raise RuntimeError('unexpected')

    monkeypatch.setattr(pp, 'rpc_call_wrapper', fake_rpc)

    app = pp.PlecsApp()
    res = app.check_if_simulation_running(None)
    assert isinstance(res, dict)
    assert res['server_available'] is True
    assert res['running'] is True


def test_check_if_simulation_running_model_specific(monkeypatch):
    # Simulate plecs.status failing, but plecs.get(model,'SimulationStatus')
    # returning 'running'
    def fake_rpc(proxy, method_name, *args, **kwargs):
        if method_name == 'plecs.status':
            raise RuntimeError('status not available')
        if method_name == 'plecs.get':
            # model status query
            return 'running'
        raise RuntimeError('unexpected')

    monkeypatch.setattr(pp, 'rpc_call_wrapper', fake_rpc)

    app = pp.PlecsApp()
    result = app.check_if_simulation_running('simple_buck')
    # model-specific call should return True
    assert result is True


def test_check_if_simulation_running_unreachable(monkeypatch):
    # Make _get_proxy throw and psutil.process_iter return empty
    def _raise_no_server(*a, **k):
        raise RuntimeError('no server')

    def _raise_no_rpc(*a, **k):
        raise RuntimeError('no rpc')

    monkeypatch.setattr(pp.xmlrpc.client, 'Server', _raise_no_server)
    monkeypatch.setattr(pp, 'rpc_call_wrapper', _raise_no_rpc)
    monkeypatch.setattr(pp.psutil, 'process_iter', lambda *a, **k: [])

    app = pp.PlecsApp()
    with pytest.raises(pp.PlecsConnectionError):
        app.check_if_simulation_running(None)
