"""Offline PLECS schematic conversion through the public Circuit Model."""

from pathlib import Path
from typing import Optional, Sequence

from .circuit import Circuit, Component, Net, Pin
from .emitters import PlecsProbeSignal, emit_ltspice, emit_plecs, emit_spice
from .ltspice_parser import LtspiceParseError, parse_ltspice
from .parser import PlecsParseError, parse_plecs


def ltspice_to_plecs(
    source: Circuit | str | Path,
    output_path: Optional[str | Path] = None,
    *,
    probes: Sequence[tuple[str, str]] = (),
) -> str:
    """Convert a Circuit Model or LTspice ``.asc`` file to a runnable ``.plecs`` schematic.

    ``probes`` are ``(component, PLECS signal name)`` pairs, e.g. ``("C1", "Capacitor voltage")``,
    wired to the model's output so a simulation returns them.
    """
    circuit = source if isinstance(source, Circuit) else parse_ltspice(source)
    content = emit_plecs(circuit, probes=[PlecsProbeSignal(component, signal) for component, signal in probes])
    if output_path is not None:
        _write_output(output_path, content)
    return content


def plecs_to_spice(source: Circuit | str | Path, output_path: Optional[str | Path] = None) -> str:
    """Convert a Circuit Model or ``.plecs`` file to SPICE netlist text."""
    circuit = source if isinstance(source, Circuit) else parse_plecs(source)
    content = emit_spice(circuit)
    if output_path is not None:
        _write_output(output_path, content)
    return content


def plecs_to_ltspice(source: Circuit | str | Path, output_path: Optional[str | Path] = None) -> str:
    """Convert a Circuit Model or ``.plecs`` file to LTspice schematic text."""
    circuit = source if isinstance(source, Circuit) else parse_plecs(source)
    content = emit_ltspice(circuit)
    if output_path is not None:
        _write_output(output_path, content)
    return content


def _write_output(path: str | Path, content: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


__all__ = [
    "Circuit",
    "Component",
    "LtspiceParseError",
    "Net",
    "Pin",
    "PlecsParseError",
    "ltspice_to_plecs",
    "parse_ltspice",
    "parse_plecs",
    "plecs_to_ltspice",
    "plecs_to_spice",
]
