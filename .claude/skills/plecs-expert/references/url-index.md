# URL Fallback Index

Topics not covered offline. Skill must `WebFetch` URL, summarize caveman style, cite URL.

All URLs verified 200 OK on 2026-04-27 via `curl -L`.

| Topic | URL |
|-------|-----|
| RT Box product page (covered by future plecs-rtbox skill) | https://www.plexim.com/products/rt_box |
| Field-oriented control transforms (Park / Clarke / D-Q) | https://docs.plexim.com/plecs/latest/components-by-category/abc2dq/ |
| Saturable inductor component | https://docs.plexim.com/plecs/latest/components-by-category/saturableinductor/ |
| Configurable subsystem variants | https://docs.plexim.com/plecs/latest/components-by-category/conf_subsystem/ |
| PLECS Coder / code generation root | https://docs.plexim.com/plecs/latest/codegeneration/ |
| Solver tolerance tuning (simulation parameters) | https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/ |
| MATLAB / Simulink scripting integration | https://docs.plexim.com/plecs/latest/scripting/ |
| Modulator block library (symmetrical PWM example) | https://docs.plexim.com/plecs/latest/components-by-category/symmetricalpwm/ |
| Three-phase machines (PMSM example) | https://docs.plexim.com/plecs/latest/components-by-category/pmsm/ |
| Power semiconductor thermal modeling (thermal library) | https://docs.plexim.com/plecs/latest/thermal-modeling/thermal-library/ |

## Notes

Topic catalog hand-built. Original `/UserManual/<Subdir>/<File>.html` slugs all 404 — Plexim uses `/components-by-category/<slug>/` and `/<topic>/` instead. Slugs above probed via curl + index pages on 2026-04-27.

No dedicated FOC library page. Closest match: D-Q / Clarke transform components under `components-by-category/`.

No dedicated MATLAB integration page. MATLAB content lives under `scripting/` (Command Line Interface in PLECS Blockset).

No dedicated target-support list page. PLECS Coder targets ship as separate target-support packages — start at `codegeneration/`.

RT Box has no `docs.plexim.com/rtbox/` subdomain. Product overview at `plexim.com/products/rt_box`.
