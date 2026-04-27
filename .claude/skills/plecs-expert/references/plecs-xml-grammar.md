# `.plecs` XML Grammar

Hand-authored from `data/*.plecs` samples in this repo. PLECS publishes no public XML grammar page on docs.plexim.com.

PLECS files are not XML. Format is Tcl-ish curly-brace key-value text. Keys followed by atom or quoted string. Sub-blocks open with `Name {` and close with `}`. Multi-line strings continue on the next line by closing the quote and reopening it. Comments do not appear in saved files.

Top-level outer block: `Plecs { ... }`. Inside it: scalar settings, then `Terminal { ... }` (zero or more), then `Schematic { ... }`. The `Schematic` block holds `Component { ... }` and `Connection { ... }` children.

## Top-level grammar (extracted from `data/simple_buck_prb.plecs.bak`)

<!-- BEGIN VERBATIM TABLE: plecs-xml-grammar -->

| Element | Parent | Cardinality | Children / Notes |
| --- | --- | --- | --- |
| `Plecs { }` | (file root) | 1 | Outer container. Holds model name, version, solver settings, code-gen settings, init code, then `Terminal` and `Schematic`. |
| `Name "<str>"` | `Plecs` | 1 | Model name. |
| `Version "<str>"` | `Plecs` | 1 | PLECS version that wrote the file. Example: `"4.7"`. |
| `CircuitModel "<str>"` | `Plecs` | 1 | Either `"ContStateSpace"` or `"DiscStateSpace"`. |
| `StartTime "<expr>"` | `Plecs` | 1 | Solver start time. String holding a MATLAB/Octave expression. |
| `TimeSpan "<expr>"` | `Plecs` | 1 | Solver run length. |
| `Solver "<str>"` | `Plecs` | 1 | One of `auto`, `dopri`, `radau`, `discrete`. |
| `MaxStep`, `InitStep`, `FixedStep`, `Refine`, `ZCStepSize`, `RelTol`, `AbsTol` | `Plecs` | 1 each | Solver tuning knobs. Strings holding numbers. |
| `TurnOnThreshold "<expr>"` | `Plecs` | 1 | Diode turn-on threshold. |
| `InitializationCommands "<str>"` | `Plecs` | 1 | Multi-line MATLAB/Octave init code. Lines wrap by closing+reopening quotes. |
| `InitialState`, `SystemState` | `Plecs` | 1 each | Initial-condition selector + stored state struct. |
| `TaskingMode`, `TaskConfigurations` | `Plecs` | 1 each | Code-gen tasking config. |
| `CodeGen*` keys | `Plecs` | 0..N | All code-gen options (`CodeGenTarget`, `CodeGenBaseName`, `CodeGenOutputDir`, `CodeGenParameterInlining`, etc.). |
| `Terminal { ... }` | `Plecs` | 0..N | Sub-block. Holds `Type Output` or `Type Input` and `Index "<int>"`. |
| `Schematic { ... }` | `Plecs` | 1 | Holds the model graph: `Location`, `ZoomFactor`, then `Component` and `Connection` children. |
| `Component { ... }` | `Schematic` | 0..N | One block per component instance. See child grammar below. |
| `Connection { ... }` | `Schematic` | 0..N | One per wire. See child grammar below. |
| `Type <atom>` | `Component` | 1 | Library type name. Examples: `Resistor`, `Inductor`, `Capacitor`, `Diode`, `Mosfet`, `DCVoltageSource`, `PulseGenerator`, `Scope`, `PlecsProbe`, `Output`, `Display`, `Constant`. |
| `Name "<str>"` | `Component` | 1 | Instance name. Newlines allowed via `\n`. |
| `Show <on\|off>` | `Component` | 1 | Whether name label is visible. |
| `Position [x, y]` | `Component` | 1 | Schematic placement. |
| `Direction <up\|down\|left\|right>` | `Component` | 1 | Rotation. |
| `Flipped <on\|off>` | `Component` | 1 | Mirror flag. |
| `LabelPosition <atom>` | `Component` | 1 | One of `north`, `south`, `east`, `west`, `northeast`, `southeast`, etc. |
| `Frame [x1, y1; x2, y2]` | `Component` | 0..1 | Bounding box for masked / textual blocks. |
| `Parameter { Variable "<name>" Value "<expr>" Show <on\|off> }` | `Component` | 0..N | One entry per editable parameter. `Variable` matches the docs name; `Value` is a MATLAB/Octave expression. |
| `Probe { Component "<inst>" Path "<str>" Signals { "<sig>", ... } }` | `Component` of Type `PlecsProbe` | 0..N | Per measured signal entry. |
| `Type Wire` | `Connection` | 1 | Always `Wire` for electrical/signal connections. |
| `SrcComponent "<inst>"`, `SrcTerminal <n>` | `Connection` | 1 each | Source block + terminal index. |
| `DstComponent "<inst>"`, `DstTerminal <n>` | `Connection` | 0..1 each | Destination block + terminal index. Absent when wire ends in a junction. |
| `Points [x1, y1; x2, y2; ...]` | `Connection` | 0..1 | Polyline waypoints in schematic coords. |
| `Branch { ... }` | `Connection` | 0..N | T-junction child wire. Same fields as `Connection`. |

_Source: hand-extracted from `data/simple_buck_prb.plecs.bak`, `data/cuk.plecs`, `data/B6_diode.plecs`._

<!-- END VERBATIM TABLE: plecs-xml-grammar -->

## MVE — minimum viable buck excerpt

Trimmed from `data/simple_buck_prb.plecs.bak`. Shows top-level scalars, one `Component`, one `Connection`.

```
Plecs {
  Name          "simple_buck_prb"
  Version       "4.7"
  CircuitModel  "ContStateSpace"
  StartTime     "0.0"
  TimeSpan      "T_sim"
  Solver        "radau"
  MaxStep       "1e-6"
  InitializationCommands "T_sim = 1e-3;\nVi = 24;\nVo_ref = 12;\n"
  Schematic {
    Location      [915, 288; 1725, 613]
    ZoomFactor    1
    Component {
      Type          DCVoltageSource
      Name          "VDCin"
      Show          on
      Position      [85, 95]
      Direction     up
      Flipped       off
      LabelPosition west
      Parameter {
        Variable      "V"
        Value         "Vi"
        Show          off
      }
    }
    Component {
      Type          Resistor
      Name          "R1"
      Show          on
      Position      [370, 100]
      Direction     up
      Flipped       off
      LabelPosition east
      Parameter {
        Variable      "R"
        Value         "Ro"
        Show          off
      }
    }
    Connection {
      Type          Wire
      SrcComponent  "VDCin"
      SrcTerminal   1
      Points        [85, 60]
      DstComponent  "R1"
      DstTerminal   1
    }
  }
}
```

### Notes

- File is plain ASCII. Editable by hand. CRLF line endings on Windows save.
- Boolean atoms: `on` / `off` (component flags), or strings like `"1"` / `"0"` (numeric flags).
- Multi-line strings split with `"...continue\n"` followed by `"...next line"` on next physical row.
- Component `Type` strings match the underlying PLECS class name, not the dialog title (e.g. `Mosfet`, not `MOSFET`).
- Terminal indices in `Connection` start at 1.
- For converter use cases the round-trip parser only needs to handle: `Plecs`, `Schematic`, `Component`, `Connection`, `Parameter`, `Probe`, `Branch`, `Terminal`. Other top-level keys are scalar and can pass through verbatim.
