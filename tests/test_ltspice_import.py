"""LTspice ``.asc`` import into the Circuit Model, and out again as a runnable ``.plecs`` (#43 track 1)."""

import re
from pathlib import Path

import pytest

from pyplecs.converter import ltspice_to_plecs, parse_ltspice, parse_plecs
from pyplecs.converter.cli import main as converter_main
from pyplecs.converter.ltspice_parser import (
    LtspiceParseError,
    parse_ltspice_text,
    to_plecs_expression,
    transform_offset,
)

FIXTURES = Path(__file__).parent / "fixtures"
RC_STEP = FIXTURES / "rc_step.asc"


def _connection_block(text: str, src_component: str) -> str:
    match = re.search(
        rf'    Connection \{{\n(?:.*\n)*?      SrcComponent  "{re.escape(src_component)}"\n(?:.*\n)*?    \}}\n',
        text,
    )
    assert match, f"no Connection block found with SrcComponent {src_component!r}"
    return match.group(0)


def test_rc_step_component_geometry_matches_the_authored_drawing():
    """Position/Direction are derived from the two absolute pin points (#94); verified by hand against the fixture."""
    circuit = parse_ltspice(RC_STEP)
    by_name = {c.name: c for c in circuit.components}
    assert by_name["V1"].position == (60, 85) and by_name["V1"].direction == "up"
    assert by_name["R1"].position == (175, 60) and by_name["R1"].direction == "right"
    assert by_name["C1"].position == (210, 80) and by_name["C1"].direction == "up"
    assert all(not c.flipped for c in circuit.components)


def test_rc_step_routing_follows_the_authored_wires():
    """Connection Points/Branch geometry follows the drawn wires (#94), pruning dangling body/ground stubs."""
    text = ltspice_to_plecs(RC_STEP)

    n001 = _connection_block(text, "R1")
    assert 'SrcTerminal   2' in n001
    assert "Points        [150, 60; 60, 60]" in n001
    assert 'DstComponent  "V1"' in n001 and "DstTerminal   1" in n001
    assert "80" not in re.search(r"Points\s+\[[^\]]*\]", n001).group(0)

    n002 = _connection_block(text, "C1")
    # C1 sources both non-ground nets; pick the one destined for R1 terminal 1
    n002_block = next(
        block
        for block in re.findall(r'    Connection \{\n(?:.*\n)*?    \}\n', text)
        if 'SrcComponent  "C1"' in block and 'DstComponent  "R1"' in block
    )
    assert 'SrcTerminal   1' in n002_block
    assert "Points        [210, 60; 200, 60]" in n002_block
    assert "DstTerminal   1" in n002_block

    ground_block = next(
        block
        for block in re.findall(r'    Connection \{\n(?:.*\n)*?    \}\n', text)
        if 'SrcComponent  "C1"' in block and 'DstComponent  "V1"' in block
    )
    assert 'SrcTerminal   2' in ground_block
    assert "Points        [210, 100; 210, 130; 60, 130; 60, 110]" in ground_block
    assert "DstTerminal   2" in ground_block
    assert "140" not in text  # the FLAG 96 224 0 stub (scaled y=140) is pruned


@pytest.mark.parametrize(
    "orient, expected_direction",
    [
        ("R0", "up"),
        ("R90", "right"),
        ("R180", "down"),
        ("R270", "left"),
        ("M0", "up"),
        ("M90", "left"),
        ("M180", "down"),
        ("M270", "right"),
    ],
)
def test_symbol_direction_reflects_which_side_terminal_one_faces(orient, expected_direction):
    """Direction names the side terminal 1 faces (#94); Flipped is never emitted for a two-terminal part."""
    text = (
        f"Version 4\nSHEET 1 400 400\nSYMBOL res 100 100 {orient}\nSYMATTR InstName R1\nSYMATTR Value 1\n"
        "TEXT 0 0 Left 2 !.tran 1m\n"
    )
    circuit = parse_ltspice_text(text)
    component = circuit.components[0]
    assert component.direction == expected_direction
    assert component.flipped is False


def test_pass_through_pins_emit_branches_at_the_interior_points():
    """Four pins share one wire; the two interior ones must appear as Dst branches, not swallowed (#94)."""
    text = (
        "Version 4\nSHEET 1 400 400\n"
        "WIRE 0 100 300 100\n"
        "SYMBOL res 100 84 R90\nSYMATTR InstName R1\nSYMATTR Value 1\n"
        "SYMBOL res 300 84 R90\nSYMATTR InstName R2\nSYMATTR Value 1\n"
        "FLAG 150 100 mid\n"
        "TEXT 0 0 Left 2 !.tran 1m\n"
    )
    circuit = parse_ltspice_text(text)
    text_out = ltspice_to_plecs(circuit)
    block = _connection_block(text_out, min(p.component for p in circuit.nets[0].pins))
    # every pin ends up either as the Src, a leaf Dst, or a Branch Dst
    for pin in circuit.nets[0].pins:
        assert f'"{pin.component}"' in block
    assert block.count("Branch {") >= 2


def test_rc_step_schematic_becomes_the_circuit_model_ltspice_netlists():
    circuit = parse_ltspice(RC_STEP)
    assert circuit.name == "rc_step"
    assert {(c.name, c.type) for c in circuit.components} == {("V1", "DCVoltageSource"), ("R1", "Resistor"), ("C1", "Capacitor")}
    by_name = {c.name: c for c in circuit.components}
    assert by_name["V1"].parameters == {"V": "V_step"}
    assert by_name["R1"].parameters == {"R": "R"}
    assert by_name["C1"].parameters == {"C": "C", "v_init": "0"}
    # LTspice 26 netlisted this fixture as: V1 N001 0 / R1 N002 N001 / C1 N002 0
    nets = {net.name: {(pin.component, pin.terminal) for pin in net.pins} for net in circuit.nets}
    assert nets == {
        "N001": {("V1", 1), ("R1", 2)},
        "0": {("V1", 2), ("C1", 2)},
        "N002": {("R1", 1), ("C1", 1)},
    }
    assert circuit.raw_params == {"V_step": "1", "R": "1e3", "C": "1e-6", "T_sim": "5e-3", "max_step": "1e-6"}


@pytest.mark.parametrize(
    "orient, expected",
    [("R0", (16, 96)), ("R90", (-96, 16)), ("R180", (-16, -96)), ("R270", (96, -16)), ("M0", (-16, 96)), ("M90", (96, 16)), ("M180", (16, -96)), ("M270", (-96, -16))],
)
def test_symbol_orientation_matches_the_ltspice_netlister(orient, expected):
    """Verified against LTspice 26 with a resistor in every orientation and a net label on each predicted pin."""
    assert transform_offset(orient, 16, 96) == expected


def test_values_translate_to_plecs_expressions():
    assert to_plecs_expression("{R}") == "R"
    assert to_plecs_expression("1k") == "1e3" and to_plecs_expression("4.7u") == "4.7e-6" and to_plecs_expression("2Meg") == "2e6"
    assert to_plecs_expression("{Vo_ref**2/Po}") == "Vo_ref^2/Po"
    assert to_plecs_expression("{2*R+1m}") == "2*R+1e-3"
    assert to_plecs_expression("1e-3") == "1e-3"


def test_unknown_symbols_and_missing_tran_are_hard_failures():
    base = "Version 4\nSHEET 1 100 100\nSYMBOL {sym} 0 0 R0\nSYMATTR InstName X1\nSYMATTR Value 1\nFLAG 0 16 a\nFLAG 0 96 0\n{tran}"
    with pytest.raises(LtspiceParseError, match="unsupported LTspice symbol 'npn'"):
        parse_ltspice_text(base.format(sym="npn", tran="TEXT 0 0 Left 2 !.tran 1m\n"))
    with pytest.raises(LtspiceParseError, match="no .tran"):
        parse_ltspice_text(base.format(sym="voltage", tran=""))


def test_pins_join_wires_at_endpoints_interiors_and_labels():
    text = (
        "Version 4\nSHEET 1 400 400\n"
        "WIRE 0 100 300 100\n"  # one long wire; pins touch its interior
        "SYMBOL res 100 84 R90\nSYMATTR InstName R1\nSYMATTR Value 1\n"  # R90 pins: (100-16, 84+16)=(84,100) and (100-96,100)=(4,100)
        "SYMBOL res 300 84 R90\nSYMATTR InstName R2\nSYMATTR Value 1\n"  # pins (284,100) and (204,100)
        "FLAG 150 100 mid\n"
        "TEXT 0 0 Left 2 !.tran 1m\n"
    )
    circuit = parse_ltspice_text(text)
    assert [net.name for net in circuit.nets] == ["mid"]
    assert len(circuit.nets[0].pins) == 4
    assert circuit.raw_params == {"T_sim": "1e-3", "max_step": "T_sim/1000"}


def test_round_trip_to_plecs_preserves_components_nets_and_parameters(tmp_path):
    out = tmp_path / "rc_step.plecs"
    ltspice_to_plecs(RC_STEP, out, probes=(("C1", "Capacitor voltage"),))
    reparsed = parse_plecs(out)
    original = parse_ltspice(RC_STEP)
    assert {(c.name, c.type) for c in reparsed.components} == {(c.name, c.type) for c in original.components}
    original_nets = {frozenset((p.component, p.terminal) for p in net.pins) for net in original.nets}
    reparsed_nets = {frozenset((p.component, p.terminal) for p in net.pins) for net in reparsed.nets}
    assert reparsed_nets == original_nets
    for name, value in original.raw_params.items():
        assert reparsed.raw_params[name] == value
    text = out.read_text(encoding="utf-8")
    assert 'Signals       {"Capacitor voltage"}' in text and "Type          Output" in text


def test_cli_converts_an_asc_to_plecs(tmp_path):
    assert converter_main([str(RC_STEP), "--format", "plecs", "-o", str(tmp_path)]) == 0
    assert (tmp_path / "rc_step.plecs").is_file()
    assert parse_plecs(tmp_path / "rc_step.plecs").name == "rc_step"
