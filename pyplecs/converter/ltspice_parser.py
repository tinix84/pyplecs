"""Parse an LTspice ``.asc`` schematic into the Circuit Model (ADR-0001: one seam, every format an adapter).

Only the symbols the SPICE mapper already knows are accepted; anything else is
a hard failure, because a silently dropped component is a wrong circuit.
Pin geometry comes from LTspice's own symbol library (``lib/sym/*.asy``); the
orientation transform (rotate, then mirror) was verified against LTspice 26's
netlister for all eight orientations.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

from .circuit import Circuit, Component, Net, Pin
from .mapper import COMPONENT_MAPPINGS

# Pin offsets relative to the symbol origin at R0, in SpiceOrder (lib/sym/*.asy).
SYMBOL_PINS: dict[str, tuple[tuple[int, int], ...]] = {
    "voltage": ((0, 16), (0, 96)),
    "res": ((16, 16), (16, 96)),
    "ind": ((16, 16), (16, 96)),
    "cap": ((16, 0), (16, 64)),
    "diode": ((16, 0), (16, 64)),
}

# LTspice symbol → PLECS component type, the inverse of the SPICE mapper table.
SYMBOL_TYPES = {mapping.symbol: plecs_type for plecs_type, mapping in COMPONENT_MAPPINGS.items() if mapping.symbol in SYMBOL_PINS}

_SUFFIXES = {"t": "e12", "g": "e9", "meg": "e6", "k": "e3", "m": "e-3", "u": "e-6", "µ": "e-6", "n": "e-9", "p": "e-12", "f": "e-15"}
_SUFFIXED_NUMBER = re.compile(r"(?<![\w.])(\d+\.?\d*|\.\d+)(meg|[tgkmunpfµ])(?![\w])", re.IGNORECASE)


class LtspiceParseError(ValueError):
    """The schematic cannot become a Circuit Model without guessing."""


def parse_ltspice(path: str | Path) -> Circuit:
    path = Path(path)
    return parse_ltspice_text(path.read_text(encoding="utf-8", errors="replace"), name=path.stem)


def parse_ltspice_text(text: str, *, name: str = "circuit") -> Circuit:
    if "\x00" in text:
        raise LtspiceParseError("schematic looks UTF-16 encoded; save it as ASCII/UTF-8")
    wires: list[tuple[tuple[int, int], tuple[int, int]]] = []
    flags: dict[tuple[int, int], str] = {}
    symbols: list[dict] = []
    directives: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        fields = line.split()
        if not fields:
            continue
        keyword = fields[0]
        if keyword == "WIRE" and len(fields) == 5:
            x1, y1, x2, y2 = map(int, fields[1:5])
            wires.append(((x1, y1), (x2, y2)))
        elif keyword == "FLAG" and len(fields) >= 4:
            flags[(int(fields[1]), int(fields[2]))] = fields[3]
        elif keyword == "SYMBOL" and len(fields) >= 5:
            symbols.append({"symbol": fields[1].split("\\")[-1].split("/")[-1].lower(), "x": int(fields[2]), "y": int(fields[3]), "orient": fields[4], "attrs": {}})
        elif keyword == "SYMATTR" and symbols and len(fields) >= 3:
            symbols[-1]["attrs"][fields[1]] = line.split(None, 2)[2]
        elif keyword == "TEXT":
            match = re.search(r"\s!(.*)$", raw_line)
            if match:
                directives.append(match.group(1).strip())

    components: list[Component] = []
    pin_points: list[tuple[Pin, tuple[int, int]]] = []
    for index, symbol in enumerate(symbols):
        plecs_type = SYMBOL_TYPES.get(symbol["symbol"])
        if plecs_type is None:
            raise LtspiceParseError(f"unsupported LTspice symbol '{symbol['symbol']}' (supported: {', '.join(sorted(SYMBOL_TYPES))})")
        attrs = symbol["attrs"]
        component_name = attrs.get("InstName", f"{symbol['symbol']}{index + 1}")
        mapping = COMPONENT_MAPPINGS[plecs_type]
        parameters: dict[str, str] = {}
        if mapping.value_parameter and "Value" in attrs:
            parameters[mapping.value_parameter] = to_plecs_expression(attrs["Value"])
        if mapping.initial_parameter:
            initial = re.search(r"\bic=(\S+)", attrs.get("SpiceLine", ""))
            if initial:
                parameters[mapping.initial_parameter] = to_plecs_expression(initial.group(1))
        absolute_pins = [
            (symbol["x"] + dx, symbol["y"] + dy)
            for dx, dy in (transform_offset(symbol["orient"], *offset) for offset in SYMBOL_PINS[symbol["symbol"]])
        ]
        p1, p2 = absolute_pins
        components.append(
            Component(
                name=component_name,
                type=plecs_type,
                position=_scale(((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)),
                direction=_direction(p1, p2),
                flipped=False,
                parameters=parameters,
            )
        )
        for terminal, point in enumerate(absolute_pins, start=1):
            pin_points.append((Pin(component_name, terminal), point))

    nets = _build_nets(wires, flags, pin_points)
    raw_params = _parameters(directives)
    return Circuit(name=name, components=components, nets=nets, raw_params=raw_params)


def _scale(point: tuple[float, float]) -> tuple[int, int]:
    """LTspice (grid 16) → Circuit Model/PLECS (grid 10) schematic coordinates."""
    x, y = point
    return (round(x * 5 / 8), round(y * 5 / 8))


def _direction(p1: tuple[int, int], p2: tuple[int, int]) -> str:
    """PLECS Direction names the side terminal 1 (``p1``) faces, derived from the two pin points."""
    if p1[1] < p2[1]:
        return "up"
    if p1[1] > p2[1]:
        return "down"
    if p1[0] < p2[0]:
        return "left"
    return "right"


def transform_offset(orient: str, x: int, y: int) -> tuple[int, int]:
    """LTspice symbol placement: rotate clockwise by the R/M angle, then mirror in x for M."""
    kind, degrees = orient[0].upper(), int(orient[1:] or 0)
    for _ in range((degrees // 90) % 4):
        x, y = -y, x
    if kind == "M":
        x = -x
    return x, y


def to_plecs_expression(value: str) -> str:
    """LTspice value → PLECS initialization expression: braces off, unit suffixes to exponents, ``**`` to ``^``."""
    stripped = value.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        stripped = stripped[1:-1].strip()
    stripped = stripped.replace("**", "^")
    return _SUFFIXED_NUMBER.sub(lambda m: f"{m.group(1)}{_SUFFIXES[m.group(2).lower()]}", stripped)


def _parameters(directives: Iterable[str]) -> dict[str, str]:
    raw_params: dict[str, str] = {}
    tran: Optional[list[str]] = None
    for directive in directives:
        fields = directive.split()
        keyword = fields[0].lower()
        if keyword == ".param":
            for assignment in re.findall(r"(\w+)\s*=\s*(\{[^}]*\}|\S+)", directive[len(".param"):]):
                raw_params[assignment[0]] = to_plecs_expression(assignment[1])
        elif keyword == ".tran":
            tran = fields[1:]
    if tran is None:
        raise LtspiceParseError("schematic has no .tran directive; PLECS needs a simulation span")
    # .tran <tstop> | .tran <tstep> <tstop> [tstart [tmaxstep]] [uic]
    numeric = [field for field in tran if field.lower() != "uic"]
    tstop = numeric[0] if len(numeric) == 1 else numeric[1]
    raw_params.setdefault("T_sim", to_plecs_expression(tstop))
    if len(numeric) >= 4:
        raw_params.setdefault("max_step", to_plecs_expression(numeric[3]))
    else:
        raw_params.setdefault("max_step", "T_sim/1000")
    return raw_params


def _build_nets(
    wires: list[tuple[tuple[int, int], tuple[int, int]]],
    flags: dict[tuple[int, int], str],
    pin_points: list[tuple[Pin, tuple[int, int]]],
) -> list[Net]:
    parent: dict[tuple[int, int], tuple[int, int]] = {}

    def find(point):
        parent.setdefault(point, point)
        while parent[point] != point:
            parent[point] = parent[parent[point]]
            point = parent[point]
        return point

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for start, end in wires:
        union(start, end)
    points = [point for _, point in pin_points] + list(flags)
    for point in points:  # a pin or label lying on a wire (endpoint or interior) joins it
        for start, end in wires:
            if _on_segment(point, start, end):
                union(point, start)
    for a, b in zip(points, points[1:]):  # coincident pins/labels connect directly
        if a == b:
            union(a, b)

    names: dict[tuple[int, int], str] = {}
    for point, label in flags.items():
        root = find(point)
        if label == "0" or names.get(root) is None:
            names[root] = label
    nets: dict[tuple[int, int], Net] = {}
    order: list[tuple[int, int]] = []
    counter = 1
    for pin, point in pin_points:
        root = find(point)
        if root not in nets:
            name = names.get(root)
            if name is None:
                name = f"N{counter:03d}"
                counter += 1
            nets[root] = Net(name=name)
            order.append(root)
        nets[root].pins.append(pin)
        nets[root].pin_points[pin] = _scale(point)
    for start, end in wires:  # a wire whose root owns no pin belongs to no net; drop it
        root = find(start)
        if root in nets:
            nets[root].segments.append((_scale(start), _scale(end)))
    return [nets[root] for root in order]


def _on_segment(point, start, end) -> bool:
    (px, py), (x1, y1), (x2, y2) = point, start, end
    if (x2 - x1) * (py - y1) != (y2 - y1) * (px - x1):
        return False
    return min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2)


__all__ = ["LtspiceParseError", "SYMBOL_PINS", "SYMBOL_TYPES", "parse_ltspice", "parse_ltspice_text", "to_plecs_expression", "transform_offset"]
