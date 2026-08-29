"""Shared fixtures: the live-PLECS gate and the canonical Operating Point (ADR-0013)."""

import pytest

from pyplecs.pyplecs import _is_plecs_xmlrpc_alive

from .verification.manifest import isolated_config, load_manifest, require_live_plecs


@pytest.fixture(scope="session")
def canonical_buck():
    """The tracked canonical buck manifest."""
    return load_manifest()


@pytest.fixture(scope="session")
def live_plecs(canonical_buck):
    """Probe the configured XML-RPC endpoint once; skip every live test with the endpoint named."""
    host, port = canonical_buck.endpoint
    require_live_plecs(host, port, _is_plecs_xmlrpc_alive)
    return canonical_buck.endpoint


@pytest.fixture
def live_config(tmp_path, canonical_buck, live_plecs):
    """Isolated temporary configuration for one live test."""
    return isolated_config(tmp_path, canonical_buck)
