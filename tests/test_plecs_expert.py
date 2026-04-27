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
    if not root.exists():
        return  # phase 1 vacuous pass
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
    if not refs.exists() or not notes.exists():
        return  # phase 1 vacuous pass
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
    if not idx.exists():
        return  # phase 1 vacuous pass
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


def _strip_code_blocks(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


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
        prose = _strip_code_blocks(text)
        for line_no, line in enumerate(prose.splitlines(), start=1):
            tokens = re.findall(r"\b\w+\b", line.lower())
            for word in BANNED_WORDS:
                if word in tokens:
                    failures.append(f"{md.relative_to(SKILL_ROOT)}:{line_no} banned: {word}")
    assert not failures, "\n".join(failures)
