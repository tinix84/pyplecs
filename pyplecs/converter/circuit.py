"""Public, tool-neutral Circuit Model interchange seam."""

from dataclasses import dataclass, field


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
    """One tool-neutral circuit component parsed from a foreign format."""

    name: str
    type: str
    position: tuple[int, int] = (0, 0)
    direction: str = "right"
    flipped: bool = False
    parameters: dict[str, str] = field(default_factory=dict)


@dataclass
class Net:
    """One electrical connection shared by component pins."""

    name: str
    pins: list[Pin] = field(default_factory=list)


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
