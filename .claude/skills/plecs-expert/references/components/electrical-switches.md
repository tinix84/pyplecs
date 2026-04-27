# electrical-switches

<!-- BEGIN VERBATIM TABLE: mosfet-parameters -->

| Name | Description |
| --- | --- |
| On-resistance | The resistance \(R_{\mathrm{on}}\) of the conducting device, in ohms \((\Omega)\) . The default is 0 . |
| Initial conductivity | Initial conduction state of the MOSFET. The MOSFET is initially blocking if the parameter evaluates to zero, otherwise it is conducting. |
| Thermal description | Switching losses, conduction losses and thermal equivalent circuit of the component. For more information see chapter Thermal Modeling . If no thermal description is given, the losses are calculated based on the voltage drop \(v_{\mathrm{on}} = R_{\mathrm{on}}\cdot i\) . |
| Thermal interface resistance | The thermal resistance of the interface material between case and heat sink, in \((\mathrm{K}/\mathrm{W})\) . The default is 0 . |
| Number of parallel devices | This parameter is used to simulate the effect of connecting multiple identical devices in parallel while adding only one single switch element to the electrical system equations. Other component parameters such as the Thermal description , the Thermal interface resistance and also the electrical On-resistance refer to the characteristics of an individual device, while the calculated losses and other probe signals refer to the sum over all devices. If \(N_\mathrm{p}\) is the number of parallel devices, each device will conduct \(1/N_\mathrm{p}\) of the total current through the component, and the total component loss will be \(N_\mathrm{p}\) times the loss of an individual device. The effective electrical on-resistance and the effective thermal interface resistance of the component are also \(1/N_\mathrm{p}\) times the respective parameter values. The default is 1 . Note If Number of parallel devices is greater than \(1\) , the component itself cannot be vectorized, i.e. all other component parameters must have scalar values, and the component terminals must be connected to a scalar connection (see also Vectorizing Physical Components ). Example Model See the example model “Thermal Modeling with Parallel Devices” . Find it in PLECS under Help > PLECS Documentation > List of Example Models . |
| Initial temperature | This parameter is used only if the device has an internal thermal impedance and specifies the temperature of the thermal capacitance at the junction at simulation start. The temperatures of the other thermal capacitances are initialized based on a thermal “DC” analysis. If the parameter is left blank, all temperatures are initialized from the external temperature. See also Temperature Initialization . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/mosfet/_

<!-- END VERBATIM TABLE: mosfet-parameters -->

<!-- BEGIN VERBATIM TABLE: mosfet-probes -->

| Probe signal | Description |
| --- | --- |
| MOSFET voltage | The voltage measured between drain and source. |
| MOSFET current | The current through the MOSFET flowing from drain to source. |
| MOSFET gate signal | The gate input signal of the MOSFET. |
| MOSFET conductivity | Conduction state of the internal switch. The signal outputs \(0\) when the MOSFET is blocking, and \(1\) when it is conducting. |
| MOSFET junction temperature | Temperature of the first thermal capacitor in the equivalent Cauer network. |
| MOSFET conduction loss | Continuous thermal conduction losses in watts \((\mathrm{W})\) . Only defined if the component is placed on a heat sink. |
| MOSFET switching loss | Instantaneous thermal switching losses in joules \((\mathrm{J})\) . Only defined if the component is placed on a heat sink. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/mosfet/_

<!-- END VERBATIM TABLE: mosfet-probes -->

<!-- BEGIN VERBATIM TABLE: igbt-parameters -->

| Name | Description |
| --- | --- |
| Forward voltage | Additional dc voltage \(V_\mathrm{f}\) in volts \((\mathrm{V})\) between collector and emitter when the IGBT is conducting. The default is 0 . |
| On-resistance | The resistance \(R_\mathrm{on}\) of the conducting device, in ohms \((\Omega)\) . The default is 0 . |
| Initial conductivity | Initial conduction state of the IGBT. The IGBT is initially blocking if the parameter evaluates to zero, otherwise it is conducting. |
| Thermal description | Switching losses, conduction losses and thermal equivalent circuit of the component. For more information see chapter Thermal Modeling . If no thermal description is given, the losses are calculated based on the voltage drop \(v_\mathrm{on} = V_\mathrm{f} + R_\mathrm{on}\cdot i\) . |
| Thermal interface resistance | The thermal resistance of the interface material between case and heat sink, in \((\mathrm{K}/\mathrm{W})\) . The default is 0 . |
| Initial temperature | This parameter is used only if the device has an internal thermal impedance and specifies the temperature of the thermal capacitance at the junction at simulation start. The temperatures of the other thermal capacitances are initialized based on a thermal “DC” analysis. If the parameter is left blank, all temperatures are initialized from the external temperature. See also Temperature Initialization . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/igbt/_

<!-- END VERBATIM TABLE: igbt-parameters -->

<!-- BEGIN VERBATIM TABLE: igbt-probes -->

| Probe signal | Description |
| --- | --- |
| IGBT voltage | The voltage measured between collector and emitter. |
| IGBT current | The current through the IGBT flowing from collector to emitter. |
| IGBT gate signal | The gate input signal of the IGBT. |
| IGBT conductivity | Conduction state of the internal switch. The signal outputs \(0\) when the IGBT is blocking, and \(1\) when it is conducting. |
| IGBT junction temperature | Temperature of the first thermal capacitor in the equivalent Cauer network. |
| IGBT conduction loss | Continuous thermal conduction losses in watts \((\mathrm{W})\) . Only defined if the component is placed on a heat sink. |
| IGBT switching loss | Instantaneous thermal switching losses in joules \((\mathrm{J})\) . Only defined if the component is placed on a heat sink. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/igbt/_

<!-- END VERBATIM TABLE: igbt-probes -->

<!-- BEGIN VERBATIM TABLE: diode-parameters -->

| Name | Description |
| --- | --- |
| Forward voltage | Additional dc voltage \(V_\mathrm{f}\) in volts \((\mathrm{V})\) between anode and cathode when the diode is conducting. The default is 0 . |
| On-resistance | The resistance \(R_\mathrm{on}\) of the conducting device, in ohms \((\Omega)\) . The default is 0 . |
| Thermal description | Switching losses, conduction losses and thermal equivalent circuit of the component. For more information see chapter Thermal Modeling . If no thermal description is given, the losses are calculated based on the voltage drop \(v_\mathrm{on} = V_\mathrm{f} + R_\mathrm{on}\cdot i\) . |
| Thermal interface resistance | The thermal resistance of the interface material between case and heat sink, in \((\mathrm{K}/\mathrm{W})\) . The default is 0 . |
| Number of parallel devices | This parameter is used to simulate the effect of connecting multiple identical devices in parallel while adding only one single switch element to the electrical system equations. Other component parameters such as the Thermal description , the Thermal interface resistance and also the electrical On-resistance refer to the characteristics of an individual device, while the calculated losses and other probe signals refer to the sum over all devices. If \(N_\mathrm{p}\) is the number of parallel devices, each device will conduct \(1/N_\mathrm{p}\) of the total current through the component, and the total component loss will be \(N_\mathrm{p}\) times the loss of an individual device. The effective electrical on-resistance and the effective thermal interface resistance of the component are also \(1/N_\mathrm{p}\) times the respective parameter values. The default is 1 . Note If Number of parallel devices is greater than \(1\) , the component itself cannot be vectorized, i.e. all other component parameters must have scalar values, and the component terminals must be connected to a scalar connection (see also Vectorizing Physical Components ). Example Model See the example model “Thermal Modeling with Parallel Devices” . Find it in PLECS under Help > PLECS Documentation > List of Example Models . |
| Initial temperature | This parameter is used only if the device has an internal thermal impedance and specifies the temperature of the thermal capacitance at the junction at simulation start. The temperatures of the other thermal capacitances are initialized based on a thermal “DC” analysis. If the parameter is left blank, all temperatures are initialized from the external temperature. See also Temperature Initialization . |
| Switch model (CPU code generation) | Select the switch model in the generated code. |
| Fundamental grid frequency | Frequency where non-ideal switches in the open state have increased series impedance, in hertz \((\mathrm{Hz})\) . The default is 0 . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/diode/_

<!-- END VERBATIM TABLE: diode-parameters -->

<!-- BEGIN VERBATIM TABLE: diode-probes -->

| Probe signal | Description |
| --- | --- |
| Diode voltage | The voltage measured between anode and cathode. |
| Diode current | The current through the diode flowing from anode to cathode. |
| Diode conductivity | Conduction state of the internal switch. The signal outputs \(0\) when the diode is blocking, and \(1\) when it is conducting. |
| Diode junction temperature | Temperature of the first thermal capacitor in the equivalent Cauer network. |
| Diode conduction loss | Continuous thermal conduction losses in watts \((\mathrm{W})\) . Only defined if the component is placed on a heat sink. |
| Diode switching loss | Instantaneous thermal switching losses in joules \((\mathrm{J})\) . Only defined if the component is placed on a heat sink. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/diode/_

<!-- END VERBATIM TABLE: diode-probes -->

<!-- BEGIN VERBATIM TABLE: switch-parameters -->

| Name | Description |
| --- | --- |
| Initial conductivity | Initial conduction state of the switch. The switch is initially open if the parameter evaluates to zero, otherwise closed. This parameter may either be a scalar or a vector corresponding to the implicit width of the component. The default value is 0 . |
| Switch model (CPU code generation) | Select the switch model in the generated code. |
| Fundamental grid frequency | Frequency where non-ideal switches in the open state have increased series impedance, in hertz \((\mathrm{Hz})\) . The default is 0 . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/switch/_

<!-- END VERBATIM TABLE: switch-parameters -->

<!-- BEGIN VERBATIM TABLE: switch-probes -->

| Probe signal | Description |
| --- | --- |
| Switch conductivity | Conduction state of the switch. The signal outputs \(0\) if the switch is open, and \(1\) if it is closed. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/switch/_

<!-- END VERBATIM TABLE: switch-probes -->
