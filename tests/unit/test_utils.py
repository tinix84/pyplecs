import socket

from pyplecs.utils import dict_to_plecs_opts, rpc_call_wrapper


class FakeProxyTransient:
    """Fake proxy that fails a few times then succeeds for 'plecs.ping'."""
    def __init__(self, fail_times=2):
        self.fail_times = fail_times
        self.calls = 0

    def __getattr__(self, item):
        if item == 'plecs':
            return self
        if item == 'ping':
            def _fn():
                self.calls += 1
                if self.calls <= self.fail_times:
                    raise socket.error('simulated transient')
                return 'pong'
            return _fn
        raise AttributeError(item)


def test_dict_to_plecs_opts_basic():
    inp = {'Vi': 230, 'Ii_max': '5'}
    out = dict_to_plecs_opts(inp)
    assert 'ModelVars' in out
    assert isinstance(out['ModelVars']['Vi'], float)
    assert isinstance(out['ModelVars']['Ii_max'], float)
    assert out['ModelVars']['Vi'] == 230.0


def test_dict_to_plecs_opts_preserve_when_no_coerce():
    inp = {'Vi': '10*2'}
    out = dict_to_plecs_opts(inp, coerce=False)
    assert out['ModelVars']['Vi'] == '10*2'


def test_rpc_call_wrapper_retries():
    proxy = FakeProxyTransient()
    # should succeed after retries
    result = rpc_call_wrapper(proxy, 'plecs.ping', retries=3, backoff=0.01)
    assert result == 'pong'


def test_rpc_call_wrapper_fails():
    proxy = FakeProxyTransient()
    # force more failures than allowed
    proxy.fail_times = 5
    try:
        rpc_call_wrapper(proxy, 'plecs.ping', retries=2, backoff=0.01)
    except socket.error:
        # expected
        return
    assert False, 'Expected rpc_call_wrapper to raise'
