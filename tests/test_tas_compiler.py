import copy
import json
from pathlib import Path

import pytest

from pyplecs.converter.circuit import Pin
from pyplecs.tas import DiagnosticSeverity, TasCapture, TasCompilationError, TasCompiler

FIXTURE = Path(__file__).parent / "fixtures" / "tas_buck_inline.json"


def _document():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _component(compilation, name):
    return next(component for component in compilation.circuit.components if component.name == name)


def _net_for(compilation, component, terminal):
    pin = Pin(component, terminal)
    return next(net.name for net in compilation.circuit.nets if pin in net.pins)


def test_compile_inline_tas_buck_characterizes_the_supported_projection(tmp_path):
    source = _document()

    compilation = TasCompiler(tmp_path).compile(source)

    assert compilation.source == source
    assert compilation.source is not source
    assert compilation.artifact_path.exists()
    assert compilation.artifact_path.parent == tmp_path
    assert compilation.artifact_path.suffix == ".plecs"

    expected_types = {
        "power_stage.Q1": "Mosfet",
        "power_stage.D1": "Diode",
        "power_stage.L1": "Inductor",
        "power_stage.C_in": "Capacitor",
        "power_stage.C_out": "Capacitor",
        "power_stage.R_bleed": "Resistor",
        "__tas_input": "DCVoltageSource",
        "__tas_source_resistance": "Resistor",
        "__tas_load": "Resistor",
        "__tas_pwm": "PulseGenerator",
        "__tas_vin_meter": "Voltmeter",
        "__tas_vout_meter": "Voltmeter",
    }
    assert {
        component.name: component.type
        for component in compilation.circuit.components
        if component.name in expected_types
    } == expected_types

    assert _component(compilation, "power_stage.Q1").parameters["Ron"] == "0.002"
    assert _component(compilation, "power_stage.D1").parameters == {
        "Ron": "0.01",
        "Vf": "0.45",
    }
    assert _component(compilation, "power_stage.L1").parameters["L"] == "2.2e-05"
    assert _component(compilation, "power_stage.C_out").parameters["C"] == "0.0001"
    assert _component(compilation, "power_stage.R_bleed").parameters["R"] == "1000"

    # Explicit CIAS pin names map to PLECS terminal order and polarity.
    assert _net_for(compilation, "power_stage.Q1", 1) == "Vin"
    assert _net_for(compilation, "power_stage.Q1", 2) == "power_stage.sw_node"
    assert _net_for(compilation, "power_stage.Q1", 3) == "power_stage.gate"
    assert _net_for(compilation, "power_stage.D1", 1) == "GND"
    assert _net_for(compilation, "power_stage.D1", 2) == "power_stage.sw_node"

    assert [point.name for point in compilation.operating_points] == [
        "nominal",
        "high_line",
    ]
    assert compilation.operating_points[0].parameters == {
        "D": 0.42,
        "R_load": 2.5,
        "T_sim": 0.0005,
        "Vin": 12.0,
        "fs": 500000.0,
        "max_step": 2e-08,
    }
    assert compilation.operating_points[1].parameters["R_load"] == 5.0
    assert compilation.operating_points[1].parameters["fs"] == 500000.0

    warning = next(d for d in compilation.diagnostics if d.code == "TAS_VIRTUAL_CONTROL_IGNORED")
    assert warning.severity == DiagnosticSeverity.WARNING
    assert warning.location == "$.topology.stages[1]"
    assert warning.message

    content = compilation.artifact_path.read_text(encoding="ascii")
    for component_type in expected_types.values():
        assert f"Type          {component_type}" in content
    assert 'TimeSpan      "T_sim"' in content
    assert 'MaxStep       "max_step"' in content
    assert 'Variable      "DutyCycle"' in content
    assert 'Value         "D"' in content
    assert 'Component     "__tas_vout_meter"' in content
    assert 'Signals       {"Measured voltage"}' in content
    assert 'Component     "__tas_load"' in content
    assert 'Signals       {"Resistor current"}' in content


def test_equivalent_projection_has_identical_content_and_content_address(tmp_path):
    source = _document()
    reordered = copy.deepcopy(source)
    circuit = reordered["topology"]["stages"][0]["circuit"]
    circuit["components"].reverse()
    circuit["connections"].reverse()
    # This inline value is shadowed by the stage-qualified override.
    circuit["components"][-1]["data"]["mosfet"]["manufacturerInfo"]["datasheetInfo"]["electrical"][
        "onResistance"
    ] = 0.5

    compiler = TasCompiler(tmp_path)
    first = compiler.compile(source)
    second = compiler.compile(reordered)

    assert first.artifact_path == second.artifact_path
    assert first.artifact_path.read_bytes() == second.artifact_path.read_bytes()


def test_operating_point_values_do_not_change_the_shared_model_artifact(tmp_path):
    source = _document()
    changed = copy.deepcopy(source)
    changed["inputs"]["operatingPoints"][0]["inputVoltage"] = 11.0

    compiler = TasCompiler(tmp_path)
    first = compiler.compile(source)
    second = compiler.compile(changed)

    assert first.artifact_path == second.artifact_path
    assert first.artifact_path.read_bytes() == second.artifact_path.read_bytes()
    assert first.operating_points[0].parameters["Vin"] == 12.0
    assert second.operating_points[0].parameters["Vin"] == 11.0


def test_uri_values_require_an_explicit_caller_resolver(tmp_path):
    source = _document()
    inline_q1 = source["topology"]["stages"][0]["circuit"]["components"][0]["data"]
    source["topology"]["stages"][0]["circuit"]["components"][0]["data"] = (
        "parts.ndjson?partNumber=Q1"
    )

    with pytest.raises(TasCompilationError) as missing:
        TasCompiler(tmp_path).compile(source)
    assert missing.value.diagnostics[0].code == "TAS_RESOLVER_REQUIRED"

    calls = []

    def resolver(uri):
        calls.append(uri)
        return inline_q1

    compilation = TasCompiler(tmp_path, resolver=resolver).compile(source)
    assert compilation.artifact_path.exists()
    assert calls == ["parts.ndjson?partNumber=Q1"]

    def failing_resolver(uri):
        raise LookupError("not found")

    with pytest.raises(TasCompilationError) as failed:
        TasCompiler(tmp_path, resolver=failing_resolver).compile(source)
    assert failed.value.diagnostics[0].code == "TAS_RESOLUTION_FAILED"
    assert "not found" in failed.value.diagnostics[0].message


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda doc: doc["topology"]["stages"].append(
                copy.deepcopy(doc["topology"]["stages"][0])
            ),
            "TAS_DUPLICATE_STAGE",
        ),
        (
            lambda doc: doc["topology"]["stages"][0]["circuit"]["components"].append(
                copy.deepcopy(doc["topology"]["stages"][0]["circuit"]["components"][0])
            ),
            "TAS_DUPLICATE_COMPONENT",
        ),
        (
            lambda doc: doc["topology"]["stages"][0]["circuit"]["connections"][1][
                "endpoints"
            ].append({"component": "Q1", "pin": "D"}),
            "TAS_CONTRADICTORY_PIN",
        ),
        (
            lambda doc: doc["topology"]["stages"][0]["circuit"]["connections"][0][
                "endpoints"
            ][0].update(pin="unknown"),
            "TAS_UNKNOWN_PIN",
        ),
        (
            lambda doc: doc["topology"]["stages"][0].update(role="outputFilter"),
            "TAS_UNSUPPORTED_STAGE_ROLE",
        ),
        (
            lambda doc: doc["inputs"]["operatingPoints"][0]["outputs"][0].update(
                loadType="constantPower"
            ),
            "TAS_UNSUPPORTED_LOAD",
        ),
        (
            lambda doc: doc["simulation"]["analyses"][0].update(type="ac"),
            "TAS_UNSUPPORTED_ANALYSIS",
        ),
        (
            lambda doc: doc["simulation"].update(stimulus=[]),
            "TAS_MISSING_PWM_STIMULUS",
        ),
        (
            lambda doc: doc["simulation"]["overrides"][0].update(component="missing"),
            "TAS_MALFORMED_OVERRIDE_REFERENCE",
        ),
        (
            lambda doc: doc["simulation"]["overrides"][0].update(model="vendor-model"),
            "TAS_UNSUPPORTED_MODEL_BINDING",
        ),
    ],
)
def test_invalid_or_unsupported_required_content_prevents_artifact(tmp_path, mutate, code):
    source = _document()
    mutate(source)

    with pytest.raises(TasCompilationError) as caught:
        TasCompiler(tmp_path).compile(source)

    assert any(diagnostic.code == code for diagnostic in caught.value.diagnostics)
    assert all(diagnostic.location.startswith("$") for diagnostic in caught.value.diagnostics)
    assert all(diagnostic.message for diagnostic in caught.value.diagnostics)
    assert list(tmp_path.glob("*.plecs")) == []


def test_optional_net_and_component_captures_are_validated_and_emitted(tmp_path):
    captures = [
        TasCapture("switch_voltage", "net", "power_stage.sw_node", "voltage"),
        TasCapture("inductor_current", "component", "power_stage.L1", "current"),
    ]

    compilation = TasCompiler(tmp_path).compile(_document(), captures=captures)
    content = compilation.artifact_path.read_text(encoding="ascii")

    assert {capture.name for capture in compilation.captures} >= {
        "Vin.voltage",
        "Vin.current",
        "Vout.voltage",
        "Vout.current",
        "switch_voltage",
        "inductor_current",
    }
    assert "__tas_meter_switch_voltage" in content
    assert 'Component     "power_stage.L1"' in content
    assert 'Signals       {"Inductor current"}' in content

    with pytest.raises(TasCompilationError) as caught:
        TasCompiler(tmp_path).compile(
            _document(), captures=[TasCapture("bad", "net", "missing", "voltage")]
        )
    assert caught.value.diagnostics[0].code == "TAS_UNKNOWN_CAPTURE_TARGET"


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (
            lambda doc: doc["topology"]["stages"][0]["circuit"]["connections"][0][
                "endpoints"
            ].append({"component": "Q1", "pin": "D"}),
            "TAS_MULTIPLY_CONNECTED_PIN",
        ),
        (
            lambda doc: doc["topology"]["stages"][0]["circuit"]["connections"][0][
                "endpoints"
            ].pop(1),
            "TAS_UNCONNECTED_PIN",
        ),
    ],
)
def test_every_component_terminal_is_connected_exactly_once(tmp_path, mutate, code):
    source = _document()
    mutate(source)

    with pytest.raises(TasCompilationError) as caught:
        TasCompiler(tmp_path).compile(source)

    assert any(diagnostic.code == code for diagnostic in caught.value.diagnostics)
    assert list(tmp_path.glob("*.plecs")) == []


def test_conflicting_inline_fixed_values_require_an_override(tmp_path):
    source = _document()
    resistor = source["topology"]["stages"][0]["circuit"]["components"][5]["data"]
    resistor["resistor"]["manufacturerInfo"]["datasheetInfo"]["modelParams"] = {
        "r": 999.0
    }

    with pytest.raises(TasCompilationError) as caught:
        TasCompiler(tmp_path).compile(source)

    assert any(
        diagnostic.code == "TAS_AMBIGUOUS_COMPONENT_VALUE"
        for diagnostic in caught.value.diagnostics
    )


def test_future_domain_and_unknown_root_content_are_preserved_with_diagnostics(tmp_path):
    source = _document()
    source["thermalNetwork"] = {"nodes": [{"name": "case"}]}

    compilation = TasCompiler(tmp_path).compile(source)

    diagnostics = {(item.code, item.location) for item in compilation.diagnostics}
    assert ("TAS_FUTURE_DOMAIN_PRESERVED", "$.topology.stages[0].circuit.components[2].data.magnetic") in diagnostics
    assert ("TAS_UNKNOWN_ROOT_CONTENT_PRESERVED", "$.thermalNetwork") in diagnostics
    assert compilation.source["thermalNetwork"] == source["thermalNetwork"]


def test_unconsumed_stimulus_prevents_execution(tmp_path):
    source = _document()
    source["simulation"]["stimulus"].append(
        {
            "stage": "power_stage",
            "component": "Q1",
            "signal": "drain",
            "waveform": {"type": "constant", "value": 1},
        }
    )

    with pytest.raises(TasCompilationError) as caught:
        TasCompiler(tmp_path).compile(source)

    diagnostic = next(
        item for item in caught.value.diagnostics if item.code == "TAS_UNSUPPORTED_STIMULUS"
    )
    assert diagnostic.location == "$.simulation.stimulus[1]"
    assert list(tmp_path.glob("*.plecs")) == []


def test_component_diagnostic_location_uses_source_array_index(tmp_path):
    source = _document()
    components = source["topology"]["stages"][0]["circuit"]["components"]
    components.reverse()
    source_index = next(
        index for index, component in enumerate(components) if component["name"] == "Q1"
    )
    components[source_index]["data"] = {}

    with pytest.raises(TasCompilationError) as caught:
        TasCompiler(tmp_path).compile(source)

    diagnostic = next(
        item for item in caught.value.diagnostics if item.code == "TAS_UNSUPPORTED_COMPONENT"
    )
    assert diagnostic.location == (
        f"$.topology.stages[0].circuit.components[{source_index}].data"
    )


def test_connection_diagnostic_location_uses_source_array_index(tmp_path):
    source = _document()
    connections = source["topology"]["stages"][0]["circuit"]["connections"]
    connections.reverse()
    sorted_source_indexes = sorted(
        range(len(connections)), key=lambda index: connections[index]["name"]
    )
    source_index = next(
        index
        for sorted_index, index in enumerate(sorted_source_indexes)
        if index != sorted_index
    )
    endpoint_index = next(
        index
        for index, endpoint in enumerate(connections[source_index]["endpoints"])
        if "component" in endpoint
    )
    connections[source_index]["endpoints"][endpoint_index]["pin"] = "unknown"

    with pytest.raises(TasCompilationError) as caught:
        TasCompiler(tmp_path).compile(source)

    diagnostic = next(
        item for item in caught.value.diagnostics if item.code == "TAS_UNKNOWN_PIN"
    )
    assert diagnostic.location == (
        f"$.topology.stages[0].circuit.connections[{source_index}]"
        f".endpoints[{endpoint_index}].pin"
    )
