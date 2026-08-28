"""Canonical topology document: what a PLECS schematic *is*, minus how it is drawn.

The document is a persisted, inspectable JSON text whose digest is the
``topology_id`` of a Cache Record. It is invariant to layout and cosmetics and
to declaration order, and it never claims equality it cannot prove: any
construct the canonicalizer does not understand is folded in as normalized
bytes (so it causes a miss, never a wrong hit) and recorded in the coverage
section of the document.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

FORMAT = "pyplecs-topology/1"

# Fields on any Component block that only describe how it is drawn.
COSMETIC_COMPONENT_FIELDS = frozenset(
    {
        "Show",
        "Position",
        "Direction",
        "Flipped",
        "LabelPosition",
        "LabelAlign",
        "Frame",
        "MaskIconFrame",
        "MaskIconOpaque",
        "MaskIconRotates",
        "MaskDisplay",
        "MaskDisplayLang",
        "MaskDescription",
        "MaskHelp",
        "MaskType",
        # Scope / Display window state.
        "Location",
        "State",
        "SavedViews",
        "HeaderState",
        "PlotPalettes",
        "Axes",
        "TimeRange",
        "ScrollingMode",
        "SingleTimeAxis",
        "Open",
        "XAxisLabel",
        "ShowLegend",
        "Axis",
        "Fourier",
        # Nested schematic view state on subsystems.
        "ZoomFactor",
        "SliderPosition",
        "ShowBrowser",
        "BrowserWidth",
    }
)

# Fields on any Component block whose value changes what is simulated. They are
# kept verbatim in the node record.
STRUCTURAL_COMPONENT_FIELDS = frozenset(
    {
        "CommentOut",
        "SampleTime",
        "CodeGenTarget",
        "CodeGenDiscretizationMethod",
        "TreatAsAtomicUnit",
        "Configurations",
        "TerminalNames",
        "MaskInit",
        "MaskProbe",
        "Ts",
        "SampleLimit",
    }
)

# Fields the canonicalizer models explicitly rather than copying.
_MODELLED_COMPONENT_FIELDS = frozenset(
    {"Type", "Name", "Parameter", "Probe", "SrcComponent", "Terminal", "Schematic"}
)

# Parameter sub-fields that only affect the dialog, not the value.
_COSMETIC_PARAMETER_FIELDS = frozenset({"Show", "Prompt", "TabName"})

COSMETIC_SCHEMATIC_FIELDS = frozenset(
    {
        "Location",
        "ZoomFactor",
        "SliderPosition",
        "ShowBrowser",
        "BrowserWidth",
        "Annotation",
        "RectangleAnnotation",
    }
)

# Pure annotations: the node is dropped entirely.
ANNOTATION_TYPES = frozenset({"FreeText"})

_LOCAL_VISIBILITY = "1"


@dataclass
class Coverage:
    """Which regions of a schematic the canonicalizer understood."""

    nodes_total: int = 0
    nodes_degraded: int = 0
    connections_total: int = 0
    connections_degraded: int = 0
    degraded: list[dict[str, str]] = field(default_factory=list)

    def note(self, kind: str, name: str, reason: str) -> None:
        self.degraded.append({"kind": kind, "name": name, "reason": reason})

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes_total": self.nodes_total,
            "nodes_degraded": self.nodes_degraded,
            "connections_total": self.connections_total,
            "connections_degraded": self.connections_degraded,
            "degraded": sorted(self.degraded, key=lambda item: (item["kind"], item["name"], item["reason"])),
        }


@dataclass(frozen=True)
class TopologyDocument:
    """The canonical form of one schematic and its digest."""

    content: dict[str, Any]
    topology_id: str

    def to_json(self) -> str:
        return canonical_json(self.content)

    @property
    def coverage(self) -> dict[str, Any]:
        return self.content["coverage"]


def canonical_json(value: Any) -> str:
    """Deterministic text: sorted keys, ASCII only, LF line ends."""
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, default=str) + "\n"


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonicalize_document(document: dict[str, Any]) -> TopologyDocument:
    """Canonicalize a parsed ``.plecs`` document (the output of ``parse_plecs_text``)."""
    root = document.get("Plecs")
    if not isinstance(root, dict):
        raise ValueError("PLECS document must contain one top-level 'Plecs' block")
    schematic = root.get("Schematic")
    if not isinstance(schematic, dict):
        raise ValueError("PLECS document must contain a 'Schematic' block")
    return canonicalize_schematic(schematic, _blocks(root.get("Terminal")))


def canonicalize_schematic(schematic: dict[str, Any], terminals: list[dict[str, Any]]) -> TopologyDocument:
    coverage = Coverage()
    subsystems: dict[str, dict[str, Any]] = {}
    nodes: dict[str, dict[str, Any]] = {}
    teleports: dict[str, dict[str, list[str]]] = {"Goto": {}, "From": {}}

    for block in _blocks(schematic.get("Component")):
        component_type = str(block.get("Type", ""))
        name = block.get("Name")
        if component_type in ANNOTATION_TYPES or name is None:
            continue
        name = str(name)
        coverage.nodes_total += 1
        node = _node_record(block, component_type, name, coverage, subsystems)
        nodes[name] = node
        if component_type in teleports and node.get("degraded") is None:
            visibility = node["parameters"].get("Visibility", _LOCAL_VISIBILITY)
            tag = node["parameters"].get("Tag", "")
            if visibility == _LOCAL_VISIBILITY and tag:
                teleports[component_type].setdefault(tag, []).append(name)

    nets = _NetBuilder(coverage)
    for connection in _blocks(schematic.get("Connection")):
        nets.add_connection(connection)

    _collapse_teleports(nodes, nets, teleports, coverage)

    for key in schematic:
        if key in ("Component", "Connection") or key in COSMETIC_SCHEMATIC_FIELDS:
            continue
        coverage.note("schematic", key, "unrecognised schematic field")
        nodes.setdefault("", {"name": "", "type": "", "parameters": {}, "degraded": {}})
        nodes[""]["degraded"][key] = _normalized(schematic[key])

    content = {
        "format": FORMAT,
        "interface": [str(terminal.get("Type", "")) for terminal in terminals],
        "nodes": [nodes[name] for name in sorted(nodes)],
        "nets": nets.to_list(set(nodes)),
        "subsystems": subsystems,
        "coverage": coverage.to_dict(),
    }
    text = canonical_json(content)
    return TopologyDocument(content=content, topology_id=digest(text))


def _node_record(
    block: dict[str, Any],
    component_type: str,
    name: str,
    coverage: Coverage,
    subsystems: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    record: dict[str, Any] = {"name": name, "type": component_type, "parameters": {}}
    degraded: dict[str, Any] = {}

    for parameter in _blocks(block.get("Parameter")):
        variable = parameter.get("Variable")
        if variable is None:
            degraded[f"Parameter[{len(degraded)}]"] = _normalized(parameter)
            continue
        record["parameters"][str(variable)] = _parameter_value(parameter)

    if "SrcComponent" in block:
        record["library_path"] = str(block["SrcComponent"])
    if "Probe" in block:
        record["probes"] = sorted(
            (
                {
                    "component": str(probe.get("Component", "")),
                    "path": str(probe.get("Path", "")),
                    "signals": _normalized(probe.get("Signals", "")),
                }
                for probe in _blocks(block.get("Probe"))
            ),
            key=canonical_json,
        )
    if "Schematic" in block:
        child = canonicalize_schematic(_first_block(block["Schematic"]), _blocks(block.get("Terminal")))
        subsystems[child.topology_id] = child.content
        record["topology_id"] = child.topology_id
        record["interface"] = child.content["interface"]
    elif "Terminal" in block:
        record["interface"] = [str(terminal.get("Type", "")) for terminal in _blocks(block.get("Terminal"))]

    for key, value in block.items():
        if key in _MODELLED_COMPONENT_FIELDS or key in COSMETIC_COMPONENT_FIELDS:
            continue
        if key in STRUCTURAL_COMPONENT_FIELDS:
            record.setdefault("fields", {})[key] = _normalized(value)
            continue
        degraded[key] = _normalized(value)

    if degraded:
        coverage.nodes_degraded += 1
        for key in sorted(degraded):
            coverage.note("node", name, f"unrecognised field {key}")
        record["degraded"] = degraded
    return record


def _parameter_value(parameter: dict[str, Any]) -> Any:
    extras = {
        key: _normalized(value)
        for key, value in parameter.items()
        if key not in ("Variable", "Value") and key not in _COSMETIC_PARAMETER_FIELDS
    }
    value = _text(parameter.get("Value", ""))
    if not extras:
        return value
    return {"value": value, **extras}


class _NetBuilder:
    """Union-find over pins, one edge set with an electrical/signal kind tag."""

    def __init__(self, coverage: Coverage):
        self._coverage = coverage
        self._parent: dict[tuple[str, int], tuple[str, int]] = {}
        self._kind: dict[tuple[str, int], str] = {}
        self.degraded: list[Any] = []

    def add_connection(self, connection: dict[str, Any]) -> None:
        self._coverage.connections_total += 1
        kind = {"Wire": "electrical", "Signal": "signal"}.get(str(connection.get("Type", "")))
        pins, complete = _connection_pins(connection)
        if kind is None or not complete:
            self._coverage.connections_degraded += 1
            self._coverage.note("connection", str(connection.get("SrcComponent", "")), "unrecognised connection")
            self.degraded.append(_normalized({key: value for key, value in connection.items() if key != "Points"}))
            return
        self.union_all(pins, kind)

    def union_all(self, pins: list[tuple[str, int]], kind: str) -> None:
        for pin in pins:
            self._parent.setdefault(pin, pin)
            self._kind.setdefault(pin, kind)
        for pin in pins[1:]:
            self._union(pins[0], pin)

    def _find(self, pin: tuple[str, int]) -> tuple[str, int]:
        root = self._parent[pin]
        while root != self._parent[root]:
            root = self._parent[root]
        while pin != root:
            self._parent[pin], pin = root, self._parent[pin]
        return root

    def _union(self, first: tuple[str, int], second: tuple[str, int]) -> None:
        first_root, second_root = self._find(first), self._find(second)
        if first_root != second_root:
            self._parent[second_root] = first_root

    def pins_of(self, component: str) -> list[tuple[str, int]]:
        return [pin for pin in self._parent if pin[0] == component]

    def groups(self) -> dict[tuple[str, int], list[tuple[str, int]]]:
        grouped: dict[tuple[str, int], list[tuple[str, int]]] = {}
        for pin in list(self._parent):
            grouped.setdefault(self._find(pin), []).append(pin)
        return grouped

    def to_list(self, known_components: set[str]) -> list[dict[str, Any]]:
        nets = []
        for root, pins in self.groups().items():
            live = sorted(pin for pin in pins if pin[0] in known_components)
            if len(live) < 2:
                continue
            kinds = sorted({self._kind[pin] for pin in pins})
            nets.append(
                {
                    "kind": kinds[0] if len(kinds) == 1 else "mixed",
                    "pins": [f"{component}:{terminal}" for component, terminal in live],
                }
            )
        nets.sort(key=lambda net: (net["kind"], net["pins"]))
        if self.degraded:
            nets.append({"kind": "degraded", "connections": sorted(self.degraded, key=canonical_json)})
        return nets


def _collapse_teleports(
    nodes: dict[str, dict[str, Any]],
    nets: _NetBuilder,
    teleports: dict[str, dict[str, list[str]]],
    coverage: Coverage,
) -> None:
    """Merge every local ``From`` onto the net feeding its ``Goto``; both nodes vanish."""
    for tag, gotos in teleports["Goto"].items():
        froms = teleports["From"].get(tag, [])
        if len(gotos) != 1:
            for name in gotos + froms:
                coverage.note("node", name, f"ambiguous Goto tag {tag!r}")
                nodes[name]["degraded"] = {"Tag": tag}
            continue
        pins = nets.pins_of(gotos[0]) + [pin for name in froms for pin in nets.pins_of(name)]
        if pins:
            nets.union_all(pins, "signal")
        for name in [gotos[0]] + froms:
            del nodes[name]
    for tag, froms in teleports["From"].items():
        if tag in teleports["Goto"]:
            continue
        for name in froms:
            coverage.note("node", name, f"From tag {tag!r} has no local Goto")
            nodes[name]["degraded"] = {"Tag": tag}


def _connection_pins(connection: dict[str, Any]) -> tuple[list[tuple[str, int]], bool]:
    """Every (component, terminal) endpoint of a connection tree, and whether all parsed."""
    pins: list[tuple[str, int]] = []
    complete = True

    def visit(node: dict[str, Any]) -> None:
        nonlocal complete
        for component_key, terminal_key in (("SrcComponent", "SrcTerminal"), ("DstComponent", "DstTerminal")):
            if component_key in node:
                try:
                    pins.append((str(node[component_key]), int(node[terminal_key])))
                except (KeyError, TypeError, ValueError):
                    complete = False
        for branch in _blocks(node.get("Branch")):
            visit(branch)

    visit(connection)
    return pins, complete


def _normalized(value: Any) -> Any:
    """Light normalization for degraded regions: drop cosmetics, keep everything else."""
    if isinstance(value, dict):
        return {
            key: _normalized(item)
            for key, item in sorted(value.items())
            if key not in COSMETIC_COMPONENT_FIELDS and key != "Points"
        }
    if isinstance(value, (list, tuple)):
        return [_normalized(item) for item in value]
    return _text(value)


def _text(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "on" if value else "off"
    return value


def _blocks(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _first_block(value: Any) -> dict[str, Any]:
    blocks = _blocks(value)
    return blocks[0] if blocks else {}


__all__ = [
    "ANNOTATION_TYPES",
    "COSMETIC_COMPONENT_FIELDS",
    "COSMETIC_SCHEMATIC_FIELDS",
    "FORMAT",
    "STRUCTURAL_COMPONENT_FIELDS",
    "Coverage",
    "TopologyDocument",
    "canonical_json",
    "canonicalize_document",
    "canonicalize_schematic",
    "digest",
]
