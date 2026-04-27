"""Read-only MCP tools backed by the plecs-expert skill content + pyplecs introspection."""
from __future__ import annotations

import inspect
import re
from pathlib import Path
from typing import Any

# Resolve skill root: <repo>/.claude/skills/plecs-expert/
# __file__              = <repo>/pyplecs/mcp/plecs_tools.py
# .parent               = <repo>/pyplecs/mcp
# .parent.parent        = <repo>/pyplecs   (the package dir)
# .parent.parent.parent = <repo>           (repo root, where .claude/ lives)
PYPLECS_PKG = Path(__file__).resolve().parent.parent  # <repo>/pyplecs
REPO_ROOT = PYPLECS_PKG.parent  # <repo>
SKILL_ROOT = REPO_ROOT / ".claude" / "skills" / "plecs-expert"
REFERENCES = SKILL_ROOT / "references"


def _read_ref(rel: str) -> str:
    path = REFERENCES / rel
    if not path.exists():
        return f"(no offline reference for `{rel}`)"
    return path.read_text(encoding="utf-8")


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


# Registry consumed by server.py and the test
TOOL_REGISTRY: dict[str, Any] = {
    "plecs_lookup": plecs_lookup,
    "plecs_search": plecs_search,
    "plecs_xml": plecs_xml,
    "plecs_url": plecs_url,
    "plecs_component": plecs_component,
    "plecs_rpc": plecs_rpc,
    "pyplecs_wrappers": pyplecs_wrappers,
    "pyplecs_rpc_surface": pyplecs_rpc_surface,
}


__all__ = ["TOOL_REGISTRY", *TOOL_REGISTRY.keys()]
