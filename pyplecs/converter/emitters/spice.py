"""Emit a SPICE ``.cir`` netlist from the Circuit Model."""

from typing import Optional

from ..circuit import Circuit, Component, Pin
from ..mapper import (
    SpiceMapping,
    map_component,
    model_name,
    sanitize_identifier,
    spice_expression,
    spice_instance_name,
    spice_parameter_value,
)


def emit_spice(circuit: Circuit) -> str:
    """Return a deterministic SPICE netlist for one Circuit Model."""
    pin_nets = {pin: net.name for net in circuit.nets for pin in net.pins}
    lines = [f"* {circuit.name} -- converted from PLECS"]
    for name, value in circuit.raw_params.items():
        lines.append(f".param {sanitize_identifier(name)}={spice_parameter_value(value)}")

    model_lines: list[str] = []
    gate_lines: list[str] = []
    for component in circuit.components:
        mapping = map_component(component)
        if mapping is None:
            if component.type != "Ground":
                lines.append(f"* WARNING: unsupported PLECS component {component.name} ({component.type})")
            continue
        element_line, model_line, gate_line = _emit_component(component, mapping, pin_nets)
        if element_line is None:
            lines.append(f"* WARNING: component {component.name} is missing an electrical terminal")
            continue
        lines.append(element_line)
        if model_line is not None:
            model_lines.append(model_line)
        if gate_line is not None:
            gate_lines.append(gate_line)

    lines.extend(gate_lines)
    lines.extend(model_lines)
    tran_value = spice_expression(circuit.raw_params.get("T_sim"), "1m")
    lines.extend([f".tran {tran_value}", ".end"])
    return "\n".join(lines) + "\n"


def _emit_component(
    component: Component,
    mapping: SpiceMapping,
    pin_nets: dict[Pin, str],
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    first = pin_nets.get(Pin(component.name, 1))
    second = pin_nets.get(Pin(component.name, 2))
    if first is None or second is None:
        return None, None, None

    instance_name = spice_instance_name(component, mapping)
    if mapping.model_kind == "switch":
        gate_node = f"N_GATE_{sanitize_identifier(component.name)}"
        switch_model = model_name(component, mapping)
        ron = spice_expression(component.parameters.get("Ron"), "1m")
        model_line = f".model {switch_model} SW(Ron={ron} Roff=1e9 Vt=0.5 Vh=0)"
        gate_name = f"V_GATE_{sanitize_identifier(component.name)}"
        gate_line = f"{gate_name} {gate_node} 0 PULSE(0 1 0 1n 1n {{D/fs}} {{1/fs}})"
        return (
            f"{instance_name} {first} {second} {gate_node} 0 {switch_model}",
            model_line,
            gate_line,
        )
    if mapping.model_kind == "diode":
        diode_model = model_name(component, mapping)
        vf = spice_expression(component.parameters.get("Vf"), "0")
        ron = spice_expression(component.parameters.get("Ron"), "1m")
        model_line = f".model {diode_model} D(Vfwd={vf} Ron={ron})"
        return f"{instance_name} {first} {second} {diode_model}", model_line, None

    value = spice_expression(component.parameters.get(mapping.value_parameter or ""))
    initial = ""
    if mapping.initial_parameter:
        initial_value = component.parameters.get(mapping.initial_parameter)
        if initial_value not in (None, ""):
            initial = f" ic={spice_expression(initial_value)}"
    return f"{instance_name} {first} {second} {value}{initial}", None, None
