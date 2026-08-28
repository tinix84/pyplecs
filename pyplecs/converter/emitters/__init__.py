"""Circuit Model output adapters."""

from .ltspice import emit_ltspice
from .spice import emit_spice

__all__ = ["emit_ltspice", "emit_spice"]
from .plecs import PlecsProbeSignal, emit_plecs

__all__ = ["PlecsProbeSignal", "emit_plecs"]
