"""Public, tool-neutral Circuit Model interchange seam."""

from dataclasses import dataclass, field

Point = tuple[int, int]
"""One schematic coordinate, Circuit Model convention: y grows downward, unit is PLECS px."""


@dataclass(frozen=True)
class Pin:
    """One numbered terminal on a named component."""

    component: str
    terminal: int

    def __post_init__(self) -> None:
        if not self.component:
            raise ValueError("Circuit pin component name must not be empty")
        if self.terminal < 1:
            raise ValueError("Circuit pin terminals are one-based")


@dataclass
class Component:
    """One tool-neutral circuit component parsed from a foreign format.

    ``position`` is the component's body centre in Circuit Model schematic coordinates
    (the PLECS convention: y grows downward, unit is PLECS px).
    """

    name: str
    type: str
    position: tuple[int, int] = (0, 0)
    direction: str = "right"
    flipped: bool = False
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass
class Net:
    """One electrical connection shared by component pins.

    ``segments`` and ``pin_points`` are optional wire-drawing geometry in Circuit Model
    schematic coordinates (see ``Component.position``): ``segments`` are the wire pieces
    of this net, ``pin_points`` is where each pin attaches to them. Both default empty for
    formats without layout; every parser/emitter that ignores them keeps working.
    """

    name: str
    pins: list[Pin] = field(default_factory=list)
    segments: list[tuple[Point, Point]] = field(default_factory=list)
    pin_points: dict[Pin, Point] = field(default_factory=dict)


@dataclass
class Circuit:
    """The single public interchange shape consumed by every emitter."""

    name: str
    components: list[Component] = field(default_factory=list)
    nets: list[Net] = field(default_factory=list)
    raw_params: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        component_names = [component.name for component in self.components]
        if len(component_names) != len(set(component_names)):
            raise ValueError("Circuit component names must be unique")
        net_names = [net.name for net in self.nets]
        if len(net_names) != len(set(net_names)):
            raise ValueError("Circuit net names must be unique")

        known_components = set(component_names)
        for net in self.nets:
            if len(net.pins) != len(set(net.pins)):
                raise ValueError(f"Circuit net '{net.name}' contains duplicate pins")
            unknown = [pin.component for pin in net.pins if pin.component not in known_components]
            if unknown:
                raise ValueError(
                    f"Circuit net '{net.name}' references unknown component(s): {', '.join(sorted(set(unknown)))}"
                )
            stray_pin_points = [pin for pin in net.pin_points if pin not in net.pins]
            if stray_pin_points:
                raise ValueError(
                    f"Circuit net '{net.name}' has pin_points for pin(s) not in its pins: {stray_pin_points}"
                )
