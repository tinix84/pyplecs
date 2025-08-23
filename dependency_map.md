# PyPLECS Dependency Map

## Core Class and Method Relationships

- `PlecsApp`
  - Uses: `ConfigManager` (for config)
  - Starts/stops PLECS process (no longer does GUI automation)
  - Used by: CLI demo, integration tests
  - Calls: `_find_plecs_executable`, `open_plecs`, `kill_plecs`, `set_plecs_high_priority`, `get_plecs_cpu`
  - Can instantiate `PlecsServer` (via `load_file`)

- `PlecsServer`
  - Uses: `xmlrpc.client.Server` for XML-RPC communication
  - Methods: `run_sim_single`, `run_sim_with_datastream`, `load_modelvars`, `close`, etc.
  - Used by: `RealPlecsSimulator` (in CLI demo), tests, orchestration

- `RealPlecsSimulator` (cli_demo_nomocks.py)
  - Uses: `PlecsApp` to start/stop PLECS
  - Uses: `PlecsServer` for XML-RPC
  - Uses: `SimulationCache` for caching
  - Used by: CLI demo

- `SimulationPlan`, `SimulationViewer` (pyplecs/orchestration)
  - Used by: CLI demo, orchestration, tests

- `SimulationCache`
  - Used by: `RealPlecsSimulator`, orchestration

- `ConfigManager`
  - Used by: `PlecsApp`, `PlecsServer`

## XML-RPC Communication Patterns

- `PlecsServer` is the main XML-RPC client:
  - Instantiates: `self.server = xmlrpc.client.Server('http://localhost:' + port + '/RPC2')`
  - Calls: `self.server.plecs.load(...)`, `self.server.plecs.set(...)`, `self.server.plecs.getModelVariables(...)`, `self.server.plecs.run(...)`, etc.
  - Used by: `run_sim_with_datastream`, `load_modelvars`, etc.

- `RealPlecsSimulator` (cli_demo_nomocks.py):
  - Calls `PlecsServer.load_modelvars()` and `PlecsServer.run_sim_with_datastream()`
  - Handles parameter conversion and debug printing

- Tests:
  - Use `PlecsServer` directly or via `pyplecs` import
  - Mock XML-RPC calls for unit/integration tests

## File/Module Relationships

- `pyplecs/pyplecs.py` defines core classes: `PlecsApp`, `PlecsServer`
- `pyplecs/orchestration/` contains orchestration and planning tools
- `pyplecs/cache.py` provides caching
- `pyplecs/config.py` provides configuration
- `cli_demo_nomocks.py` demonstrates end-to-end workflow
- `tests/` use all of the above, with mocks for XML-RPC where needed

---

This map summarizes the main dependencies and communication flows in PyPLECS as of this scan. For more detail, see the code and test files directly.
