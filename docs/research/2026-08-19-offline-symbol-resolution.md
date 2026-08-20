# Research: How far can symbols and InitializationCommands be resolved offline?

**Ticket**: [tinix84/pyplecs#33](https://github.com/tinix84/pyplecs/issues/33), part of the [wayfinder map #30](https://github.com/tinix84/pyplecs/issues/30) (topology-based simulation cache key).
**Governing invariant** (from #30): the key never claims equality it cannot prove; unrecognised constructs degrade to normalized-byte inclusion, never fail open.
**Date**: 2026-08-19

## Corpus note (discrepancy from ticket premise)

The ticket and parent map assume "the 25 models in `data/*.plecs`." At `research/offline-symbol-resolution` (branch cut from `master`), `data/*.plecs` contains **5 files**, not 25:

- `data/fb_src_prb.plecs` (1103 lines)
- `data/simple_boost_prb.plecs` (626 lines)
- `data/simple_buck_prb.plecs` (580 lines)
- `data/simple_buckboost_prb.plecs` (627 lines)
- `data/simple_nibb_prb.plecs` (970 lines)

`git log --all --diff-filter=A -- 'data/*.plecs'` shows only two additional historical filenames (`data/01/simple_buck01.plecs`, `data/02/simple_buck02.plecs`, `data/simple_buck.plecs`) that no longer exist in the working tree. The repo's `.gitignore` (added in #28, "chore(gitignore): exclude local PLECS samples") ignores new untracked `data/*.plecs*` going forward, so any additional samples a contributor drops in locally will not be visible to future research either. **All findings below are evidenced against these 5 files**; conclusions about "what the corpus contains" should be read as "what these 5 tracked models contain," not a 25-model sample. This gap itself argues for the conservative degrade path (map decision 6): a canonicalizer sized to this corpus's construct set will hit unfamiliar constructs the moment richer models are added, and must degrade to byte-inclusion rather than mis-resolve them.

## Q1 — Precedence: InitializationCommands vs ModelVars

**Source**: `.claude/skills/plecs-expert/references/rpc-api.md` (offline reference), sourced from `https://docs.plexim.com/plecs/latest/scripting/`.

Verbatim from the `ModelVars` row of PLECS's scripted-simulation options table:

> "The optional field `ModelVars` is a struct variable that allows you to override variable values defined by the model initialization commands... **The override values are applied after the model initialization commands have been evaluated and before the component parameters are evaluated**, as shown in Fig. 117."

This resolves the question directly:

- **Order of evaluation**: (1) `InitializationCommands` runs in the model workspace → (2) `ModelVars` overrides are applied to that workspace → (3) component `Value` expressions (e.g. `"Lo"`) are evaluated by looking up identifiers in that workspace.
- **Which wins on a name collision**: `ModelVars` wins — it is applied strictly after `InitializationCommands`, so a `ModelVars` entry overwrites any same-named variable the init script set.
- **Is the init script aware of ModelVars?** No. Because the override step happens after the init script has already finished evaluating, `InitializationCommands` cannot observe or branch on `ModelVars` values (e.g. it cannot compute `derived = Vi_override * 2` reflecting an override — `Vi_override` does not exist yet when the init script runs).

This maps cleanly onto map decision 4's `topology_id`/`params_id` split: `params_id` should record the *post-override* workspace value (what the component parameter actually resolved to), and the resolution pipeline must apply `ModelVars` strictly after simulating the init script's side effects — matching `pyplecs/pyplecs.py:355` (`dict_to_plecs_opts` wraps a params dict as `{"ModelVars": varin}`) and the call at `pyplecs/pyplecs.py:356` (`self.server.plecs.simulate(self.modelName, opts)`), which hands this struct to PLECS over XML-RPC exactly as the docs describe.

Confirmed by direct file evidence in the corpus's `InitializationCommands` string (identical pattern in all 5 files, e.g. `data/simple_buck_prb.plecs:26`):

```
InitializationCommands "%% input\nT_sim = 1e-3; % simulation time\ndt = 1e-6"
```

`T_sim` and `dt` are set here; they are never present as `ModelVars` in any test or example in this repo — consistent with them being simulation-scaffolding constants rather than swept design parameters.

## Q2 — Where symbols come from

**Direct file evidence**, `data/simple_buck_prb.plecs`: the `InitializationCommands` block (line 26) only ever assigns `T_sim` and `dt`. Every electrical/control component parameter is a bare symbolic string, not a literal:

```
data/simple_buck_prb.plecs:74:   Value "Vi"
data/simple_buck_prb.plecs:88:   Value "Ro"
data/simple_buck_prb.plecs:102:  Value "Lo"
data/simple_buck_prb.plecs:121:  Value "Co"
data/simple_buck_prb.plecs:126:  Value "Vo_ref"
data/simple_buck_prb.plecs:140:  Value "Vf_d"
data/simple_buck_prb.plecs:145:  Value "Ron_d"
data/simple_buck_prb.plecs:174:  Value "ron"
data/simple_buck_prb.plecs:218:  Value "fs"
data/simple_buck_prb.plecs:223:  Value "D"
data/simple_buck_prb.plecs:426:  Value "Ii_max"
```

None of `Vi, Ro, Lo, Co, Vo_ref, Vf_d, Ron_d, ron, fs, D, Ii_max` are ever assigned inside any `InitializationCommands` in the corpus (verified across all 5 files — the `InitializationCommands` string is byte-identical in shape across all of them, only ever touching `T_sim`/`dt`). **Confirmed**: these symbols arrive exclusively via `ModelVars` at `simulate()`-call time (`pyplecs/pyplecs.py:335-356`), not via the model file itself. This is the intended pattern per Q1's evaluation order — it is also the *only* pattern evidenced in this corpus; there is no example of a symbol being bound by `InitializationCommands` instead of `ModelVars`.

**What happens if a symbol is bound nowhere — not resolvable offline.** `WebFetch` against `https://docs.plexim.com/plecs/latest/scripting/` (the same page backing Q1) was asked directly whether PLECS raises an error or silently defaults when a component parameter references an undefined variable. Result: **the documentation does not state this.** This is a genuine gap — not a memory-recall shortcut avoided, but an honest "the primary source is silent here." It should feed the conservative degrade path (map decision 6): the canonicalizer cannot assume unresolved symbols simulate successfully (or fail loudly) without a live PLECS/MATLAB check; treat an unbound symbol as unresolved (byte-degrade that component's parameter binding) rather than guessing PLECS's runtime behavior.

## Q3 — Expression language actually present in the corpus

Enumerated directly from all 5 files (`grep -n "InitializationCommands"` plus a scan of every `Value` field with a symbolic or numeric literal):

**`InitializationCommands` constructs found** (identical construct set in all 5 files, only literal values differ):
- `%%` cell-marker comment (`%% input`)
- `%` trailing line comment (`% simulation time`)
- Plain scalar assignment (`T_sim = 1e-3`, `dt = 1e-6`)
- Scientific-notation numeric literals (`1e-3`, `1e-6`, `1`)
- Semicolon statement suppression — **inconsistently applied**: `simple_buck_prb.plecs` omits the trailing `;` after `dt`'s assignment; the other four files include it (with a trailing space after). This is itself evidence that PLECS tolerates a missing trailing semicolon/newline at the end of the script.

**Constructs NOT found in any `InitializationCommands` in the corpus**: vectors/matrices (`[...]`), function calls, conditionals (`if`), loops (`for`/`while`), string literals, cell arrays, multi-statement chains beyond the two assignments shown above.

**`Value` field constructs found** (checked across all 5 files with `grep -nE 'Value\s+"[^"]*[*/+()].*"'`, which matched **zero** lines in any file):
- Bare symbolic identifiers only, e.g. `"Vi"`, `"Lo"`, `"Vo_ref"`, `"Ron_d"`, `"Ii_max"` (mixed case, underscores)
- Plain numeric literals: `"0"`, `"1"`, `"-1"`, `"4"`, `"10"`, `"3"`
- One empty string `Value ""` (`data/simple_nibb_prb.plecs:439`) — belongs to a non-electrical/meta field, not an evaluated component parameter expression

**Not found in any `Value` field in the corpus**: arithmetic expressions (`*`, `/`, `+`, parenthesized sub-expressions), function calls, vectors, conditionals. The corpus's expression surface is narrower than MATLAB/Octave's full grammar — it only exercises "bare identifier" or "bare numeric literal," never a computed expression.

**Caveat**: this describes what these 5 files exercise, not what PLECS's `Value`/`InitializationCommands` grammar *permits*. PLECS's own scripting reference (`.claude/skills/plecs-expert/references/components/system.md`, sourced from `https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/`) documents mask "Edit" parameters as accepting arbitrary MATLAB/Octave expressions evaluated at simulation start, and Lua control structures (`if/then/else`, `for`) for mask icon-drawing scripts (a different, non-simulation-affecting language) — so the ceiling for what a canonicalizer must eventually cope with is broader than this corpus samples, even though this corpus never exercises it.

## Q4 — Feasible offline subset (recommendation)

Given Q3's evidence, the offline-evaluable-without-MATLAB subset that actually matters for the *current* corpus is narrow and safe to hand-parse:

- Recognize and evaluate: numeric literals (incl. scientific notation), bare identifier references, `%`/`%%` comment stripping, optional trailing `;`.
- Everything else (arithmetic expressions, function calls, vectors, conditionals, `for`/`while`) is **out of scope for a hand-rolled offline evaluator** — MATLAB/Octave semantics (operator precedence, broadcasting, built-in function library) are not something to reimplement piecemeal without risking a silent wrong answer, which the governing invariant explicitly forbids ("the key never claims equality it cannot prove").

**Recommended boundary**: parse `InitializationCommands` far enough to (a) strip comments/cell markers and (b) extract `identifier = <literal-or-simple-arithmetic>` assignments where the right-hand side is itself only literals/previously-bound identifiers with `+ - * /`, treating anything that doesn't match that shape (function calls, vectors, conditionals, unrecognized operators) as an opaque, byte-included region per the map's degrade path. This boundary happens to cover 100% of what this corpus contains today, while explicitly failing closed (not open) on the richer constructs the docs confirm PLECS actually permits.

## Q5 — Scope resolution into Subsystem interiors

**Corpus check first**: none of the 5 tracked models contain a `Subsystem` block at all (`grep -c Subsystem` returns `0` for every file). This is a second corpus gap: the Merkle-hierarchy design (map decision 5, "each `Subsystem` canonicalizes to its own `topology_id`") has **zero direct file evidence** to validate against in this repo today. Everything below is therefore sourced from PLECS's own docs, not from repo evidence.

**Masked subsystems — confirmed, with exact citation.** `WebFetch` on `https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/` returned this verbatim:

> **Variable Scope**: "PLECS associates a local variable workspace with each masked subsystem that has one or more mask parameters defined. Components in the underlying schematics can access only variables that are defined in this mask workspace."
>
> **Initialization Commands**: "Mask initialization commands are defined on the Initialization pane. They are evaluated in the mask workspace when a simulation is started." ... "Variables defined in the base workspace cannot be accessed."

So for a **masked** subsystem: it has its own isolated mask workspace, populated by its own mask parameters and mask-level `InitializationCommands`; a top-level `ModelVars` entry does **not** reach a symbol used inside a masked subsystem's interior unless that symbol is re-exposed as one of the subsystem's own mask parameters. This directly affects map decision 4/5: `topology_id` for a masked subsystem cannot assume the parent's `params_id` bindings apply inside it — the mask boundary is a hard scope wall, and the Merkle child's `params_id` must be resolved from its own mask workspace, not inherited.

**Plain (unmasked) subsystems — not resolvable offline.** The same fetch explicitly reported: "The documentation does not discuss what happens to variable scope in unmasked (plain) subsystems... There is no comparative discussion between masked versus unmasked subsystem behavior." A second, independent fetch against `https://docs.plexim.com/plecs/latest/scripting/` for the general execution-order question likewise surfaced only the `CurrentComponent`/`CurrentCircuit` special-variable substitution rule (a leading `.` in a component path resolves to "the component currently being evaluated" during mask/model init, or the model itself during model init) — nothing about whether an unmasked subsystem's interior shares its parent's base workspace by default.

**This is the honest degrade-path case for Q5**: whether an unmasked `Subsystem`'s interior components resolve symbols against the *parent* model's workspace (i.e., no scope wall unless masked) is not stated anywhere found in the offline reference or the two docs.plexim.com pages fetched, and there is no PLECS instance available to test it empirically in this task. Recommendation: the canonicalizer should **not assume** unmasked subsystems inherit the parent workspace transparently; per the governing invariant, treat symbol resolution across an unmasked-subsystem boundary as unproven until either (a) a live-PLECS test confirms the behavior, or (b) a docs.plexim.com page is found that states it explicitly. Until then, degrade that boundary to byte-inclusion rather than assuming pass-through scoping.

## Summary of what feeds the conservative degrade path (map decision 6)

1. **Undefined-symbol runtime behavior** (Q2) — docs.plexim.com's scripting page does not state whether PLECS errors or silently defaults on an unbound `Value` symbol. Unresolvable offline without a live PLECS instance.
2. **Full MATLAB/Octave expression grammar** (Q3/Q4) — the corpus only exercises bare literals/identifiers, but PLECS's mask "Edit" parameters accept arbitrary MATLAB/Octave expressions per the docs; a hand-rolled canonicalizer should only claim the literal/identifier/simple-arithmetic subset and degrade everything else.
3. **Unmasked-subsystem variable scope** (Q5) — masked-subsystem scoping is documented and isolated (confirmed), but plain/unmasked subsystem scoping relative to the parent workspace is not stated in any offline reference or the two docs.plexim.com pages fetched for this ticket, and the corpus contains zero `Subsystem` blocks to test against directly.
4. **Corpus size mismatch** — the ticket/map's premise of "25 models" does not match the 5 files actually present in `data/*.plecs` at this branch; every finding above is evidenced against those 5, not 25.

## Sources consulted

- `pyplecs/pyplecs.py:52-56` (`dict_to_plecs_opts`), `:335-356` (`simulate`), `:404-414` (`load_modelvars`) — direct repo evidence for the `ModelVars` call path.
- `data/fb_src_prb.plecs`, `data/simple_boost_prb.plecs`, `data/simple_buck_prb.plecs`, `data/simple_buckboost_prb.plecs`, `data/simple_nibb_prb.plecs` — direct repo evidence, greped for `InitializationCommands`, `Value`, `Subsystem`.
- `.claude/skills/plecs-expert/references/rpc-api.md` — offline reference, sourced from `https://docs.plexim.com/plecs/latest/scripting/`.
- `.claude/skills/plecs-expert/references/components/system.md` — offline reference, sourced from `https://docs.plexim.com/plecs/latest/components-by-category/subsystem/`, `.../conf_subsystem/`, and `https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/`.
- `https://docs.plexim.com/plecs/latest/scripting/` — direct WebFetch (URL fallback), for the undefined-symbol question and the `CurrentComponent`/`CurrentCircuit` scoping rule.
- `https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/` — direct WebFetch (URL fallback), for masked-subsystem variable scope and initialization commands.
