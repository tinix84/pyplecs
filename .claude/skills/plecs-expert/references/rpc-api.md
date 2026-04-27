# rpc-api

PLECS exposes an XML-RPC interface on `localhost:1080` (default). pyplecs wraps a curated subset via `pyplecs.PlecsServer`. Methods on that wrapper: `close`, `health_check`, `is_available`, `load_modelvars`, `run_sim_with_datastream`, `run_sim_with_mat_file`, `set_value`, `simulate`, `simulate_batch`, `simulate_raw`. Anything else use `plecs_rpc(...)` for live introspection.

## Scope export — bitmap options

Field bag passed to `plecs.scope.SaveAsImage` and similar. Not wrapped — call via `plecs_rpc('plecs.scope.SaveAsImage', ...)`.

<!-- BEGIN VERBATIM TABLE: scripting-table-0 -->

| Name | Description |
| --- | --- |
| Size | A two-element integer vector specifying the width and height of the bitmap in pixels. |
| Resolution | An integer specifying the resolution of the bitmap in pixels per inch. |
| TimeRange | A two-element real vector specifying the time range of the data to be shown. |
| XLim | A two-element real vector specifying the limits of the x-axis. For a normal scope this is equivalent to TimeRange . |
| YLim | A cell array containing two-element real vectors specifying the limits of the y-axis of the plot(s). For a scope with a single plot a vector may be given directly. |
| XLabel | A string specifying the x-axis label. |
| YLabel | A cell array containing strings specifying the y-axis labels of the plot(s). For a scope with a single plot a string may be given directly. |
| Title | A cell array containing strings specifying the title of the plot(s). For a scope with a single plot a string may be given directly. |
| LegendPosition | A string specifying the legend position. Possible values are none , topleft , topmiddle , topright , bottomleft , bottommiddle and bottomright . |
| Font | A string specifying the font name to be used for the labels and the legend. |
| LabelFontSize | An integer specifying the label font size in points. |
| LegendFontSize | An integer specifying the legend font size in points. |

_Source: https://docs.plexim.com/plecs/latest/scripting/_

<!-- END VERBATIM TABLE: scripting-table-0 -->

## SolverOpts — simulate / simulate_raw

`SolverOpts` overrides solver settings for one simulation run. Wrapped via `pyplecs.PlecsServer.simulate` and `simulate_raw` — pass dict as `solver_opts=` kwarg.

<!-- BEGIN VERBATIM TABLE: scripting-table-1 -->

| Parameter | Description |
| --- | --- |
| Solver | The solver to use for the simulation. Possible values are auto , dopri , radau and discrete (see PLECS Standalone Parameters ). |
| StartTime | The start time specifies the initial value of the simulation time variable \(t\) at the beginning of a simulation, in seconds \((\mathrm{s})\) . |
| TimeSpan | The simulation ends when the simulation time has advanced by the specified time span. |
| StopTime | This option is obsolete. It is provided to keep old scripts working. We strongly advise against using it in new code. |
| OutputTimes OutputTimesOption | These options control the simulation times that are included in the result of a scripted simulation. See the table below. |
| InitialSystemState | Specifies the initial system state used for the simulation. This will override the System State setting in the simulation parameters (see System State ). The system state struct can be retrieved after the completion of a simulation or steady-state analysis using the command plecs ( 'get' , mdlName , 'SystemState' ) |
| Timeout | A non-negative number that specifies the maximum number of seconds (wall-clock time) that a simulation or analysis is allowed to run. After this period the simulation or analysis is stopped with a timeout error. A value of 0 disables the timeout. |
| MaxStep | See the description for Max Step Size in section PLECS Standalone Parameters . This parameter is only evaluated for variable step solvers. |
| InitStep | See the description for Initial Step Size in section PLECS Standalone Parameters . This parameter is only evaluated for variable step solvers. |
| FixedStep | This option specifies the fixed time increments for the solver and also the sample time used for the state-space discretization of the physical model. It is only evaluated for the fixed step solver. |
| AbsTol | See the description for Tolerances in section PLECS Standalone Parameters . |
| RelTol | See the description for Tolerances in section PLECS Standalone Parameters . |
| Refine | See parameter Refine factor in section PLECS Standalone Parameters . |

_Source: https://docs.plexim.com/plecs/latest/scripting/_

<!-- END VERBATIM TABLE: scripting-table-1 -->

## OutputTimesOption — output-time mode

Controls how `OutputTimes` is interpreted by the scripted simulator. Use via `solver_opts={'OutputTimes': [...], 'OutputTimesOption': 'specified'}`.

<!-- BEGIN VERBATIM TABLE: scripting-table-2 -->

| OutputTimesOption | Interpretation of OutputTimes |
| --- | --- |
| specified | The simulation result contains only the simulation times specified in the OutputTimes vector. This is also the default behavior if only the vector OutputTimes is provided and OutputTimesOption is omitted. |
| additional | The simulation result contains the simulation times specified in the OutputTimes vector in addition to all simulation steps that the solver makes. |
| range | The simulation result contains all simulation steps that the solver makes within the time span from OutputTimes(1) to OutputTimes(end) . If the vector OutputTimes contains more than two values, the additional simulation times are also included in the result. |

_Source: https://docs.plexim.com/plecs/latest/scripting/_

<!-- END VERBATIM TABLE: scripting-table-2 -->

## AnalysisOpts — steady-state and small-signal

Field bag for `plecs.analyze(...)`. Not wrapped — call via `plecs_rpc('plecs.analyze', mdl, name, opts)`.

<!-- BEGIN VERBATIM TABLE: scripting-table-3 -->

| Parameter | Description |
| --- | --- |
| TimeSpan | System period length; this is the least common multiple of the periods of independent sources in the system. |
| StartTime | Simulation start time. |
| Tolerance | Relative error tolerance used in the convergence criterion of a steady-state analysis. |
| MaxIter | Maximum number of iterations allowed in a steady-state analysis. |
| JacobianPerturbation | Relative perturbation of the state variables used to calculate the approximate Jacobian matrix. |
| JacobianCalculation | Controls the way the Jacobian matrix is calculated ( full , fast ). The default is fast . |
| InitCycles | Number of cycle-by-cycle simulations that should be performed before the actual analysis. This parameter can be used to provide the initial steady-state analysis with a better starting point. |
| ShowCycles | Number of steady-state cycles that should be simulated at the end of an analysis. This parameter is evaluated only for a steady-state analysis. |
| FrequencyRange | Range of the perturbation frequencies. This parameter is evaluated only for a small-signal analysis. |
| FrequencyScale | Specifies whether the sweep frequencies should be distributed on a linear or logarithmic scale. This parameter is evaluated only for a small-signal analysis. |
| AdditionalFreqs | A vector specifying frequencies to be swept in addition to the automatically distributed frequencies. This parameter is evaluated only for a small-signal analysis. |
| NumPoints | The number of automatically distributed perturbation frequencies. This parameter is evaluated only for a small-signal analysis. |
| Perturbation | The full block path (excluding the model name) of the Small Signal Perturbation block that will be active during an analysis. This parameter is evaluated only for a small-signal analysis. |
| Response | The full block path (excluding the model name) of the Small Signal Response block that will record the system response during an analysis. This parameter is evaluated only for a small-signal analysis. |
| AmplitudeRange | The amplitude range of the sinusoidal perturbation signals for an ac sweep. This parameter is evaluated only for an ac sweep. |
| Amplitude | The amplitude of the discrete pulse perturbation for an impulse response analysis. This parameter is evaluated only for an impulse response analysis. |
| MaxNumberOfThreads | The maximum number of parallel threads that may be used during the analysis. |
| ShowResults | Specifies whether to show a Bode plot after a small-signal analysis. This parameter is evaluated only for a small-signal analysis. |

_Source: https://docs.plexim.com/plecs/latest/scripting/_

<!-- END VERBATIM TABLE: scripting-table-3 -->

## OutputFormat / ModelVars / SolverOpts — top-level options struct

Top-level dict given to `plecs.simulate(mdl, opts)` or `plecs.analyze(mdl, name, opts)`. `ModelVars` is wrapped via `pyplecs.PlecsServer.load_modelvars` (loads a `.m` file) and via `set_value` (per-parameter). `SolverOpts` is wrapped via `simulate` / `simulate_raw`. `OutputFormat` controls return shape; pyplecs wrappers select the right value.

<!-- BEGIN VERBATIM TABLE: scripting-scripted-simulation-and-analysis-options -->

| Name | Description |
| --- | --- |
| OutputFormat | The optional field OutputFormat is a string that lets you choose whether the results of a simulation or analysis should be returned as a RPC struct ( Plain ) or in binary form using the MAT-file format ( MatFile ). The binary format is much more efficient if the result contains many data points, but the client may not be able to interpret it, so the default is Plain . |
| ModelVars | The optional field ModelVars is a struct variable that allows you to override variable values defined by the model initialization commands. Each field name is treated as a variable name; the field value is assigned to the corresponding variable. Values can be numerical scalars, vectors, matrices or 3d arrays or strings. The override values are applied after the model initialization commands have been evaluated and before the component parameters are evaluated as shown in Fig. 117 . Fig. 117 Execution order for Simulation Scripts (left) and RPC (right)  |
| SolverOpts | The optional field SolverOpts is a struct variable that allows you to override the solver settings specified in the Simulation Parameters dialog. Each field name is treated as a solver parameter name; the field value is assigned to the corresponding solver parameter. Tab. 18 lists the possible parameters. |

_Source: https://docs.plexim.com/plecs/latest/scripting/_

<!-- END VERBATIM TABLE: scripting-scripted-simulation-and-analysis-options -->

<!-- BEGIN VERBATIM TABLE: scripting-scripted-simulation-and-analysis-options-2 -->

| Name | Description |
| --- | --- |
| AnalysisOpts | For an analysis the optional field AnalysisOpts is a struct variable that allows you to override the analysis settings defined in the Analysis Tools dialog. Each field name is treated as an analysis parameter name, the field value is assigned to the corresponding analysis parameter. The following tables list the possible parameters: |

_Source: https://docs.plexim.com/plecs/latest/scripting/_

<!-- END VERBATIM TABLE: scripting-scripted-simulation-and-analysis-options-2 -->

### Notes
- pyplecs targets the simulation path. Steady-state and small-signal analysis are not wrapped — call via `plecs_rpc('plecs.analyze', mdl, name, opts)`.
- `MatFile` mode returns binary; `simulate_raw` covers it. `Plain` returns dict; `simulate` covers it.
- Variable overrides via `ModelVars` apply after init commands and before component param evaluation.
