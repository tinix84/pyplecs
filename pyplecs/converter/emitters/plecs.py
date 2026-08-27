"""Deterministically emit a runnable PLECS schematic from Circuit Model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from ..circuit import Circuit, Component, Net


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
