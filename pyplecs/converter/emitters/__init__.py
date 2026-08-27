"""Circuit Model output adapters used by supported projections."""

from .plecs import PlecsProbeSignal, emit_plecs

__all__ = ["PlecsProbeSignal", "emit_plecs"]
