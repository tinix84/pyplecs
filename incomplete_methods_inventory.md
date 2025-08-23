# Incomplete Methods and TODO Inventory

## pyplecs/pyplecs.py

- `PlecsApp.run_simulation_by_gui(self, plecs_mdl)`
  - `raise NotImplementedError("GUI automation removed. Use PlecsServer with XML-RPC instead.")`
- `PlecsApp.load_file(self, plecs_mdl, mode='XML-RPC')` (when mode=="gui")
  - `raise NotImplementedError("GUI mode removed. Use XML-RPC mode instead.")`
- `PlecsApp.check_if_simulation_running(self, plecs_mdl)`
  - `# TODO: implement via XML-RPC or process monitoring`
- `PlecsServer.load_modelvars(self, model_vars: dict)`
  - `#TODO: merge with load_model_vars`
- (Commented) `# TODO: read input parameter list from plecs file, parsing init workspace`
- (Commented) `# TODO: read from workspace write to plecs file`

## tests/integration/test_automated.py
- `# TODO: Implement simulation status checking logic`
- `# TODO: Implement value setting logic`

## docs/DEV_PLAN.md
- Plan references: "Fix all incomplete implementations and TODO items"
- Plan references: "Incomplete implementations with 'TODO' comments and 'Not implemented mode' exceptions"
- Plan references: "Address the incomplete implementations and TODO items, particularly in the core pyplecs.py file"

## docs/PROGRESS_MEMO.md
- Mentions: "GUI automation methods now raise NotImplementedError with helpful messages"
- Mentions: "run_simulation_by_gui() - now raises NotImplementedError"
- Mentions: "GUI-based file loading - now raises NotImplementedError"

---

This inventory lists all known incomplete, stubbed, or not-yet-implemented methods and TODOs as of this scan. See also the DEV_PLAN.md for project priorities.
