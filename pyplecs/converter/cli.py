"""Command-line interface for offline PLECS conversion."""

import argparse
from pathlib import Path
from typing import Optional, Sequence

from . import parse_plecs, plecs_to_ltspice, plecs_to_spice


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pyplecs-convert",
        description="Convert a PLECS schematic offline to SPICE and/or LTspice.",
    )
    parser.add_argument("plecs_file", type=Path)
    parser.add_argument("--format", choices=("cir", "asc", "all"), default="cir", dest="format")
    parser.add_argument("-o", "--output", type=Path, default=Path("."))
    arguments = parser.parse_args(argv)

    try:
        circuit = parse_plecs(arguments.plecs_file)
        output_dir = arguments.output
        if output_dir.suffix and arguments.format != "all":
            output_file = output_dir
            output_dir = output_file.parent
        else:
            output_file = None
        output_dir.mkdir(parents=True, exist_ok=True)

        if arguments.format in {"cir", "all"}:
            destination = output_file if output_file is not None else output_dir / f"{circuit.name}.cir"
            plecs_to_spice(circuit, destination)
        if arguments.format in {"asc", "all"}:
            destination = output_file if output_file is not None else output_dir / f"{circuit.name}.asc"
            plecs_to_ltspice(circuit, destination)
    except (OSError, ValueError) as error:
        parser.exit(2, f"pyplecs-convert: error: {error}\n")
    return 0
