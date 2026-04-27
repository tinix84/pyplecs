# control

<!-- BEGIN VERBATIM TABLE: continuouspidcontroller-anti-windup-methods -->

| Name | Description |
| --- | --- |
| Back-Calculation | The Back-calculation method changes the integral action when the controller output is in saturation. The integral term is reduced/increased when the controller output is higher/lower than the upper/lower saturation limit. This is done by feeding back the difference between the saturated and the unsaturated controller output. The value of the back-calculation gain \(K_\mathrm{bc}\) determines the rate at which the integrator is reset and is therefore crucial for performance of the anti-windup mechanism. A common choice for this back-calculation gain is: \[K_\mathrm{bc} = \sqrt{\frac{K_\mathrm{i}}{K_\mathrm{d}}}.\] However, this rule can only be applied to full PID controllers. In the case of a PI controller, where \(K_\mathrm{d} = 0\) , it is suggested that \[K_\mathrm{bc} = \frac{K_\mathrm{i}}{K_\mathrm{p}}.\] |
| Conditional Integration | The Conditional integration method stops the integration when the controller output saturates and the control error \(e\) and the control variable \(u\) have the same sign. This means, the integral action is still applied if it helps to push the controller output out of saturation. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/continuouspidcontroller/_

<!-- END VERBATIM TABLE: continuouspidcontroller-anti-windup-methods -->

<!-- BEGIN VERBATIM TABLE: continuouspidcontroller-anti-windup-methods-2 -->

| Name | Description |
| --- | --- |
| Anti-Windup with External Saturation | If the saturation is placed externally to the PID controller block, i.e. Saturation is set to external , one can still use the above described anti-windup methods. To feedback the saturated output of the external Saturation block an additional subsystem port \(u^*\) is made visible if the Saturation parameter is set to external and the Anti-windup method parameters is set to an option other than none , see the figure below. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/continuouspidcontroller/_

<!-- END VERBATIM TABLE: continuouspidcontroller-anti-windup-methods-2 -->

<!-- BEGIN VERBATIM TABLE: continuouspidcontroller-basic -->

| Name | Description |
| --- | --- |
| Controller type | Specifies the controller type. The controller can be of type P , I , PI , PD or PID . |
| Parameter source | Specifies whether the controller parameters are provided via the mask parameters ( internal ) or via input signals ( external ). |
| Proportional gain Kp | The proportional gain of the controller. This parameter is shown only if the Controller type parameter is set to P , PI , PD or PID and the Parameter source parameter is set to internal . |
| Integral gain Ki | The integral gain of the controller. This parameter is shown only if the Controller type parameter is set to I , PI or PID and the Parameter source parameter is set to internal . |
| Derivative gain Kd | The derivative gain of the controller. This parameter is shown only if the Controller type parameter is set to PD or PID and the Parameter source parameter is set to internal . |
| Derivative filter coefficient Kf | The filter coefficient which specifies the pole location of the first-order filter in the derivative term. This parameter is shown only if the Controller type parameter is set to PD or PID and the Parameter source parameter is set to internal . |
| External reset | The behavior of the external reset input. The values rising , falling and either cause a reset of the integrator on the rising, falling or both edges of the reset signal. A rising edge is detected when the signal changes from \(0\) to a positive value, a falling edge is detected when the signal changes from a positive value to \(0\) . If level is chosen, the output signal keeps the initial value while the reset input is not \(0\) . Only the integrator in the integral action is reset. |
| Initial condition source | Specifies wheter the initial condition is provided via the Initial condition parameter ( internal ) or via an input signal ( external ). |
| Initial condition | The initial condition of the integrator in the integral action. The value may be a scalar or a vector corresponding to the implicit width of the component. This parameter is shown only if the Initial condition source parameter is set to internal . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/continuouspidcontroller/_

<!-- END VERBATIM TABLE: continuouspidcontroller-basic -->

<!-- BEGIN VERBATIM TABLE: continuouspidcontroller-anti-windup -->

| Name | Description |
| --- | --- |
| Saturation | Specifies if the internally placed saturation ( internal ) is used or if the user wants to place the saturation externally ( external ) to the Continuous PID Controller block . If external is selected, the internal Saturation block is not active. |
| Saturation limits | Specifies whether the saturation limits are provided via the mask parameters ( constant ) or via input signals ( variable ). |
| Upper saturation limit | An upper limit for the output signal. If the value is inf , the output signal is unlimited. If input and output are vectorized, signals a vector can be used. The number of elements in the vector must match the number of input signals. This parameter is shown only if the Saturation parameter is set to internal and the Saturation limits parameter is set to constant . |
| Lower saturation limit | A lower limit for the output signal. If the value is -inf , the output signal is unlimited. If input and output are vectorized, signals a vector can be used. The number of elements in the vector must match the number of input signals. This parameter is shown only if the Saturation parameter is set to internal and the Saturation limits parameter is set to constant . |
| Anti-Windup method | Specifies the method to avoid windup of the integral action. See Anti-windup methods above. |
| Back-calculation gain | The gain of the back-calculation anti-windup method. This parameter is shown only of the Anti-windup method parameter is set to Back-calculation . |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/continuouspidcontroller/_

<!-- END VERBATIM TABLE: continuouspidcontroller-anti-windup -->

<!-- BEGIN VERBATIM TABLE: continuouspidcontroller-probes -->

| Probe signal | Description |
| --- | --- |
| Proportional action | Proportion of the proportional action of the controller output signal. |
| Integral action | Proportion of the integral action of the controller output signal. |
| Derivative action | Proportion of the derivative action of the controller output signal. |
| Controller output before saturation | The input signal of the saturation block. |
| Controller output after saturation | The output signal of the saturation block. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/continuouspidcontroller/_

<!-- END VERBATIM TABLE: continuouspidcontroller-probes -->

<!-- BEGIN VERBATIM TABLE: transferfcn-parameters -->

| Name | Description |
| --- | --- |
| Numerator coefficients | A vector of the \(s\) term coefficients \([n_n \ldots  n_1, n_0]\) for the numerator, written in descending order of powers of \(s\) . For example, the numerator \(s^3+2s\) would be entered as [1,0,2,0] }. The Transfer Function supports multiple outputs for a single input by entering a matrix for the numerator. Each row of the matrix defines the numerator coefficients of an output. |
| Denominator coefficients | A vector of the \(s\) term coefficients \([d_n \ldots d_1, d_0]\) for the denominator, written in descending order of powers of \(s\) . Note The order of the denominator (highest power of \(s\) ) must be greater than or equal to the order of the numerator. |
| Initial condition | The initial condition vector of the internal states of the Transfer Function in the form \([x_n \ldots  x_1, x_0]\) . The initial condition must be specified for the controller normal form, depicted below for the transfer function \[\frac{Y(s)}{U(s)}=\frac{n_2s^2+n_1s+n_0}{d_2s^2+d_1s+d_0} = b_2\left(a_2 + \frac{a_1s + a_0}{s^2 + b_1s + b_0}\right)\] Fig. 161 Transfer function controller normal form  where \[\begin{split}\begin{array}{rcll} b_i & = & \frac{\displaystyle d_i}{\displaystyle d_n} & \mbox{for $i<n$ }\\ b_n & = & \frac{\displaystyle 1}{\displaystyle d_n}\\ a_i & = & n_i - \frac{\displaystyle n_n d_i}{\displaystyle d_n} & \mbox{for $i<n$}\\ a_n & = & n_n \end{array}\end{split}\] For the normalized transfer function (with \(n_n = 0\) and \(d_n = 1\) ) this simplifies to \(b_i = d_i\) and \(a_i = n_i\) . Note The number of internal states is defined by the highest power of \(s\) of the denominator. Note A scalar initial condition will be applied to all internal states. Note In case of scalar expansion (multiple input signals), the initial condition can also be a matrix, where each row defines the initial condition for the individual inputs. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/transferfcn/_

<!-- END VERBATIM TABLE: transferfcn-parameters -->

<!-- BEGIN VERBATIM TABLE: transferfcn-probes -->

| Probe signal | Description |
| --- | --- |
| Input | The input signal. |
| Output | The output signal. |
| State | The internal states of the controller normal form. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/transferfcn/_

<!-- END VERBATIM TABLE: transferfcn-probes -->

<!-- BEGIN VERBATIM TABLE: statemachines-table-0 -->

| Macro | Type | Access | Description |
| --- | --- | --- | --- |
| CurrentTime | double | R | Returns the current simulation time. |
| SetErrorMessage ( char * msg ) | void | W | Use this macro to report errors that occur in your code. The simulation will be terminated after the current simulation step. In general, this macro should be followed by a return statement. The pointer msg must point to static memory. |
| SetWarningMessage ( char * msg ) | void | W | Use this macro to report warnings. The warning status is reset after the execution of the current simulation step, so you do not need to reset it manually. The pointer msg must point to static memory. |

_Source: https://docs.plexim.com/plecs/latest/statemachines/_

<!-- END VERBATIM TABLE: statemachines-table-0 -->

<!-- BEGIN VERBATIM TABLE: statemachines-table-1 -->

| Type | Value |  |
| --- | --- | --- |
| Continuous | [0, 0] or 0 |  |
| Discrete-Periodic | [ T p , T o ] or T p | T p : Sample period, \(0 < {}\) T p T o : Sample offset, \(0 \le{}\) T o \({}<{}\) T p |
| Inherited | [-1, 0] or -1 |  |

_Source: https://docs.plexim.com/plecs/latest/statemachines/_

<!-- END VERBATIM TABLE: statemachines-table-1 -->
