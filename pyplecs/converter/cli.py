"""Command-line interface for offline schematic conversion through the Circuit Model."""

import argparse
from pathlib import Path
from typing import Optional, Sequence

from . import ltspice_to_plecs, parse_ltspice, parse_plecs, plecs_to_ltspice, plecs_to_spice


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="pyplecs-convert",
        description="Convert a PLECS schematic offline to SPICE and/or LTspice, or an LTspice schematic to PLECS.",
    )
    parser.add_argument("source_file", type=Path, help="a .plecs schematic, or a .asc schematic for --format plecs")
    parser.add_argument("--format", choices=("cir", "asc", "all", "plecs"), default="cir", dest="format")
    parser.add_argument("-o", "--output", type=Path, default=Path("."))
    parser.add_argument(
        "--probe",
        action="append",
        default=[],
        metavar="COMPONENT:SIGNAL",
        help="with --format plecs: wire a PLECS probe signal to the model output, e.g. 'C1:Capacitor voltage'",
    )
    arguments = parser.parse_args(argv)

    try:
        output_dir = arguments.output
        if output_dir.suffix and arguments.format != "all":
            output_file = output_dir
            output_dir = output_file.parent
        else:
            output_file = None
        output_dir.mkdir(parents=True, exist_ok=True)

        if arguments.format == "plecs":
            circuit = parse_ltspice(arguments.source_file)
            probes = [tuple(item.split(":", 1)) for item in arguments.probe]
            if any(len(probe) != 2 for probe in probes):
                raise ValueError("--probe expects COMPONENT:SIGNAL")
            destination = output_file if output_file is not None else output_dir / f"{circuit.name}.plecs"
            ltspice_to_plecs(circuit, destination, probes=probes)
            return 0

        circuit = parse_plecs(arguments.source_file)
        if arguments.format in {"cir", "all"}:
            destination = output_file if output_file is not None else output_dir / f"{circuit.name}.cir"
            plecs_to_spice(circuit, destination)
        if arguments.format in {"asc", "all"}:
            destination = output_file if output_file is not None else output_dir / f"{circuit.name}.asc"
            plecs_to_ltspice(circuit, destination)
    except (OSError, ValueError) as error:
        parser.exit(2, f"pyplecs-convert: error: {error}\n")
    return 0
