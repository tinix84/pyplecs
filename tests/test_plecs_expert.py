"""Tests for the plecs-expert skill (file layout, content, MCP wiring).

Platform-independent: no PLECS instance, no network, no subprocess.
"""
from __future__ import annotations

import re
from pathlib import Path

SKILL_ROOT = Path(__file__).parent.parent / ".claude" / "skills" / "plecs-expert"

MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
URL_RE = re.compile(r"https?://[^\s)>\]]+")


def _walk_md(root: Path):
    return sorted(p for p in root.rglob("*.md"))


def test_skill_md_under_4kb():
    """SKILL.md body must be lookup-fast; cap at 4 KB."""
    skill_md = SKILL_ROOT / "SKILL.md"
    assert skill_md.exists(), f"missing: {skill_md}"
    size = skill_md.stat().st_size
    assert size <= 4096, f"SKILL.md is {size} bytes (limit 4096)"


def test_references_no_dead_links():
    """Every relative link in references/*.md resolves to an existing file."""
    root = SKILL_ROOT / "references"
    failures: list[str] = []
    for md in _walk_md(root):
        text = md.read_text(encoding="utf-8")
        for target in MD_LINK_RE.findall(text):
            if target.startswith(("http://", "https://", "#")):
                continue
            target_path = (md.parent / target.split("#", 1)[0]).resolve()
            if not target_path.exists():
                failures.append(f"{md}: dead link → {target}")
    assert not failures, "\n".join(failures)


def test_license_notes_complete():
    """Every references/*.md is classified in LICENSE-NOTES.md."""
    notes = SKILL_ROOT / "LICENSE-NOTES.md"
    refs = SKILL_ROOT / "references"
    notes_text = notes.read_text(encoding="utf-8")
    failures: list[str] = []
    for md in _walk_md(refs):
        rel = md.relative_to(SKILL_ROOT).as_posix()
        if rel not in notes_text:
            failures.append(f"{rel} not listed in LICENSE-NOTES.md")
    assert not failures, "\n".join(failures)


def test_url_index_resolvable():
    """URLs in url-index.md are syntactically valid (no fetch)."""
    idx = SKILL_ROOT / "references" / "url-index.md"
    failures: list[str] = []
    for url in URL_RE.findall(idx.read_text(encoding="utf-8")):
        if "docs.plexim.com" not in url:
            continue
        if " " in url or url.endswith((".",  ",", ";")):
            failures.append(f"malformed URL: {url}")
    assert not failures, "\n".join(failures)


BANNED_WORDS = {
    # caveman methodology — drop articles, fillers, hedging.
    # We can't strip articles globally without false positives, so the
    # banned set is just fillers + hedges. See style/caveman.md.
    "basically",
    "really",
    "actually",
    "essentially",
    "obviously",
    "simply",
    "just",     # ambiguous in code contexts; allow override via marker
    "very",
    "quite",
    "perhaps",
    "maybe",
}

ALLOW_MARKER = "<!-- caveman:allow -->"


def _strip_non_prose(text: str) -> str:
    """Strip fenced code blocks AND verbatim-table sections from text.

    Verbatim sections (between BEGIN/END VERBATIM TABLE markers) are facts
    quoted from PLECS docs; they are exempt from caveman-style enforcement.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(
        r"<!--\s*BEGIN VERBATIM TABLE:.*?<!--\s*END VERBATIM TABLE:.*?-->",
        "",
        text,
        flags=re.DOTALL,
    )
    return text


def test_caveman_compliance():
    """Rewritten prose in references/*.md must avoid banned filler words."""
    refs = SKILL_ROOT / "references"
    if not refs.exists():
        return
    failures: list[str] = []
    for md in _walk_md(refs):
        text = md.read_text(encoding="utf-8")
        if ALLOW_MARKER in text:
            continue
        prose = _strip_non_prose(text)
        for line_no, line in enumerate(prose.splitlines(), start=1):
            tokens = re.findall(r"\b\w+\b", line.lower())
            for word in BANNED_WORDS:
                if word in tokens:
                    failures.append(f"{md.relative_to(SKILL_ROOT)}:{line_no} banned: {word}")
    assert not failures, "\n".join(failures)


def test_slash_command_routes():
    """The /plecs slash command exists and routes to the plecs-expert skill."""
    cmd = SKILL_ROOT.parent.parent / "commands" / "plecs.md"
    assert cmd.exists(), f"missing: {cmd}"
    text = cmd.read_text(encoding="utf-8")
    assert "plecs-expert" in text, "command does not reference the plecs-expert skill"


EXPECTED_MCP_TOOLS = {
    "plecs_lookup",
    "plecs_search",
    "plecs_xml",
    "plecs_url",
    "plecs_component",
    "plecs_rpc",
    "pyplecs_wrappers",
    "pyplecs_rpc_surface",
}


def test_pyplecs_wrappers_introspectable():
    """pyplecs.plecs_components imports clean and exposes *PlecsMdl classes."""
    import pyplecs.plecs_components as comps  # noqa: F401
    from pyplecs.mcp.plecs_tools import pyplecs_wrappers

    wrappers = pyplecs_wrappers()
    assert wrappers, "no wrapper classes found in pyplecs.plecs_components"
    assert any(w.endswith("PlecsMdl") for w in wrappers), (
        f"expected *PlecsMdl naming convention; got: {wrappers}"
    )


def test_mcp_tools_register():
    """Importing pyplecs.mcp.plecs_tools exposes the expected 8 tools."""
    from pyplecs.mcp.plecs_tools import TOOL_REGISTRY

    assert set(TOOL_REGISTRY) == EXPECTED_MCP_TOOLS, (
        f"tool registry mismatch: extra={set(TOOL_REGISTRY) - EXPECTED_MCP_TOOLS} "
        f"missing={EXPECTED_MCP_TOOLS - set(TOOL_REGISTRY)}"
    )
    # Each entry is callable
    for name, fn in TOOL_REGISTRY.items():
        assert callable(fn), f"{name} not callable"
