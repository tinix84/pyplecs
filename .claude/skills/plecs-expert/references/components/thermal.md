# thermal

<!-- BEGIN VERBATIM TABLE: heatsink-parameters -->

| Name | Description |
| --- | --- |
| Number of terminals | This parameter allows you to change the number of external thermal connectors of a heat sink. The default is 0 . |
| Thermal capacitance | The value of the internal thermal capacitance, in \((\mathrm{J}/\mathrm{K})\) . The default is 0 . If the capacitance is set to zero, the heat sink must be connected to an external thermal capacitance or to a fixed temperature. |
| Initial temperature | The initial temperature difference between the heat sink and the thermal reference at simulation start, in degrees Celsius \((^\circ\mathrm{C})\) . If left blank or if the value is nan , PLECS will initialize the value based on a thermal “DC” analysis, see Temperature Initialization . |
| Width | This parameter allows you to set the width of the internal thermal capacitance and the external terminals. The default is 1 . A non-scalar heat sink can enclose only components that have the same width. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/heatsink/_

<!-- END VERBATIM TABLE: heatsink-parameters -->

<!-- BEGIN VERBATIM TABLE: heatsink-probes -->

| Probe signal | Description |
| --- | --- |
| Temperature | The temperature difference between the heat sink and the thermal reference, in degrees Celsius \((^\circ\mathrm{C})\) . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/heatsink/_

<!-- END VERBATIM TABLE: heatsink-probes -->

<!-- BEGIN VERBATIM TABLE: thermalcapacitor-parameters -->

| Name | Description |
| --- | --- |
| Capacitance | The value of the capacitor, in \((\mathrm{J/K})\) . All finite positive and negative values are accepted, including 0 . The default is 1 . |
| Initial temperature | The initial temperature difference between the thermal ports or between the thermal port and thermal reference at simulation start, in degrees Celsius \((^\circ\mathrm{C})\) . If left blank or if the value is nan , PLECS will initialize the value based on a thermal DC analysis, see Temperature Initialization . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/thermalcapacitor/_

<!-- END VERBATIM TABLE: thermalcapacitor-parameters -->

<!-- BEGIN VERBATIM TABLE: thermalcapacitor-probes -->

| Probe signal | Description |
| --- | --- |
| Temperature | The temperature difference measured across the capacitance, in degrees Celsius \((^\circ\mathrm{C})\) . A positive value is measured when the temperature at the terminal marked with “+” is greater than the temperature at the unmarked terminal. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/thermalcapacitor/_

<!-- END VERBATIM TABLE: thermalcapacitor-probes -->

<!-- BEGIN VERBATIM TABLE: ambienttemperature-parameters -->

| Name | Description |
| --- | --- |
| Allow vector connection to scalar heat sink | This parameter is only relevant if the block has a non-scalar inner connection. When the parameter is set to on , the enclosing heat sink must also be non-scalar and have a matching width. When the parameter is set to off (the default), the enclosing heat sink may also be scalar, and all elements of the inner connection will be connected to the single heat sink element. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/ambienttemperature/_

<!-- END VERBATIM TABLE: ambienttemperature-parameters -->
