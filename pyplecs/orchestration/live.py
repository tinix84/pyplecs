"""The production PLECS adapter: XML-RPC sessions routed by model file."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Dict, Optional

from ..config import ConfigManager
from ..core.models import SimulationRequest


class LivePlecsAdapter:
    """Run Simulation Requests on the configured PLECS, one model session per model file.

    The orchestrator's default seam sends only parameter vectors; this adapter
    takes whole requests (``simulate_requests``) so one orchestrator can serve
    many models. Nothing touches PLECS at construction time.
    """

    def __init__(
        self,
        config: ConfigManager,
        *,
        server_factory: Optional[Callable[..., Any]] = None,
        probe: Optional[Callable[[str, int, float], bool]] = None,
    ):
        self._plecs = config.plecs
        self._server_factory = server_factory
        self._probe = probe

    def is_available(self) -> bool:
        """A real reachability probe against the configured XML-RPC endpoint."""
        probe = self._probe
        if probe is None:
            from ..pyplecs import _is_plecs_xmlrpc_alive

            probe = _is_plecs_xmlrpc_alive
        return bool(probe(self._plecs.xmlrpc_host, self._plecs.xmlrpc_port, float(self._plecs.xmlrpc_timeout)))

    def simulate_batch(self, parameter_list: Sequence[Dict[str, Any]]) -> Sequence[Any]:
        raise RuntimeError("LivePlecsAdapter routes by model file; it needs whole Simulation Requests")

    def simulate_requests(self, requests: Sequence[SimulationRequest]) -> list[Any]:
        """One PLECS model session per distinct model file; results in request order."""
        factory = self._server_factory
        if factory is None:
            from ..pyplecs import PlecsServer

            factory = PlecsServer

        groups: dict[str, list[int]] = {}
        for index, request in enumerate(requests):
            groups.setdefault(request.model_file, []).append(index)

        results: list[Any] = [None] * len(requests)
        for model_file, indices in groups.items():
            with factory(
                model_file=model_file,
                port=str(self._plecs.xmlrpc_port),
                auto_launch=self._plecs.auto_launch,
            ) as server:
                raw_results = server.simulate_batch([requests[index].parameters for index in indices])
            if not isinstance(raw_results, Sequence) or len(raw_results) != len(indices):
                raise ValueError(
                    f"PLECS returned {len(raw_results) if isinstance(raw_results, Sequence) else 'no'} "
                    f"Raw PLECS Results for {len(indices)} requests on {model_file}"
                )
            for index, raw_result in zip(indices, raw_results):
                results[index] = raw_result
        return results


__all__ = ["LivePlecsAdapter"]
