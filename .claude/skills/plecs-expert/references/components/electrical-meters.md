# electrical-meters

<!-- BEGIN VERBATIM TABLE: voltmeter-probes -->

| Probe signal | Description |
| --- | --- |
| Measured voltage | The measured voltage in volts \((\mathrm{V})\) . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/voltmeter/_

<!-- END VERBATIM TABLE: voltmeter-probes -->

<!-- BEGIN VERBATIM TABLE: ammeter-probes -->

| Probe signal | Description |
| --- | --- |
| Measured current | The measured current in amperes ( \(\mathrm{A}\) ). |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/ammeter/_

<!-- END VERBATIM TABLE: ammeter-probes -->

<!-- BEGIN VERBATIM TABLE: scope-scope-setup -->

| Name | Description |
| --- | --- |
| Number of plots | This parameter specifies the number of plots shown in the scope window. Each plot corresponds to a terminal on the outside of the block. For each plot, a tab is displayed in the lower part of the dialog where the plot settings can be edited. |
| Sample time | A scalar specifying the sampling period or a two-element vector specifying the sampling period and offset, in seconds \((\mathrm{s})\) , used to sample the input signals. The default is -1 (inherited). Other valid settings are 0 (continuous) or a valid fixed-step discrete sample time pair. See also section Sample Times . |
| Limit samples | If this option is selected, the PLECS scope will only save the last \(n\) sample values during a simulation. It can be used in long simulations to limit the amount of memory that is used by PLECS. If the option is unchecked, all sample values are stored in memory. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/scope/_

<!-- END VERBATIM TABLE: scope-scope-setup -->

<!-- BEGIN VERBATIM TABLE: scope-time-axis-parameters -->

| Name | Description |
| --- | --- |
| Display time axis | The time axis is either shown underneath each plot or underneath the last plot only. |
| Time axis label | The time axis label is shown below the time axis in the scope. |
| Time range | The time range value determines the initial time range that is displayed in the scope, in seconds \((\mathrm{s})\) . If set to auto , the simulation time range is used. |
| Scrolling mode | The scrolling mode determines the way in which the x-axis is scrolled if during a simulation the current simulation time goes beyond the right x-axis limit. In the paged mode, the plots are cleared when the simulation time reaches the right limit and the x-axis is scrolled by one full x-axis span, i.e. the former right limit becomes the new left limit. In the continuous mode, the plots are continuously scrolled so that new data is always drawn at the right plot border. Note that this mode may affect runtime performance as it causes frequent updates of relatively large screen areas. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/scope/_

<!-- END VERBATIM TABLE: scope-time-axis-parameters -->

<!-- BEGIN VERBATIM TABLE: scope-individual-plot-parameters -->

| Name | Description |
| --- | --- |
| Title | The name which is displayed above the plot. |
| Axis label | The axis label is displayed on the left of the y-axis. |
| Y-limits | The initial lower and upper bound of the y-axis. If set to auto , the y-axis limits are automatically chosen based on the minimum and maximum curve value in the visible time range. If you check the Keep baseline option, the limits are chosen so that the specified baseline value is always included. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/scope/_

<!-- END VERBATIM TABLE: scope-individual-plot-parameters -->
