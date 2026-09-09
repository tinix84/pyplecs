```
uv run pyplecs-convert tests/fixtures/rc_step.asc --format plecs --probe 'C1:Capacitor voltage' --probe 'R1:Resistor current' -o tests/evidence/rc_step/step/2026-08-29T210930Z-ltspice-import
```
Circuit Model: 3 components, 3 nets; parameters {'V_step': '1', 'R': '1e3', 'C': '1e-6', 'T_sim': '5e-3', 'max_step': '1e-6'}.
The step is applied at t = 0: DC source with the capacitor's initial voltage 0 in both simulators (`ic=0` + `uic` in LTspice).
