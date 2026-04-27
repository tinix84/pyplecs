# solver

Solver settings live in the model's Simulation Parameters dialog. Override per run via the `SolverOpts` field; see [rpc-api.md](rpc-api.md). Wrapped via `pyplecs.PlecsServer.simulate` and `simulate_raw` — pass `solver_opts={'Solver': 'radau', ...}` etc.

## Simulation Time

Top-level run window. `StartTime` and `TimeSpan` are also exposed in `SolverOpts`.

<!-- BEGIN VERBATIM TABLE: simulation-parameters-simulation-time -->

| Name | Description |
| --- | --- |
| Start Time | The start time specifies the initial value of the simulation time variable \(t\) at the beginning of a simulation, in seconds \((\mathrm{s})\) . If a simulation is started from a stored system state (see System State ), this parameter is ignored and the simulation time specified in the system state is used instead. |
| Time Span | The simulation ends when the simulation time has advanced by the specified time span. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-simulation-time -->

### Notes
- `StartTime` ignored when running from a stored system state.

## Solver — variable-step

Two variable-step methods: DOPRI (non-stiff, default) and RADAU (stiff). `auto` picks DOPRI then switches to RADAU on stiffness detection.

<!-- BEGIN VERBATIM TABLE: simulation-parameters-solver -->

| Name | Description |
| --- | --- |
| Variable-step | A variable-step solver can adopt the step size during the simulation depending on model dynamics. At times of rapid state changes the step size is reduced to maintain accuracy; when the model states change only slowly, the step size is increased to save unnecessary computations. The step size can also be adjusted in order to accurately simulate discontinuities. For these reasons, a variable-step solver should generally be preferred. DOPRI is a variable-step solver using a fifth-order accurate explicit Runge-Kutta formula (the Dormand-Prince pair). This solver is most efficient for non-stiff systems and is selected by default. A stiff system can be sloppily defined as one having time constants that differ by several orders of magnitudes. Such a system forces a non-stiff solver to choose excessively small time steps. If DOPRI detects stiffness in a system, it will abort the simulation with the recommendation to switch to a stiff solver. RADAU is a variable-step solver for stiff systems using a fifth-order accurate fully-implicit three-stage Runge-Kutta formula (Radau IIA). For non-stiff systems DOPRI is more efficient than RADAU. When auto is selected, PLECS starts a simulation with DOPRI and automatically switches to RADAU if the system is found to become stiff during a simulation. This is the default choice for a variable-step solver. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-solver -->

## Solver — fixed-step

Fixed-step `discrete` solver. Used for real-time simulation and code-gen. Forward Euler for non-state-space dynamics.

<!-- BEGIN VERBATIM TABLE: simulation-parameters-solver-2 -->

| Name | Description |
| --- | --- |
| Fixed-step | The fixed-step solver Discrete does not actually solve any differential equations but just advances the simulation time with fixed increments. If this solver is chosen, the linear state-space equations of the physical model are discretized as described in section Physical Model Discretization . All other continuous state variables are updated using the Forward Euler method. Events and discontinuities that occur between simulation steps are accounted for by a linear interpolation method. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-solver-2 -->

## Variable-step solver options

Tuning knobs for DOPRI / RADAU. Defaults are usable; tighten `RelTol` and `AbsTol` if curves look noisy.

<!-- BEGIN VERBATIM TABLE: simulation-parameters-variable-step-solver-options -->

| Name | Description |
| --- | --- |
| Max Step Size | The maximum step size specifies the largest time step that the solver can take and should not be chosen unnecessarily small. If you suspect that the solver is missing events, try reducing the maximum step size. However, if you just require more output points for smoother curves, you should increase the refine factor (see below). |
| Initial Step Size | This parameter can be used to suggest a step size to be used for the first integration step. The default setting auto causes the solver to choose the step size according to the initial state derivatives. You should only change this parameter if you suspect that the solver is missing an event at the beginning of a simulation. |
| Tolerances | The relative and absolute specify the acceptable local integration errors for the individual state variables according to: \[\mathrm{err}_i \le \mathrm{rtol}\cdot \|x_i\| + \mathrm{atol}_i\] If all error estimates are smaller than the limit, the solver will increase the step size for the following step. If any error estimate is larger than the limit, the solver will discard the current step and repeat it with a smaller step size. The default absolute tolerance setting auto causes the solver to update the absolute tolerance for each state variable individually, based on the maximum absolute value encountered so far. |
| Refine factor | The refine factor is an efficient method for generating additional output points in order to achieve smoother results. For each successful integration step, the solver calculates \(r-1\) intermediate steps by interpolating the continuous states based on a higher-order polynomial. This is computationally much cheaper than reducing the maximum step size (see above). |
| Jacobian computation | This parameter specifies how the solver calculates the Jacobian matrix required for the integration of stiff systems. The default setting analytical uses exact derivatives provided by the model for improved accuracy and performance. Select finite differences to revert to the legacy method, where the Jacobian is approximated numerically by perturbing each state variable. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-variable-step-solver-options -->

### Notes
- `Refine factor` >1 cheaper than reducing `MaxStep` for smoother plots.
- `analytical` Jacobian preferred over `finite differences` for RADAU.

## Fixed-step options

<!-- BEGIN VERBATIM TABLE: simulation-parameters-fixed-step-solver-options -->

| Name | Description |
| --- | --- |
| Fixed step size | This parameter specifies the fixed time increments for the solver and also the sample time used for the state-space discretization of the physical model. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-fixed-step-solver-options -->

## Circuit model — diode threshold

Globally controls turn-on detection for line-commutated devices.

<!-- BEGIN VERBATIM TABLE: simulation-parameters-circuit-model-options -->

| Name | Description |
| --- | --- |
| Diode Turn-On Threshold | This parameter globally controls the turn-on behavior of line commutated devices such as diodes, thyristors, GTOs and similar semiconductors. A diode starts conducting as soon as the voltage across it becomes larger than the sum of the forward voltage and the threshold voltage. Similar conditions apply to the other line commutated devices. The default value for this parameter is 0 . For most applications the threshold could also be set to zero. However, in certain cases it is necessary to set this parameter to a small positive value to prevent line commutated devices from bouncing. Bouncing occurs if a switch receives an opening command and a closing command repeatedly in subsequent simulation steps or even within the same simulation step. Such a situation can arise in large, stiff systems that contain many interconnected switches. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-circuit-model-options -->

## Circuit model — discretization and switch behavior

<!-- BEGIN VERBATIM TABLE: simulation-parameters-circuit-model-options-2 -->

| Name | Description |
| --- | --- |
| Non-ideal switch resistance (code generation) | This parameter specifies the resistance for non-ideal switches when generating code from a simulation model. For details refer to section Ideal and Non-Ideal Switch Models in Electric Circuits . |
| Disc. method | This parameter determines the algorithm used to discretize the state-space equations of the electro-magnetic model. |
| ZC step size | This parameter is used by the Switch Manager when a non-sampled event (usually the zero crossing of a current or voltage) is detected. It controls the relative size of a step taken across the event. The default is 1e-9 . |
| Tolerances | The error tolerances are used to check whether the state variables are consistent after a switching event. The defaults are 1e-3 for the relative tolerance and 1e-6 for the absolute tolerance. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-circuit-model-options-2 -->

## Sample times

<!-- BEGIN VERBATIM TABLE: simulation-parameters-sample-times -->

| Name | Description |
| --- | --- |
| Synchronize fixed-step sample times | This option specifies whether PLECS should attempt to find a common base sample rate for blocks that specify a discrete sample time. |
| Use single base sample rate | This option specifies whether PLECS should attempt to find a single common base sample rate for all blocks that specify a discrete sample time. These options can only be modified for a variable-step solver; for a fixed-step solver they are checked by default. For details see section Multirate Systems . |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-sample-times -->

## State-space calculation

<!-- BEGIN VERBATIM TABLE: simulation-parameters-state-space-calculation -->

| Name | Description |
| --- | --- |
| Use extended precision | When this option is checked, PLECS uses higher-precision arithmetics for the internal calculation of the state-space matrices for a physical model. Check this option if PLECS reports that the system matrix is close to singular. |
| Remove unused state-space outputs | When this option is checked, PLECS removes the output equations for physical meters that are not used in the model in order to avoid unnecessary calculations. You may need to uncheck this option if you want to calculate state-space matrices in a simulation script, see Extraction of State-Space Matrices . By default, this option is checked. |
| Enable state-space splitting | When this option is checked, PLECS will attempt to split the state-space model for a physical domain into smaller independent models that can be calculated and updated individually. This can reduce the calculation effort at runtime, which is particularly advantageous for real-time simulations. |
| Display state-space splitting | When this option is checked, PLECS will issue diagnostic messages that highlight the components that make up the individual state-space models after splitting. This is useful e.g. in order to connect Model Settings blocks in the appropriate places (see Electrical Model Settings , Rotational Model Settings and Translational Model Settings ). |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-state-space-calculation -->

## Data types

<!-- BEGIN VERBATIM TABLE: simulation-parameters-data-types -->

| Name | Description |
| --- | --- |
| Use floating-point data type for fixed-point signals | When this option is enabled, PLECS will replace all fixed-point data types with the target floating-point data type (see section Data Types ). |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-data-types -->

## Assertions

<!-- BEGIN VERBATIM TABLE: simulation-parameters-assertions -->

| Name | Description |
| --- | --- |
| Assertion action | Use this option to override the action that is executed when an assertion fails (see Assertion block ). The default is use local settings , which uses the actions specified in each individual assertion. Assertions with the individual setting ignore are always ignored, even if this option is different from use local settings . Note that during analyses and simulation scripts, assertions may be partly disabled (see section Assertions ). |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-assertions -->

## Algebraic loops

<!-- BEGIN VERBATIM TABLE: simulation-parameters-algebraic-loops -->

| Name | Description |
| --- | --- |
| Method | Use this option to select the strategy adopted by the nonlinear equation solver. Currently, either a line search method or a trust region method can be used. |
| Tolerance | The relative error bound. The solver updates the block outputs iteratively until the maximum relative change from one iteration to the next and the maximum relative residual of the loop equations are both smaller than this value. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-algebraic-loops -->

## Diagnostics

Severity controls per failure mode. Default action: `error` for most.

<!-- BEGIN VERBATIM TABLE: simulation-parameters-diagnostics -->

| Name | Description |
| --- | --- |
| Division by zero | This option determines the diagnostic action to take if PLECS encounters a division by zero in a Product block or a Function block . A division by zero yields \(\pm\infty\) or nan (“not a number”, if you divide \(0/0\) ). Using these values as inputs for other blocks may lead to unexpected model behavior. Possible choices are ignore , warning and error . In new models, the default is error . |
| Datatype overflow | This option determines the diagnostic action to take if PLECS encounters a data type overflow. PLECS can issue an error or a warning message or can continue silently. In the latter two cases, the result is handled according to the individual data type overflow handling setting of the block. If the individual setting is Assert with error , PLECS always issues an error message. |
| Datatype inheritance conflict | This option allows to apply less strict data type inheritance rules (see section Data Types ). In new models, the default is error . |
| Continuous sample time conflict | This option determines the diagnostic action to take if PLECS detects a continuous sample time conflict (see section Continuous Sample Time Conflicts ). In new models, the default is error . |
| Negative switch loss | This option determines the diagnostic action to take if PLECS encounters negative loss values during the calculation of switch losses (see section Loss Calculation ). PLECS can issue an error or a warning message or can continue silently. In the latter two cases, the losses that are injected into the thermal model are cropped to zero. |
| Stiffness detection | This parameter only applies to the non-stiff, variable-step DOPRI solver. The DOPRI solver contains an algorithm to detect when a model becomes “stiff” during the simulation. Stiff models cannot be solved efficiently with non-stiff solvers, because they constantly need to adjust the step size at relatively small values to keep the solution from becoming numerically unstable. If the DOPRI solver detects stiffness in model, it will raise a warning or error message depending on this parameter setting with the recommendation to use the stiff RADAU solver instead. |
| Max. number of consecutive zero-crossings | This parameter only applies to variable-step solvers. For a model that contains discontinuities (also termed “zero-crossings”), a variable-step solver will reduce the step size so as to make a simulation step precisely at the time when a discontinuity occurs (see section Event Detection Loop ). If many discontinuities occur in subsequent steps, the simulation may come to an apparent halt without actually stopping because the solver is forced to reduce the step size to an excessively small value. This parameter specifies an upper limit for the number of discontinuities in consecutive simulation steps before PLECS stops the simulation with an error message that shows the responsible component(s). To disable this diagnostic, set this parameter to 0 . |
| Algebraic loop with state machines | This option determines the diagnostic action to take if PLECS detects an algebraic loop that includes a State Machine . This may lead to unexpected behavior because the state machine will be executed multiple times for the same simulation step during the iterative solution of the algebraic loop. Possible choices are ignore , warning and error . The default is error . |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-diagnostics -->

## System State

<!-- BEGIN VERBATIM TABLE: simulation-parameters-system-state -->

| Name | Description |
| --- | --- |
| Block parameters | When this option is selected, the state variables are initialized with the values specified in the individual block parameters. |
| Stored system state | When this option is selected, the state variables are initialized globally from a previously stored system state; the initial values specified in the individual block parameters are ignored. This option is disabled if no state has been stored. |
| Store system state… | Pressing this button after a transient simulation run or an analysis will store the final system state along with a time stamp and an optional comment. When you save the model, this information will be stored in the model file so that it can be used in future sessions. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-system-state -->

## Diode Turn-On Threshold and Type (Blockset variant)

<!-- BEGIN VERBATIM TABLE: simulation-parameters-id1 -->

| Name | Description |
| --- | --- |
| Diode Turn-On Threshold | This parameter globally controls the turn-on behavior of line commutated devices such as diodes, thyristors, GTOs and similar semiconductors. A diode starts conducting as soon as the voltage across it becomes larger than the sum of the forward voltage and the threshold voltage. Similar conditions apply to the other line commutated devices. The default value for this parameter is 1e-3 . For most applications the threshold could also be set to zero. However, in certain cases it is necessary to set this parameter to a small positive value to prevent line commutated devices from bouncing. Bouncing occurs if a switch receives an opening command and a closing command repeatedly in subsequent simulation steps or even within the same simulation step. Such a situation can arise in large, stiff systems that contain many interconnected switches. Note The Diode Turn-On Threshold is not equivalent to the voltage drop across a device when it is conducting. The turn-on threshold only delays the instant when a device turns on. The voltage drop across a device is solely determined by the forward voltage and/or on-resistance specified in the device parameters. |
| Type | This parameter lets you choose between the continuous and discrete state-space method for setting up the physical model equations. For details please refer to section Physical Model Equations . When you choose Continuous state-space , PLECS employs the Simulink solver to solve the differential equations and integrate the state variables. The Switch Manager communicates with the solver in order to ensure that switching occurs at the correct time. This is done with Simulink’s zero-crossing detection capability. For this reason the continuous method can only be used with a variable-step solver. In general, the default solver of Simulink, ode45 , is recommended. However, your choice of circuit parameters may lead to stiff differential equations, e.g. if you have large resistors connected in series with inductors. In this case you should choose one of Simulink’s stiff solvers. When you choose Discrete state-space , PLECS discretizes the linear state-space equations of the physical model as described in section Physical Model Discretization . All other continuous state variables are updated using the Forward Euler method. This method can be used with both variable-step and fixed-step solvers. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-id1 -->

## Discrete state-space options (Blockset)

<!-- BEGIN VERBATIM TABLE: simulation-parameters-discrete-state-space-options -->

| Name | Description |
| --- | --- |
| Sample time | This parameter determines the rate with which Simulink samples the circuit. A setting of auto or -1 means that the sample time is inherited from the Simulink model. |
| Refine factor | This parameter controls the internal step size which PLECS uses to discretize the state-space equations. The discretization time step \(\Delta t\) is thus calculated as the sample time divided by the refine factor. The refine factor must be a positive integer. The default is 1 . Choosing a refine factor larger than 1 allows you to use a sample time that is convenient for your discrete controller while at the same time taking into account the usually faster dynamics of the electrical system. |
| Disc. method | This parameter determines the algorithm used to discretize the state-space equations of the electro-magnetic model. |
| ZC step size | This parameter is used by the Switch Manager when a non-sampled event (usually the zero crossing of a current or voltage) is detected. It controls the relative size of a step taken across the event. The default is 1e-9 . |
| Tolerances | The error tolerances are used to check whether the state variables are consistent after a switching event. The defaults are 1e-3 for the relative tolerance and 1e-6 for the absolute tolerance. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-discrete-state-space-options -->

## Diagnostics (Blockset variant)

<!-- BEGIN VERBATIM TABLE: simulation-parameters-id2 -->

| Name | Description |
| --- | --- |
| Zero crossing detection disabled | In order to accurately determine the proper switching times of power semiconductors, PLECS highly depends on the solver’s capability to locate zero crossings. If you switch off the zero crossing detection in the Simulink solver or use the less accurate “Adaptive” detection algorithm, PLECS will therefore issue a diagnostic message. This option allows you to specify the severity level ( warning or error ) of this message. If you encounter problems due to many consecutive zero crossings, it is usually not advisable to modify the zero crossing detection settings. Consecutive zero crossings are often caused by insufficient simulation accuracy, typically in conjunction with a stiff model. In this case it may help to tighten the relative tolerance of the Simulink solver (from the default 1e-3 to 1e-5 or 1e-6 ) and to switch from the default solver ode45 to a stiff solver such as ode23tb and, where applicable, set the Simulink solver option Solver reset method to Robust . |
| Number of consecutive gate signal changes | If you configure a Signal Inport block in a top-level schematic to be a gate signal , PLECS expects this signal to change only at discrete instants. If instead the signal changes in more than the specified number of consecutive simulation time steps, PLECS will issue an error message to indicate that there may be a problem in the gate signal generator. You can disable this diagnostic by entering 0 . |
| Division by zero | This option determines the diagnostic action to take if PLECS encounters a division by zero in a Product block or a Function block . A division by zero yields \(\pm\infty\) or nan (“not a number”, if you divide \(0/0\) ). Using these values as inputs for other blocks may lead to unexpected model behavior. Possible choices are ignore , warning and error . In new models, the default is error . |
| Datatype overflow | This option determines the diagnostic action to take if PLECS encounters a data type overflow. PLECS can issue an error or a warning message or can continue silently. In the latter two cases, the result is handled according to the individual data type overflow handling setting of the block. If the individual setting is Assert with error , PLECS always issues an error message. |
| Datatype inheritance conflict | This option allows to apply less strict data type inheritance rules (see section Data Types ). In new models, the default is error . |
| Continuous sample time conflict | This option determines the diagnostic action to take if PLECS detects a continuous sample time conflict (see section Continuous Sample Time Conflicts ). In new models, the default is error . |
| Algebraic loop with state machines | This option determines the diagnostic action to take if PLECS detects an algebraic loop that includes a State Machine . This may lead to unexpected behavior because the state machine will be executed multiple times for the same simulation step during the iterative solution of the algebraic loop. Possible choices are ignore , warning and error . The default is error . |
| Negative switch loss | This option determines the diagnostic action to take if PLECS encounters negative loss values during the calculation of switch losses (see section Loss Calculation ). PLECS can issue an error or a warning message or can continue silently. In the latter two cases, the losses that are injected into the thermal model are cropped to zero. |
| Assertion action | Use this option to override the action that is executed when an assertion fails (see Assertion block ). The default is use local settings , which uses the actions specified in each individual assertion. Assertions with the individual setting ignore are always ignored, even if this option is different from use local settings . Note that during analyses and simulation scripts, assertions may be partly disabled (see Assertions ). |
| Use floating-point data type for fixed-point signals | When this option is enabled, PLECS will replace all fixed-point data types with the target floating-point data type (see section Data Types ). |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-id2 -->

## Sample times (Blockset variant)

<!-- BEGIN VERBATIM TABLE: simulation-parameters-id3 -->

| Name | Description |
| --- | --- |
| Synchronize fixed-step sample times | This option specifies whether PLECS should attempt to find a common base sample rate for blocks that specify a discrete sample time. |
| Use single base sample rate | This option specifies whether PLECS should attempt to find a single common base sample rate for all blocks that specify a discrete sample time. These options can only be modified for a Continuous State-Space model; for a Discrete State-Space model they are checked by default. For details see section Multirate Systems . |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-id3 -->

## Algebraic loops (Blockset variant)

<!-- BEGIN VERBATIM TABLE: simulation-parameters-id4 -->

| Name | Description |
| --- | --- |
| Method | Use this option to select the strategy adopted by the nonlinear equation solver. Currently, either a line search method or a trust region method can be used. |
| Tolerance | The relative error bound. The solver updates the block outputs iteratively until the maximum relative change from one iteration to the next and the maximum relative residual of the loop equations are both smaller than this value. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-id4 -->

## State-space calculation (Blockset variant)

<!-- BEGIN VERBATIM TABLE: simulation-parameters-id5 -->

| Name | Description |
| --- | --- |
| Use extended precision | When this option is checked, PLECS uses higher-precision arithmetics for the internal calculation of the state-space matrices for a physical model. Check this option if PLECS reports that the system matrix is close to singular. |
| Remove unused state-space outputs | When this option is checked, PLECS removes the output equations for physical meters that are not used in the model in order to avoid unnecessary calculations. You may need to uncheck this option if you want to calculate state-space matrices in a simulation script, see Extraction of State-Space Matrices . By default, this option is checked. |
| Enable state-space splitting | When this option is checked, PLECS will attempt to split the state-space model for a physical domain into smaller independent models that can be calculated and updated individually. This can reduce the calculation effort at runtime, which is particularly advantageous for real-time simulations. |
| Display state-space splitting | When this option is checked, PLECS will issue diagnostic messages that highlight the components that make up the individual state-space models after splitting. This is useful e.g. in order to connect Model Settings blocks in the appropriate places (see Electrical Model Settings , Rotational Model Settings and Translational Model Settings ). |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-id5 -->

## Simulink Coder integration (Blockset)

<!-- BEGIN VERBATIM TABLE: simulation-parameters-simulink-coder -->

| Name | Description |
| --- | --- |
| Target | This option specifies the code generation target that is used when you generate code with the Simulink Coder. For details on the available targets see section Target . |
| Inline circuit parameters for RSim target | This option controls whether PLECS inlines parameter values or whether it should keep them tunable when it creates code for the RSim target. For details see section Tunable Circuit Parameters in Rapid Simulations . |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/simulation-parameters/_

<!-- END VERBATIM TABLE: simulation-parameters-simulink-coder -->

### Notes
- "Blockset variant" tables (id1..id5) duplicate fields from PLECS Standalone with Simulink-specific names. Treat them as the same knobs.
- For pyplecs (Standalone XML-RPC) only the non-Blockset tables apply at run time.
