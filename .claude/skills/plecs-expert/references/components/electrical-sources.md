# electrical-sources

<!-- BEGIN VERBATIM TABLE: acvoltagesource-parameters -->

| Name | Description |
| --- | --- |
| Amplitude | The amplitude \(A\) of the voltage, in volts \((\mathrm{V})\) . The default is 1 . |
| Frequency | The angular frequency \(\omega\) , in \(\left( \frac{\mathrm{rad}}{\mathrm{s}} \right)\) . The default is 2*pi*50 which corresponds to \(50\,\mathrm{Hz}\) . |
| Phase | The phase shift \(\varphi\) , in radians. The default is 0 . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/acvoltagesource/_

<!-- END VERBATIM TABLE: acvoltagesource-parameters -->

<!-- BEGIN VERBATIM TABLE: acvoltagesource-probes -->

| Probe signal | Description |
| --- | --- |
| Source voltage | The source voltage in volts \((\mathrm{V})\) . |
| Source current | The current flowing through the source, in amperes \((\mathrm{A})\) . |
| Source power | The instantaneous output power of the source, in watts \((\mathrm{W})\) . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/acvoltagesource/_

<!-- END VERBATIM TABLE: acvoltagesource-probes -->

<!-- BEGIN VERBATIM TABLE: dcvoltagesource-parameters -->

| Name | Description |
| --- | --- |
| Voltage | The magnitude of the constant voltage, in volts \((\mathrm{V})\) . This parameter may either be a scalar or a vector defining the width of the component. The default value is 1 . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/dcvoltagesource/_

<!-- END VERBATIM TABLE: dcvoltagesource-parameters -->

<!-- BEGIN VERBATIM TABLE: dcvoltagesource-probes -->

| Probe signal | Description |
| --- | --- |
| Source voltage | The source voltage in volts \((\mathrm{V})\) . |
| Source current | The current flowing through the source, in amperes \((\mathrm{A})\) . |
| Source power | The instantaneous output power of the source, in watts \((\mathrm{W})\) . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/dcvoltagesource/_

<!-- END VERBATIM TABLE: dcvoltagesource-probes -->

<!-- BEGIN VERBATIM TABLE: controlledvoltagesource-parameters -->

| Name | Description |
| --- | --- |
| Discretization behavior | Specifies whether a zero-order hold or a first-order hold is applied to the input signal when the model is discretized. For details, see Physical Model Discretization . The option Non-causal zero-order hold applies a zero-order hold with the input signal value from the current simulation step instead of the previous one. This option can be used to compensate for a known delay of the input signal. |
| Allow state-space inlining | For expert use only! When set to on and the input signal is a linear combination of electrical measurements, PLECS will eliminate the input variable from the state-space equations and substitute it with the corresponding output variables. The default is off . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/controlledvoltagesource/_

<!-- END VERBATIM TABLE: controlledvoltagesource-parameters -->

<!-- BEGIN VERBATIM TABLE: controlledvoltagesource-probes -->

| Probe signal | Description |
| --- | --- |
| Source voltage | The source voltage in volts \((\mathrm{V})\) . |
| Source current | The current flowing through the source, in amperes \((\mathrm{A})\) . |
| Source power | The instantaneous output power of the source, in watts \((\mathrm{W})\) . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/controlledvoltagesource/_

<!-- END VERBATIM TABLE: controlledvoltagesource-probes -->

<!-- BEGIN VERBATIM TABLE: controlledcurrentsource-parameters -->

| Name | Description |
| --- | --- |
| Discretization behavior | Specifies whether a zero-order hold or a first-order hold is applied to the input signal when the model is discretized. For details, see Physical Model Discretization . The option Non-causal zero-order hold applies a zero-order hold with the input signal value from the current simulation step instead of the previous one. This option can be used to compensate for a known delay of the input signal. |
| Allow state-space inlining | For expert use only! When set to on and the input signal is a linear combination of electrical measurements, PLECS will eliminate the input variable from the state-space equations and substitute it with the corresponding output variables. The default is off . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/controlledcurrentsource/_

<!-- END VERBATIM TABLE: controlledcurrentsource-parameters -->

<!-- BEGIN VERBATIM TABLE: controlledcurrentsource-probes -->

| Probe signal | Description |
| --- | --- |
| Source current | The source current in amperes \((\mathrm{A})\) . |
| Source voltage | The voltage measured across the source, in volts \((\mathrm{V})\) . |
| Source power | The instantaneous output power of the source, in watts \((\mathrm{W})\) . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/controlledcurrentsource/_

<!-- END VERBATIM TABLE: controlledcurrentsource-probes -->
