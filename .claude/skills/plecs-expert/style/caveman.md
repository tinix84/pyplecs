# Caveman Style — Prose Rules for plecs-expert

Reference: https://github.com/juliusbrussee/caveman

## Core rule

Drop: articles, filler, hedging, pleasantries.
Fragments OK.
Pattern: `[thing] [action] [reason]. [next step].`
Code blocks: never modified — kept exactly as authored.

## Banned words (enforced by `tests/test_plecs_expert.py::test_caveman_compliance`)

`basically`, `really`, `actually`, `essentially`, `obviously`, `simply`, `just`, `very`, `quite`, `perhaps`, `maybe`.

## Allow marker

If a banned word is unavoidable (rare), include the literal marker `<!-- caveman:allow -->` anywhere in the file. The whole file is then exempt. Use sparingly; comment why.

## Examples

**Bad:**
> The Inductor block is basically just a passive component that really stores energy in a magnetic field. You can simply set its initial current via the IL_init parameter.

**Good (caveman):**
> Inductor block. Passive. Stores energy in magnetic field. Param `IL_init` sets initial current.

**Bad:**
> Note that the MOSFET model is actually quite detailed and includes both conduction and switching losses if you configure it properly.

**Good (caveman):**
> MOSFET model. Conduction + switching loss. Enable via `model_level=2`.

## What's verbatim, what's rewritten

| Section type | Posture |
|--------------|---------|
| Parameter tables | Verbatim (facts) |
| RPC function signatures | Verbatim (facts) |
| XML element grammar | Verbatim (facts) |
| Defaults & units | Verbatim (facts) |
| Explanatory prose | Rewritten in caveman style |
| Examples (our own) | Caveman style |

## Style guide for tables

Tables are facts. Keep verbatim from docs.plexim.com. Add a `Source:` line below each table pointing to the source URL.
