import threading
import time
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler

import pytest
from pyplecs.pyplecs import PlecsServer, SimulationError


class RequestHandler(SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)


class FakePlecs:
    def __init__(self):
        self.running = False

    def status(self):
        return {'running': self.running}

    def simulate(self, modelName, optStruct=None):
        # emulate some work
        time.sleep(0.1)

        class R:
            Time = [0.0, 1.0, 2.0]
            Values = [[0, 1, 2], [2, 3, 4]]

        return R()


def start_server(port, stop_event):
    server = SimpleXMLRPCServer(
        ('localhost', port), requestHandler=RequestHandler, logRequests=False,
        allow_none=True,
    )
    plecs = FakePlecs()
    # Register functions under dotted names so client calls like
    # proxy.plecs.simulate map to 'plecs.simulate' on the server
    server.register_function(plecs.status, 'plecs.status')
    server.register_function(plecs.simulate, 'plecs.simulate')

    def serve():
        while not stop_event.is_set():
            server.handle_request()

    t = threading.Thread(target=serve, daemon=True)
    t.start()
    return server, plecs, t


def test_run_sim_single_against_local_server():
    port = 19000
    stop_event = threading.Event()
    server, plecs, thread = start_server(port, stop_event)

    try:
        ps = PlecsServer(
            sim_path='.', sim_name='model.plecs', port=str(port), load=False
        )
        res = ps.run_sim_single({'Vi': 230}, timeout=5.0)
        assert res['success'] is True
        assert 'results' in res
    finally:
        stop_event.set()


def test_run_sim_single_timeout(monkeypatch):
    # start a server whose simulate sleeps long
    port = 19001
    stop_event = threading.Event()

    class SlowPlecs(FakePlecs):
        def simulate(self, modelName, optStruct=None):
            time.sleep(2.0)
            return super().simulate(modelName, optStruct)

    server = SimpleXMLRPCServer(
        ('localhost', port), requestHandler=RequestHandler, logRequests=False,
        allow_none=True,
    )
    slow = SlowPlecs()
    server.register_function(slow.status, 'plecs.status')
    server.register_function(slow.simulate, 'plecs.simulate')

    def serve():
        while not stop_event.is_set():
            server.handle_request()

    t = threading.Thread(target=serve, daemon=True)
    t.start()

    try:
        ps = PlecsServer(
            sim_path='.', sim_name='model.plecs', port=str(port), load=False
        )
        with pytest.raises(SimulationError):
            ps.run_sim_single({'Vi': 230}, timeout=0.5)
    finally:
        stop_event.set()

