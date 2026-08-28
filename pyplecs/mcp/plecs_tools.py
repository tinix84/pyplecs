"""Read-only MCP tools backed by the plecs-expert skill content + pyplecs introspection."""
from __future__ import annotations

import inspect
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

# Resolve skill root: <repo>/.claude/skills/plecs-expert/
# __file__              = <repo>/pyplecs/mcp/plecs_tools.py
# .parent               = <repo>/pyplecs/mcp
# .parent.parent        = <repo>/pyplecs   (the package dir)
# .parent.parent.parent = <repo>           (repo root, where .claude/ lives)
PYPLECS_PKG = Path(__file__).resolve().parent.parent  # <repo>/pyplecs
REPO_ROOT = PYPLECS_PKG.parent  # <repo>
SKILL_ROOT = REPO_ROOT / ".claude" / "skills" / "plecs-expert"
REFERENCES = SKILL_ROOT / "references"
_REFERENCES_RESOLVED = REFERENCES.resolve()


def _read_ref(rel: str) -> str:
    """Read references/<rel>; reject path-traversal attempts.

    `rel` is treated as a path under REFERENCES. After resolving, the path
    must be inside REFERENCES — otherwise the call is rejected. This prevents
    a malicious MCP client from passing e.g. `../../../etc/passwd`.
    """
    candidate = (REFERENCES / rel).resolve()
    try:
        candidate.relative_to(_REFERENCES_RESOLVED)
    except ValueError:
        return f"(invalid reference path: {rel})"
    if not candidate.exists():
        return f"(no offline reference for `{rel}`)"
    return candidate.read_text(encoding="utf-8")


def plecs_lookup(topic: str) -> str:
    """Read references/<topic>.md (or .md added if missing)."""
    rel = topic if topic.endswith(".md") else f"{topic}.md"
    return _read_ref(rel)


def plecs_search(query: str) -> str:
    """Grep across references/ for `query`. Returns file:line matches."""
    if not REFERENCES.exists():
        return "(references/ not yet populated)"
    needle = query.lower()
    matches: list[str] = []
    for md in sorted(REFERENCES.rglob("*.md")):
        for i, line in enumerate(md.read_text(encoding="utf-8").splitlines(), start=1):
            if needle in line.lower():
                matches.append(f"{md.relative_to(SKILL_ROOT)}:{i}: {line.strip()}")
    return "\n".join(matches) if matches else f"no matches for '{query}'"


def plecs_xml(element: str) -> str:
    """Look up a `.plecs` element in plecs-xml-grammar.md.

    `.plecs` files use a Tcl-ish curly-brace key-value format, not XML.
    The grammar table documents elements as backtick-wrapped tokens
    (e.g. ``Component { ... }``, ``Type <atom>``). Match those forms.
    """
    text = _read_ref("plecs-xml-grammar.md")
    esc = re.escape(element)
    pattern = re.compile(rf"`{esc}\b[^`]*`", re.IGNORECASE)
    matches = pattern.findall(text)
    if matches:
        return "\n".join(matches[:10])
    return f"element `{element}` not documented; try plecs_url('xml-grammar')"


def plecs_url(topic: str) -> str:
    """Return the docs.plexim.com URL for `topic` from url-index.md."""
    text = _read_ref("url-index.md")
    needle = topic.lower()
    for line in text.splitlines():
        if needle in line.lower():
            urls = re.findall(r"https?://[^\s)>\]]+", line)
            if urls:
                return urls[0]
    return f"no URL fallback for '{topic}'"


def pyplecs_wrappers() -> list[str]:
    """List `*PlecsMdl` classes in pyplecs.plecs_components."""
    import pyplecs.plecs_components as comps
    return sorted(
        n for n, obj in inspect.getmembers(comps, inspect.isclass)
        if obj.__module__ == comps.__name__
    )


def pyplecs_rpc_surface() -> list[str]:
    """List PlecsServer public methods."""
    from pyplecs.pyplecs import PlecsServer
    return sorted(
        n for n, _ in inspect.getmembers(PlecsServer, predicate=inspect.isfunction)
        if not n.startswith("_")
    )


def plecs_component(name: str) -> dict[str, Any]:
    """Composed: pyplecs wrapper if present, else search references/components/.

    Match priority:
      1. exact match against `<Name>PlecsMdl` (case-insensitive on stem)
      2. substring match, but only when `name` is at least 3 chars
         (avoids `name="r"` matching every wrapper containing the letter)
    """
    wrappers = pyplecs_wrappers()
    needle = name.lower()
    exact = next(
        (w for w in wrappers if w.lower().removesuffix("plecsmdl") == needle),
        None,
    )
    if exact is not None:
        matched_wrapper: str | None = exact
    elif len(needle) >= 3:
        matched_wrapper = next((w for w in wrappers if needle in w.lower()), None)
    else:
        matched_wrapper = None
    body = {
        "name": name,
        "pyplecs_wrapper": matched_wrapper,
        "docs_excerpt": plecs_search(name),
    }
    return body


def plecs_rpc(function: str) -> dict[str, Any]:
    """Composed: PlecsServer method introspection if present, else docs lookup."""
    from pyplecs.pyplecs import PlecsServer
    method = getattr(PlecsServer, function, None)
    body: dict[str, Any] = {
        "function": function,
        "wrapped_in_pyplecs": method is not None,
    }
    if method is not None:
        try:
            sig = str(inspect.signature(method))
        except (TypeError, ValueError):
            sig = "(signature not introspectable)"
        body["signature"] = f"PlecsServer.{function}{sig}"
        body["docstring"] = inspect.getdoc(method) or ""
    body["docs_excerpt"] = plecs_search(function)
    return body


@dataclass(frozen=True)
class ToolDefinition:
    """One explicit MCP tool interface and its in-process implementation."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Any]


@dataclass(frozen=True)
class ToolDispatchResult:
    """Catalogue-owned success or explicit tool error."""

    value: Any = None
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


class ToolCatalogue:
    """Own MCP listing, schemas, validation, dispatch, and error semantics."""

    def __init__(self, definitions: list[ToolDefinition]):
        names = [definition.name for definition in definitions]
        if len(names) != len(set(names)):
            raise ValueError("MCP tool names must be unique")
        self._definitions = tuple(definitions)
        self._by_name = {definition.name: definition for definition in definitions}

    @property
    def definitions(self) -> tuple[ToolDefinition, ...]:
        return self._definitions

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(definition.name for definition in self._definitions)

    def dispatch(
        self, name: str, arguments: Optional[Mapping[str, Any]] = None
    ) -> ToolDispatchResult:
        definition = self._by_name.get(name)
        if definition is None:
            return ToolDispatchResult(error=f"unknown tool: {name}")

        try:
            validated = self._validate(
                definition, {} if arguments is None else arguments
            )
        except ValueError as error:
            return ToolDispatchResult(error=f"tool '{name}' validation error: {error}")

        try:
            return ToolDispatchResult(value=definition.handler(**validated))
        except Exception as error:
            return ToolDispatchResult(error=f"tool '{name}' execution error: {error}")

    @staticmethod
    def _validate(
        definition: ToolDefinition, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(arguments, Mapping):
            raise ValueError("arguments must be an object")

        properties = definition.input_schema.get("properties", {})
        required = definition.input_schema.get("required", [])
        unexpected = sorted(set(arguments) - set(properties))
        if unexpected:
            raise ValueError(f"unexpected argument(s): {', '.join(unexpected)}")
        missing = [name for name in required if name not in arguments]
        if missing:
            raise ValueError(f"missing required argument(s): {', '.join(missing)}")

        validated = dict(arguments)
        for argument_name, value in validated.items():
            schema = properties[argument_name]
            if schema.get("type") == "string" and not isinstance(value, str):
                raise ValueError(f"argument '{argument_name}' must be a string")
            if schema.get("minLength") and not value:
                raise ValueError(f"argument '{argument_name}' must not be empty")
        return validated


def _string_input(name: str, description: str) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            name: {
                "type": "string",
                "minLength": 1,
                "description": description,
            }
        },
        "required": [name],
        "additionalProperties": False,
    }


def _no_input() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    }


TOOL_CATALOGUE = ToolCatalogue(
    [
        ToolDefinition(
            name="plecs_lookup",
            description="Read one offline PLECS reference by topic name or Markdown filename.",
            input_schema=_string_input(
                "topic", "Offline reference topic, with or without the .md suffix."
            ),
            handler=plecs_lookup,
        ),
        ToolDefinition(
            name="plecs_search",
            description="Search every offline PLECS reference and return file-and-line matches.",
            input_schema=_string_input(
                "query", "Case-insensitive text to find in the offline references."
            ),
            handler=plecs_search,
        ),
        ToolDefinition(
            name="plecs_xml",
            description="Look up a PLECS schematic-format element in the offline grammar.",
            input_schema=_string_input(
                "element", "PLECS schematic element or key, such as Component or Type."
            ),
            handler=plecs_xml,
        ),
        ToolDefinition(
            name="plecs_url",
            description="Resolve a PLECS documentation topic to its docs.plexim.com URL.",
            input_schema=_string_input(
                "topic", "Topic text to match in the offline URL index."
            ),
            handler=plecs_url,
        ),
        ToolDefinition(
            name="plecs_component",
            description="Combine PyPLECS wrapper discovery with offline component references.",
            input_schema=_string_input(
                "name", "PLECS component name, such as Mosfet or Inductor."
            ),
            handler=plecs_component,
        ),
        ToolDefinition(
            name="plecs_rpc",
            description="Combine PlecsServer method details with offline RPC references.",
            input_schema=_string_input(
                "function", "PLECS or PlecsServer RPC function name."
            ),
            handler=plecs_rpc,
        ),
        ToolDefinition(
            name="pyplecs_wrappers",
            description="List the PLECS component wrapper classes shipped by PyPLECS.",
            input_schema=_no_input(),
            handler=pyplecs_wrappers,
        ),
        ToolDefinition(
            name="pyplecs_rpc_surface",
            description="List the public methods exposed by PyPLECS PlecsServer.",
            input_schema=_no_input(),
            handler=pyplecs_rpc_surface,
        ),
    ]
)


__all__ = [
    "TOOL_CATALOGUE",
    "ToolCatalogue",
    "ToolDefinition",
    "ToolDispatchResult",
    "plecs_component",
    "plecs_lookup",
    "plecs_rpc",
    "plecs_search",
    "plecs_url",
    "plecs_xml",
    "pyplecs_rpc_surface",
    "pyplecs_wrappers",
]
