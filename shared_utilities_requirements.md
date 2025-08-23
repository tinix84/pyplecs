# Shared Utilities Requirements — PyPLECS

Purpose: list and specify small, reusable utilities that make the core PlecsServer / PlecsApp methods concise, testable, and consistent.

Each utility below includes: purpose, suggested signature, behavior, edge-cases, and simple tests to add.

---

## 1) optstruct_builder / dict_to_plecs_opts
Purpose: convert a bare dict of model variables into a PLECS `optStruct` with proper type coercion.
Suggested signature:
- def dict_to_plecs_opts(vars_dict: dict, coerce: bool = True) -> dict

Behavior:
- If `vars_dict` contains key `ModelVars`, normalize the inner dict's values to float (or leave expressions as str if cannot coerce and coerce=False).
- If bare dict, return `{'ModelVars': normalized_dict}`.

Edge cases:
- Values like `"1e3"`, `"3.14"` -> coerce to floats.
- Non-numeric expressions like `"10*sin(2*pi)"` -> when coerce=False leave as-is; when coerce=True raise ValueError or accept string if PLECS accepts expressions.

Tests:
- bare ints/floats -> floats
- contains `ModelVars` -> normalized
- coerce=False -> string preserved

---

## 2) rpc_call_wrapper with retries
Purpose: centralize and standardize RPC calls to PLECS, adding timeouts and retry logic.
Suggested signature:
- def rpc_call(server_proxy, method_name: str, *args, timeout: float = 5.0, retries: int = 3, backoff: float = 0.5)

Behavior:
- Use `getattr(server_proxy, method_name)` or `server_proxy.plecs.<method>` pattern as needed.
- On connection errors (socket.error, xmlrpc.client.ProtocolError), retry with exponential/backoff until retries exhausted.
- On xmlrpc.client.Fault, propagate the Fault.

Edge cases:
- Long-running RPC calls: allow passing `timeout=None` to block until completion.

Tests:
- Mock server proxy to raise socket.error twice then succeed; wrapper returns value after retries.

---

## 3) normalize_simulation_result
Purpose: Convert PLECS `simulate` return payload into a consistent Python structure (times array + values mapping or pandas.DataFrame).
Signature:
- def normalize_simulation_result(raw_result) -> dict

Behavior:
- Accepts payloads like `{'time': [...], 'signals': {...}}` or PLECS proprietary structures.
- Always return `{'time': np.ndarray, 'signals': {name: np.ndarray}}` and optionally `dataframe`: pandas.DataFrame with a 'time' column.

Edge cases:
- Scalar results for single-signal simulations -> wrap into arrays.
- Missing 'time' field -> infer from sample count and `sampleInterval` if present.

Tests:
- Varied raw_result shapes -> consistent outputs.

---

## 4) model_vars_validator
Purpose: Validate that provided model variables match expected names from model metadata.
Signature:
- def validate_model_vars(provided: dict, allowed: Optional[set]=None, strict: bool = False) -> Tuple[dict, list]

Behavior:
- If allowed provided, return tuple (filtered_vars, unknown_vars_list). When `strict=True`, raise ValueError on unknown vars.
- When allowed not provided, return provided as-is and empty unknown list.

Tests:
- unknown vars returned in list; strict raises.

---

## 5) conversion helpers for timeseries
Purpose: small helpers to convert between dataset shapes that PLECS RPC requires and pandas/numpy objects used by the project.
Signatures:
- timeseries_to_plecs_matrix(ts: pd.DataFrame or dict) -> list-of-lists
- plecs_matrix_to_dataframe(mat) -> pd.DataFrame

Behavior:
- Ensure time column is present and first column in the matrix shape.

Tests:
- round-trip test with simple DataFrame.

---

## 6) process_inspector helpers
Purpose: encapsulate psutil queries for PLECS processes and translate to model instances.
Signature:
- def find_plecs_processes() -> List[psutil.Process]
- def process_matches_model(proc: psutil.Process, model_name: str) -> bool

Behavior:
- `find_plecs_processes` returns running PLECS executables by executable name or command line match.
- `process_matches_model` attempts to inspect cmdline or window title (if available) to match model_name.

Tests:
- Mock psutil.Process objects and assert filtering.

---

## 7) caching adapter interface
Purpose: standardize how SimulationCache is called from PlecsServer and RealPlecsSimulator.
Signature (interface):
- class CacheAdapter:
    - def get(cache_key) -> Optional[result]
    - def set(cache_key, result, ttl=None) -> None
    - def key_for_simulation(model_name, optStruct) -> str

Behavior:
- Keys should be stable and deterministic across equivalent optStruct inputs; use canonical serialization (sorted keys, stable float formatting).

Tests:
- Two equivalent optStructs create same key; setting and getting returns expected value.

---

## 8) small utilities: logging helpers, config readers
- `get_rpc_url_from_config(cfg) -> str` — standardize host/port building for PlecsServer
- `safe_float_cast(x, default=None)` — cast subsystems values to float or return default.


---

## Prioritization
1. `dict_to_plecs_opts` and `rpc_call_wrapper` — these immediate helpers make most server code simpler and safer.
2. `normalize_simulation_result` and `model_vars_validator` — required for consistent downstream processing.
3. `process_inspector` — needed for `check_if_simulation_running`.
4. CacheAdapter — improves determinism and testing for simulate_batch flows.


---

## Tests to add (minimum)
- Unit tests for `dict_to_plecs_opts` with coerce True/False
- Unit tests for `rpc_call_wrapper` with retries
- Unit tests for `normalize_simulation_result` with three representative PLECS payloads
- Unit tests for `model_vars_validator` strict vs non-strict
- Mocked tests for `process_inspector` using fake Process objects



