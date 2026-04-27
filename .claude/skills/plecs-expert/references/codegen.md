# codegen

PLECS Coder generates ANSI C from a schematic. Two targets: RSim (rapid sim, interpreted parameters) and Real-Time (inlined). Not wrapped in pyplecs — drive code-gen via PLECS GUI or direct RPC `plecs_rpc('plecs.generateCode', ...)`.

## Targets at a glance

<!-- BEGIN VERBATIM TABLE: codegeneration-table-0 -->

|  | RSim Target | Real-Time Target |
| --- | --- | --- |
| Purpose | Rapid, non-real-time simulations. | Real-time simulations. |
| Technique | A compressed description of the circuit schematic is embedded in the code and interpreted at run time. | Signal and state-space equations are inlined as ANSI C code. |
| Limitations | None | Limited support for naturally commutated devices and non-linear components. |
| Inlining | Parameters may be declared tunable, so that they are evaluated at run time. | All parameters are inlined, i.e. evaluated at compile time and embedded into the generated code. |
| Deployment | Requires distribution of the PLECS RSim module. | Generated code does not have external dependencies. |
| Licensing | If a PLECS Coder license is available at build time , the generated code will run without a license. Otherwise, a PLECS license is required at run time . | Requires a PLECS Coder license at build time . |

_Source: https://docs.plexim.com/plecs/latest/codegeneration/_

<!-- END VERBATIM TABLE: codegeneration-table-0 -->

### Notes
- RSim ships everywhere with no extra deps but needs the RSim runtime DLL.
- Real-Time embeds zero deps in the C output. Best for HIL targets.

## RSim runtime libraries

<!-- BEGIN VERBATIM TABLE: codegeneration-table-1 -->

| Platform | Library Files |
| --- | --- |
| Windows 64-bit | plecs/bin/win64/plecsrsim.dll |
| Mac Intel 64-bit | plecs/bin/maci64/libplecsrsim.dylib |
| Linux 64-bit | plecs/bin/glnxa64/libplecsrsim.so |

_Source: https://docs.plexim.com/plecs/latest/codegeneration/_

<!-- END VERBATIM TABLE: codegeneration-table-1 -->

### Notes
- Ship the platform DLL/dylib/so next to the generated code when deploying RSim.

## Switching algorithm

How the coder resolves switch transitions in generated C. Iterative: small code, variable per-step time. Direct Look-up: bigger code, uniform per-step time.

<!-- BEGIN VERBATIM TABLE: codegeneration-switching-algorithm -->

| Name | Description |
| --- | --- |
| Iterative | PLECS generates code that implements an iterative switching method as described above. As a consequence of the iteration, simulation steps, in which a switching occurs, require more computation time than simulation steps without switching events. This is usually undesirable in real-time simulations because the longest execution time determines the feasible sample rate. |
| Direct Look-up | Alternatively, PLECS can generate code that determines the proper switch conduction states directly as functions of the current physical model states and inputs and the gate signals of externally controlled switches. In order to generate these direct look-up functions, PLECS must analyze all possible transitions between all possible combinations of conduction states. This increases the computation time of the code generation process but yields nearly uniform execution times of simulation steps with or without switching events. |

_Source: https://docs.plexim.com/plecs/latest/codegeneration/_

<!-- END VERBATIM TABLE: codegeneration-switching-algorithm -->

### Notes
- Direct Look-up scales as O(2^n) over n switches in build time. Use for small switching topologies on real-time targets.
- Iterative scales linearly in build time. Variable execution time per step.

## Switch model in generated code

<!-- BEGIN VERBATIM TABLE: codegeneration-codegenswitchtypes -->

| Name | Description |
| --- | --- |
| Ideal switch model | Ideal switches provide an ideal short or open circuit between its two electrical terminals. The ideal switch model adds one or more switching elements to the electrical system, increasing the total number of switching combinations and state-space matrices as described previously. |
| Non-ideal switch model | A fixed-value resistor in parallel with a controlled current source represents the switching element. The state-space matrices do not change if a non-ideal switch is open or closed because the non-ideal switch resistance is constant. Therefore, non-ideal switches do not increase the total number of switching combinations and are suitable for models with large numbers of switches. Each non-ideal switch includes an internal logic that models forced and natural commutation behavior. The switch state determines the controlled current source’s update rule. When the switch is closed, the current update rule drives the voltage across the switching element to zero. The update rule for an open switch drives the current through the device to zero. The update rules do not result in an ideal short or open circuit. Rather, a closed non-ideal switch behaves like a small inductor and an open non-ideal switch a small capacitor with additional series damping elements. The non-ideal switch resistance and the discretization step size determine the effective inductance and capacitance of the switch. The Non-ideal switch resistance (code generation) parameter in the Simulation Parameters menu (see PLECS Blockset Parameters and PLECS Standalone Parameters ) sets the resistance. The non-zero impedance of an open-circuit non-ideal switch will result in a leakage current through the open switch. In AC systems the leakage current may be unacceptably large at the fundamental frequency. Certain electrical switches, like the Breaker component , offer the capability to increase the effective switch impedance at a defined frequency, thereby blocking a specific AC component of the current through the switch. |

_Source: https://docs.plexim.com/plecs/latest/codegeneration/_

<!-- END VERBATIM TABLE: codegeneration-codegenswitchtypes -->

### Notes
- Ideal model = combinatorial state-space matrix per switching combination.
- Non-ideal model = constant matrix; cheap for many switches but adds leakage.

## Generated C entry points

The PLECS-Standalone code-gen output exposes these C functions. Wrap them in a sample-time loop on the target.

<!-- BEGIN VERBATIM TABLE: codegeneration-code-generation-with-plecs-standalone -->

| Name | Description |
| --- | --- |
| void model_initialize ( double time ) | This function should be called once at the beginning of a simulation to initialize the internal data structures and the start value of the global clock for components that depend on the absolute time. |
| void model_step () void model_step ( int task_id ) | This function should be called at every simulation step to advance the model by one step. The second form is used if the multi-tasking mode is enabled (see Scheduling ) and the model has more than one task. |
| void model_output () void model_output ( int task_id ) | This function calculates the outputs of the current simulation step. It should be called at every simulation step before the model_update function. The second form is used if the multi-tasking mode is enabled. |
| void model_update () void model_update ( int task_id ) | This function updates the internal states of the current simulation step. It should be called at every simulation step after the model_output function. The second form is used if the multi-tasking mode is enabled. |
| void model_terminate () | This function should be called at the end of a simulation to release resources that were acquired at the beginning of or during a simulation. |

_Source: https://docs.plexim.com/plecs/latest/codegeneration/_

<!-- END VERBATIM TABLE: codegeneration-code-generation-with-plecs-standalone -->

### Notes
- Loop order: `model_initialize` → repeat (`model_output`, `model_update` OR single `model_step`) → `model_terminate`.
- Split output/update needed for low-latency I/O paths (DMA, DAC).

## General code-gen options

<!-- BEGIN VERBATIM TABLE: codegeneration-general -->

| Name | Description |
| --- | --- |
| Discretization method | This parameter specifies the algorithm used to discretize the physical model equations (see Physical Model Discretization ). |
| Floating point format | This parameter specifies the default data type ( float or double ) that is used for floating point variables in the generated code. |
| Usage of absolute time | This setting allows you to specify the diagnostic action to be taken if PLECS generates code for a component that depends on the absolute time. In order to minimize round-off errors, PLECS generates code to calculate the absolute time using a signed 64-bit integer tick counter. If a simulation runs for an infinite time, this tick counter will eventually reach its maximum value, where it is halted to avoid problems that might occur if the counter was wrapped to the (negative) minimum value, such as a Step block resetting to its initial value. To put things into perspective, assuming a step size of \(1\,\mu\mathrm{s}\) , this would occur after \(292{,}271\) years. Depending on this setting, PLECS will either ignore this condition or it will issue a warning or error message that indicates the components that use the absolute time. |
| Base name | This parameter allows you to specify a custom prefix used to name the generated files and the exported symbols such as the interface functions or the input, output and parameter structs. By default, i.e. if you clear this field, the base name is derived from the model or subsystem name. |
| Output directory | This parameter allows you to specify, where the generated files are stored. This can be an absolute path or a relative path with respect to the location of the model file. The default path is a directory model_codegen next to the model file. |

_Source: https://docs.plexim.com/plecs/latest/codegeneration/_

<!-- END VERBATIM TABLE: codegeneration-general -->

### Notes
- Default output dir = `<model>_codegen` next to `.plecs` file.
- Float vs double: pick float on MCU FPUs without 64-bit support.

## Parameter inlining

<!-- BEGIN VERBATIM TABLE: codegeneration-parameter-inlining -->

| Name | Description |
| --- | --- |
| Default behavior | This setting specifies whether PLECS inlines the parameter values as numeric constants directly into the code ( Inline parameter values ) or generates a data structure from which the values are read ( Keep parameters tunable ). Inlining parameter values reduces the code size and increases the execution speed. However, changing an inlined parameter value requires regenerating and recompiling the code. On the other hand, the values of tunable parameters can be changed at execution time without recompiling the code. |
| Exceptions | For the components listed here, the opposite of the default behavior applies. If the default behavior is to inline all parameter values, the components listed here will keep their parameters tunable and vice versa. To add components to this list, simply drag them from the schematic into the list. Use the Remove button to remove components from the list. To view the selected component in the schematic editor, click the Show component button. |

_Source: https://docs.plexim.com/plecs/latest/codegeneration/_

<!-- END VERBATIM TABLE: codegeneration-parameter-inlining -->

### Notes
- Inline = smaller, faster, recompile to retune.
- Tunable = larger, slower, runtime-writable struct.

## Target options

<!-- BEGIN VERBATIM TABLE: codegeneration-target -->

| Name | Description |
| --- | --- |
| Generate separate output and update functions | If you choose this option, the model_step function is replaced by the two functions model_output and model_update . Choose this option when you need access to the outputs as early as possible during task execution (e.g. to transfer the values to an analog or digital output, update a logger, start a DMA transfer, etc.). |

_Source: https://docs.plexim.com/plecs/latest/codegeneration/_

<!-- END VERBATIM TABLE: codegeneration-target -->

## Scheduling — multi-tasking

<!-- BEGIN VERBATIM TABLE: codegeneration-scheduling -->

| Name | Description |
| --- | --- |
| Tasking mode | This parameter allows you to choose between the single-tasking and multi-tasking modes. |
| Discretization step size | This parameter specifies the base sample time of the generated code and is used to discretize the physical model equations (see Physical Model Discretization ) and continuous state variables of control blocks. |
| Task configuration | If you choose the multi-tasking mode, the dialog will show a table that lets you define a set of tasks. A task has a Task name and a Sample time that must be an integer multiple of the base sample time. The value 0 is replaced with the base sample time itself. If the selected target supports multi-core processing, a task is also associated with a Core . If the selected target has multiple processors, a task is also associated with a CPU . The radio buttons in the Default column specify the default task (see below). Each task must have a unique name, and the core/sample time pairs must also be unique. Note that the task set must comprise a base task that is associated with the base sample time and core 0 (if applicable). For this reason, these columns in the first row are locked. To assign a block or a group of blocks to a task, copy a Task Frame into the schematic, open the Task Frame dialog to choose the desired task, and drag the frame around the blocks. Blocks that are not enclosed by a Task Frame are scheduled in the default task . Note that blocks do not need to have the same sample time as the task that they are assigned to; the block sample time can be continuous or an integer multiple of the task sample time. |
| Thermal model task | In multi-tasking mode you can choose to execute all thermal model calculations in a dedicated task, typically on a separate core with a slower sample time in order to allow for the longer computation time for the calculation of switch losses. This asynchronous execution mode is supported only for power modules in Sub-cycle average configuration. To configure a dedicated thermal model task, select its name in the combo box. The default setting, use native task , means that a thermal model is executed according to the Task Frame configuration synchronously with an associated electrical model. |

_Source: https://docs.plexim.com/plecs/latest/codegeneration/_

<!-- END VERBATIM TABLE: codegeneration-scheduling -->

### Notes
- Multi-tasking spawns one C task per row in the table.
- Sample time per task = integer multiple of base step. 0 means base.

## Simulink Coder options (Blockset)

<!-- BEGIN VERBATIM TABLE: codegeneration-simulink-coder-options -->

| Name | Description |
| --- | --- |
| Code generation target | This parameter specifies the code generation target (see Code Generation Targets ). The default, auto , means that PLECS selects the target depending on the Simulink Coder target. |
| Inline circuit parameters for RSim target | Specifies for the RSim target whether component parameters should be evaluated at compile time and inlined into the code ( on ) or evaluated at run time ( off ). See also Tunable Circuit Parameters in Rapid Simulations . |
| Generate license-free code (requires PLECS Coder license) | If this option is checked, PLECS will attempt to check-out a PLECS Coder license at build time and, if successful, will generate code for the RSim target that will run without requiring a PLECS license. Otherwise, the generated executable will require a PLECS license at run time. |
| Show code generation progress | If this option is checked, PLECS opens a dialog window during code generation that shows the progress of the code generation process. You can abort the process by clicking the Cancel button or closing the dialog window. |

_Source: https://docs.plexim.com/plecs/latest/codegeneration/_

<!-- END VERBATIM TABLE: codegeneration-simulink-coder-options -->
