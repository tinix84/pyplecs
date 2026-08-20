# PLECS `Reference` block semantics — findings

**Ticket:** [tinix84/pyplecs#34](https://github.com/tinix84/pyplecs/issues/34) — "What does a PLECS Reference block point to, and does its target affect results?"
**Parent map:** [tinix84/pyplecs#30](https://github.com/tinix84/pyplecs/issues/30) — Wayfinder: topology-based simulation cache key. Governing invariant: *the key never claims equality it cannot prove.*
**Branch:** `research/plecs-reference-semantics`
**Date:** 2026-08-19

## Corpus note (read this first)

The parent map states "the 25 models in `data/*.plecs` are the working evidence base." At the time of this research, `git ls-files data/` on `master` shows only **5** tracked `.plecs` files (`fb_src_prb`, `simple_boost_prb`, `simple_buck_prb`, `simple_buckboost_prb`, `simple_nibb_prb`), because `.gitignore` (commit `2e60035`, "exclude local PLECS samples") now ignores `data/*.plecs*` for anything not already tracked. The other 20 files the ticket's "82 occurrences / 25 models" figure depends on are **local, untracked, gitignored** files that exist only in the maintainer's main working copy at `D:\OneDrive\claude\pyplecs\data\` — not in this git worktree, and not in the repository at all from any other clone's point of view.

Counting `^\s*Type\s+Reference\s*$` across that full 25-file local directory gives exactly **82** matches, confirming the ticket's number and letting this research inspect the actual blocks. But this is evidence about the maintainer's local sample set, not about tracked repository content: a fresh clone of `tinix84/pyplecs` has only the 2 `Reference` blocks that live in the tracked `simple_nibb_prb.plecs`. Any canonicalizer/coverage-report design should note that the "82 across `data/*.plecs`" premise describes local fixtures, not the committed corpus — worth flagging back to map issue #30's evidence-base framing.

## 1. What a `Reference` component *is*

A PLECS `Reference` component is **not** a copy of a component's definition. Per docs.plexim.com:

> "When you copy a library component – either into a circuit schematic or into another or even the same component library – PLECS automatically creates a reference component rather than a full copy."
> — https://docs.plexim.com/plecs/5.0/using-plecs/libraries/

Every one of the 82 blocks in the corpus is this same kind of thing: a **link to a built-in PLECS Component Library entry**, not a user-authored external subsystem and not what PLECS docs separately call a "model reference" (a link to a whole external `.plecs`/Simulink model file — see §6). The block's `SrcComponent` field is the library path, e.g.:

```
Component {
  Type          Reference
  SrcComponent  "Components/Control/Filters/RMS Value"
  Name          "RMS Value"
  ...
  Parameter { Variable "x0" Value "0"  Show off }
  Parameter { Variable "ts" Value "0"  Show off }
  Parameter { Variable "fs" Value "fs" Show off }
  Terminal { Type Input  Position [-15, 0] Direction left }
  Terminal { Type Output Position [19, 0]  Direction right }
}
```
(`data/simple_nibb_prb.plecs:635-643`, identical structure tracked in both the worktree and main repo copies.)

Fields:
- `Type Reference` — marks the block as a library-linked component, not an inline primitive.
- `SrcComponent "<path>"` — the library path the block links to, in the form `Components/<Category>/<Subcategory>/<Component Name>` for every block observed (see §6).
- `Name` — the instance name in *this* schematic (independent of the library component's own name).
- `Parameter { Variable ... Value ... Show ... }` — per-instance overrides of the linked component's mask parameters (see §4).
- `Terminal { ... }` — the block's port geometry, duplicated from the library component so the schematic can render/connect without opening the library.

## 2. How the target is located

> "The reference component links to the library component by its full path, i.e. the Simulink path of the PLECS Library block and the path of the component within the component library as they are in effect at the time the copy is made."
> — https://docs.plexim.com/plecs/5.0/using-plecs/libraries/

So resolution is by a **library path fixed at copy time**, not a filesystem-relative path stored per-model. If PLECS can't find the library (e.g., a custom/third-party library rather than the shipped standard one), the documented recovery is:

> "In PLECS Blockset, add the directory that contains the required Simulink model to the MATLAB path and reload the circuit."
> — https://docs.plexim.com/plecs/5.0/using-plecs/libraries/

For the standard `Components/...` library used throughout this corpus, resolution is against PLECS's own bundled Component Library, which ships with the PLECS installation — it is not looked up via a project-relative search path the way `data/*.m`/thermal descriptions can be (a separate, unrelated PLECS Preferences → Thermal tab "description search path" mechanism referenced in code comments inside `bdc_nibb.plecs`, not applicable to `Reference` component resolution).

Separately, for **library link or model reference** subsystems specifically, the offline reference notes relative-path resolution semantics for an unrelated field (mask help HTML), which nonetheless confirms the general rule that reference/link targets resolve relative to *the external source file*, not the referencing model:

> "If the subsystem is a library link or model reference, the relative path is resolved relative to the parent folder of the source library or model file."
> — `.claude/skills/plecs-expert/references/components/system.md:189`, sourced from https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/

## 3. Copied into the file, or resolved at simulation time?

**Resolved at load time, not embedded at save time.**

> "Library references are resolved upon loading of a model. Afterwards, any changes that you make to a referenced library component are propagated to the referencing components when you start a simulation or when you manually update the simulation model with **Synchronize all external links…**"
> — https://docs.plexim.com/plecs/5.0/using-plecs/libraries/ (menu path confirmed as **Edit → Synchronize all external links…**)

This is the load-bearing fact for the parent map. The `.plecs` file's `Reference` block stores only the link path, the instance name/position, the per-instance parameter overrides, and terminal geometry — **not** the linked component's internal schematic, equations, or default mask behavior. That internal definition lives in the PLECS Component Library shipped with the installed PLECS version, and PLECS re-resolves and re-propagates it every load and every simulation start.

**Consequence for the cache key (the correctness stake the map cares about):** the byte content of a `.plecs` file does not fully determine simulation results for any model containing a `Reference` block. The PLECS *version* (and, in principle, any non-standard library on the search path) is an external dependency the file's bytes cannot see. Two `.plecs` files with byte-identical `Reference` blocks, simulated under two different installed PLECS versions where Plexim revised the internal implementation of e.g. `Components/Control/Filters/RMS Value`, are not guaranteed to produce identical results — and a cache key computed from file bytes alone would produce a **wrong cache hit** across a PLECS upgrade. This is exactly the failure mode the governing invariant forbids. Whether this is addressed by folding a PLECS version/build identifier into `solver_id` (already a candidate key component per map decision 3) or a dedicated "library resolution" dimension is a decision for the design spec, not this ticket — but the fact that resolution is external and dynamic, not embedded, is established.

## 4. Can a reference be parameterised/masked, and does it follow the symbol-vs-binding split?

Yes to parameterization; masking is inherited, not re-authorable per instance:

> "You can modify the parameters of the reference component but you cannot mask it or, if it is already masked, edit the mask."
> — https://docs.plexim.com/plecs/5.0/using-plecs/libraries/

So: the *set* of mask parameters (names, types, dialog layout, icon) comes from the library component and cannot be changed per reference instance. The *values* bound to those parameters are per-instance and stored directly on the block, using the identical `Parameter { Variable "<name>" Value "<expr>" Show <on|off> }` structure used by ordinary (non-Reference) components. Corpus evidence, `data/simple_nibb_prb_show.plecs:1683-1766` (`Continuous PID Controller` reference, 15 `Parameter` entries: `cont_type`, `par_source`, `kp`, `ki`, `kd`, `kf`, `ex_reset`, `x0_source`, `x0`, `ex_sat`, `sat_lim`, `up_limit`, `low_limit`, `aw_method`, `kbc`) and `data/simple_nibb_prb.plecs:644-658` (`RMS Value` reference: `Variable "fs" Value "fs"`, i.e. the mask parameter `fs` is bound to a same-named outer-model symbol, not a literal) show `Value` fields holding either literal numbers (`"0"`, `"20"`) or bare symbols (`"fs"`) that resolve against the enclosing model's variables/`InitializationCommands`.

This is the identical `Variable`/`Value` shape the map's decision 4 already assumes for ordinary component parameters (`L1.L <- "Lo"` style symbol binding, `topology_id` records the symbol, `params_id` records the resolved literal). Reference-block parameters need no special-casing in the canonicalizer beyond treating the block itself as a typed node whose type identity is `SrcComponent`, not `Type Reference` generically — two `Reference` blocks with different `SrcComponent` values are different component types for topology purposes even though both say `Type Reference`.

## 5. Behavior when the target is missing or changed

> "If PLECS is unable to resolve a library reference, it highlights the reference component and issues an error message."
> — https://docs.plexim.com/plecs/5.0/using-plecs/libraries/

This is a hard **error**, not a silent substitution and not merely a warning — for the case of the *library itself* being unreachable (unresolvable path). Recovery per the docs is either recreating the reference or restoring the library to the search path and reloading.

The documentation available through the plecs-expert skill's offline reference and the fetched pages does **not** address the narrower case of the library file being found but the specific *component within it* having been renamed or deleted (as opposed to the whole library being missing) — that finding could not be sourced and is left open rather than guessed.

## 6. Corpus evidence: what do the 82 targets actually resolve to?

Every `SrcComponent` value immediately following a `Type Reference` line, across all 25 local sample files (82 blocks total), was extracted directly (not from memory) and inspected. All 82 resolve to a path of the shape:

```
Components/<Category>/<Subcategory>/<Component Name>
```

Observed distinct targets (17 unique library components, reused across models):

```
Components/Assertions/Assert Range
Components/Control/Continuous/Continuous PID\nController
Components/Control/Continuous/Three-Phase PLL
Components/Control/Delays/Pulse Delay
Components/Control/Delays/Turn-on Delay
Components/Control/Filters/Moving Average
Components/Control/Filters/Periodic Average
Components/Control/Filters/RMS Value
Components/Control/Logical/D Flip-flop
Components/Control/Logical/SR Flip-flop
Components/Control/Modulators/6-Pulse\nGenerator
Components/Control/Modulators/Blanking Time
Components/Control/Modulators/Peak Current\nController
Components/Control/Modulators/Symmetrical PWM
Components/Electrical/Converters/Diode\nRectifier
Components/Electrical/Transformers/Ydy Trafo
```

Distribution by file (block count, verified with `grep -A1 -E "^\s*Type\s+Reference\s*$"` per file against the maintainer's local `data/` directory — 5 files, 4 of the 5 tracked-in-git files, have zero `Reference` blocks and are omitted):

| File | Reference blocks | Targets |
|---|---|---|
| `05_DAB_TCM_OTM_CPM_Script_data.plecs` | 12 | Turn-on Delay ×2, Periodic Average, Moving Average, Blanking Time ×8 |
| `12-pulse-rectifier-bl.plecs` | 4 | 6-Pulse Generator ×2, Three-Phase PLL, Ydy Trafo |
| `4th_leg_dcm_const_ripple.plecs` | 5 | Symmetrical PWM ×2, Continuous PID Controller, Moving Average ×2 |
| `B6_diode.plecs` | 1 | Diode Rectifier |
| `bdc_nibb.plecs` | 9 | SR Flip-flop ×2, Assert Range ×2, Turn-on Delay ×2, Moving Average, D Flip-flop ×2 |
| `bst_bcm_bsc5.plecs` | 3 | Turn-on Delay ×2, SR Flip-flop |
| `bst_bcm_bsc5_cscript.plecs` | 3 | Turn-on Delay ×2, SR Flip-flop |
| `buck_converter_bcm_rt.plecs` | 13 | Assert Range, Pulse Delay ×8, Turn-on Delay ×3, SR Flip-flop |
| `nibb_EKK_1.plecs` | 4 | Turn-on Delay ×2, SR Flip-flop ×2 |
| `nibb_EKK_2.plecs` | 5 | Turn-on Delay ×2, SR Flip-flop ×2, Peak Current Controller |
| `nibb_EKK_3.plecs` | 5 | Turn-on Delay ×2, SR Flip-flop ×2, Peak Current Controller |
| `simple_nibb_prb.plecs` (**tracked**) | 2 | RMS Value ×2 |
| `simple_nibb_prb_or.plecs` | 2 | RMS Value ×2 |
| `simple_nibb_prb_show.plecs` | 6 | RMS Value ×3, SR Flip-flop, Continuous PID Controller, Peak Current Controller |
| `simple_nibb_prb_vctrl.plecs` | 6 | (same set as `_show`) |
| `test_short.plecs` | 2 | RMS Value ×2 |
| **Total** | **82** | |

**None of the 82 targets lie outside the repository as another project's model file, another user's `.plecs`, or an absolute filesystem path.** All 82 point into the PLECS standard Component Library, which is bundled with every PLECS installation. So in the narrow sense of "does a target point at a sibling `.plecs` file somewhere on disk that isn't in this repo" — no, none do.

But the target *does* lie outside the repository in the sense that matters for the cache key: **the PLECS Component Library is not part of this git repository, is not pinned by these `.plecs` files, and its content can change between PLECS versions/installations independent of any change to the `.plecs` file's bytes** (see §3). No `Reference` block in the corpus points to a fully self-contained, in-file definition — every one of them is an external dependency by construction, just one that's externalized to "the PLECS install" rather than "another file in `data/`."

## Summary for the map decision

| Question | Answer |
|---|---|
| Is `Reference` a library link, alias, or external subsystem instance? | Library link (to the built-in PLECS Component Library in every corpus block observed) |
| Copied into `.plecs` on save, or resolved at load/run time? | **Resolved at load time**, re-propagated at simulation start; not embedded |
| Can it be masked/parameterised? | Parameters yes (per-instance `Variable`/`Value` overrides, same symbol/literal shape as decision 4); mask itself is inherited, not per-instance re-authorable |
| Missing/changed target behavior | Error + highlighted block when the *library* is unresolvable; renamed/deleted *component within* an otherwise-resolvable library is undocumented in available sources |
| Do any of the 82 corpus targets point outside the repo? | Not to another file on disk, but yes to the installed PLECS Component Library — an external, version-dependent dependency not captured by file bytes |

The correctness stake: a topology cache key that hashes `.plecs` bytes (or a canonicalized form of them) alone, without recording anything about the resolved `Reference` targets or the PLECS version resolving them, can produce a wrong cache hit across a PLECS upgrade that changes a linked library component's internal behavior — the exact failure the governing invariant forbids. Whether the fix is a `solver_id`/environment component recording PLECS version, a dedicated coverage flag for `Reference` blocks, or something else is left to the design spec this ticket feeds.

## Sources

- https://docs.plexim.com/plecs/5.0/using-plecs/libraries/ (fetched via WebFetch; page not present in the plecs-expert skill's offline `references/` cache)
- `D:\OneDrive\claude\pyplecs\.claude\skills\plecs-expert\references\components\system.md` (offline plecs-expert reference; masking-subsystems tables, sourced from https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/)
- Direct inspection of `data/*.plecs` — both the 5 files tracked on `master` and the maintainer's local (gitignored, untracked) 25-file sample set at `D:\OneDrive\claude\pyplecs\data\`, using `grep -A1 -E "^\s*Type\s+Reference\s*$"` and `Read` on specific line ranges.
