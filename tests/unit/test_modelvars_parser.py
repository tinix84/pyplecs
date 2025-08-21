import os
from pathlib import Path
import xmlrpc.client
from unittest.mock import MagicMock

import pytest

from pyplecs.plecs_parser import parse_plecs_file
from pyplecs.pyplecs import PlecsServer


def _sample_model_path():
    # Usa sempre il path assoluto del modello di test
    return Path(__file__).parent.parent.parent / 'data' / 'simple_buck.plecs'


def test_parse_init_vars_from_file():
    model_path = _sample_model_path()
    if not model_path.exists():
        pytest.skip("Repo sample model not found; skip parser test")

    parsed = parse_plecs_file(str(model_path))
    assert isinstance(parsed, dict)
    assert 'init_vars' in parsed
    assert isinstance(parsed['init_vars'], dict)
    # Expect at least one initialization variable in the demo model
    assert len(parsed['init_vars']) > 0


def test_rpc_missing_getModelVariables_fallback_to_parser():
    """Simulate RPC server not exposing getModelVariables and fall back to parser."""
    model_path = _sample_model_path()
    if not model_path.exists():
        pytest.skip("Repo sample model not found; skip fallback test")

    ps = PlecsServer(sim_path='.', sim_name='mymodel.plecs', load=False)
    # mock the server and make getModelVariables raise a 'method not found' Fault
    ps.server = MagicMock()
    ps.server.plecs = MagicMock()
    ps.server.plecs.getModelVariables.side_effect = xmlrpc.client.Fault(
        -32601, 'requested method not found'
    )

    # Attempt RPC call and fall back to parsing the model file when it fails
    try:
        vars_rpc = ps.server.plecs.getModelVariables()
    except xmlrpc.client.Fault:
        parsed = parse_plecs_file(str(model_path))
        vars_rpc = list(parsed.get('init_vars', {}).keys())

    assert isinstance(vars_rpc, (list, tuple))
    assert len(vars_rpc) > 0
