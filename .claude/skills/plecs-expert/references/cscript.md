# cscript

<!-- BEGIN VERBATIM TABLE: c-scripts-table-0 -->

| Macro | Type | Access | Description |
| --- | --- | --- | --- |
| NumInputTerminals | int | R | Returns the number of input terminals. |
| NumOutputTerminals | int | R | Returns the number of output terminals. |
| NumInputSignals ( int i ) | int | R | Returns the number of elements (i.e. the width) of the signal connected to the i th input terminal. |
| NumOutputSignals ( int i ) | int | R | Returns the number of elements (i.e. the width) of the signal connected to the i th output terminal. |
| NumContStates | int | R | Returns the number of continuous states. |
| NumDiscStates | int | R | Returns the number of discrete states. |
| NumZCSignals | int | R | Returns the number of zero-crossing signals. |
| NumParameters | int | R | Returns the number of user parameters. |
| CurrentTime | double | R | Returns the current simulation time (resp. the simulation start time during the start function call). |
| NumSampleTime | int | R | Returns the number of sample times. |
| SampleTimePeriod ( int i ) | int | R | Returns the period of the i th sample time. |
| SampleTimeOffset ( int i ) | int | R | Returns the offset of the i th sample time. |
| IsMajorStep | int | R | Returns 1 during major time steps, else 0 . |
| IsSampleHit ( int i ) | int | R | Returns 1 if the i th sample time currently has a hit, else 0 . |
| NextSampleHit | double | R/W | Specifies the next simulation time when the block should be executed. This is relevant only for blocks that have registered a discrete-variable sample time. |
| InputSignal ( int i , int j ) | double | R | Returns the value of the j th element of the i th input signal terminal. See the C-Script block for information on how to increase the default number of input signal terminals. |
| OutputSignal ( int i , int j ) | double | R/W | Provides access to the value of the j th element of the i th output signal terminal. See the C-Script block for information on how to increase the default number of output signal terminals. Output signals may only be changed during the output function call. |
| ContState ( int i ) | double | R/W | Provides access to the value of the i th continuous state. Continuous state variables may not be changed during minor time steps. |
| ContDeriv ( int i ) | double | R/W | Provides access to the derivative of the i th continuous state. |
| DiscState ( int i ) | double | R/W | Provides access to the value of the i th discrete state. Discrete state variables may not be changed during minor time steps. |
| ZCSignal ( int i ) | double | R/W | Provides access to the i th zero-crossing signal. |
| ParamNumDims ( int i ) | int | R | Returns the number of dimensions of the i th user parameter. |
| ParamDim ( int i , int j ) | int | R | Returns the j th dimension of the i th user parameter. |
| ParamRealData ( int i , int j ) | double | R | Returns the value of the j th element of the i th user parameter. The index j is a linear index into the parameter elements. Indices into multi-dimensional arrays must be calculated using the information provided by the ParamNumDims and ParamDim macros. If the parameter is a string, this macro will produce a runtime error or an access violation if runtime checks are disabled. |
| ParamStringData ( int i ) | char* | R | Returns a pointer to a UTF-8 encoded, null-terminated C string that represents the i th user parameter. If the parameter is not a string, this macro will produce a runtime error or returns NULL if runtime checks are disabled. |
| WriteCustomStateDouble ( double val ) WriteCustomStateInt ( int val ) WriteCustomStateData ( void * data , int len ) | void void void | W | Write a custom state of type double, int or custom data with len number of bytes. Use multiple calls for multiple values. |
| ReadCustomStateDouble () ReadCustomStateInt () ReadCustomStateData ( void * data , int len ) | double int void | R | Read a custom state of type double, int or custom data with len number of bytes. Use multiple calls for multiple values. |
| SetErrorMessage ( char * msg ) | void | W | Use this macro to report errors that occur in your code. The simulation will be terminated after the current simulation step. In general, this macro should be followed by a return statement. The pointer msg must point to static memory. |
| SetWarningMessage ( char * msg ) | void | W | Use this macro to report warnings. The warning status is reset as soon as the current C-Script function returns, so you do not need to reset it manually. The pointer msg must point to static memory. |

_Source: https://docs.plexim.com/plecs/latest/c-scripts/_

<!-- END VERBATIM TABLE: c-scripts-table-0 -->
