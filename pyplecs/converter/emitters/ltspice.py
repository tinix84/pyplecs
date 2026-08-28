"""Emit an LTspice ``.asc`` schematic from the Circuit Model."""

from ..circuit import Circuit, Component
from ..mapper import (
    map_component,
    model_name,
    sanitize_identifier,
    spice_expression,
    spice_instance_name,
    spice_parameter_value,
)

SCALE_FACTOR = 2


def emit_ltspice(circuit: Circuit) -> str:
    """Return an LTspice schematic using snapped PLECS positions."""
    positions = _component_positions(circuit.components)
    lines = ["Version 4", "SHEET 1 880 680"]

    for net in circuit.nets:
        connected_positions = [positions[pin.component] for pin in net.pins if pin.component in positions]
        if len(connected_positions) < 2:
            continue
        origin = connected_positions[0]
        for destination in connected_positions[1:]:
            lines.append(f"WIRE {origin[0]} {origin[1]} {destination[0]} {destination[1]}")

    model_directives: list[str] = []
    warning_index = 0
    for component in circuit.components:
        mapping = map_component(component)
        if mapping is None:
            if component.type != "Ground":
                y = 320 + warning_index * 24
                warning_index += 1
                lines.append(f"TEXT -32 {y} Left 2 ; WARNING unsupported {component.name} ({component.type})")
            continue
        x, y = positions[component.name]
        lines.append(f"SYMBOL {mapping.symbol} {x} {y} {_orientation(component)}")
        lines.append(f"SYMATTR InstName {spice_instance_name(component, mapping)}")
        if mapping.model_kind:
            value = model_name(component, mapping)
        else:
            value = spice_expression(component.parameters.get(mapping.value_parameter or ""))
        lines.append(f"SYMATTR Value {value}")

        if mapping.initial_parameter:
            initial_value = component.parameters.get(mapping.initial_parameter)
            if initial_value not in (None, ""):
                lines.append(f"SYMATTR SpiceLine ic={spice_expression(initial_value)}")
        if mapping.model_kind == "switch":
            ron = spice_expression(component.parameters.get("Ron"), "1m")
            model_directives.append(f".model {value} SW(Ron={ron} Roff=1e9 Vt=0.5 Vh=0)")
        elif mapping.model_kind == "diode":
            vf = spice_expression(component.parameters.get("Vf"), "0")
            ron = spice_expression(component.parameters.get("Ron"), "1m")
            model_directives.append(f".model {value} D(Vfwd={vf} Ron={ron})")

    directive_y = 300
    for name, value in circuit.raw_params.items():
        lines.append(f"TEXT -32 {directive_y} Left 2 !.param {sanitize_identifier(name)}={spice_parameter_value(value)}")
        directive_y += 24
    for directive in model_directives:
        lines.append(f"TEXT -32 {directive_y} Left 2 !{directive}")
        directive_y += 24
    tran_value = spice_expression(circuit.raw_params.get("T_sim"), "1m")
    lines.append(f"TEXT -32 {directive_y} Left 2 !.tran {tran_value}")
    return "\n".join(lines) + "\n"


def _component_positions(components: list[Component]) -> dict[str, tuple[int, int]]:
    positions: dict[str, tuple[int, int]] = {}
    fallback_index = 0
    for component in components:
        if component.position == (0, 0):
            x = 96 + fallback_index * 96
            y = 96
            fallback_index += 1
        else:
            x = _snap(component.position[0] * SCALE_FACTOR)
            y = _snap(component.position[1] * SCALE_FACTOR)
        positions[component.name] = (x, y)
    return positions


def _snap(value: int) -> int:
    return round(value / 16) * 16


def _orientation(component: Component) -> str:
    rotations = {"right": 0, "down": 90, "left": 180, "up": 270}
    prefix = "M" if component.flipped else "R"
    return f"{prefix}{rotations.get(component.direction.lower(), 0)}"
