"""PlecsServer pass-throughs (SolverOpts, get, scope) against a fake XML-RPC proxy.

No PLECS needed: the proxy records every call and returns a canned value.
"""

from unittest.mock import patch

import pytest

from pyplecs.pyplecs import PlecsServer


class _Namespace:
    def __init__(self, calls, prefix):
        self._calls = calls
        self._prefix = prefix

    def __getattr__(self, name):
        def call(*args):
            self._calls.append((f"{self._prefix}.{name}", args))
            return f"ret:{name}"

        return call


class FakeProxy:
    def __init__(self):
        self.calls = []
        self.plecs = _Namespace(self.calls, "plecs")


@pytest.fixture
def server_and_calls():
    proxy = FakeProxy()
    with (
        patch("pyplecs.pyplecs._is_plecs_xmlrpc_alive", return_value=True),
        patch("pyplecs.pyplecs.xmlrpc.client.Server", return_value=proxy),
    ):
        server = PlecsServer(model_file="dir/mdl.plecs", load=False, auto_launch=False)
    return server, proxy.calls


def test_simulate_without_arguments(server_and_calls):
    server, calls = server_and_calls
    assert server.simulate() == "ret:simulate"
    assert calls == [("plecs.simulate", ("mdl",))]


def test_simulate_parameters_only_is_unchanged(server_and_calls):
    server, calls = server_and_calls
    server.simulate({"Vi": 12})
    assert calls == [("plecs.simulate", ("mdl", {"ModelVars": {"Vi": 12.0}}))]
    assert type(calls[0][1][1]["ModelVars"]["Vi"]) is float


def test_simulate_solver_opts_only(server_and_calls):
    server, calls = server_and_calls
    opts = {"OutputTimes": [0.0, 1e-3], "Timeout": 60}
    server.simulate(solver_opts=opts)
    assert calls == [("plecs.simulate", ("mdl", {"SolverOpts": opts}))]


def test_simulate_parameters_and_solver_opts(server_and_calls):
    server, calls = server_and_calls
    opts = {"Timeout": 60}
    server.simulate({"Vi": 12, "Table": [1, 2.5]}, solver_opts=opts)
    assert calls == [
        (
            "plecs.simulate",
            ("mdl", {"ModelVars": {"Vi": 12.0, "Table": [1.0, 2.5]}, "SolverOpts": opts}),
        )
    ]
    mv = calls[0][1][1]["ModelVars"]
    assert type(mv["Vi"]) is float
    assert all(type(x) is float for x in mv["Table"])


def test_simulate_list_ints_beyond_xmlrpc_range_become_floats(server_and_calls):
    server, calls = server_and_calls
    server.simulate({"Big": [2**40, 1]})
    sent = calls[0][1][1]["ModelVars"]["Big"]
    assert sent == [float(2**40), 1.0]
    assert all(type(x) is float for x in sent)


def test_simulate_does_not_mutate_solver_opts(server_and_calls):
    server, _ = server_and_calls
    opts = {"OutputTimes": [0.0, 1e-3], "Timeout": 60}
    server.simulate({"Vi": 12}, solver_opts=opts)
    server.simulate_batch([{"Vi": 12}], solver_opts=opts)
    assert opts == {"OutputTimes": [0.0, 1e-3], "Timeout": 60}


def test_simulate_empty_parameters_sends_empty_model_vars(server_and_calls):
    server, calls = server_and_calls
    server.simulate({})
    assert calls == [("plecs.simulate", ("mdl", {"ModelVars": {}}))]


def test_simulate_batch_applies_solver_opts_to_every_struct(server_and_calls):
    server, calls = server_and_calls
    opts = {"Timeout": 5}
    server.simulate_batch([{"Vi": 12}, {"Vi": 24}], solver_opts=opts)
    assert type(calls[0][1][1][0]["ModelVars"]["Vi"]) is float
    assert calls == [
        (
            "plecs.simulate",
            (
                "mdl",
                [
                    {"ModelVars": {"Vi": 12.0}, "SolverOpts": opts},
                    {"ModelVars": {"Vi": 24.0}, "SolverOpts": opts},
                ],
            ),
        )
    ]


def test_simulate_batch_without_solver_opts_is_unchanged(server_and_calls):
    server, calls = server_and_calls
    server.simulate_batch([{"Vi": 12}])
    assert calls == [("plecs.simulate", ("mdl", [{"ModelVars": {"Vi": 12.0}}]))]


def test_get_model_level(server_and_calls):
    server, calls = server_and_calls
    assert server.get(parameter="StopTime") == "ret:get"
    server.get()
    assert calls == [("plecs.get", ("mdl", "StopTime")), ("plecs.get", ("mdl",))]


def test_get_component_level(server_and_calls):
    server, calls = server_and_calls
    server.get("Sub/R1", "R")
    server.get("Sub/R1")
    assert calls == [("plecs.get", ("mdl/Sub/R1", "R")), ("plecs.get", ("mdl/Sub/R1",))]


def test_scope(server_and_calls):
    server, calls = server_and_calls
    assert server.scope("Scope", "SaveTraces", "out.csv") == "ret:scope"
    server.scope("Scope", "ClearTraces")
    assert calls == [
        ("plecs.scope", ("mdl/Scope", "SaveTraces", "out.csv")),
        ("plecs.scope", ("mdl/Scope", "ClearTraces")),
    ]
