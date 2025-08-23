# Method Specifications — PyPLECS

Scope: analyze incomplete methods and nearby working methods in `pyplecs/pyplecs.py`. For each method below I document: expected inputs, outputs, side-effects, error modes, and suggested signature.

## Summary of incomplete/stubbed methods
- `PlecsApp.check_if_simulation_running(plecs_mdl)` — TODO
- `PlecsServer.load_modelvars(model_vars: dict)` — marked TODO: merge with `load_model_vars`
- `GenericConverterPlecsMdl.__repr__(self)` — `pass`
- Commented helpers: `load_modelvars_struct_from_plecs`, `load_input_vars`

Additionally we document related server methods to align signatures and patterns.

---

## Conventions used below
- Types use standard Python typing (str, int, float, bool, dict, list, Path-like)
- "RPC" denotes the PLECS XML-RPC server proxy available at `self.server`
- "optStruct" denotes the PLECS option structure used by `plecs.simulate` where `{'ModelVars': {...}}`

---

### 1) PlecsApp.check_if_simulation_running(plecs_mdl)
Purpose: return the current running status of a loaded PLECS model instance.
Suggested signature:
- def check_if_simulation_running(self, plecs_mdl) -> bool

Inputs:
- plecs_mdl: object with attributes identifying the model instance; at minimum it should expose either `simulation_name` or `model_name` or the window/process identifier. Accepts either `GenericConverterPlecsMdl` or an object with `.simulation_name`.

Outputs:
- bool — True if simulation is running, False otherwise.

Side effects:
- None (read-only). Optionally logs at DEBUG level.

Errors and modes:
- On inability to determine status (e.g., XML-RPC not connected and process not found) raise `RuntimeError('Unknown simulation state')` or return `False` if the design prefers conservative behavior.

Implementation notes / recommended behavior:
- Prefer XML-RPC call if `PlecsServer` is available: call `plecs.scope` or a specific RPC helper to check simulation state if available (some PLECS servers expose `getSimulationStatus` or similar).
- Fallback: check OS processes for PLECS process and inspect model name via RPC `get` on top-level scope or via title (if accessible). Use `psutil` to find running PLECS processes.
- Edge cases: multiple PLECS instances with same model loaded — return True if any instance reports running.

---

### 2) PlecsServer.load_modelvars(model_vars: dict)
Purpose: Set `self.optStruct` from a dictionary of model variables (accept either raw model_vars or wrapped `{'ModelVars': {...}}`). Align behavior with `load_model_vars`.
Suggested signature:
- def load_modelvars(self, model_vars: dict) -> None

Inputs:
- model_vars: either
  - dict like `{'ModelVars': {'Vi': 250.0, ...}}` or
  - dict like `{'Vi': 250.0, ...}` (bare model vars)

Outputs:
- None. Updates `self.optStruct` internal state to a valid optStruct ready for call to `simulate`.

Side effects:
- Mutates `self.optStruct` on success. Logs at INFO/DEBUG levels. Validates numeric typing.

Errors and modes:
- Raises `TypeError` for invalid input types.
- Raises `ValueError` if conversion to float fails for a value and caller did not request lenient mode.

Implementation notes:
- If input contains top-level key `'ModelVars'` assume it's already in correct shape and assign after converting contained values to float.
- If input is bare dict of variables, convert to optStruct via `dict_to_plecs_opts` helper.
- Always coerce values to standard Python float (XML-RPC limitations), but allow an optional parameter `coerce=True` in future.
- Add an optional `validate=True` flag to fail early on unknown variables (requires model variable list).

Example behavior:
- `load_modelvars({'Vi': 250, 'Ii_max': 25})` -> sets `self.optStruct = {'ModelVars': {'Vi': 250.0, 'Ii_max': 25.0}}`
- `load_modelvars({'ModelVars': {...}})` -> normalizes numeric types and assigns.

---

### 3) GenericConverterPlecsMdl.__repr__(self)
Purpose: Implement a readable representation for debugging and logging.
Suggested signature:
- def __repr__(self) -> str

Outputs:
- A short string e.g. "GenericConverterPlecsMdl(name='simple_buck', folder='data', type='plecs', model_vars=14)"

Side effects:
- None.

Notes:
- Use only available attributes (`_name`, `_model_name`, `_folder`). Avoid heavy computation or I/O.

### GenericConverterPlecsMdl.load_modelvars_struct_from_plecs(self)
Purpose: Extract model variables structure from PLECS file.
Suggested signature:
- def load_modelvars_struct_from_plecs(self) -> dict

Outputs:
- A dictionary containing initialized variables and parameters.

Side effects:
- Updates `optStruct` with parsed variables.

Notes:
- Raise `ModelParsingError` for parsing failures.

### GenericConverterPlecsMdl.get_model_info(self)
Purpose: Get comprehensive model information.
Suggested signature:
- def get_model_info(self) -> dict

Outputs:
- A dictionary containing model name, file path, type, folder, model variables, components, and outputs.

Side effects:
- None.

Notes:
- Ensure all attributes are populated before returning.

---

## Analysis of existing working methods for patterns

A. XML-RPC usage pattern (PlecsServer):
- `self.server = xmlrpc.client.Server('http://localhost:' + port + '/RPC2')`
- RPC methods called as `self.server.plecs.<fn>(...)`.
- Methods guard for availability using `hasattr(self.server, 'plecs')` and `hasattr(self.server.plecs, 'getModelVariables')`.
- Errors from RPC are handled with `xmlrpc.client.Fault` in some places.

B. Data normalization pattern:
- `dict_to_plecs_opts()` coerces values to float and wraps them in `{'ModelVars': ...}`.
- `load_model_vars` and `load_modelvar` set `self.optStruct` and coerce to float where needed.

C. Simulation invocation:
- `run_sim_with_datastream` calls `self.load_modelvars(model_vars=param_dict)` then `self.server.plecs.simulate(self.modelName, self.optStruct)`.

D. Error handling pattern:
- Methods either raise exceptions or return (ok, value) tuples for caller convenience — `list_model_variables()` uses (ok, value) pattern.

---

## Method signatures to add to code (recommended minimal implementations)

1. PlecsApp.check_if_simulation_running
- def check_if_simulation_running(self, plecs_mdl) -> bool
  - prefer RPC: call a helper (see shared utilities) `rpc_get_simulation_status(server, model_name)`
  - fallback to process detection via `psutil`

2. PlecsServer.load_modelvars
- def load_modelvars(self, model_vars: dict, coerce: bool = True, validate: bool = False) -> None
  - normalize into `self.optStruct`

3. GenericConverterPlecsMdl.__repr__
- def __repr__(self) -> str

4. GenericConverterPlecsMdl.load_modelvars_struct_from_plecs
- def load_modelvars_struct_from_plecs(self) -> dict

5. GenericConverterPlecsMdl.load_input_vars
- def load_input_vars(self) -> None

---

## Edge cases & test cases to include for each spec
- Missing RPC server (connection refused) -> ensure graceful fallback to parser or process-check and appropriate exception message.
- Non-numeric model variable values (expressions) -> should either be rejected or handled as expressions depending on upstream design.
- Partial variable sets -> `load_modelvars` should merge with default `optStruct` rather than overwrite, or provide explicit `overwrite` flag.
- Multiple PLECS instances -> identify by model name; document behavior.

---

## Next steps
- Implement `PlecsServer.load_modelvars` and add unit tests for coercion and input shapes.
- Implement `PlecsApp.check_if_simulation_running` using an XML-RPC helper and psutil fallback; add unit tests using mocks for RPC and psutil.
- Implement `GenericConverterPlecsMdl.__repr__` and add small test.



