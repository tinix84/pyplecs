# ADR-0016 — AGENTS.md is the one agent-instruction file

- **Status**: Accepted
- **Date**: 2026-11-02

## Context

`CLAUDE.md` held the project instructions for Claude Code: build and test
commands, the architecture quick reference, the statement-owner table and the
Decision Log. On 2026-10-30 a Codex setup copied it to `AGENTS.md`, with a
find-and-replace of "Claude" by "Codex". Within three days the copy was wrong:

- It did not have the ADR-0015 row in the Decision Log.
- It pointed at `.Codex/skills/`, a path that does not exist.

Two files with the same content drift, because each edit must go into both.
ADR-0004 gives each kind of statement exactly one owner. Two instruction files
break that rule.

## Decision

**`AGENTS.md` at the repository root is the one agent-instruction file.** It
holds the content that `CLAUDE.md` held, including the Decision Log.

`CLAUDE.md` contains only a pointer and the import line `@AGENTS.md`, so
Claude Code loads the same text. Other agents read `AGENTS.md` directly.

Tool-specific copies stay out of the repository: `.agents/` and `.codex/` are
ignored.

## Consequences

- Add each new ADR row to the Decision Log in `AGENTS.md`.
- `AGENTS.md` keeps the real paths, such as `.claude/skills/plecs-expert/`.
  The file is shared, but those paths do not change per tool.
- The 2026-02-24 rule "Keep CLAUDE.md <50 lines" does not apply any more.
  `CLAUDE.md` is now a pointer.
- If an agent cannot read imports or `AGENTS.md`, give it a pointer file like
  `CLAUDE.md`, never a copy.
