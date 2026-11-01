"""dict_to_plecs_opts marshalling, probe timeout and __exit__ safety (#114, #115).

No PLECS needed: XML-RPC is mocked or replaced with a local socket.
"""

import socket
import threading
import time
import xmlrpc.client
from unittest.mock import MagicMock, patch

import pytest

from pyplecs.pyplecs import PlecsServer, _is_plecs_xmlrpc_alive, dict_to_plecs_opts


def test_nested_list_above_int32_marshals():
    opts = dict_to_plecs_opts({"M": [[1, 2**40]]})
    assert opts["ModelVars"]["M"] == [[1.0, float(2**40)]]
    assert all(isinstance(x, float) for x in opts["ModelVars"]["M"][0])
    xmlrpc.client.dumps((opts,))


def test_numpy_scalars_become_float():
    np = pytest.importorskip("numpy")
    opts = dict_to_plecs_opts(
        {"a": [np.int64(3), np.float64(2.5)], "b": (np.int64(2**40),)}
    )
    assert opts["ModelVars"]["a"] == [3.0, 2.5]
    assert opts["ModelVars"]["b"] == [float(2**40)]
    assert all(type(x) is float for x in opts["ModelVars"]["a"])
    xmlrpc.client.dumps((opts,))


def test_string_scalar_and_list_element_agree():
    opts = dict_to_plecs_opts({"s": "1.5", "l": ["1.5"]})
    assert opts["ModelVars"]["s"] == 1.5
    assert opts["ModelVars"]["l"] == [1.5]


def test_caller_dict_not_mutated():
    params = {"x": 1, "y": [1, 2], "z": [[3]]}
    snapshot = {"x": 1, "y": [1, 2], "z": [[3]]}
    opts = dict_to_plecs_opts(params)
    assert params == snapshot
    assert type(params["x"]) is int
    assert opts["ModelVars"] is not params


def _silent_server():
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)
    conns = []

    def accept():
        try:
            while True:
                conn, _ = srv.accept()
                conns.append(conn)
        except OSError:
            pass

    threading.Thread(target=accept, daemon=True).start()
    return srv, conns


def test_alive_probe_honours_timeout():
    srv, conns = _silent_server()
    try:
        start = time.monotonic()
        alive = _is_plecs_xmlrpc_alive("127.0.0.1", srv.getsockname()[1], timeout=0.5)
        elapsed = time.monotonic() - start
    finally:
        srv.close()
        for c in conns:
            c.close()
    assert alive is False
    assert elapsed < 2.0


def _make_server():
    proxy = MagicMock()
    with (
        patch("pyplecs.pyplecs._is_plecs_xmlrpc_alive", return_value=True),
        patch("pyplecs.pyplecs.xmlrpc.client.Server", return_value=proxy),
    ):
        server = PlecsServer(model_file="dir/mdl.plecs", load=False, auto_launch=False)
    return server, proxy


def test_exit_close_failure_does_not_mask_body_exception():
    server, proxy = _make_server()
    proxy.plecs.close.side_effect = RuntimeError("close failed")
    with pytest.raises(ValueError, match="body"):
        with server:
            raise ValueError("body")
    proxy.plecs.close.assert_called_once()


def test_exit_close_failure_propagates_without_body_exception():
    server, proxy = _make_server()
    proxy.plecs.close.side_effect = RuntimeError("close failed")
    with pytest.raises(RuntimeError, match="close failed"):
        with server:
            pass
