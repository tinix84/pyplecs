"""Offline PLECS schematic conversion through the public Circuit Model."""

from pathlib import Path
from typing import Optional

from .circuit import Circuit, Component, Net, Pin
from .emitters import emit_ltspice, emit_spice
from .parser import PlecsParseError, parse_plecs


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
    "Net",
    "Pin",
    "PlecsParseError",
    "parse_plecs",
    "plecs_to_ltspice",
    "plecs_to_spice",
]
