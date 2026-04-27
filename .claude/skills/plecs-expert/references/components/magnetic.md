# magnetic

## Magnetic Permeance

`Lib/Magnetic/Permeance`. Magnetic-domain analog of capacitance. Pins: 1=marked, 2=unmarked. Sign: flux Φ flows marked→unmarked.

Wrapped in pyplecs: no.

SPICE map: n/a (no SPICE equivalent).

<!-- BEGIN VERBATIM TABLE: magneticpermeance-parameters -->

| Name | Description |
| --- | --- |
| Permeance | Magnetic permeance of the flux path, in webers per ampere-turn \((\mathrm{Wb/A})\) . |
| Initial MMF | Magneto-motive force at simulation start, in ampere-turns \((\mathrm{A})\) . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/magneticpermeance/_

<!-- END VERBATIM TABLE: magneticpermeance-parameters -->

<!-- BEGIN VERBATIM TABLE: magneticpermeance-probes -->

| Probe signal | Description |
| --- | --- |
| MMF | The magneto-motive force measured from the marked to the unmarked terminal, in ampere-turns \((\mathrm{A})\) . |
| Flux | The magnetic flux flowing through the component, in webers \((\mathrm{Wb})\) . A flux entering at the marked terminal is counted as positive. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/magneticpermeance/_

<!-- END VERBATIM TABLE: magneticpermeance-probes -->

### Notes
- Permeance P = 1/Reluctance. Units Wb/A. Larger P = easier flux flow.
- Magnetic-domain dual: MMF↔V, flux-rate↔I, permeance↔C.

## Constant MMF

`Lib/Magnetic/Constant MMF`. Ideal magneto-motive-force source. Pins: 1=marked, 2=unmarked.

Wrapped in pyplecs: no.

SPICE map: n/a (no SPICE equivalent).

<!-- BEGIN VERBATIM TABLE: constantmmf-parameters -->

| Name | Description |
| --- | --- |
| Voltage | The magnitude of the MMF, in ampere-turns \((\mathrm{A})\) . The default value is 1 . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/constantmmf/_

<!-- END VERBATIM TABLE: constantmmf-parameters -->

<!-- BEGIN VERBATIM TABLE: constantmmf-probes -->

| Probe signal | Description |
| --- | --- |
| MMF | The magneto-motive force of the source, in ampere-turns \((\mathrm{A})\) . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/constantmmf/_

<!-- END VERBATIM TABLE: constantmmf-probes -->

### Notes
- Parameter labelled `Voltage` but unit is ampere-turns (analogy with electrical V source).
- Models permanent magnet or DC bias winding.

## Flux Rate Meter

`Lib/Magnetic/Flux Rate Meter`. Outputs dΦ/dt across two magnetic terminals. Pins: 1=p, 2=n, 3=signal out.

Wrapped in pyplecs: no.

SPICE map: n/a (no SPICE equivalent).

<!-- BEGIN VERBATIM TABLE: fluxratemeter-probes -->

| Probe signal | Description |
| --- | --- |
| Flux rate | The rate-of-change \(\dot{\Phi}\) of magnetic flux flowing through the component, in \((\mathrm{Wb}/\mathrm{s})\) or \(\mathrm{V}\) . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/fluxratemeter/_

<!-- END VERBATIM TABLE: fluxratemeter-probes -->

### Notes
- Output Wb/s = volts per turn. Multiply by N to get winding voltage.
- Loss-free. Inserts as zero-MMF branch.
