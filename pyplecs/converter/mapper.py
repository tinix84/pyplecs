"""Map Circuit Model component types to SPICE/LTspice primitives."""

import re
from dataclasses import dataclass
from typing import Optional

from .circuit import Component


@dataclass(frozen=True)
class SpiceMapping:
    """Format-neutral SPICE mapping consumed by both emitters."""

    prefix: str
    symbol: str
    value_parameter: Optional[str] = None
    initial_parameter: Optional[str] = None
    model_kind: Optional[str] = None


COMPONENT_MAPPINGS = {
    "DCVoltageSource": SpiceMapping("V", "voltage", "V"),
    "Resistor": SpiceMapping("R", "res", "R"),
    "Capacitor": SpiceMapping("C", "cap", "C", "v_init"),
    "Inductor": SpiceMapping("L", "ind", "L", "i_init"),
    "Mosfet": SpiceMapping("S", "sw", model_kind="switch"),
    "Diode": SpiceMapping("D", "diode", model_kind="diode"),
}


def map_component(component: Component) -> Optional[SpiceMapping]:
    """Return the explicit mapping for one supported PLECS component type."""
    return COMPONENT_MAPPINGS.get(component.type)


def spice_instance_name(component: Component, mapping: SpiceMapping) -> str:
    """Return a stable SPICE element name with the required type prefix."""
    sanitized = sanitize_identifier(component.name)
    if sanitized.upper().startswith(mapping.prefix) and len(sanitized) > 1:
        return sanitized
    return f"{mapping.prefix}_{sanitized}"


def sanitize_identifier(value: str) -> str:
    """Make a stable identifier accepted by SPICE and LTspice."""
    sanitized = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    return sanitized or "unnamed"


def to_spice_operators(value: str) -> str:
    """Translate a PLECS (MATLAB-style) expression into SPICE operators.

    PLECS ``^`` is power; in SPICE and LTspice ``^`` is boolean XOR, so a
    verbatim ``Ro=Vo_ref^2/Po`` silently evaluates to the wrong load. The
    converter acceptance pack exposed this on the canonical buck (#20).
    ``**`` is folded to ``^`` first so the translation is idempotent.
    """
    return value.replace("**", "^").replace("^", "**")


def spice_expression(value: Optional[str], default: str = "0") -> str:
    """Wrap symbolic PLECS values as SPICE expressions; leave literals bare."""
    if value is None or not value.strip():
        return default
    stripped = value.strip()
    if re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", stripped):
        return stripped
    if stripped.startswith("{") and stripped.endswith("}"):
        return to_spice_operators(stripped)
    return f"{{{to_spice_operators(stripped)}}}"


def model_name(component: Component, mapping: SpiceMapping) -> str:
    suffix = sanitize_identifier(component.name).upper()
    if mapping.model_kind == "switch":
        return f"SW_{suffix}"
    if mapping.model_kind == "diode":
        return f"DMOD_{suffix}"
    raise ValueError(f"Component '{component.name}' does not use a SPICE model")
