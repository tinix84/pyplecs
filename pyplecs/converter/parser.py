"""Offline parser from PLECS schematic text to the Circuit Model."""

import json
import re
from pathlib import Path
from typing import Any, Optional

from .circuit import Circuit, Component, Net, Pin

CONTROL_COMPONENT_TYPES = frozenset(
    {
        "Constant",
        "Display",
        "From",
        "Goto",
        "Input",
        "Output",
        "PlecsProbe",
        "PulseGenerator",
        "Reference",
        "Scope",
        "SignalDemux",
        "SignalMux",
    }
)


class PlecsParseError(ValueError):
    """Raised when a PLECS schematic cannot be parsed offline."""


def parse_plecs(path: str | Path) -> Circuit:
    """Parse one ``.plecs`` file into the public Circuit Model."""
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError as error:
        raise PlecsParseError(f"Could not read PLECS schematic '{source}': {error}") from error

    document = parse_plecs_text(text)
    root = document.get("Plecs")
    if not isinstance(root, dict):
        raise PlecsParseError("PLECS schematic must contain one top-level 'Plecs' block")
    schematic = root.get("Schematic")
    if not isinstance(schematic, dict):
        raise PlecsParseError("PLECS schematic must contain a 'Schematic' block")

    raw_component_blocks = blocks(schematic.get("Component"))
    all_component_types = {
        str(block.get("Name")): str(block.get("Type", ""))
        for block in raw_component_blocks
        if block.get("Name") is not None
    }
    components = [component for block in raw_component_blocks if (component := _component(block)) is not None]
    nets = _build_nets(blocks(schematic.get("Connection")), components, all_component_types)

    name = str(root.get("Name") or source.stem)
    raw_params = _parse_initialization_commands(str(root.get("InitializationCommands", "")))
    return Circuit(name=name, components=components, nets=nets, raw_params=raw_params)


def parse_plecs_text(text: str) -> dict[str, Any]:
    """Parse PLECS nested-block text into mappings, tuples, and scalar values."""
    lines = text.splitlines()
    document, next_index = _parse_block(lines, 0, expect_close=False)
    for index in range(next_index, len(lines)):
        if lines[index].strip():
            raise PlecsParseError(f"Unexpected content at line {index + 1}")
    return document


def _parse_block(lines: list[str], start: int, *, expect_close: bool) -> tuple[dict[str, Any], int]:
    data: dict[str, Any] = {}
    last_key: Optional[str] = None
    index = start
    while index < len(lines):
        line_number = index + 1
        stripped = lines[index].strip()
        index += 1
        if not stripped:
            continue
        if stripped == "}":
            if not expect_close:
                raise PlecsParseError(f"Unexpected closing brace at line {line_number}")
            return data, index
        if stripped.endswith("{"):
            key = stripped[:-1].strip()
            if not key or any(character.isspace() for character in key):
                raise PlecsParseError(f"Invalid block declaration at line {line_number}")
            child, index = _parse_block(lines, index, expect_close=True)
            _add_value(data, key, child)
            last_key = key
            continue
        if stripped.startswith('"'):
            if last_key is None:
                raise PlecsParseError(f"String continuation has no preceding field at line {line_number}")
            if _is_brace_list(data[last_key]):
                _append_brace_list_continuation(data, last_key, stripped, line_number)
                continue
            continuation = _decode_quoted(stripped, line_number)
            _append_continuation(data, last_key, continuation, line_number)
            continue

        parts = stripped.split(maxsplit=1)
        if len(parts) != 2:
            raise PlecsParseError(f"Expected key and value at line {line_number}")
        key, raw_value = parts
        _add_value(data, key, _parse_value(raw_value, line_number))
        last_key = key

    if expect_close:
        raise PlecsParseError("Unterminated PLECS block at end of file")
    return data, index


class _BraceList(str):
    """Raw text of a brace list such as ``Signals {"a", "b"}``; only its quoted chunks wrap."""


def _parse_value(raw_value: str, line_number: int) -> Any:
    if raw_value.startswith('"'):
        return _decode_quoted(raw_value, line_number)
    if raw_value.startswith("{"):
        return _BraceList(raw_value)
    if raw_value.startswith("["):
        if not raw_value.endswith("]"):
            raise PlecsParseError(f"Unterminated array at line {line_number}")
        return _parse_array(raw_value[1:-1], line_number)
    if raw_value == "on":
        return True
    if raw_value == "off":
        return False
    if re.fullmatch(r"[-+]?\d+", raw_value):
        return int(raw_value)
    if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+)(?:[eE][-+]?\d+)?", raw_value):
        return float(raw_value)
    return raw_value


def _decode_quoted(raw_value: str, line_number: int) -> str:
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError as error:
        raise PlecsParseError(f"Invalid quoted string at line {line_number}: {error.msg}") from error
    if not isinstance(value, str):
        raise PlecsParseError(f"Expected quoted string at line {line_number}")
    return value


def _parse_array(body: str, line_number: int) -> tuple[Any, ...]:
    rows = []
    for raw_row in body.split(";"):
        values = []
        for raw_value in raw_row.split(","):
            value = raw_value.strip()
            if not value:
                continue
            if re.fullmatch(r"[-+]?\d+", value):
                values.append(int(value))
            elif re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?", value):
                values.append(float(value))
            else:
                values.append(value)
        rows.append(tuple(values))
    if len(rows) == 1:
        return rows[0]
    if not rows:
        raise PlecsParseError(f"Empty array at line {line_number}")
    return tuple(rows)


def _add_value(data: dict[str, Any], key: str, value: Any) -> None:
    if key not in data:
        data[key] = value
    elif isinstance(data[key], list):
        data[key].append(value)
    else:
        data[key] = [data[key], value]


def _append_continuation(data: dict[str, Any], key: str, continuation: str, line_number: int) -> None:
    value = data[key]
    if isinstance(value, list):
        if not value or not isinstance(value[-1], str):
            raise PlecsParseError(f"Invalid string continuation at line {line_number}")
        value[-1] += continuation
    elif isinstance(value, str):
        data[key] += continuation
    else:
        raise PlecsParseError(f"Invalid string continuation at line {line_number}")


def _is_brace_list(value: Any) -> bool:
    if isinstance(value, list):
        value = value[-1] if value else None
    return isinstance(value, _BraceList) and value.endswith('"')


def _append_brace_list_continuation(data: dict[str, Any], key: str, line: str, line_number: int) -> None:
    if len(line) < 2 or line.count('"') % 2:
        raise PlecsParseError(f"Invalid brace list continuation at line {line_number}")
    value = data[key]
    if isinstance(value, list):
        value[-1] = _BraceList(value[-1][:-1] + line[1:])
    else:
        data[key] = _BraceList(value[:-1] + line[1:])


def blocks(value: Any) -> list[dict[str, Any]]:
    """Normalize a parsed field to its list of block mappings (PLECS repeats keys for lists)."""
    if value is None:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _component(block: dict[str, Any]) -> Optional[Component]:
    component_type = str(block.get("Type", ""))
    name_value = block.get("Name")
    if not component_type or name_value is None or component_type in CONTROL_COMPONENT_TYPES:
        return None

    parameters: dict[str, str] = {}
    for parameter in blocks(block.get("Parameter")):
        variable = parameter.get("Variable")
        if variable is not None:
            parameters[str(variable)] = str(parameter.get("Value", ""))

    position_value = block.get("Position", (0, 0))
    if (
        isinstance(position_value, tuple)
        and len(position_value) == 2
        and all(isinstance(value, (int, float)) for value in position_value)
    ):
        position = (int(position_value[0]), int(position_value[1]))
    else:
        position = (0, 0)

    return Component(
        name=str(name_value),
        type=component_type,
        position=position,
        direction=str(block.get("Direction", "right")),
        flipped=bool(block.get("Flipped", False)),
        parameters=parameters,
    )


class _DisjointPins:
    def __init__(self) -> None:
        self.parent: dict[Pin, Pin] = {}

    def add(self, pin: Pin) -> None:
        self.parent.setdefault(pin, pin)

    def find(self, pin: Pin) -> Pin:
        root = self.parent[pin]
        if root != pin:
            self.parent[pin] = self.find(root)
        return self.parent[pin]

    def union(self, first: Pin, second: Pin) -> None:
        first_root = self.find(first)
        second_root = self.find(second)
        if first_root != second_root:
            self.parent[second_root] = first_root


def _build_nets(
    connection_blocks: list[dict[str, Any]],
    components: list[Component],
    all_component_types: dict[str, str],
) -> list[Net]:
    included_names = {component.name for component in components}
    disjoint = _DisjointPins()
    pin_order: list[Pin] = []

    for connection in connection_blocks:
        if connection.get("Type") != "Wire":
            continue
        connection_pins = [pin for pin in _connection_pins(connection) if pin.component in included_names]
        unique_pins = list(dict.fromkeys(connection_pins))
        if len(unique_pins) < 2:
            continue
        for pin in unique_pins:
            if pin not in disjoint.parent:
                disjoint.add(pin)
                pin_order.append(pin)
        for pin in unique_pins[1:]:
            disjoint.union(unique_pins[0], pin)

    groups: dict[Pin, list[Pin]] = {}
    group_order: list[Pin] = []
    for pin in pin_order:
        root = disjoint.find(pin)
        if root not in groups:
            groups[root] = []
            group_order.append(root)
        groups[root].append(pin)

    ground_root = next(
        (
            root
            for root in group_order
            if any(all_component_types.get(pin.component) == "Ground" for pin in groups[root])
        ),
        None,
    )
    if ground_root is None:
        ground_root = next(
            (
                root
                for root in group_order
                if any(
                    all_component_types.get(pin.component) == "DCVoltageSource" and pin.terminal == 2
                    for pin in groups[root]
                )
            ),
            None,
        )

    nets: list[Net] = []
    next_number = 1
    for root in group_order:
        if root == ground_root:
            name = "0"
        else:
            name = f"N{next_number:03d}"
            next_number += 1
        nets.append(Net(name=name, pins=groups[root]))
    return nets


def _connection_pins(connection: dict[str, Any]) -> list[Pin]:
    pins: list[Pin] = []
    source = _pin(connection, "SrcComponent", "SrcTerminal")
    if source is not None:
        pins.append(source)

    def visit(node: dict[str, Any]) -> None:
        destination = _pin(node, "DstComponent", "DstTerminal")
        if destination is not None:
            pins.append(destination)
        for branch in blocks(node.get("Branch")):
            visit(branch)

    visit(connection)
    return pins


def _pin(block: dict[str, Any], component_key: str, terminal_key: str) -> Optional[Pin]:
    component = block.get(component_key)
    terminal = block.get(terminal_key)
    if component is None or terminal is None:
        return None
    try:
        terminal_number = int(terminal)
    except (TypeError, ValueError):
        return None
    return Pin(component=str(component), terminal=terminal_number)


def _parse_initialization_commands(commands: str) -> dict[str, str]:
    without_comments = "\n".join(line.split("%", 1)[0] for line in commands.splitlines())
    assignments: dict[str, str] = {}
    for match in re.finditer(r"(?:^|[;\n])\s*([A-Za-z_]\w*)\s*=\s*([^;\n]+)", without_comments):
        name, expression = match.groups()
        assignments[name] = expression.strip()
    return assignments
