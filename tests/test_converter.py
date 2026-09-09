import re
from pathlib import Path

import pytest
import tomllib

from pyplecs.api import _get_app
from pyplecs.api.converter import ConversionRequest, convert_plecs
from pyplecs.config import ConfigManager
from pyplecs.converter import (
    Circuit,
    Component,
    Net,
    Pin,
    parse_plecs,
    plecs_to_ltspice,
    plecs_to_spice,
)
from pyplecs.converter.cli import main as converter_main
from pyplecs.converter.emitters import emit_plecs
from pyplecs.converter.mapper import map_component, spice_expression
from pyplecs.converter.parser import PlecsParseError, parse_plecs_text

REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("filename", "component_count", "net_count", "component_types"),
    [
        (
            "simple_buck_prb.plecs",
            6,
            4,
            {"DCVoltageSource", "Resistor", "Inductor", "Capacitor", "Diode", "Mosfet"},
        ),
        (
            "simple_boost_prb.plecs",
            6,
            4,
            {"DCVoltageSource", "Resistor", "Inductor", "Capacitor", "Diode", "Mosfet"},
        ),
        (
            "simple_buckboost_prb.plecs",
            6,
            4,
            {"DCVoltageSource", "Resistor", "Inductor", "Capacitor", "Diode", "Mosfet"},
        ),
        (
            "simple_nibb_prb.plecs",
            8,
            5,
            {"DCVoltageSource", "Resistor", "Inductor", "Capacitor", "Diode", "Mosfet"},
        ),
    ],
)
def test_parser_characterizes_tracked_power_stage_models(filename, component_count, net_count, component_types):
    circuit = parse_plecs(DATA_DIR / filename)

    assert len(circuit.components) == component_count
    assert len(circuit.nets) == net_count
    assert {component.type for component in circuit.components} == component_types
    assert all(len(net.pins) >= 2 for net in circuit.nets)
    assert "PulseGenerator" not in {component.type for component in circuit.components}
    assert circuit.raw_params["Vi"] == "24"
    assert circuit.raw_params["D"]


def test_parser_traces_nested_wire_branches_into_one_net():
    circuit = parse_plecs(DATA_DIR / "simple_buck_prb.plecs")
    ground = next(net for net in circuit.nets if net.name == "0")

    assert set(ground.pins) == {
        Pin("VDCin", 2),
        Pin("R1", 2),
        Pin("C1", 2),
        Pin("D1", 1),
    }
    assert circuit.raw_params["Ro"] == "Vo_ref^2/Po"


def test_parser_rejects_malformed_blocks():
    with pytest.raises(PlecsParseError, match="Unterminated"):
        parse_plecs_text('Plecs {\n  Name "broken"\n')


@pytest.mark.parametrize(
    ("component_type", "prefix", "symbol", "value_parameter"),
    [
        ("DCVoltageSource", "V", "voltage", "V"),
        ("Resistor", "R", "res", "R"),
        ("Capacitor", "C", "cap", "C"),
        ("Inductor", "L", "ind", "L"),
        ("Mosfet", "S", "sw", None),
        ("Diode", "D", "diode", None),
    ],
)
def test_mapper_owns_day_one_component_mapping(component_type, prefix, symbol, value_parameter):
    mapping = map_component(Component("X1", component_type))

    assert mapping.prefix == prefix
    assert mapping.symbol == symbol
    assert mapping.value_parameter == value_parameter


def test_mapper_wraps_symbols_but_preserves_numeric_values():
    assert spice_expression("24") == "24"
    assert spice_expression("1e-6") == "1e-6"
    assert spice_expression("Vo_ref/Vi") == "{Vo_ref/Vi}"


def test_spice_emitter_matches_known_good_buck_reference():
    circuit = parse_plecs(DATA_DIR / "simple_buck_prb.plecs")

    generated = plecs_to_spice(circuit)
    expected = (FIXTURES / "simple_buck_prb.cir").read_text(encoding="utf-8")

    assert generated == expected


def test_simple_nibb_parses_and_emits_a_complete_spice_netlist():
    circuit = parse_plecs(DATA_DIR / "simple_nibb_prb.plecs")
    netlist = plecs_to_spice(circuit)

    assert len(circuit.components) == 8
    assert "WARNING" not in netlist
    assert netlist.endswith(".end\n")
    assert re.search(r"^\.tran\s+\S+", netlist, re.MULTILINE)
    assert len(re.findall(r"^\.model\s+", netlist, re.MULTILINE)) == 4
    for component in circuit.components:
        assert component.name in netlist
    for net in circuit.nets:
        assert re.search(rf"\b{re.escape(net.name)}\b", netlist)


def test_unknown_component_emits_a_warning_instead_of_failing():
    circuit = Circuit(
        "unknown",
        components=[Component("X1", "FuturePowerDevice")],
    )

    netlist = plecs_to_spice(circuit)

    assert "WARNING: unsupported PLECS component X1 (FuturePowerDevice)" in netlist
    assert netlist.endswith(".end\n")


def test_ltspice_emitter_preserves_snapped_positions_and_structure():
    circuit = parse_plecs(DATA_DIR / "simple_buck_prb.plecs")

    schematic = plecs_to_ltspice(circuit)

    assert schematic.startswith("Version 4\nSHEET 1 880 680\n")
    assert "WIRE " in schematic
    assert "SYMBOL res " in schematic
    assert "SYMATTR InstName R1" in schematic
    assert "TEXT -32 " in schematic
    symbol_positions = re.findall(r"^SYMBOL\s+\S+\s+(\d+)\s+(\d+)\s+", schematic, re.MULTILINE)
    assert symbol_positions
    assert all(int(value) % 16 == 0 for pair in symbol_positions for value in pair)


def test_parse_emit_preserves_every_supported_component_and_net():
    circuit = parse_plecs(DATA_DIR / "simple_boost_prb.plecs")

    netlist = plecs_to_spice(circuit)

    assert all(component.name in netlist for component in circuit.components)
    assert all(net.name in netlist for net in circuit.nets)


@pytest.mark.parametrize(
    ("format_name", "extensions"),
    [("cir", {".cir"}), ("asc", {".asc"}), ("all", {".cir", ".asc"})],
)
def test_cli_writes_requested_formats(tmp_path, format_name, extensions):
    output_dir = tmp_path / "output"

    exit_code = converter_main(
        [
            str(DATA_DIR / "simple_buck_prb.plecs"),
            "--format",
            format_name,
            "-o",
            str(output_dir),
        ]
    )

    assert exit_code == 0
    assert {path.suffix for path in output_dir.iterdir()} == extensions


def test_packaged_cli_and_rest_routes_are_registered():
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    app = _get_app(ConfigManager(search_paths=[]))

    assert project["project"]["scripts"]["pyplecs-convert"] == "pyplecs.converter.cli:main"
    assert "/api/v1/convert" in app.openapi()["paths"]


@pytest.mark.asyncio
@pytest.mark.parametrize("format_name", ["cir", "asc"])
async def test_rest_converter_returns_filename_and_content(format_name):
    response = await convert_plecs(
        ConversionRequest(
            plecs_file=str(DATA_DIR / "simple_buck_prb.plecs"),
            format=format_name,
        )
    )

    assert response.filename == f"simple_buck_prb.{format_name}"
    assert response.content


def test_circuit_model_rejects_pins_for_unknown_components():
    with pytest.raises(ValueError, match="unknown component"):
        Circuit("invalid", nets=[Net("N001", [Pin("missing", 1)])])


def test_circuit_model_requires_one_based_pin_numbers():
    with pytest.raises(ValueError, match="one-based"):
        Pin("R1", 0)


def test_parse_plecs_text_keeps_brace_list_values_across_continuation_lines():
    text = (
        "Plecs {\n"
        "  Schematic {\n"
        "    Component {\n"
        "      Type          Scope\n"
        '      Name          "Scope"\n'
        "      Axis {\n"
        '        Signals       {"Load Current", "Inductor Current", "Average Inductor C"\n'
        '"urrent"}\n'
        "        SignalTypes   [ ]\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n"
    )

    document = parse_plecs_text(text)

    axis = document["Plecs"]["Schematic"]["Component"]["Axis"]
    assert axis["Signals"] == '{"Load Current", "Inductor Current", "Average Inductor Current"}'
    assert axis["SignalTypes"] == ()


def test_routed_connection_regression_lock_for_plecs_native_circuits():
    """parse_plecs never populates segments/pin_points (#94); emit_plecs must stay byte-identical for such circuits."""
    circuit = parse_plecs(DATA_DIR / "simple_buck_prb.plecs")
    assert all(not net.segments and not net.pin_points for net in circuit.nets)

    text = emit_plecs(circuit)

    assert "Points" not in text
    ground = next(net for net in circuit.nets if net.name == "0")
    assert len(ground.pins) == 4
    block = next(
        m.group(0)
        for m in re.finditer(r'    Connection \{\n(?:.*\n)*?    \}\n', text)
        if 'SrcComponent  "C1"' in m.group(0) and 'SrcTerminal   2' in m.group(0)
    )
    expected = (
        '    Connection {\n'
        '      Type          Wire\n'
        '      SrcComponent  "C1"\n'
        '      SrcTerminal   2\n'
        '      Branch {\n'
        '        DstComponent  "D1"\n'
        '        DstTerminal   1\n'
        '      }\n'
        '      Branch {\n'
        '        DstComponent  "R1"\n'
        '        DstTerminal   2\n'
        '      }\n'
        '      Branch {\n'
        '        DstComponent  "VDCin"\n'
        '        DstTerminal   2\n'
        '      }\n'
        '    }\n'
    )
    assert block == expected


def test_plecs_power_operator_becomes_spice_power_in_every_emitted_expression():
    """PLECS ``^`` is power; in SPICE/LTspice ``^`` is XOR, so ``Ro=Vo_ref^2/Po`` silently loaded the buck with the wrong resistor (#20)."""
    circuit = parse_plecs(DATA_DIR / "simple_buck_prb.plecs")
    spice = plecs_to_spice(circuit)
    ltspice = plecs_to_ltspice(circuit)
    assert ".param Ro=Vo_ref**2/Po" in spice and "^" not in spice
    assert "!.param Ro=Vo_ref**2/Po" in ltspice and "^" not in ltspice
