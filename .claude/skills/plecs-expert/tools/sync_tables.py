#!/usr/bin/env python3
"""Scrape factual tables from PLECS docs into references/*.md.

Reads URLs from manifest.json. For each URL:
  1. Fetches HTML (httpx).
  2. Extracts <table> elements (BeautifulSoup).
  3. Renders each as a Markdown table.
  4. Writes/updates the verbatim sections of the corresponding references/*.md
     file, preserving any prose between BEGIN/END markers.

Per-section markers are HTML comments:
  <!-- BEGIN VERBATIM TABLE: <slug> -->
  ...table markdown...
  <!-- END VERBATIM TABLE: <slug> -->

Prose between marker pairs is left untouched. Hashes are written to
manifest.json so check_drift.py can detect upstream changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup, Tag

SKILL_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = SKILL_ROOT / "manifest.json"

BEGIN_RE = re.compile(r"<!--\s*BEGIN VERBATIM TABLE:\s*(?P<slug>[^\s-]+)\s*-->")
END_RE = re.compile(r"<!--\s*END VERBATIM TABLE:\s*(?P<slug>[^\s-]+)\s*-->")


def slugify(url: str) -> str:
    return Path(url.rstrip("/")).name.replace(".html", "").lower()


def _clean_cell(text: str) -> str:
    """Escape pipes and collapse whitespace so the cell is markdown-safe."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def html_table_to_markdown(table: Tag) -> str:
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [_clean_cell(td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
        if cells:
            rows.append(cells)
    if not rows:
        return ""
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |"]
    out.append("| " + " | ".join(["---"] * width) + " |")
    for r in rows[1:]:
        out.append("| " + " | ".join(r) + " |")
    return "\n".join(out)


def dl_to_markdown(dl: Tag, header: tuple[str, str] = ("Name", "Description")) -> str:
    """Render a <dl>...</dl> as a 2-column Markdown table.

    PLECS docs encode component parameters and probe signals as definition
    lists rather than HTML tables. The dt is the parameter/probe name and
    the dd is its description (factual: units, defaults, ranges).
    """
    rows: list[tuple[str, str]] = []
    dts = dl.find_all("dt", recursive=False)
    dds = dl.find_all("dd", recursive=False)
    for dt, dd in zip(dts, dds):
        name = _clean_cell(dt.get_text(" ", strip=True))
        desc = _clean_cell(dd.get_text(" ", strip=True))
        if name or desc:
            rows.append((name, desc))
    if not rows:
        return ""
    out = [f"| {header[0]} | {header[1]} |", "| --- | --- |"]
    for name, desc in rows:
        out.append(f"| {name} | {desc} |")
    return "\n".join(out)


def fetch(url: str) -> str:
    resp = httpx.get(url, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


PROBE_SECTIONS = {"probes", "probe-signals", "probe_signals"}


def _enclosing_section_id(node: Tag) -> str:
    for anc in node.parents:
        if getattr(anc, "name", None) == "section" and anc.get("id"):
            return anc.get("id")  # type: ignore[return-value]
    return "section"


def extract_tables(html: str, url: str) -> dict[str, str]:
    """Extract factual tables from a PLECS doc page.

    PLECS docs encode facts in two markups:
      * <table>...</table> (used on RPC / codegen / scripting pages).
      * <dl><dt>name</dt><dd>desc</dd>...</dl> for parameter and probe
        listings (used on every component page and on solver pages).
    Both are rendered to Markdown tables.
    """
    soup = BeautifulSoup(html, "html.parser")
    base_slug = slugify(url)
    out: dict[str, str] = {}
    used_slugs: set[str] = set()

    def _add(slug: str, body: str) -> None:
        candidate = slug
        idx = 1
        while candidate in used_slugs:
            idx += 1
            candidate = f"{slug}-{idx}"
        used_slugs.add(candidate)
        out[candidate] = body

    # 1) Native HTML tables.
    for i, t in enumerate(soup.find_all("table")):
        md = html_table_to_markdown(t)
        if md:
            _add(f"{base_slug}-table-{i}", md)

    # 2) Top-level <dl> elements (skipping nested dls). Slug by enclosing
    #    section id so multiple parameter blocks on the same page stay
    #    distinct (e.g. solver page has 21 dls across 14 sections).
    for dl in soup.find_all("dl"):
        if dl.find_parent("dl") is not None:
            continue
        sec_id = _enclosing_section_id(dl)
        header = (
            ("Probe signal", "Description")
            if sec_id in PROBE_SECTIONS
            else ("Name", "Description")
        )
        md = dl_to_markdown(dl, header=header)
        if md:
            _add(f"{base_slug}-{sec_id}", md)
    return out


def replace_section(text: str, slug: str, body: str) -> str:
    begin = f"<!-- BEGIN VERBATIM TABLE: {slug} -->"
    end = f"<!-- END VERBATIM TABLE: {slug} -->"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), re.DOTALL)
    block = f"{begin}\n\n{body}\n\n{end}"
    if pattern.search(text):
        return pattern.sub(block, text)
    sep = "\n\n" if text and not text.endswith("\n") else "\n"
    return text + sep + block + "\n"


def update_file(target: Path, sections: dict[str, str], source_url: str) -> dict[str, str]:
    target.parent.mkdir(parents=True, exist_ok=True)
    text = target.read_text(encoding="utf-8") if target.exists() else f"# {target.stem}\n"
    hashes: dict[str, str] = {}
    for slug, body in sections.items():
        marked = f"{body}\n\n_Source: {source_url}_"
        text = replace_section(text, slug, marked)
        hashes[slug] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    target.write_text(text, encoding="utf-8")
    return hashes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    failures: list[str] = []
    for rel_file, entry in manifest["files"].items():
        target = SKILL_ROOT / rel_file
        all_hashes: dict[str, str] = {}
        for url in entry["source_urls"]:
            try:
                html = fetch(url)
            except Exception as exc:
                failures.append(f"FETCH {url}: {exc}")
                continue
            sections = extract_tables(html, url)
            if not sections:
                failures.append(f"NO TABLES {url}")
                continue
            if args.dry_run:
                print(f"[dry-run] {rel_file} <- {len(sections)} tables from {url}")
                continue
            new_hashes = update_file(target, sections, url)
            all_hashes.update(new_hashes)
        if not args.dry_run:
            entry["table_section_hashes"] = all_hashes
    if not args.dry_run:
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
