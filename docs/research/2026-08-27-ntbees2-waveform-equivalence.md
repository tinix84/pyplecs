# Research: ntbees2 waveform-equivalence method for converter acceptance

**Ticket:** [Extract the ntbees2 waveform-equivalence method for converter acceptance](https://github.com/tinix84/pyplecs/issues/58)  
**Parent map:** [Wayfinder: verify live PyPLECS execution and converter waveform fidelity](https://github.com/tinix84/pyplecs/issues/56)  
**Source snapshot:** [`tinix84/ntbees2@fc481090177c705e89de94725df87b111b40c56c`](https://github.com/tinix84/ntbees2/tree/fc481090177c705e89de94725df87b111b40c56c)  
**Date:** 2026-08-27

## Finding

PyPLECS should adapt ntbees2's **configuration shape and comparison mechanics**, not import its Layer-1/Layer-2 harness or copy its tolerances. The reusable core is: a named Operating Point and explicit signal map; a settled, whole-switching-period window; time-weighted steady-state metrics as the pass/fail oracle; and phase-aligned NRMSE as diagnostic evidence. The analytical converter models, parameter mappers, component-stress taxonomy, expected-DCM-divergence cases, and broad topology-specific tolerance bands belong to ntbees2.

For the first PyPLECS semi-manual acceptance slice, use one canonical `simple_buck_prb` Operating Point to compare PLECS against the generated `.cir` quantitatively. Treat generated `.asc` as an LTspice load/run check with the same key scalar metrics. Keep the validator and evidence schema under PyPLECS tests; do not add waveform-analysis concepts to the PyPLECS runtime API.

## What ntbees2 actually does

### 1. Test selection and simulator availability

The canonical buck comparison is an opt-in `external` pytest module. ntbees2's default pytest options exclude `external` and `slow`, and the marker is defined as requiring an external simulator with automatic skip when unreachable ([`pyproject.toml:107-114`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/pyproject.toml#L107-L114)). The integration fixture reads the configured base URL, probes `/health` with a three-second timeout, and gives a specific skip reason when PyPLECS is not reachable ([`tests/integration/conftest.py:16-42`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/integration/conftest.py#L16-L42)).

This pattern fits a live PLECS acceptance test, but the converter comparison requested by the parent map is semi-manual because a second simulator must be run by the maintainer. Its Python comparison stage can still use an explicit `external`/manual selection and should fail with an actionable missing-evidence message rather than silently joining the default suite.

### 2. Configuration, signal mapping, and Operating Points

ntbees2 keeps simulator address/model path, lossless-device defaults, signal-map indices, steady-state settings, tolerances, and named Operating Points in topology YAML. For buck, PLECS output columns `0..12` are mapped to canonical names including `i_S1`, `i_S2`, `i_L`, `v_L`, `v_C`, `i_C`, `i_R`, and `v_R` ([`buck_lossless.yaml:6-35`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/plugins/plecs_adapter/config/buck_lossless.yaml#L6-L35)). The REST adapter serializes integer map keys to JSON strings and converts the returned time and named-signal arrays to `float64` ([`plugins/plecs_adapter/client.py:42-84`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/plugins/plecs_adapter/client.py#L42-L84)). The WaveformSet adapter then infers current/voltage units from names and records source/slicing metadata ([`plugins/plecs_adapter/signal_mapper.py:16-91`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/plugins/plecs_adapter/signal_mapper.py#L16-L91)).

The buck matrix contains four positive CCM cases—nominal, high voltage, low frequency, and high power—and one deliberately invalid CCM-vs-DCM case ([`buck_lossless.yaml:42-81`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/plugins/plecs_adapter/config/buck_lossless.yaml#L42-L81)). The negative case passes only when the analytical CCM model diverges from PLECS by more than 20% and PLECS inductor current reaches approximately zero ([`test_plecs_l1_vs_l2.py:212-270`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/integration/test_plecs_l1_vs_l2.py#L212-L270)). That is useful model-validation evidence in ntbees2, not a converter-equivalence oracle: PyPLECS is comparing two representations of the same Circuit Model, so expected physical divergence would indicate a conversion or test-setup defect.

The YAML idea should be adapted into a PyPLECS acceptance manifest with source-specific expressions mapped to common names. At minimum, require `i_L` and output voltage (`v_C` or `v_R`); add switch/diode currents where both simulator exports have the same polarity convention. Required signals must be validated before comparison. ntbees2's helper skips missing signals ([`l1_vs_l2_harness.py:266-274`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/helpers/l1_vs_l2_harness.py#L266-L274)), which can produce a vacuous pass and is unsafe for converter acceptance.

### 3. Steady-state windowing

The comparison does not gate on the last percentage of samples. Although the YAML's `last_period_fraction: 0.1` is used for component-stress calculation, waveform acceptance extracts the last **five switching periods** from each result ([`l1_vs_l2_harness.py:294-339`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/helpers/l1_vs_l2_harness.py#L294-L339)). This matters for PLECS variable-step grids, where “last N% of points” neither represents a fixed duration nor aligns to period boundaries ([`core/signal_processing/steady_state.py:1-6`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/core/signal_processing/steady_state.py#L1-L6)).

Boundaries are detected once per layer and shared across all signals in that layer. The detector prefers a gate signal if supplied, otherwise the first current signal, and finally falls back to boundaries synthesized from `f_sw` ([`steady_state.py:456-514`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/core/signal_processing/steady_state.py#L456-L514), [`steady_state.py:562-590`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/core/signal_processing/steady_state.py#L562-L590)). Numerical detection uses signal minima with sub-sample interpolation ([`steady_state.py:140-190`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/core/signal_processing/steady_state.py#L140-L190)).

Convergence is defined as the standard deviation of time-weighted per-period RMS divided by its mean over the last five periods, with a default 1% threshold ([`steady_state.py:231-273`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/core/signal_processing/steady_state.py#L231-L273)). The extraction result records this flag, but the shared comparison helper does not assert it before comparing metrics. PyPLECS should make convergence and “at least five complete periods” explicit preconditions; otherwise a stable-looking comparison can be made on an unsettled tail.

For the semi-manual pack, the simplest deterministic rule is: run long enough to settle; require convergence; select the last five complete periods using the known `f_sw`; and use a gate edge when both exports provide a comparable gate, otherwise use the configured period anchored at the end of the run. Record the chosen window in evidence.

### 4. Metrics and pass/fail policy

Per period, ntbees2 calculates time-weighted mean and RMS with trapezoidal integration, plus sampled min, max, and peak-to-peak; it then averages each metric over the extracted periods ([`steady_state.py:306-330`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/core/signal_processing/steady_state.py#L306-L330), [`steady_state.py:424-449`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/core/signal_processing/steady_state.py#L424-L449)). This is the canonical buck waveform test's primary gate; last-period NRMSE is printed but not asserted ([`test_plecs_l1_vs_l2.py:178-209`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/integration/test_plecs_l1_vs_l2.py#L178-L209)).

The default steady-state tolerances are 3% for mean/RMS, 5% for min/max, and 10% for peak-to-peak; callers override them per signal ([`steady_state.py:595-646`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/core/signal_processing/steady_state.py#L595-L646)). Buck uses that 3/5/10 pattern for inductor current and 5% mean/RMS for switch quantities ([`test_plecs_l1_vs_l2.py:70-88`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/integration/test_plecs_l1_vs_l2.py#L70-L88)). Relative error is symmetric—its denominator is the larger magnitude—and both values below a single absolute floor of `0.01` pass regardless of relative error ([`steady_state.py:604-646`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/core/signal_processing/steady_state.py#L604-L646)).

PyPLECS can reuse the metric family and the “steady-state metrics are authoritative” policy, but not the numeric tolerances unchanged. ntbees2's thresholds were calibrated for an analytical switching-cell model versus a circuit simulator: its inductor-current NRMSE alone permits 20%, while switch-current/voltage NRMSE permits 8% ([`test_plecs_l1_vs_l2.py:70-79`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/integration/test_plecs_l1_vs_l2.py#L70-L79)). PLECS and generated SPICE represent the same circuit and should receive tolerances calibrated from repeated runs with recorded PLECS/SPICE versions. Absolute floors must be per signal/unit rather than one shared `0.01` for both amperes and volts.

### 5. Interpolation, phase alignment, and NRMSE

For time-domain diagnostics, ntbees2 takes the last switching period from both results, shifts each time axis to zero, interpolates the PLECS-side signal onto the reference grid, circularly phase-aligns it using mean-removed cross-correlation, and computes NRMSE ([`l1_vs_l2_harness.py:216-289`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/helpers/l1_vs_l2_harness.py#L216-L289)). NRMSE is RMSE divided by the reference peak-to-peak range, falling back to its maximum absolute value for a nearly constant reference ([`l1_vs_l2_harness.py:66-75`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/helpers/l1_vs_l2_harness.py#L66-L75)).

This is useful diagnostic evidence but has three limits for PyPLECS acceptance:

- Linear interpolation smears discontinuities, especially because the harness itself notes PLECS may supply only about ten points per switching period before it resamples a tolerance-band comparison to 1000 points/period ([`l1_vs_l2_harness.py:402-428`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/helpers/l1_vs_l2_harness.py#L402-L428)).
- The one-period helper independently chooses the best circular shift for each signal, so it can hide a systematic timing error and does not preserve relative phase between signals.
- Peak-to-peak normalization is unstable for nearly constant or very-low-ripple signals.

Therefore PyPLECS should retain aligned NRMSE as an advisory column and record the alignment lag. Its pass/fail result should remain based on time-weighted steady-state metrics. If time-domain alignment later becomes a gate, use one phase reference (normally the gate or `i_L`) and apply its shift to every signal, as ntbees2's three-period tolerance-band implementation does ([`l1_vs_l2_harness.py:359-438`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/helpers/l1_vs_l2_harness.py#L359-L438)).

The ntbees2 tolerance-band KPI—three periods, a band of ±30% of PLECS peak-to-peak, and at least 80% of samples in band—is asserted for some topology tests ([`test_plecs_boost_l1_vs_l2.py:219-254`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/integration/test_plecs_boost_l1_vs_l2.py#L219-L254)). It is deliberately broad and abstraction-specific; it should remain in ntbees2 rather than become PyPLECS converter acceptance.

### 6. Evidence artifacts

The main ntbees2 helper formats stress, NRMSE, and tolerance-band tables to stdout ([`l1_vs_l2_harness.py:78-175`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/helpers/l1_vs_l2_harness.py#L78-L175)). An optional `NTBEES2_DEBUG_PLOT=1` utility saves multi-signal overlay PNGs under `tests/integration/debug_plots` ([`plecs_debug_plot.py:1-21`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/integration/plecs_debug_plot.py#L1-L21), [`plecs_debug_plot.py:152-161`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/tests/integration/plecs_debug_plot.py#L152-L161)). The canonical buck test does not persist raw arrays, metrics, tool versions, or a manifest, so its console output alone is insufficient for a repeatable semi-manual sign-off.

A PyPLECS evidence bundle should preserve:

1. acceptance-manifest snapshot: Circuit Model path/hash, Operating Point, `f_sw`, simulator-specific signal expressions and polarity, chosen window, tolerances;
2. generated `.cir` and `.asc` files plus conversion command/log;
3. PLECS and SPICE/LTspice product/version and solver settings;
4. raw exported time-series files from both simulators;
5. machine-readable comparison results, including convergence, per-metric errors/pass flags, NRMSE, and phase lag;
6. human-readable summary table and last-period overlay plot;
7. for `.asc`, a short load/run checklist and key scalar result, because the parent map explicitly does not require a second full waveform comparison.

## Recommended ownership boundary for the map

### Adapt into PyPLECS tests

- A small test-only waveform reader/comparator; no production `WaveformSet` dependency and no new runtime waveform API.
- A repo-relative acceptance manifest with named Operating Point, explicit signal/polarity mappings for PLECS and SPICE, required signals, window and provisional tolerances.
- Preconditions that fail on missing signals, non-monotonic/empty time axes, insufficient periods, or non-convergence.
- Last-five-period, time-weighted mean/RMS plus signal-appropriate min/max/peak-to-peak as the quantitative `.cir` gate.
- One-period common-phase aligned NRMSE, phase-lag value, and overlay plot as diagnostics.
- Semi-manual evidence ingestion: the maintainer runs the generated `.cir`/`.asc` in the available SPICE tool and exports waveforms; Python performs the repeatable comparison.
- Opt-in execution and explicit skip/missing-evidence reporting, leaving the fast structural converter tests in the default suite. This complements the platform-independent parser/emitter strategy owned by [feat: PLECS-to-netlist converter (.cir + .asc)](https://github.com/tinix84/pyplecs/issues/20), rather than replacing it.

### Keep in ntbees2

- `LayerResult`, `WaveformSet`, analytical Layer-1 converter simulations, topology parameter mappers, and domain stress calculators.
- The four-corner buck sweep and the expected CCM-vs-DCM mismatch test; PyPLECS's first converter acceptance needs a canonical same-circuit buck canary, then can expand only when the parent map decides broader coverage.
- Topology-specific L1-vs-L2 tolerances, including 20% inductor-current NRMSE and the ±30%/80% tolerance-band KPI.
- Broad cross-topology physics-validation suites and ntbees2's optional debug-plot naming/layout.

## Known limitations to carry into the decision ticket

1. ntbees2 compares an analytical approximation to PLECS, not PLECS to emitted SPICE; its thresholds are evidence of harness shape, not evidence of acceptable converter error.
2. Its YAML contains a machine-specific PyPLECS model path and URL ([`buck_lossless.yaml:6-10`](https://github.com/tinix84/ntbees2/blob/fc481090177c705e89de94725df87b111b40c56c/plugins/plecs_adapter/config/buck_lossless.yaml#L6-L10)); PyPLECS acceptance data must be repo-relative and environment-explicit.
3. Missing signals and too-short waveforms are skipped by comparison helpers, and convergence is recorded but not enforced. PyPLECS must fail closed.
4. Independently phase-aligning each signal can conceal timing/polarity defects; use a shared phase reference and retain the lag in evidence.
5. Interpolation around switching edges and sparse variable-step samples make samplewise NRMSE less trustworthy than time-weighted aggregate metrics.
6. The current ntbees2 test output is mostly ephemeral console text; a semi-manual process needs a durable, reviewable evidence bundle.

## Sources consulted

- ntbees2 source at [`fc481090177c705e89de94725df87b111b40c56c`](https://github.com/tinix84/ntbees2/tree/fc481090177c705e89de94725df87b111b40c56c): canonical buck YAML/test, shared comparison harness, steady-state signal processing, PyPLECS REST/signal adapters, pytest configuration, and debug plot utility linked above. The cited files were clean relative to that commit during inspection.
- [feat: PLECS-to-netlist converter (.cir + .asc)](https://github.com/tinix84/pyplecs/issues/20): owning PyPLECS converter scope, day-one models, output formats, and platform-independent structural test strategy.
- Read-only inspection of the current PyPLECS main worktree's uncommitted `tests/test_converter.py` and generated `tests/fixtures/simple_buck_prb.cir`, used only to confirm that current converter checks are structural/textual and that live waveform equivalence is a new acceptance layer; no claim relies on those uncommitted files as a durable source.
