# system

<!-- BEGIN VERBATIM TABLE: subsystem-execution-settings -->

| Name | Description |
| --- | --- |
| Treat as atomic unit | If this parameter is checked, PLECS treats the subsystem as atomic, otherwise as virtual (see Virtual and Atomic Subsystems ). |
| Minimize occurrence of algebraic loops | This parameter only applies to atomic subsystems. If it is unchecked , PLECS assumes that all inputs of the subsystem have direct feedthrough , i.e. the output functions of the blocks feeding these inputs must be executed before the output function of the subsystem itself can be executed (see Block Sorting ). If the atomic subsystem is part of a feedback loop, this can result in algebraic loop errors where a virtual subsystem could be used without problems. If the parameter is checked , PLECS determines the actual feedthrough behavior of the individual inputs from the internal connectivity. A subsystem input that is internally only connected to non-direct feedthrough inputs of other blocks (e.g. the inputs of Integrator, Memory or Delay blocks) does not have direct feedthrough. This can help reduce the occurrence of algebraic loops. |
| Sample time | A scalar specifying the sampling period or a two-element vector specifying the sampling period and offset, in seconds \((\mathrm{s})\) . This parameter is enabled only if the subsystem is atomic and specifies the sample time with which the subsystem and the components that it comprises are executed. A setting of auto (which is the default) causes the subsystem to choose its sample time based on the components that it comprises. See also section Sample Times . |
| Enable code generation | Checking this option causes the subsystem to be added to the list of systems in the Coder Options dialog (see Generating Code ). Note that it is not possible to enable code generation for a subsystem that is contained by or that itself contains other subsystems that enable code generation. Checking this option also implicitly makes the subsystem atomic and disables the minimization of algebraic loops. |
| Discretization step size | This parameter is enabled only if code generation is enabled. It specifies the base sample time for the generated code, in seconds \((\mathrm{s})\) , and is used to discretize the physical model equations (see Physical Model Discretization ) and continuous state variables of control blocks. |
| Simulation mode | This parameter is enabled only if code generation is enabled. When this parameter is set to Normal , which is the default, the subsystem is simulated like a normal atomic subsystem. When the parameter is set to CodeGen , the generated code is compiled and linked to PLECS to be executed instead of the subsystem during a simulation. In connection with the “Traces” feature of the scopes (see Adding Traces ), this allows you to easily verify the fidelity of the generated code against a normal simulation. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/subsystem/_

<!-- END VERBATIM TABLE: subsystem-execution-settings -->

<!-- BEGIN VERBATIM TABLE: conf_subsystem-parameters -->

| Name | Description |
| --- | --- |
| Configuration | The name of the internal schematic that is used during simulation. The variable Configuration can be used in the mask initialization commands to check the current configuration. It contains an integer value starting at \(1\) for the first configuration. |

_Source: https://docs.plexim.com/plecs/latest/components-by-category/conf_subsystem/_

<!-- END VERBATIM TABLE: conf_subsystem-parameters -->

<!-- BEGIN VERBATIM TABLE: masking-subsystems-table-0 -->

| Property | Description |
| --- | --- |
| FontSize | An integer specifying the font size of the text. |
| TextFormat | Specify the string PlainText to display the text as is (the default) or RichText to enable HTML markup such as <b></b> or <sup></sup> . |
| Color | A string specifying the color name (preferred). All appearance-sensitive PLECS Colors are allowed. A vector { r , g , b } of three integers in the range from \(0\) to \(255\) specifying the color in RBG format. This color applies in light mode and is automatically transformed in dark mode (similar hue, inverted lightness). A table { light = { r , g , b }, dark = { r2 , g2 , b2 }} assigning custom colors in RGB format to each appearance. Note The table’s dark mode color defaults to the light mode color, such that {light = {r, g, b}} results in a fixed color for all appearances. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/_

<!-- END VERBATIM TABLE: masking-subsystems-table-0 -->

<!-- BEGIN VERBATIM TABLE: masking-subsystems-table-1 -->

| Command | Syntax |
| --- | --- |
| Text | text('text') text(x, y, 'text') |
| Line | line(xvec, yvec) |
| Patch | patch(xvec, yvec) |
| Circle | circle(x, y, r) |
| Color | color(r, g, b) |
| Image | image(xvec, yvec, imread('filename')) image(xvec, yvec, imread('filename'), 'on') |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/_

<!-- END VERBATIM TABLE: masking-subsystems-table-1 -->

<!-- BEGIN VERBATIM TABLE: masking-subsystems-table-2 -->

| Color name | Light | Dark | Description |
| --- | --- | --- | --- |
| "text" |  |  | default text color |
| "electrical" |  |  | electrical domain color |
| "signal" |  |  | signal connection color |
| "axis" |  |  | axis color for icons |
| "thermal" |  |  | thermal domain color |
| "thermalBg" |  |  | thermal domain background |
| "magnetic" |  |  | magnetic domain color |
| "magneticBg" |  |  | magnetic domain background |
| "rotational" |  |  | rotational domain color |
| "rotationalBg" |  |  | rotational domain background |
| "translational" |  |  | translational domain color |
| "translationalBg" |  |  | translational domain background |
| "event" |  |  | event connection color |
| "normalFg" |  |  | normal foreground |
| "normalBg" |  |  | schematic background (configurable in dark mode) |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/_

<!-- END VERBATIM TABLE: masking-subsystems-table-2 -->

<!-- BEGIN VERBATIM TABLE: masking-subsystems-table-3 -->

| Component | Function Call |
| --- | --- |
| Node | IconLib.node(x0, y0) |
| Resistor | IconLib.resistor(x0, y0, params) |
| Capacitor | IconLib.capacitor(x0, y0, params) |
| Inductor | IconLib.inductor(x0, y0, params) |
| Ideal Transformer | IconLib.transformer(x0, y0, params) |
| Diode | IconLib.diode(x0, y0, params) |
| Thyristor | IconLib.thyristor(x0, y0, params) |
| MOSFET | IconLib.mosfet(x0, y0, params) |
| MOSFET with Diode | IconLib.mosfetDiode(x0, y0, params) |
| IGBT | IconLib.igbt(x0, y0, params) |
| IGBT with Diode | IconLib.igbtDiode(x0, y0, params) |
| Bipolar Junction Transistor | IconLib.bjt(x0, y0, params) |
| Junction Field Effect Transistor | IconLib.jfet(x0, y0, params) |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/_

<!-- END VERBATIM TABLE: masking-subsystems-table-3 -->

<!-- BEGIN VERBATIM TABLE: masking-subsystems-table-4 -->

| Keyword | Data Type | Description | Elements |
| --- | --- | --- | --- |
| rotate | Number | Specifies the rotation angle (clockwise rotation). Must be an integer multiple of 90. | all elements |
| flip | Boolean | Flips the unrotated icon about the x-axis. | all elements |
| wireLength | Number Table of Numbers | Specifies the additional length of the terminal wires. Can be either a number or a table of numbers (one number per terminal). The default value of 0 reproduces the standard icons used in the PLECS library browser. | all elements |
| showArrow | Boolean | Adds an arrow decoration to indicate the direction of positive current flow. | inductor |
| showPolarity | Boolean | Adds an annotation for the polarity of the device. | capacitor transformer |
| polarity | String | Sets the polarity of the transformer. Available options are "+" , "-" , "+-" and "-+" . Note that the annotation is only shown if showPolarity is enabled. | transformer |
| showCore | Boolean | Adds a magnetic core decoration. | transformer |
| deviceType | String | Defines the transistor type. For a MOSFET or a JFET, use "n" and "p" to indicate the channel type. For a BJT, the available options are "npn" and "pnp" . By default, "n" and "npn" are assumed, respectively. | mosfet mosfetDiode bjt jfet |
| shiftGate | Boolean | Shifts the gate terminal towards the source terminal (MOSFET, JFET) or the emitter terminal (IGBT). By default, the gate terminal is centered. | mosfet mosfetDiode igbt igbtDiode jfet |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/_

<!-- END VERBATIM TABLE: masking-subsystems-table-4 -->

<!-- BEGIN VERBATIM TABLE: masking-subsystems-table-5 -->

| Type | Description |
| --- | --- |
| Edit | Shows a line edit field. The entered text is interpreted as a MATLAB/Octave expression and is evaluated when a simulation is started. |
| String | Shows a line edit field and a selector that controls whether the entered text is interpreted as a literal string or as a MATLAB/Octave expression that evaluates to a string. |
| Combo Box | Shows a pop-up menu that allows the user to select an item from a list of possible options. Use the Combo box values editor below the parameter list to enter the list of possible options and their associated integer values that are assigned to the parameter variable. The values must be unique integers. |
| String-Valued Combo Box | Shows a pop-up menu that allows the user to select an item from a list of possible options. Use the String-valued combo box values editor below the parameter list to enter the list of possible options and their associated string values that are assigned to the parameter variable. |
| Thermal | Shows a thermal parameter editor that allows the user to specify a thermal description (see Thermal Description Parameter for details). If you enter a text in the Device type filter editor below the parameter list, the thermal parameter editor will show only thermal descriptions that have the matching device type. Otherwise, all thermal descriptions will be shown. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/_

<!-- END VERBATIM TABLE: masking-subsystems-table-5 -->

<!-- BEGIN VERBATIM TABLE: masking-subsystems-table-6 -->

| Property | Description |
| --- | --- |
| Value | A string specifying the parameter value |
| Enable | A boolean (i.e. true or false ) specifying the enable state of the parameter. A disabled parameter is greyed out in the dialog and cannot be modified. |
| Visible | A boolean (i.e. true or false ) specifying the visibility of the parameter in the dialog |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/_

<!-- END VERBATIM TABLE: masking-subsystems-table-6 -->

<!-- BEGIN VERBATIM TABLE: masking-subsystems-mask-icon-properties -->

| Name | Description |
| --- | --- |
| Show subsystem frame | The subsystem frame is the rectangle that encloses the block. It is drawn if this property is set, otherwise it is hidden. |
| Hide terminal labels | This property controls whether the terminal labels underneath the icon are shown or hidden. A terminal label is only shown if this property is unset and the name of the corresponding port block is visible. |
| Icon rotates | If drawing commands are provided, this property determines whether the drawn icon rotates when the component is rotated. The drawn icon remains stationary if this property is unchecked. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/_

<!-- END VERBATIM TABLE: masking-subsystems-mask-icon-properties -->

<!-- BEGIN VERBATIM TABLE: masking-subsystems-mask-help -->

| Name | Description |
| --- | --- |
| Remote URL | A URL of the form https://www.plexim.com is opened using the default browser of your operating system. |
| Local HTML File | A local HTML file is specified with an absolute path (e.g. file:///C:/absolute/path/helpdoc.html ) or with a relative path (e.g. file:relative/helpdoc.html ). A relative path is resolved relative to the parent folder of the model file containing the subsystem. If the subsystem is a library link or model reference , the relative path is resolved relative to the parent folder of the source library or model file. Local HTML files are also opened using the default browser of your operating system. |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/_

<!-- END VERBATIM TABLE: masking-subsystems-mask-help -->

<!-- BEGIN VERBATIM TABLE: masking-subsystems-types-and-variables -->

| Name | Description |
| --- | --- |
| Nil | Nil is a type with the single value nil . It is used to represent the absence of a useful value. |
| Booleans | The Boolean type has two values false and true . It can be used in conditional expressions. If you use other types in conditional expressions, beware that Lua considers only the Boolean false and nil as false and anything else as true. In particular, both the numerical 0 and the empty string '' or "" are considered true in conditional tests. Lua supports the logical operators and , or and not . |
| Numbers | Lua differentiates between (double-precision) floating point numbers and (64-bit) integer numbers. Numerals with a decimal point or an exponent are considered floats; otherwise, they are treated as integers. |
| Strings | String literals in Lua can be delimited by single or double matching quotes: local a = "a string" local b = 'another string' The difference between the two kinds is that inside one kind of quotes you can use the other kind of quote without needing to escape it. The escape character is the backslash ( \ ), and the common C escape sequences such as \n for newline are supported. Long string literals are delimited with matching double square brackets that enclose zero or more equal signs, e.g. [[...]] or [==[...]==] . They can span several lines and do not interpret escape sequences. |
| Tables | Tables are Lua’s generic data structuring mechanism. They are used to represent e.g. arrays, sets or records. A table is essentially an associative array that accepts as keys not only numbers or strings but any other value except nil . A table is constructed with curly braces and a sequence of key/value pairs, e.g.: a = { x = 10 , y = 20 } |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/_

<!-- END VERBATIM TABLE: masking-subsystems-types-and-variables -->

<!-- BEGIN VERBATIM TABLE: masking-subsystems-control-structures -->

| Name | Description |
| --- | --- |
| if, then, else | The if statement tests its condition and executes the then branch if the condition is true and otherwise the else part. The condition can result in any value, but as mentioned earlier, Lua treats all values other than nil and false as true. In particular, both the numerical 0 and the empty string ( '' ) are treated as true . if Dialog : get ( 'choice' ) == '1' then Icon : text ( '+' ) else Icon : text ( '-' ) end Multiple conditions can be tested with the elseif statement. It is similar to an else followed by an if but avoids the need for and extra end : if Dialog : get ( 'choice' ) == '1' then Icon : text ( '+' ) elseif Dialog : get ( 'choice' ) == '2' then Icon : text ( '-' ) else Icon : text ( '+/-' ) end |
| for | The for statement has the following form: for x = - 10 , 10 , 5 do Icon : line ({ x , x }, { - 10 , 10 }) end The loop variable, x , which is implicitly local to the loop, is successively assigned the values from - 10 to 10 with an increment of 5 , and for each value the loop body is executed. The result of the example will be five parallel vertical lines. The step value is optional; if it is omitted, Lua will assume a step value of 1 . |

_Source: https://docs.plexim.com/plecs/latest/using-plecs/masking-subsystems/_

<!-- END VERBATIM TABLE: masking-subsystems-control-structures -->
