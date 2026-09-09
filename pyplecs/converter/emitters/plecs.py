"""Deterministically emit a runnable PLECS schematic from Circuit Model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from ..circuit import Circuit, Component, Net, Pin, Point


@dataclass(frozen=True)
class PlecsProbeSignal:
    """One signal selected by a generated PLECS Probe block."""

    component: str
    signal: str


_PARAMETER_DEFAULTS: dict[str, tuple[tuple[str, str], ...]] = {
    "DCVoltageSource": (("V", "1"),),
    "Resistor": (("R", "1"),),
    "Capacitor": (("C", "100e-6"), ("v_init", "0")),
    "Inductor": (("L", "1e-3"), ("i_init", "0")),
    "Mosfet": (
        ("Ron", "0"),
        ("init", "0"),
        ("thermal", ""),
        ("Rth", "0"),
        ("T_init", "0"),
    ),
    "Diode": (
        ("Vf", "0"),
        ("Ron", "0"),
        ("thermal", ""),
        ("Rth", "0"),
        ("T_init", "0"),
    ),
    "PulseGenerator": (
        ("Hi", "1"),
        ("Lo", "0"),
        ("f", "1e3"),
        ("DutyCycle", "0.5"),
        ("Delay", "0"),
        ("DataType", "10"),
    ),
}


def emit_plecs(
    circuit: Circuit,
    *,
    probes: Sequence[PlecsProbeSignal] = (),
) -> str:
    """Return stable ASCII PLECS content for one Circuit Model."""
    components = sorted(circuit.components, key=lambda component: component.name)
    nets = sorted(circuit.nets, key=lambda net: net.name)
    _validate_graph(components, nets)

    lines = [
        "Plecs {",
        f'  Name          "{_quoted(circuit.name)}"',
        '  Version       "4.7"',
        '  CircuitModel  "ContStateSpace"',
        '  StartTime     "0.0"',
        '  TimeSpan      "T_sim"',
        '  Timeout       ""',
        '  Solver        "radau"',
        '  MaxStep       "max_step"',
        '  InitStep      "-1"',
        '  FixedStep     "1e-3"',
        '  Refine        "1"',
        '  ZCStepSize    "1e-9"',
        '  RelTol        "1e-3"',
        '  AbsTol        "-1"',
        '  TurnOnThreshold "1"',
        f'  InitializationCommands "{_initialization(circuit.raw_params)}"',
        '  InitialState  "1"',
        '  SystemState   ""',
    ]
    if probes:
        lines.extend(["  Terminal {", "    Type          Output", '    Index         "1"', "  }"])
    lines.extend(
        [
            "  Schematic {",
            "    Location      [0, 0; 900, 600]",
            "    ZoomFactor    1",
            "    SliderPosition [0, 0]",
            "    ShowBrowser   off",
            "    BrowserWidth  100",
        ]
    )
    for component in components:
        lines.extend(_component_block(component))
    if probes:
        lines.extend(_probe_block(probes))
        lines.extend(_output_block())
    component_types = {component.name: component.type for component in components}
    for net in nets:
        lines.extend(_connection_block(net, component_types))
    if probes:
        lines.extend(
            [
                "    Connection {",
                "      Type          Signal",
                '      SrcComponent  "__tas_probe"',
                "      SrcTerminal   1",
                '      DstComponent  "__tas_output"',
                "      DstTerminal   1",
                "    }",
            ]
        )
    lines.extend(["  }", "}"])
    return "\n".join(lines) + "\n"


def _component_block(component: Component) -> list[str]:
    lines = [
        "    Component {",
        f"      Type          {component.type}",
        f'      Name          "{_quoted(component.name)}"',
        "      Show          on",
        f"      Position      [{component.position[0]}, {component.position[1]}]",
        f"      Direction     {component.direction}",
        f"      Flipped       {'on' if component.flipped else 'off'}",
        "      LabelPosition south",
    ]
    for variable, default in _PARAMETER_DEFAULTS.get(component.type, ()):
        value = component.parameters.get(variable, default)
        lines.extend(
            [
                "      Parameter {",
                f'        Variable      "{_quoted(variable)}"',
                f'        Value         "{_quoted(value)}"',
                "        Show          off",
                "      }",
            ]
        )
    lines.append("    }")
    return lines


def _probe_block(probes: Sequence[PlecsProbeSignal]) -> list[str]:
    lines = [
        "    Component {",
        "      Type          PlecsProbe",
        '      Name          "__tas_probe"',
        "      Show          off",
        "      Position      [720, 120]",
        "      Direction     right",
        "      Flipped       off",
        "      LabelPosition south",
    ]
    for probe in probes:
        lines.extend(
            [
                "      Probe {",
                f'        Component     "{_quoted(probe.component)}"',
                '        Path          ""',
                f'        Signals       {{"{_quoted(probe.signal)}"}}',
                "      }",
            ]
        )
    lines.append("    }")
    return lines


def _output_block() -> list[str]:
    return [
        "    Component {",
        "      Type          Output",
        '      Name          "__tas_output"',
        "      Show          on",
        "      Position      [820, 120]",
        "      Direction     right",
        "      Flipped       off",
        "      LabelPosition south",
        "      Parameter {",
        '        Variable      "Index"',
        '        Value         "1"',
        "        Show          on",
        "      }",
        "      Parameter {",
        '        Variable      "Width"',
        '        Value         "-1"',
        "        Show          off",
        "      }",
        "    }",
    ]


def _connection_block(net: Net, component_types: Mapping[str, str]) -> list[str]:
    pins = sorted(net.pins, key=lambda pin: (pin.component, pin.terminal))
    signal = any(
        component_types.get(pin.component) == "PulseGenerator"
        or (component_types.get(pin.component) == "Mosfet" and pin.terminal == 3)
        for pin in pins
    )
    if net.segments and all(pin in net.pin_points for pin in pins):
        return _routed_connection_block(net, pins, signal)
    source = pins[0]
    lines = [
        "    Connection {",
        f"      Type          {'Signal' if signal else 'Wire'}",
        f'      SrcComponent  "{_quoted(source.component)}"',
        f"      SrcTerminal   {source.terminal}",
    ]
    if len(pins) == 2:
        lines.extend(
            [
                f'      DstComponent  "{_quoted(pins[1].component)}"',
                f"      DstTerminal   {pins[1].terminal}",
            ]
        )
    else:
        for pin in pins[1:]:
            lines.extend(
                [
                    "      Branch {",
                    f'        DstComponent  "{_quoted(pin.component)}"',
                    f"        DstTerminal   {pin.terminal}",
                    "      }",
                ]
            )
    lines.append("    }")
    return lines


def _routed_connection_block(net: Net, pins: list[Pin], signal: bool) -> list[str]:
    """Route ``net``'s Connection block along its drawn wires instead of a flat pin list (#94)."""
    source = pins[0]
    attach: dict[Point, list[Pin]] = {}
    for pin in pins:
        attach.setdefault(net.pin_points[pin], []).append(pin)

    protected = set(net.pin_points.values())
    adjacency = _segment_graph(net.segments, protected)
    _prune_dangling_stubs(adjacency, protected)

    source_point = net.pin_points[source]
    tree_children: dict[Point, list[Point]] = {}
    reachable: set[Point] = set()
    if source_point in adjacency:
        _build_spanning_tree(adjacency, source_point, None, reachable, tree_children)

    lines = [
        "    Connection {",
        f"      Type          {'Signal' if signal else 'Wire'}",
        f'      SrcComponent  "{_quoted(source.component)}"',
        f"      SrcTerminal   {source.terminal}",
    ]
    lines.extend(_walk_net(source_point, None, [source_point], tree_children, attach, source, 6))
    for pin in pins[1:]:
        if net.pin_points[pin] not in reachable:
            lines.extend(_branch_dst(pin, 6))
    lines.append("    }")
    return lines


def _segment_graph(segments: list[tuple[Point, Point]], extra_nodes: set) -> dict[Point, set]:
    """Build the wire graph: nodes are segment endpoints plus pin attach points lying on them."""
    all_points = set(extra_nodes)
    for start, end in segments:
        all_points.add(start)
        all_points.add(end)
    adjacency: dict[Point, set] = {}
    for start, end in segments:
        on_segment = [point for point in all_points if _on_segment(point, start, end)]
        on_segment.sort(key=lambda p: (p[0] - start[0]) * (end[0] - start[0]) + (p[1] - start[1]) * (end[1] - start[1]))
        for a, b in zip(on_segment, on_segment[1:]):
            adjacency.setdefault(a, set()).add(b)
            adjacency.setdefault(b, set()).add(a)
    return adjacency


def _on_segment(point: Point, start: Point, end: Point) -> bool:
    (px, py), (x1, y1), (x2, y2) = point, start, end
    if (x2 - x1) * (py - y1) != (y2 - y1) * (px - x1):
        return False
    return min(x1, x2) <= px <= max(x1, x2) and min(y1, y2) <= py <= max(y1, y2)


def _prune_dangling_stubs(adjacency: dict[Point, set], protected: set) -> None:
    """Repeatedly drop degree-<=1 nodes that carry no pin (a dangling body/ground-flag stub)."""
    changed = True
    while changed:
        changed = False
        for node in list(adjacency):
            neighbors = adjacency.get(node)
            if neighbors is not None and len(neighbors) <= 1 and node not in protected:
                for neighbor in neighbors:
                    adjacency[neighbor].discard(node)
                del adjacency[node]
                changed = True


def _build_spanning_tree(
    adjacency: dict[Point, set],
    node: Point,
    parent: Point | None,
    visited: set,
    tree_children: dict[Point, list[Point]],
) -> None:
    visited.add(node)
    children = [
        neighbor for neighbor in sorted(adjacency.get(node, ())) if neighbor != parent and neighbor not in visited
    ]
    for child in children:
        visited.add(child)
    tree_children[node] = children
    for child in children:
        _build_spanning_tree(adjacency, child, node, visited, tree_children)


def _walk_net(
    node: Point,
    prev: Point | None,
    run: list[Point],
    tree_children: dict[Point, list[Point]],
    attach: Mapping[Point, list[Pin]],
    exclude_pin: Pin | None,
    indent: int,
) -> list[str]:
    """Emit Points/Dst/Branch lines walking the spanning tree from ``node`` onward (plan step 4)."""
    while True:
        pins_here = [pin for pin in attach.get(node, ()) if pin != exclude_pin]
        children = tree_children.get(node, [])

        if not pins_here and not children:
            return []

        if not pins_here and len(children) == 1:
            child = children[0]
            if prev is not None and _run_direction(prev, node) != _run_direction(node, child):
                run.append(node)
            prev, node = node, child
            continue

        if len(pins_here) == 1 and not children:
            run.append(node)
            return _points_line(run, indent) + _dst_lines(pins_here[0], indent)

        run.append(node)
        lines = _points_line(run, indent)
        for pin in pins_here:
            lines.extend(_branch_dst(pin, indent))
        for child in children:
            lines.extend(_branch_child(child, node, tree_children, attach, indent))
        return lines


def _branch_child(
    child: Point,
    parent: Point,
    tree_children: dict[Point, list[Point]],
    attach: Mapping[Point, list[Pin]],
    indent: int,
) -> list[str]:
    inner_indent = indent + 2
    body = _walk_net(child, parent, [], tree_children, attach, None, inner_indent)
    return [f"{' ' * indent}Branch {{", *body, f"{' ' * indent}}}"]


def _branch_dst(pin: Pin, indent: int) -> list[str]:
    inner_indent = indent + 2
    return [f"{' ' * indent}Branch {{", *_dst_lines(pin, inner_indent), f"{' ' * indent}}}"]


def _dst_lines(pin: Pin, indent: int) -> list[str]:
    return [
        f'{" " * indent}DstComponent  "{_quoted(pin.component)}"',
        f"{' ' * indent}DstTerminal   {pin.terminal}",
    ]


def _points_line(run: list[Point], indent: int) -> list[str]:
    if not run:
        return []
    points = "; ".join(f"{x}, {y}" for x, y in run)
    return [f"{' ' * indent}Points        [{points}]"]


def _run_direction(a: Point, b: Point) -> tuple[int, int]:
    def sign(v: int) -> int:
        return (v > 0) - (v < 0)

    return (sign(b[0] - a[0]), sign(b[1] - a[1]))


def _validate_graph(components: Iterable[Component], nets: Iterable[Net]) -> None:
    supported = set(_PARAMETER_DEFAULTS) | {"Voltmeter"}
    unsupported = sorted(
        component.type for component in components if component.type not in supported
    )
    if unsupported:
        raise ValueError(f"Unsupported PLECS component type(s): {', '.join(unsupported)}")
    for net in nets:
        if len(net.pins) < 2:
            raise ValueError(f"PLECS net '{net.name}' requires at least two pins")


def _initialization(parameters: Mapping[str, str]) -> str:
    return "".join(
        f"{name} = {value};\\n" for name, value in sorted(parameters.items())
    )


def _quoted(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


__all__ = ["PlecsProbeSignal", "emit_plecs"]
