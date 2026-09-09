# rc_step — LTspice schematic imported to PLECS, step response compared

LTspice 26.0.1 for Windows (reference, 5018 samples) vs PLECS 4.7.7 (5001 samples) on `v_C`, 0 … 0.005 s, τ = 0.001 s.

**Verdict: PASS** — max |Δ| / step = 1.062e-07 (tolerance 1.0%) at t = 5e-06 s; vs analytic: LTspice 1.062e-07, PLECS 1.247e-07.

| point | t [s] | analytic | LTspice | PLECS | LTspice err | PLECS err |
|---|---|---|---|---|---|---|
| tau | 0.001 | 0.63212 | 0.63212 | 0.63212 | 0.000% | 0.000% |
| 3tau | 0.003 | 0.95021 | 0.95021 | 0.95021 | 0.000% | 0.000% |
| end | 0.005 | 0.99326 | 0.99326 | 0.99326 | 0.000% | 0.000% |
