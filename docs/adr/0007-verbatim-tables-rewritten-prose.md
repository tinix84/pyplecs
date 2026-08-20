# ADR-0007 — Verbatim tables, rewritten prose

- **Status**: Accepted
- **Date**: 2026-08-20

## Context

The `plecs-expert` skill at `.claude/skills/plecs-expert/` mirrors PLECS
reference material — component parameters, XML-RPC signatures, `.plecs` XML
grammar, solver options — so that PLECS questions can be answered offline
instead of by fetching vendor documentation each time.

That material is Plexim's proprietary documentation. This repository is public.
Mirroring it wholesale would republish someone else's copyrighted prose; not
mirroring it at all would leave the skill unable to answer anything without a
network round trip.

`LICENSE-NOTES.md` records the resulting per-file classification and is tracked.
The reasoning behind that classification was written only in a design spec under
`docs/superpowers/`, which ADR-0004 makes gitignored and disposable — so the
*why* was about to disappear while the *what* stayed.

## Decision

Two content classes, applied per section of every `references/*.md` file:

- **Verbatim — factual tables only.** Parameter names, defaults, units, RPC
  function signatures, XML element grammar. Facts and the tables that hold them
  are not copyrightable; these are also the parts that must be exact to be
  useful, and paraphrasing them would introduce errors.
- **Rewritten — all explanatory prose.** Original authorship in the caveman
  style of `style/caveman.md`. No copy-paste. The style is enforced by
  `tests/test_plecs_expert.py::test_caveman_compliance`, which also makes
  accidental verbatim copying visible.

`LICENSE-NOTES.md` classifies every section as `verbatim:tables` or
`rewritten:prose` and records its source URL. Tables are produced by
`tools/sync_tables.py`; prose is hand-authored.

## Consequences

- The auditable boundary is the point: if Plexim ever objects, the factual
  tables are the only surface carrying any risk, and `LICENSE-NOTES.md` makes a
  takedown surgical instead of forcing removal of the whole skill.
- Refreshing against a new PLECS version is two different jobs: tables
  re-extract mechanically, prose must be re-authored by hand. `tools/REFRESH.md`
  and `tools/check_drift.py` carry the procedure.
- Any new `references/*.md` file must arrive with its `LICENSE-NOTES.md` rows.
  A reference file with no classification is a defect.
- The caveman style is load-bearing, not decorative — dropping it would remove
  the signal that distinguishes original prose from mirrored prose.
