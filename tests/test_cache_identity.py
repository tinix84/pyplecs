"""Composite cache identity: invariance, sensitivity, readability, degrade, Merkle."""

import copy
import difflib
import random
import re
import sys
import time
from pathlib import Path

import pytest

from pyplecs.cache.identity import (
    CacheKey,
    PlecsEnvironment,
    identify,
    parameter_bindings,
    solver_bindings,
)
from pyplecs.cache.topology import canonicalize_document
from pyplecs.converter.parser import parse_plecs_text

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
FIXTURES = Path(__file__).parent / "fixtures"
TRACKED_MODELS = [
    "fb_src_prb.plecs",
    "simple_boost_prb.plecs",
    "simple_buck_prb.plecs",
    "simple_buckboost_prb.plecs",
    "simple_nibb_prb.plecs",
]
ENVIRONMENT = PlecsEnvironment("4.7-test")


def _document(path: Path) -> dict:
    return parse_plecs_text(path.read_text(encoding="utf-8"))


def _topology_id(document: dict) -> str:
    return canonicalize_document(document).topology_id


def _components(document: dict) -> list[dict]:
    components = document["Plecs"]["Schematic"]["Component"]
    return components if isinstance(components, list) else [components]


# -- invariance ----------------------------------------------------------------


@pytest.mark.parametrize("filename", TRACKED_MODELS)
def test_topology_id_is_invariant_to_layout_cosmetics_and_order(filename):
    document = _document(DATA_DIR / filename)
    baseline = _topology_id(document)

    perturbed = copy.deepcopy(document)
    schematic = perturbed["Plecs"]["Schematic"]
    schematic["Location"] = (0, 0, 1, 1)
    schematic["ZoomFactor"] = 2.5
    for component in _components(perturbed):
        component["Position"] = (component["Position"][0] + 40, component["Position"][1] - 15)
        component["Show"] = not component.get("Show", True)
        component["LabelPosition"] = "north"
        if component["Type"] in ("Resistor", "Inductor", "Capacitor"):
            component["Direction"] = "left" if component.get("Direction") != "left" else "up"
            component["Flipped"] = not component.get("Flipped", False)
        parameters = component.get("Parameter", [])
        for parameter in parameters if isinstance(parameters, list) else [parameters]:
            parameter["Show"] = not parameter.get("Show", False)
    random.Random(7).shuffle(schematic["Component"])
    random.Random(11).shuffle(schematic["Connection"])
    for connection in schematic["Connection"]:
        connection.pop("Points", None)
    perturbed["Plecs"]["Version"] = "4.9"

    assert _topology_id(perturbed) == baseline


def test_topology_id_is_invariant_to_line_endings_and_annotations():
    text = (FIXTURES / "subsystem_goto.plecs").read_text(encoding="utf-8")
    baseline = _topology_id(parse_plecs_text(text))

    crlf = parse_plecs_text(text.replace("\n", "\r\n"))
    assert _topology_id(crlf) == baseline

    without_note = parse_plecs_text(re.sub(r"    Component \{\n      Type          FreeText.*?\n    \}\n", "", text, flags=re.S))
    assert len(_components(without_note)) == len(_components(parse_plecs_text(text))) - 1
    assert _topology_id(without_note) == baseline


def test_goto_from_collapse_into_the_wire_they_stand_for():
    document = _document(FIXTURES / "subsystem_goto.plecs")
    baseline = canonicalize_document(document)

    renamed = copy.deepcopy(document)
    for component in _components(renamed):
        if component["Type"] in ("Goto", "From"):
            component["Parameter"][0]["Value"] = "renamed_tag"
    assert _topology_id(renamed) == baseline.topology_id

    names = {node["name"] for node in baseline.content["nodes"]}
    assert not names & {"Goto1", "From1", "note"}
    assert {"kind": "signal", "pins": ["Filter:1", "Vm1:3"]} in baseline.content["nets"]


# -- sensitivity ---------------------------------------------------------------


def test_topology_id_changes_when_a_wire_moves_or_a_type_changes():
    document = _document(DATA_DIR / "simple_buck_prb.plecs")
    baseline = _topology_id(document)

    rewired = copy.deepcopy(document)
    wire = next(c for c in rewired["Plecs"]["Schematic"]["Connection"] if c["Type"] == "Wire" and "DstTerminal" in c)
    wire["DstTerminal"] = 3 - wire["DstTerminal"]
    assert _topology_id(rewired) != baseline

    retyped = copy.deepcopy(document)
    next(c for c in _components(retyped) if c["Type"] == "Diode")["Type"] = "Thyristor"
    assert _topology_id(retyped) != baseline

    renamed = copy.deepcopy(document)
    inductor = next(c for c in _components(renamed) if c["Type"] == "Inductor")
    old_name, inductor["Name"] = inductor["Name"], inductor["Name"] + "_x"
    stack = list(renamed["Plecs"]["Schematic"]["Connection"])
    while stack:
        node = stack.pop()
        for key in ("SrcComponent", "DstComponent"):
            if node.get(key) == old_name:
                node[key] = inductor["Name"]
        branches = node.get("Branch", [])
        stack.extend(branches if isinstance(branches, list) else [branches])
    assert _topology_id(renamed) != baseline

    rebound = copy.deepcopy(document)
    next(c for c in _components(rebound) if c["Type"] == "Inductor")["Parameter"][0]["Value"] = "Lo2"
    assert _topology_id(rebound) != baseline


def test_reversed_polarised_part_changes_the_key_through_connectivity():
    document = _document(DATA_DIR / "simple_buck_prb.plecs")
    baseline = _topology_id(document)
    diode = next(c for c in _components(document) if c["Type"] == "Diode")["Name"]

    reversed_diode = copy.deepcopy(document)
    for connection in reversed_diode["Plecs"]["Schematic"]["Connection"]:
        stack = [connection]
        while stack:
            node = stack.pop()
            for component_key, terminal_key in (("SrcComponent", "SrcTerminal"), ("DstComponent", "DstTerminal")):
                if node.get(component_key) == diode:
                    node[terminal_key] = 3 - node[terminal_key]
            branches = node.get("Branch", [])
            stack.extend(branches if isinstance(branches, list) else [branches])

    assert _topology_id(reversed_diode) != baseline


# -- readability ---------------------------------------------------------------


def test_two_documents_that_differ_by_one_rewiring_diff_in_a_few_lines():
    document = _document(DATA_DIR / "simple_buck_prb.plecs")
    rewired = copy.deepcopy(document)
    wire = next(c for c in rewired["Plecs"]["Schematic"]["Connection"] if c["Type"] == "Wire" and "DstTerminal" in c)
    wire["DstTerminal"] = 3 - wire["DstTerminal"]

    before = canonicalize_document(document).to_json().splitlines()
    after = canonicalize_document(rewired).to_json().splitlines()
    diff = [line for line in difflib.unified_diff(before, after, lineterm="", n=0) if line[:1] in "+-"]
    changed = [line for line in diff if not line.startswith(("+++", "---"))]

    # One rewiring merges two nets: a dozen lines, every value line a pin.
    assert 0 < len(changed) <= 16
    value_lines = [line for line in changed if '"' in line]
    assert value_lines and all(re.search(r'"[A-Za-z0-9_]+:\d"|"kind"|"pins"', line) for line in value_lines)


# -- degrade and coverage -----------------------------------------------------------


@pytest.mark.parametrize("filename", TRACKED_MODELS)
def test_tracked_corpus_canonicalizes_without_degrading(filename):
    coverage = canonicalize_document(_document(DATA_DIR / filename)).coverage
    assert coverage["nodes_degraded"] == 0
    assert coverage["connections_degraded"] == 0
    assert coverage["degraded"] == []


def test_unrecognised_construct_degrades_only_its_own_region():
    document = _document(FIXTURES / "subsystem_goto.plecs")
    baseline = canonicalize_document(document)

    odd = copy.deepcopy(document)
    resistor = next(c for c in _components(odd) if c["Type"] == "Resistor")
    resistor["Mystery"] = "AAAACwAAAAAA"
    odd["Plecs"]["Schematic"]["Connection"].append(
        {"Type": "HeatPipe", "SrcComponent": "R1", "SrcTerminal": 1, "DstComponent": "V1", "DstTerminal": 1}
    )
    degraded = canonicalize_document(odd)

    assert degraded.topology_id != baseline.topology_id
    assert degraded.coverage["nodes_degraded"] == 1
    assert degraded.coverage["connections_degraded"] == 1
    assert {"kind": "node", "name": "R1", "reason": "unrecognised field Mystery"} in degraded.coverage["degraded"]
    untouched = [node for node in degraded.content["nodes"] if node["name"] != "R1"]
    assert untouched == [node for node in baseline.content["nodes"] if node["name"] != "R1"]

    resistor["Mystery"] = "BBBBCwAAAAAA"
    assert canonicalize_document(odd).topology_id != degraded.topology_id


def test_from_without_local_goto_is_kept_as_a_degraded_node():
    document = _document(FIXTURES / "subsystem_goto.plecs")
    for component in _components(document):
        if component["Type"] == "Goto":
            component["Parameter"][1]["Value"] = "3"  # global visibility

    topology = canonicalize_document(document)
    names = {node["name"] for node in topology.content["nodes"]}
    assert {"Goto1", "From1"} <= names
    assert {"kind": "node", "name": "From1", "reason": "From tag 'vo' has no local Goto"} in topology.coverage["degraded"]


# -- Merkle hierarchy -----------------------------------------------------------------


def test_subsystem_has_its_own_id_and_a_change_inside_it_is_attributable():
    document = _document(FIXTURES / "subsystem_goto.plecs")
    baseline = canonicalize_document(document)
    subsystem = next(node for node in baseline.content["nodes"] if node["type"] == "Subsystem")
    assert subsystem["interface"] == ["Input", "Output"]
    assert subsystem["topology_id"] in baseline.content["subsystems"]

    changed = copy.deepcopy(document)
    inner = next(c for c in _components(changed) if c["Type"] == "Subsystem")["Schematic"]["Component"]
    next(c for c in inner if c["Type"] == "Gain")["Parameter"][0]["Value"] = "0.25"
    after = canonicalize_document(changed)
    changed_subsystem = next(node for node in after.content["nodes"] if node["type"] == "Subsystem")

    assert after.topology_id != baseline.topology_id
    assert changed_subsystem["topology_id"] != subsystem["topology_id"]
    outer_nodes = lambda doc: [n for n in doc.content["nodes"] if n["type"] != "Subsystem"]  # noqa: E731
    assert outer_nodes(after) == outer_nodes(baseline)


def test_subsystem_interface_order_is_part_of_its_id():
    document = _document(FIXTURES / "subsystem_goto.plecs")
    baseline = canonicalize_document(document)
    swapped = copy.deepcopy(document)
    subsystem = next(c for c in _components(swapped) if c["Type"] == "Subsystem")
    subsystem["Terminal"].reverse()

    after = canonicalize_document(swapped)
    assert after.topology_id != baseline.topology_id


# -- params, solver, environment ---------------------------------------------------------


def test_parameter_bindings_let_runtime_model_vars_win_and_degrade_unknown_statements():
    bindings = parameter_bindings("Vi = 24; % input\nLo=10e-6;\n", {"Vi": "48"})
    assert bindings == {"bindings": {"Vi": "48", "Lo": "10e-6"}}

    scripted = parameter_bindings("Vi = 24;\nfor k=1:3, disp(k); end\n", {})
    assert scripted["bindings"] == {"Vi": "24"}
    assert scripted["script"].startswith("Vi = 24;")


def test_solver_bindings_keep_run_settings_and_route_unknown_fields_conservatively():
    root = _document(DATA_DIR / "simple_buck_prb.plecs")["Plecs"]
    solver = solver_bindings(root)

    assert solver["Solver"] == "radau" and solver["RelTol"] == "1e-3" and solver["InitialState"] == "1"
    assert "Name" not in solver and "Version" not in solver
    assert not any(key.startswith("CodeGen") for key in solver)
    assert "unclassified" not in solver

    root["FutureKnob"] = "7"
    assert solver_bindings(root)["unclassified"] == {"FutureKnob": "7"}


def test_identify_separates_the_four_ids(tmp_path):
    model = tmp_path / "buck.plecs"
    text = (DATA_DIR / "simple_buck_prb.plecs").read_text(encoding="utf-8")
    model.write_text(text, encoding="utf-8")
    baseline = identify(str(model), {"Vi": 24}, ENVIRONMENT).key

    assert baseline.differences(identify(str(model), {"Vi": 48}, ENVIRONMENT).key) == ["params"]
    assert baseline.differences(identify(str(model), {"Vi": 24, "run_id": 3}, ENVIRONMENT, ("run_id",)).key) == []
    assert baseline.differences(identify(str(model), {"Vi": 24}, PlecsEnvironment("4.9")).key) == ["environment"]

    model.write_text(text.replace('Solver        "radau"', 'Solver        "dopri"'), encoding="utf-8")
    assert baseline.differences(identify(str(model), {"Vi": 24}, ENVIRONMENT).key) == ["solver"]

    model.write_text(text.replace('Type          Diode', 'Type          Thyristor'), encoding="utf-8")
    assert baseline.differences(identify(str(model), {"Vi": 24}, ENVIRONMENT).key) == ["topology"]

    assert identify(str(model), {}, PlecsEnvironment(None, "unknown")) is None


def test_unparseable_and_missing_models_degrade_to_bytes_and_path(tmp_path):
    broken = tmp_path / "broken.plecs"
    broken.write_text("Plecs {\n  Schematic {\n", encoding="utf-8")
    identity = identify(str(broken), {}, ENVIRONMENT)
    assert identity.mode == "bytes" and identity.topology is None
    assert identity.key.topology_id.startswith("bytes-")

    broken.write_text("Plecs {\n  Schematic {\n  Name x\n", encoding="utf-8")
    assert identify(str(broken), {}, ENVIRONMENT).key.topology_id != identity.key.topology_id

    missing = identify(str(tmp_path / "nope.plecs"), {}, ENVIRONMENT)
    assert missing.mode == "missing" and missing.key.topology_id.startswith("missing-")


def test_environment_detection_prefers_config_then_executable_metadata(tmp_path):
    class Config:
        version = " 4.8.1 "
        executable_paths = [sys.executable]

    assert PlecsEnvironment.detect(Config()) == PlecsEnvironment("4.8.1", "config")

    Config.version = ""
    detected = PlecsEnvironment.detect(Config())
    if sys.platform == "win32":
        assert detected.source == "executable" and re.fullmatch(r"\d+(\.\d+){3}", detected.plecs_version)
    else:
        assert not detected.known

    Config.executable_paths = [str(tmp_path / "PLECS 4.7 (64 bit)" / "plecs.exe")]
    Path(Config.executable_paths[0]).parent.mkdir()
    Path(Config.executable_paths[0]).write_bytes(b"not an executable")
    if sys.platform == "win32":
        assert PlecsEnvironment.detect(Config()) == PlecsEnvironment("4.7", "path")

    Config.executable_paths = []
    assert PlecsEnvironment.detect(Config()) == PlecsEnvironment(None, "unknown")
    assert PlecsEnvironment(None, "unknown").environment_id is None


def test_record_id_binds_all_four_ids():
    key = CacheKey("t", "p", "s", "e")
    assert key.record_id != CacheKey("t", "p", "s", "e2").record_id
    assert key.to_dict()["record_id"] == key.record_id


# -- cost ---------------------------------------------------------------------------


def test_canonicalization_cost_is_negligible_against_a_simulation():
    text = (DATA_DIR / "simple_nibb_prb.plecs").read_text(encoding="utf-8")
    started = time.perf_counter()
    for _ in range(5):
        canonicalize_document(parse_plecs_text(text))
    assert (time.perf_counter() - started) / 5 < 0.5
