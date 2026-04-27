# electrical-passive

## Resistor

`Lib/Electrical/Passive Components/Resistor`. Linear ohmic dissipator. Pins: 1=p, 2=n. Sign: i flows p→n.

Wrapped in pyplecs: yes — `pyplecs.plecs_components.ResistorPlecsMdl`.

SPICE map: `R<name> p n {R}`.

<!-- BEGIN VERBATIM TABLE: resistor-parameters -->

| Name | Description |
| --- | --- |
| Resistance | The resistance in ohms \((\Omega)\) . All positive and negative values are accepted, including 0 and inf ( \(\infty\) ). The default is 1 . In a vectorized component, all internal resistors have the same resistance if the parameter is a scalar. To specify the resistances individually use a vector \(\left[ R_1\; R_2 \ldots R_n\right]\) . The length \(n\) of the vector determines the width of the component. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/resistor/_

<!-- END VERBATIM TABLE: resistor-parameters -->

<!-- BEGIN VERBATIM TABLE: resistor-probes -->

| Probe signal | Description |
| --- | --- |
| Resistor voltage | The voltage measured across the resistor from the positive to the negative terminal, in volts ( \(V\) ). |
| Resistor current | The current flowing through the resistor, in amperes ( \(A\) ). A current entering the resistor at the positive terminal is counted positive. |
| Resistor power | The power consumed by the resistor, in watts ( \(W\) ). |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/resistor/_

<!-- END VERBATIM TABLE: resistor-probes -->

### Notes
- Vector form `[R_1 R_2 ... R_n]` builds n parallel scalar resistors with shared width.
- Power probe = `v_R * i_R`. Sign matches passive convention.

## Inductor

`Lib/Electrical/Passive Components/Inductor`. Stores magnetic energy. Pins: 1=p, 2=n. Sign: i_L flows p→n.

Wrapped in pyplecs: yes — `pyplecs.plecs_components.InductorPlecsMdl`.

SPICE map: `L<name> p n {L} IC={IL_init}`.

<!-- BEGIN VERBATIM TABLE: inductor-parameters -->

| Name | Description |
| --- | --- |
| Inductance | The inductance in henries \((\mathrm{H})\) . All finite positive and negative values are accepted, including 0 . The default is 0.001 . In a vectorized component, all internal inductors have the same inductance if the parameter is a scalar. To specify the inductances individually use a vector \([ L_1\; L_2 \ldots L_n]\) . The length \(n\) of the vector determines the component’s  width: \[\begin{split}\begin{bmatrix} v_1 \\ v_2 \\ \vdots \\ v_n \end{bmatrix} = \begin{bmatrix} L_{1} & 0 & \cdots & 0 \\ 0 & L_{2} & \cdots & 0 \\ \vdots & \vdots & \ddots & \vdots \\ 0 & 0 & \cdots & L_{n} \end{bmatrix} \begin{bmatrix} \frac{d}{dt} i_1\\ \frac{d}{dt} i_2\\ \vdots \\ \frac{d}{dt} i_n \end{bmatrix}\end{split}\] In order to model a magnetic coupling between the internal inductors enter a square matrix. The size \(n\) of the matrix corresponds to the width of the component. \(L_{i}\) is the self inductance of the internal inductor and \(M_{i,j}\) the mutual inductance: \[\begin{split}\begin{bmatrix} v_1 \\ v_2 \\ \vdots \\ v_n \end{bmatrix} = \begin{bmatrix} L_{1} & M_{1,2} & \cdots & M_{1,n} \\ M_{2,1} & L_{2} & \cdots & M_{2,n} \\ \vdots & \vdots & \ddots & \vdots \\ M_{n,1} & M_{n,2} & \cdots & L_{n} \end{bmatrix} \begin{bmatrix} \frac{d}{dt} i_1\\ \frac{d}{dt} i_2\\ \vdots \\ \frac{d}{dt} i_n \end{bmatrix}\end{split}\] The inductance matrix must be invertible, i.e. it may not be singular. A singular inductance matrix results for example when two or more inductors are ideally coupled. To model this, use an inductor in parallel with an Ideal Transformer . The relationship between the coupling factor \(k_{i,j}\) and the mutual inductance \(M_{i,j}\) is \[M_{i,j} = M_{j,i} = k_{i,j} \sqrt{L_i \cdot L_j}\] |
| Initial current | The initial current through the inductor at simulation start, in amperes \((\mathrm{A})\) . This parameter may either be a scalar or a vector corresponding to the width of the component. The direction of a positive initial current is indicated by a small arrow in the component symbol. The default of the initial current is 0 . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/inductor/_

<!-- END VERBATIM TABLE: inductor-parameters -->

<!-- BEGIN VERBATIM TABLE: inductor-probes -->

| Probe signal | Description |
| --- | --- |
| Inductor current | The current flowing through the inductor, in amperes \((\mathrm{A})\) . The direction of a positive current is indicated with a small arrow in the component symbol. |
| Inductor voltage | The voltage measured across the inductor, in volts \((\mathrm{V})\) . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/inductor/_

<!-- END VERBATIM TABLE: inductor-probes -->

### Notes
- Initial current `IL_init` requires UIC in the `.tran` directive on SPICE side.
- Pin order matters for sign of `i_L` probe.
- Coupled inductors use a matrix `L`. Off-diagonal entries are mutual inductances `M_ij`.

## Capacitor

`Lib/Electrical/Passive Components/Capacitor`. Stores electric energy. Pins: 1=p (marked +), 2=n. Sign: v_C measured + over −.

Wrapped in pyplecs: yes — `pyplecs.plecs_components.CapacitorPlecsMdl`.

SPICE map: `C<name> p n {C} IC={V_init}`.

<!-- BEGIN VERBATIM TABLE: capacitor-parameters -->

| Name | Description |
| --- | --- |
| Capacitance | The value of the capacitor, in farads \((\mathrm{F})\) . All finite positive and negative values are accepted, including 0 . The default is 100e-6 . In a vectorized component, all internal capacitors have the same value if the parameter is a scalar. To specify the capacitances individually use a vector \([ C_1\; C_2 \ldots C_n]\) . The length \(n\) of the vector determines the component’s width: \[\begin{split}\left[ \begin{array}{c}i_1 \\i_2 \\ \vdots \\i_n \\ \end{array} \right] \; = \; \left[ \begin{array}{cccc} C_{1} & 0 & \cdots & 0 \\ 0 & C_{2} & \cdots & 0 \\ \vdots & \vdots & \ddots & \vdots \\ 0 & 0 & \cdots & C_{n} \\ \end{array} \right] \cdot \left[ \begin{array}{c} \frac{d}{dt} v_1\\ \frac{d}{dt} v_2\\ \vdots \\ \frac{d}{dt} v_n\\ \end{array} \right]\end{split}\] In order to model a coupling between the internal capacitors enter a square matrix. The size \(n\) of the matrix corresponds to the width of the component: \[\begin{split}\left[ \begin{array}{c}i_1 \\i_2 \\ \vdots \\i_n \\ \end{array} \right] \; = \; \left[ \begin{array}{cccc} C_{1} & C_{1,2} & \cdots & C_{1,n} \\ C_{2,1} & C_{2} & \cdots & C_{2,n} \\ \vdots & \vdots & \ddots & \vdots \\ C_{n,1} & C_{n,2} & \cdots & C_{n} \\ \end{array} \right] \cdot \left[ \begin{array}{c} \frac{d}{dt} v_1\\ \frac{d}{dt} v_2\\ \vdots \\ \frac{d}{dt} v_n\\ \end{array} \right]\end{split}\] The capacitance matrix must be invertible, i.e. it may not be singular. |
| Initial voltage | The initial voltage of the capacitor at simulation start, in volts \((\mathrm{V})\) . This parameter may either be a scalar or a vector corresponding to the width of the component. The positive pole is marked with a “+”. The initial voltage default is 0 . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/capacitor/_

<!-- END VERBATIM TABLE: capacitor-parameters -->

<!-- BEGIN VERBATIM TABLE: capacitor-probes -->

| Probe signal | Description |
| --- | --- |
| Capacitor voltage | The voltage measured across the capacitor, in volts \((\mathrm{V})\) . A positive voltage is measured when the potential at the terminal marked with “+” is greater than the potential at the unmarked terminal. |
| Capacitor current | The current flowing through the capacitor, in amperes \((\mathrm{A})\) . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/capacitor/_

<!-- END VERBATIM TABLE: capacitor-probes -->

### Notes
- Initial voltage `V_init` requires UIC in `.tran` on SPICE side.
- Coupled capacitors use a square matrix; matrix must be invertible.

## Transformer

`Lib/Electrical/Passive Components/Transformer`. Multi-winding magnetic coupling with finite magnetizing inductance. Pins: depend on `[w1 w2]`.

Wrapped in pyplecs: yes — `pyplecs.plecs_components.TransformerPlecsMdl`.

SPICE map: two coupled `L` lines plus `K<name> Lp Ls {coupling}`.

<!-- BEGIN VERBATIM TABLE: transformer-parameters -->

| Name | Description |
| --- | --- |
| Number of windings | A two-element vector \([w_1\; w_2]\) containing the number of windings on the primary side \(w_1\) and on the secondary side \(w_2\) . The default is [1 1] , which represents a two-winding transformer with opposite windings. |
| Number of turns | A row vector specifying the number of turns for each winding. The vector length must match the total number of primary and secondary side windings. First, all primary side windings are specified, followed by the specifications for all secondary side windings. |
| Polarity | A string consisting of one + or - per winding specifying the winding polarity. A single + or - is applied to all windings. |
| Magnetizing inductance | A non-zero scalar specifying the magnetizing inductance referred to the first winding, in henries \((\mathrm{H})\) . |
| Initial magnetizing current | A scalar specifying the initial current through the magnetizing inductance at simulation start, in amperes \((\mathrm{A})\) . Must be zero if the magnetizing inductance is infinite inf . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/transformer/_

<!-- END VERBATIM TABLE: transformer-parameters -->

### Notes
- Magnetizing inductance referred to first winding. Set inf for ideal transformer.
- Polarity vector controls dot orientation per winding.
- Initial magnetizing current must be 0 when L_m = inf.
