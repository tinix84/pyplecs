"""Portable TAS v2 electrical-subset compiler."""

from __future__ import annotations

import copy
import hashlib
import re
import tempfile
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from pyplecs.converter.circuit import Circuit, Component, Net, Pin
from pyplecs.converter.emitters.plecs import PlecsProbeSignal, emit_plecs
from pyplecs.studies import ParameterVector

from .models import (
    DiagnosticSeverity,
    TasCapture,
    TasCompilation,
    TasCompilationError,
    TasDiagnostic,
)

TasResolver = Callable[[str], Mapping[str, Any]]

_PIN_ALIASES = {
    "Resistor": {"1": 1, "2": 2, "p": 1, "n": 2},
    "Capacitor": {"1": 1, "2": 2, "p": 1, "n": 2},
    "Inductor": {
        "1": 1,
        "2": 2,
        "p": 1,
        "n": 2,
        "primary_start": 1,
        "primary_end": 2,
    },
    "Mosfet": {"d": 1, "drain": 1, "s": 2, "source": 2, "g": 3, "gate": 3},
    "Diode": {"a": 1, "anode": 1, "k": 2, "cathode": 2},
}

_PROBE_SIGNALS = {
    "DCVoltageSource": {"voltage": "Source voltage", "current": "Source current"},
    "Resistor": {"voltage": "Resistor voltage", "current": "Resistor current"},
    "Capacitor": {"voltage": "Capacitor voltage", "current": "Capacitor current"},
    "Inductor": {"voltage": "Inductor voltage", "current": "Inductor current"},
    "Mosfet": {"voltage": "MOSFET voltage", "current": "MOSFET current", "gate": "MOSFET gate input"},
    "Diode": {"voltage": "Diode voltage", "current": "Diode current"},
    "Voltmeter": {"voltage": "Measured voltage"},
}

_MODEL_VARIABLE_DEFAULTS = {
    "D": "0.5",
    "R_load": "1",
    "T_sim": "1e-3",
    "Vin": "1",
    "fs": "1e3",
    "max_step": "1e-6",
}


class TasCompiler:
    """Compile the deliberately narrow, standalone TAS electrical projection."""

    def __init__(
        self,
        artifact_directory: str | Path | None = None,
        *,
        resolver: TasResolver | None = None,
    ):
        self.artifact_directory = Path(
            artifact_directory
            if artifact_directory is not None
            else Path(tempfile.gettempdir()) / "pyplecs-tas-models"
        )
        self.resolver = resolver
        self._diagnostics: list[TasDiagnostic] = []

    def compile(
        self,
        document: Mapping[str, Any],
        *,
        captures: Sequence[TasCapture] = (),
    ) -> TasCompilation:
        """Compile one self-contained or explicitly resolved TAS document."""
        self._diagnostics = []
        if not isinstance(document, Mapping):
            self._error("TAS_MALFORMED_DOCUMENT", "$", "TAS document must be an object")
            self._raise_errors()
        source = copy.deepcopy(dict(document))
        circuit, operating_points, resolved_captures = self._project(source, captures)
        probes = tuple(
            PlecsProbeSignal(capture.plecs_component or "", capture.plecs_signal or "")
            for capture in resolved_captures
        )
        content = emit_plecs(circuit, probes=probes)
        digest = hashlib.sha256(content.encode("ascii")).hexdigest()
        artifact_path = self.artifact_directory / f"tas-{digest[:20]}.plecs"
        self.artifact_directory.mkdir(parents=True, exist_ok=True)
        encoded = content.encode("ascii")
        if not artifact_path.exists():
            artifact_path.write_bytes(encoded)
        elif artifact_path.read_bytes() != encoded:
            raise RuntimeError(f"Content-address collision at {artifact_path}")
        return TasCompilation(
            source=source,
            circuit=circuit,
            operating_points=operating_points,
            captures=resolved_captures,
            diagnostics=tuple(self._diagnostics),
            artifact_path=artifact_path,
        )

    def _project(
        self,
        document: dict[str, Any],
        requested_captures: Sequence[TasCapture],
    ) -> tuple[Circuit, tuple[ParameterVector, ...], tuple[TasCapture, ...]]:
        inputs = self._mapping(document.get("inputs"), "$.inputs")
        topology = self._mapping(document.get("topology"), "$.topology")
        stages = self._object_list(topology.get("stages"), "$.topology.stages")
        self._check_unique(stages, "name", "TAS_DUPLICATE_STAGE", "$.topology.stages")
        self._raise_errors()

        switching_stages: list[tuple[int, dict[str, Any]]] = []
        for index, stage in enumerate(stages):
            location = f"$.topology.stages[{index}]"
            role = stage.get("role")
            if role == "switchingCell":
                switching_stages.append((index, stage))
            elif role == "control" and stage.get("controlImplementation") == "virtual":
                self._warning(
                    "TAS_VIRTUAL_CONTROL_IGNORED",
                    location,
                    "Virtual control is preserved but open-loop PWM stimulus drives this Milestone 1 run",
                )
            else:
                self._error(
                    "TAS_UNSUPPORTED_STAGE_ROLE",
                    f"{location}.role",
                    f"Milestone 1 supports one switchingCell and optional virtual control, not {role!r}",
                )
        if len(switching_stages) != 1:
            self._error(
                "TAS_SWITCHING_STAGE_COUNT",
                "$.topology.stages",
                "Milestone 1 requires exactly one switchingCell stage",
            )
        self._raise_errors()

        stage_index, stage = switching_stages[0]
        stage_name = self._nonempty(stage.get("name"), f"$.topology.stages[{stage_index}].name")
        if stage.get("phaseCount", 1) != 1:
            self._error(
                "TAS_UNSUPPORTED_PHASE_COUNT",
                f"$.topology.stages[{stage_index}].phaseCount",
                "Milestone 1 supports a single physical phase",
            )
        circuit_data = self._resolve_mapping(
            stage.get("circuit"), f"$.topology.stages[{stage_index}].circuit"
        )
        self._raise_errors()

        ports = self._object_list(
            circuit_data.get("ports"), f"$.topology.stages[{stage_index}].circuit.ports"
        )
        components_data = self._object_list(
            circuit_data.get("components"),
            f"$.topology.stages[{stage_index}].circuit.components",
        )
        connections_data = self._object_list(
            circuit_data.get("connections"),
            f"$.topology.stages[{stage_index}].circuit.connections",
        )
        self._check_unique(ports, "name", "TAS_DUPLICATE_PORT", "$.topology.stages[0].circuit.ports")
        self._check_unique(
            components_data,
            "name",
            "TAS_DUPLICATE_COMPONENT",
            "$.topology.stages[0].circuit.components",
        )
        self._check_unique(
            connections_data,
            "name",
            "TAS_DUPLICATE_CONNECTION",
            "$.topology.stages[0].circuit.connections",
        )
        self._raise_errors()

        overrides = self._overrides(document.get("simulation", {}))
        known_override_targets = {
            (stage_name, str(component.get("name", "")))
            for component in components_data
        }
        unknown_override_targets = sorted(set(overrides) - known_override_targets)
        if unknown_override_targets:
            unknown_stage, unknown_component = unknown_override_targets[0]
            self._error(
                "TAS_MALFORMED_OVERRIDE_REFERENCE",
                "$.simulation.overrides",
                f"Override references unknown component {unknown_stage}.{unknown_component}",
            )
        components, component_types = self._components(
            stage_name, components_data, overrides
        )
        port_names = {self._nonempty(port.get("name"), "$.topology.stages[0].circuit.ports") for port in ports}
        external_names = self._external_net_names(topology, {stage_name: port_names})
        nets, port_nets = self._nets(
            stage_name,
            connections_data,
            port_names,
            component_types,
            external_names,
        )
        self._raise_errors()

        simulation = self._mapping(document.get("simulation"), "$.simulation")
        analysis = self._analysis(simulation)
        stimulus = self._stimulus(simulation, stage_name, component_types)
        operating_points = self._operating_points(inputs, analysis, stimulus)
        self._diagnose_preserved_content(document, simulation)
        self._raise_errors()

        input_port = self._binding_port(stage, "inputPort", stage_index)
        output_port = self._binding_port(stage, "outputPort", stage_index)
        ground_port = next((name for name in port_names if name.lower() in {"gnd", "ground", "return"}), None)
        if ground_port is None:
            self._error(
                "TAS_MISSING_GROUND_PORT",
                f"$.topology.stages[{stage_index}].circuit.ports",
                "The supported buck projection requires a ground/return port",
            )
        required_port_names = [input_port, output_port, ground_port]
        for port in required_port_names:
            if port is not None and port not in port_nets:
                self._error(
                    "TAS_UNCONNECTED_PORT",
                    f"$.topology.stages[{stage_index}].circuit.ports",
                    f"Required port {port!r} is not exposed by a CIAS connection",
                )
        self._raise_errors()
        input_net = port_nets[input_port]
        output_net = port_nets[output_port]
        ground_net = port_nets[ground_port]
        gate_component = stimulus["component"]
        gate_pin = Pin(f"{stage_name}.{gate_component}", 3)
        gate_net = self._net_containing(nets, gate_pin, "TAS_UNCONNECTED_GATE")
        self._raise_errors()

        synthesized = [
            Component("__tas_input", "DCVoltageSource", (60, 80), "up", parameters={"V": "Vin"}),
            Component(
                "__tas_source_resistance",
                "Resistor",
                (130, 80),
                "right",
                parameters={"R": "1e-6"},
            ),
            Component("__tas_load", "Resistor", (620, 220), "down", parameters={"R": "R_load"}),
            Component(
                "__tas_pwm",
                "PulseGenerator",
                (160, 260),
                "right",
                parameters={"Hi": "1", "Lo": "0", "f": "fs", "DutyCycle": "D", "Delay": "0"},
            ),
            Component("__tas_vin_meter", "Voltmeter", (100, 180), "down"),
            Component("__tas_vout_meter", "Voltmeter", (560, 180), "down"),
        ]
        self._warning(
            "TAS_SOURCE_RESISTANCE_SYNTHESIZED",
            "$.topology",
            "A 1 µΩ source resistance is synthesized to keep the ideal source and input capacitor well-posed in PLECS",
        )
        reserved = {component.name for component in synthesized}
        collisions = reserved & {component.name for component in components}
        if collisions:
            self._error(
                "TAS_RESERVED_COMPONENT_NAME",
                "$.topology.stages[0].circuit.components",
                f"CIAS component name collides with generated boundary: {sorted(collisions)[0]}",
            )
        nets.append(
            Net(
                "__tas_source_node",
                [Pin("__tas_input", 1), Pin("__tas_source_resistance", 1)],
            )
        )
        self._add_pins(
            nets,
            input_net,
            Pin("__tas_source_resistance", 2),
            Pin("__tas_vin_meter", 1),
        )
        self._add_pins(nets, output_net, Pin("__tas_load", 1), Pin("__tas_vout_meter", 1))
        self._add_pins(
            nets,
            ground_net,
            Pin("__tas_input", 2),
            Pin("__tas_load", 2),
            Pin("__tas_vin_meter", 2),
            Pin("__tas_vout_meter", 2),
        )
        self._add_pins(nets, gate_net, Pin("__tas_pwm", 1))
        components.extend(synthesized)

        default_captures = [
            self._resolved_capture("Vin.voltage", "net", input_net, "voltage", "__tas_vin_meter", "Measured voltage"),
            self._resolved_capture("Vin.current", "component", "__tas_input", "current", "__tas_input", "Source current"),
            self._resolved_capture("Vout.voltage", "net", output_net, "voltage", "__tas_vout_meter", "Measured voltage"),
            self._resolved_capture("Vout.current", "component", "__tas_load", "current", "__tas_load", "Resistor current"),
        ]
        resolved_captures = self._captures(
            list(requested_captures), components, nets, ground_net, default_captures
        )
        self._raise_errors()

        circuit = Circuit(
            name=f"tas_{self._identifier(circuit_data.get('name', 'buck'))}",
            components=sorted(components, key=lambda component: component.name),
            nets=sorted(nets, key=lambda net: net.name),
            # Keep the model artifact independent of every Operating Point.
            # Simulation Task ModelVars replace these portable open-in-PLECS
            # defaults, so one changed vector invalidates only its own cache key.
            raw_params=dict(_MODEL_VARIABLE_DEFAULTS),
        )
        return circuit, operating_points, tuple(resolved_captures)

    def _components(
        self,
        stage_name: str,
        records: list[dict[str, Any]],
        overrides: dict[tuple[str, str], dict[str, Any]],
    ) -> tuple[list[Component], dict[str, str]]:
        components: list[Component] = []
        types: dict[str, str] = {}
        for index, record in enumerate(sorted(records, key=lambda item: str(item.get("name", "")))):
            name = self._nonempty(record.get("name"), "$.topology.stages[0].circuit.components")
            location = f"$.topology.stages[0].circuit.components[{index}].data"
            data = self._resolve_mapping(record.get("data"), location)
            component_type = self._component_type(data, location)
            if component_type is None:
                continue
            parameters = self._component_parameters(
                component_type,
                data,
                overrides.get((stage_name, name), {}),
                location,
            )
            qualified = f"{stage_name}.{name}"
            types[name] = component_type
            components.append(
                Component(
                    qualified,
                    component_type,
                    position=(240 + len(components) * 70, 100 + (len(components) % 2) * 100),
                    parameters=parameters,
                )
            )
        self._raise_errors()
        return components, types

    def _component_type(self, data: Mapping[str, Any], location: str) -> str | None:
        requirements = self._dig(data, "inputs", "designRequirements") or {}
        device_type = str(requirements.get("deviceType", "")).lower()
        if "resistor" in data or device_type == "resistor":
            return "Resistor"
        if "capacitor" in data:
            return "Capacitor"
        if "magnetic" in data:
            turns_ratios = requirements.get("turnsRatios", [])
            if turns_ratios:
                self._error(
                    "TAS_UNSUPPORTED_MAGNETIC",
                    location,
                    "Milestone 1 supports only a single-winding inductor",
                )
                return None
            return "Inductor"
        if "mosfet" in data or device_type == "mosfet":
            return "Mosfet"
        if "diode" in data or device_type == "diode":
            return "Diode"
        self._error(
            "TAS_UNSUPPORTED_COMPONENT",
            location,
            "Electrical component is outside the Milestone 1 R/C/L/MOSFET/diode subset",
        )
        return None

    def _component_parameters(
        self,
        component_type: str,
        data: Mapping[str, Any],
        overrides: Mapping[str, Any],
        location: str,
    ) -> dict[str, str]:
        override = {self._parameter_alias(name): value for name, value in overrides.items()}
        paths: dict[str, dict[str, tuple[tuple[str, ...], ...]]] = {
            "Resistor": {
                "R": (
                    ("resistor", "manufacturerInfo", "datasheetInfo", "electrical", "resistance", "nominal"),
                    ("resistor", "manufacturerInfo", "datasheetInfo", "modelParams", "r"),
                )
            },
            "Capacitor": {
                "C": (
                    ("capacitor", "manufacturerInfo", "datasheetInfo", "electrical", "capacitance", "nominal"),
                    ("capacitor", "manufacturerInfo", "datasheetInfo", "modelParams", "cs"),
                )
            },
            "Inductor": {
                "L": (("inputs", "designRequirements", "magnetizingInductance", "nominal"),)
            },
            "Mosfet": {
                "Ron": (
                    ("mosfet", "manufacturerInfo", "datasheetInfo", "electrical", "onResistance"),
                    ("semiconductor", "manufacturerInfo", "datasheetInfo", "electrical", "onResistance"),
                )
            },
            "Diode": {
                "Vf": (
                    ("diode", "manufacturerInfo", "datasheetInfo", "electrical", "forwardVoltage"),
                    ("semiconductor", "manufacturerInfo", "datasheetInfo", "electrical", "forwardVoltage"),
                ),
                "Ron": (
                    ("diode", "manufacturerInfo", "datasheetInfo", "modelParams", "rs"),
                    ("semiconductor", "manufacturerInfo", "datasheetInfo", "modelParams", "rs"),
                ),
            },
        }
        parameters: dict[str, str] = {}
        unsupported_overrides = sorted(set(override) - set(paths[component_type]))
        if unsupported_overrides:
            self._error(
                "TAS_UNSUPPORTED_OVERRIDE_PARAMETER",
                location,
                f"Unsupported {component_type} override parameter {unsupported_overrides[0]!r}",
            )
        for parameter, candidates in paths[component_type].items():
            if parameter in override:
                value = override[parameter]
            else:
                inline_values = [
                    candidate
                    for path in candidates
                    if (candidate := self._dig(data, *path)) is not None
                ]
                distinct_values = {self._expression(candidate) for candidate in inline_values}
                if len(distinct_values) > 1:
                    self._error(
                        "TAS_AMBIGUOUS_COMPONENT_VALUE",
                        location,
                        f"{component_type} has conflicting inline {parameter} values; provide a stage-qualified override",
                    )
                value = inline_values[0] if inline_values else None
            if value is None:
                self._error(
                    "TAS_MISSING_COMPONENT_VALUE",
                    location,
                    f"{component_type} requires an unambiguous {parameter} value or stage-qualified override",
                )
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                self._error(
                    "TAS_INVALID_COMPONENT_VALUE",
                    location,
                    f"{component_type} {parameter} must be a numeric value or expression",
                )
                continue
            parameters[parameter] = self._expression(value)
        return parameters

    def _nets(
        self,
        stage_name: str,
        connections: list[dict[str, Any]],
        port_names: set[str],
        component_types: Mapping[str, str],
        external_names: Mapping[tuple[str, str], str],
    ) -> tuple[list[Net], dict[str, str]]:
        nets: list[Net] = []
        port_nets: dict[str, str] = {}
        assigned_pins: dict[Pin, str] = {}
        pin_occurrences: dict[Pin, int] = {}
        port_occurrences = {port_name: 0 for port_name in port_names}
        for index, connection in enumerate(sorted(connections, key=lambda item: str(item.get("name", "")))):
            local_name = self._nonempty(connection.get("name"), "$.topology.stages[0].circuit.connections")
            endpoints = self._object_list(
                connection.get("endpoints"),
                f"$.topology.stages[0].circuit.connections[{index}].endpoints",
            )
            exposed = [
                external_names[(stage_name, endpoint["port"])]
                for endpoint in endpoints
                if "port" in endpoint and (stage_name, endpoint.get("port")) in external_names
            ]
            if len(set(exposed)) > 1:
                self._error(
                    "TAS_CONTRADICTORY_EXTERNAL_NET",
                    f"$.topology.stages[0].circuit.connections[{index}]",
                    "One CIAS connection cannot expose multiple external TAS nets",
                )
            net_name = exposed[0] if exposed else f"{stage_name}.{local_name}"
            pins: list[Pin] = []
            for endpoint_index, endpoint in enumerate(endpoints):
                location = f"$.topology.stages[0].circuit.connections[{index}].endpoints[{endpoint_index}]"
                if set(endpoint) >= {"component", "pin"}:
                    component_name = endpoint.get("component")
                    component_type = component_types.get(component_name)
                    if component_type is None:
                        self._error(
                            "TAS_UNKNOWN_COMPONENT_REFERENCE",
                            location,
                            f"Unknown CIAS component {component_name!r}",
                        )
                        continue
                    terminal = _PIN_ALIASES[component_type].get(str(endpoint.get("pin")).lower())
                    if terminal is None:
                        self._error(
                            "TAS_UNKNOWN_PIN",
                            f"{location}.pin",
                            f"Unknown {component_type} pin {endpoint.get('pin')!r}",
                        )
                        continue
                    pin = Pin(f"{stage_name}.{component_name}", terminal)
                    previous = assigned_pins.get(pin)
                    if previous is not None:
                        if previous != net_name:
                            self._error(
                                "TAS_CONTRADICTORY_PIN",
                                location,
                                f"{component_name}.{endpoint.get('pin')} is assigned to both {previous!r} and {net_name!r}",
                            )
                        else:
                            self._error(
                                "TAS_MULTIPLY_CONNECTED_PIN",
                                location,
                                f"{component_name}.{endpoint.get('pin')} occurs more than once on {net_name!r}",
                            )
                    assigned_pins[pin] = net_name
                    pin_occurrences[pin] = pin_occurrences.get(pin, 0) + 1
                    pins.append(pin)
                elif set(endpoint) == {"port"}:
                    port = endpoint.get("port")
                    if port not in port_names:
                        self._error(
                            "TAS_UNKNOWN_PORT_REFERENCE",
                            location,
                            f"Unknown CIAS port {port!r}",
                        )
                        continue
                    previous = port_nets.get(port)
                    if previous is not None:
                        if previous != net_name:
                            self._error(
                                "TAS_CONTRADICTORY_PORT",
                                location,
                                f"CIAS port {port!r} is assigned to multiple nets",
                            )
                        else:
                            self._error(
                                "TAS_MULTIPLY_CONNECTED_PORT",
                                location,
                                f"CIAS port {port!r} occurs more than once on {net_name!r}",
                            )
                    port_nets[port] = net_name
                    port_occurrences[port] += 1
                else:
                    self._error(
                        "TAS_MALFORMED_ENDPOINT",
                        location,
                        "CIAS endpoint must contain exactly component+pin or port",
                    )
            nets.append(Net(net_name, sorted(set(pins), key=lambda pin: (pin.component, pin.terminal))))

        for component_name, component_type in sorted(component_types.items()):
            for terminal in sorted(set(_PIN_ALIASES[component_type].values())):
                pin = Pin(f"{stage_name}.{component_name}", terminal)
                if pin_occurrences.get(pin, 0) == 0:
                    self._error(
                        "TAS_UNCONNECTED_PIN",
                        "$.topology.stages[0].circuit.connections",
                        f"Required terminal {component_name}.{terminal} is not connected",
                    )
        for port_name, occurrences in sorted(port_occurrences.items()):
            if occurrences == 0:
                self._error(
                    "TAS_UNCONNECTED_PORT",
                    "$.topology.stages[0].circuit.connections",
                    f"CIAS port {port_name!r} is not connected",
                )
        return nets, port_nets

    def _external_net_names(
        self, topology: Mapping[str, Any], stage_ports: Mapping[str, set[str]]
    ) -> dict[tuple[str, str], str]:
        records = self._object_list(
            topology.get("interStageConnections"), "$.topology.interStageConnections"
        )
        self._check_unique(
            records, "name", "TAS_DUPLICATE_INTERSTAGE_CONNECTION", "$.topology.interStageConnections"
        )
        result: dict[tuple[str, str], str] = {}
        for index, record in enumerate(records):
            name = self._nonempty(record.get("name"), "$.topology.interStageConnections")
            if record.get("kind") not in {"externalPort", "wire"}:
                self._error(
                    "TAS_UNSUPPORTED_INTERSTAGE_CONNECTION",
                    f"$.topology.interStageConnections[{index}].kind",
                    f"Unsupported connection kind {record.get('kind')!r}",
                )
            endpoints = self._object_list(
                record.get("endpoints"), f"$.topology.interStageConnections[{index}].endpoints"
            )
            for endpoint_index, endpoint in enumerate(endpoints):
                stage = endpoint.get("stage")
                port = endpoint.get("port")
                location = f"$.topology.interStageConnections[{index}].endpoints[{endpoint_index}]"
                if stage not in stage_ports or port not in stage_ports.get(stage, set()):
                    self._error(
                        "TAS_MALFORMED_REFERENCE",
                        location,
                        f"Unknown stage-qualified port {stage!r}.{port!r}",
                    )
                    continue
                key = (stage, port)
                if key in result and result[key] != name:
                    self._error(
                        "TAS_CONTRADICTORY_PORT",
                        location,
                        f"Stage port {stage}.{port} is assigned to multiple nets",
                    )
                result[key] = name
        return result

    def _analysis(self, simulation: Mapping[str, Any]) -> dict[str, float]:
        analyses = self._object_list(simulation.get("analyses"), "$.simulation.analyses")
        if len(analyses) != 1 or analyses[0].get("type") != "transient":
            self._error(
                "TAS_UNSUPPORTED_ANALYSIS",
                "$.simulation.analyses",
                "Milestone 1 requires exactly one transient analysis",
            )
            return {"stopTime": 0.0, "maximumTimeStep": 0.0}
        analysis = analyses[0]
        stop_time = self._positive_number(analysis.get("stopTime"), "$.simulation.analyses[0].stopTime")
        max_step = self._positive_number(
            analysis.get("maximumTimeStep", stop_time / 1000 if stop_time else None),
            "$.simulation.analyses[0].maximumTimeStep",
        )
        return {"stopTime": stop_time, "maximumTimeStep": max_step}

    def _stimulus(
        self,
        simulation: Mapping[str, Any],
        stage_name: str,
        component_types: Mapping[str, str],
    ) -> dict[str, Any]:
        stimuli = self._object_list(simulation.get("stimulus"), "$.simulation.stimulus")
        supported = [
            stimulus
            for stimulus in stimuli
            if stimulus.get("stage") == stage_name
            and component_types.get(stimulus.get("component")) == "Mosfet"
            and stimulus.get("signal") == "gate"
            and isinstance(stimulus.get("waveform"), Mapping)
            and stimulus["waveform"].get("type") == "pwm"
        ]
        if len(supported) != 1:
            self._error(
                "TAS_MISSING_PWM_STIMULUS",
                "$.simulation.stimulus",
                "Milestone 1 requires exactly one PWM gate stimulus for the buck MOSFET",
            )
            return {"component": "", "frequency": 0.0, "dutyCycle": 0.0}
        stimulus = supported[0]
        waveform = stimulus["waveform"]
        frequency = self._positive_number(waveform.get("frequency"), "$.simulation.stimulus[0].waveform.frequency")
        duty = waveform.get("dutyCycle")
        if isinstance(duty, bool) or not isinstance(duty, (int, float)) or not 0 <= duty <= 1:
            self._error(
                "TAS_INVALID_PWM",
                "$.simulation.stimulus[0].waveform.dutyCycle",
                "PWM dutyCycle must be between 0 and 1",
            )
            duty = 0.0
        return {"component": stimulus["component"], "frequency": frequency, "dutyCycle": float(duty)}

    def _operating_points(
        self,
        inputs: Mapping[str, Any],
        analysis: Mapping[str, float],
        stimulus: Mapping[str, Any],
    ) -> tuple[ParameterVector, ...]:
        requirements = self._mapping(inputs.get("designRequirements"), "$.inputs.designRequirements")
        if requirements.get("inputType") != "dc":
            self._error(
                "TAS_UNSUPPORTED_INPUT",
                "$.inputs.designRequirements.inputType",
                "Milestone 1 supports a DC input source",
            )
        output_requirements = self._object_list(
            requirements.get("outputs"), "$.inputs.designRequirements.outputs"
        )
        if len(output_requirements) != 1:
            self._error(
                "TAS_UNSUPPORTED_OUTPUT_COUNT",
                "$.inputs.designRequirements.outputs",
                "Milestone 1 supports one DC output rail",
            )
            return ()
        output_requirement = output_requirements[0]
        output_name = output_requirement.get("name")
        nominal_voltage = self._dig(output_requirement, "voltage", "nominal")
        points = self._object_list(inputs.get("operatingPoints"), "$.inputs.operatingPoints")
        self._check_unique(points, "name", "TAS_DUPLICATE_OPERATING_POINT", "$.inputs.operatingPoints")
        if not points:
            self._error(
                "TAS_MISSING_OPERATING_POINT",
                "$.inputs.operatingPoints",
                "At least one named Operating Point is required",
            )
        vectors: list[ParameterVector] = []
        for index, point in enumerate(points):
            location = f"$.inputs.operatingPoints[{index}]"
            name = self._nonempty(point.get("name"), f"{location}.name")
            vin = self._positive_number(point.get("inputVoltage"), f"{location}.inputVoltage")
            temperature = point.get("ambientTemperature")
            if isinstance(temperature, bool) or not isinstance(temperature, (int, float)):
                self._error(
                    "TAS_INVALID_OPERATING_POINT",
                    f"{location}.ambientTemperature",
                    "ambientTemperature must be numeric",
                )
                temperature = 0.0
            loads = self._object_list(point.get("outputs"), f"{location}.outputs")
            matches = [load for load in loads if load.get("name") == output_name]
            if len(matches) != 1:
                self._error(
                    "TAS_INVALID_OPERATING_POINT",
                    f"{location}.outputs",
                    f"Operating Point must contain one load for output {output_name!r}",
                )
                continue
            load = matches[0]
            if load.get("loadType", "resistive") != "resistive":
                self._error(
                    "TAS_UNSUPPORTED_LOAD",
                    f"{location}.outputs[0].loadType",
                    "Milestone 1 supports a resistive output load",
                )
                continue
            voltage = load.get("voltage", nominal_voltage)
            voltage = self._positive_number(voltage, f"{location}.outputs[0].voltage")
            current = load.get("current")
            power = load.get("power")
            if (current is None) == (power is None):
                self._error(
                    "TAS_INVALID_OPERATING_POINT",
                    f"{location}.outputs[0]",
                    "Resistive load requires exactly one of current or power",
                )
                continue
            magnitude = self._positive_number(
                current if current is not None else power,
                f"{location}.outputs[0].{'current' if current is not None else 'power'}",
            )
            resistance = voltage / magnitude if current is not None else voltage * voltage / magnitude
            vectors.append(
                ParameterVector(
                    name,
                    {
                        "D": stimulus["dutyCycle"],
                        "R_load": resistance,
                        "T_sim": analysis["stopTime"],
                        "Vin": vin,
                        "fs": stimulus["frequency"],
                        "max_step": analysis["maximumTimeStep"],
                    },
                )
            )
            self._warning(
                "TAS_AMBIENT_TEMPERATURE_PRESERVED",
                f"{location}.ambientTemperature",
                f"Ambient temperature {float(temperature):g} °C is preserved but not consumed by the electrical-only projection",
            )
        return tuple(vectors)

    def _captures(
        self,
        requested: list[TasCapture],
        components: list[Component],
        nets: list[Net],
        ground_net: str,
        defaults: list[TasCapture],
    ) -> list[TasCapture]:
        names = [capture.name for capture in defaults + requested]
        if len(names) != len(set(names)):
            self._error(
                "TAS_DUPLICATE_CAPTURE",
                "$.captures",
                "Capture names must be unique",
            )
        component_by_name = {component.name: component for component in components}
        net_names = {net.name for net in nets}
        resolved = list(defaults)
        for capture in requested:
            location = f"$.captures.{capture.name}"
            if capture.kind == "net":
                if capture.target not in net_names:
                    self._error(
                        "TAS_UNKNOWN_CAPTURE_TARGET",
                        location,
                        f"Unknown Circuit Model net {capture.target!r}",
                    )
                    continue
                if capture.signal != "voltage":
                    self._error(
                        "TAS_UNSUPPORTED_CAPTURE",
                        location,
                        "Net captures support voltage only",
                    )
                    continue
                meter_name = f"__tas_meter_{self._identifier(capture.name)}"
                if meter_name in component_by_name:
                    self._error("TAS_DUPLICATE_CAPTURE", location, "Capture meter name collides")
                    continue
                meter = Component(meter_name, "Voltmeter", (650, 300 + len(resolved) * 20), "down")
                components.append(meter)
                component_by_name[meter_name] = meter
                self._add_pins(nets, capture.target, Pin(meter_name, 1))
                self._add_pins(nets, ground_net, Pin(meter_name, 2))
                resolved.append(
                    self._resolved_capture(
                        capture.name,
                        capture.kind,
                        capture.target,
                        capture.signal,
                        meter_name,
                        "Measured voltage",
                    )
                )
            elif capture.kind == "component":
                component = component_by_name.get(capture.target)
                plecs_signal = (
                    _PROBE_SIGNALS.get(component.type, {}).get(capture.signal)
                    if component is not None
                    else None
                )
                if component is None:
                    self._error(
                        "TAS_UNKNOWN_CAPTURE_TARGET",
                        location,
                        f"Unknown Circuit Model component {capture.target!r}",
                    )
                    continue
                if plecs_signal is None:
                    self._error(
                        "TAS_UNSUPPORTED_CAPTURE",
                        location,
                        f"{component.type} does not expose {capture.signal!r} in this projection",
                    )
                    continue
                resolved.append(
                    self._resolved_capture(
                        capture.name,
                        capture.kind,
                        capture.target,
                        capture.signal,
                        component.name,
                        plecs_signal,
                    )
                )
            else:
                self._error(
                    "TAS_UNSUPPORTED_CAPTURE",
                    location,
                    "Capture kind must be 'net' or 'component'",
                )
        return resolved

    def _overrides(self, simulation_value: Any) -> dict[tuple[str, str], dict[str, Any]]:
        if not isinstance(simulation_value, Mapping):
            return {}
        records = self._object_list(simulation_value.get("overrides", []), "$.simulation.overrides")
        result: dict[tuple[str, str], dict[str, Any]] = {}
        for index, record in enumerate(records):
            key = (str(record.get("stage", "")), str(record.get("component", "")))
            if key in result:
                self._error(
                    "TAS_DUPLICATE_OVERRIDE",
                    f"$.simulation.overrides[{index}]",
                    f"Duplicate override for {key[0]}.{key[1]}",
                )
                continue
            if record.get("model") is not None:
                self._error(
                    "TAS_UNSUPPORTED_MODEL_BINDING",
                    f"$.simulation.overrides[{index}].model",
                    "Band 1 ideal component projection does not consume external model bindings",
                )
            parameters = self._object_list(
                record.get("parameters", []), f"$.simulation.overrides[{index}].parameters"
            )
            parameter_names = [str(parameter.get("name", "")) for parameter in parameters]
            if len(parameter_names) != len(set(parameter_names)):
                self._error(
                    "TAS_DUPLICATE_OVERRIDE_PARAMETER",
                    f"$.simulation.overrides[{index}].parameters",
                    "Override parameter names must be unique",
                )
            result[key] = {str(parameter.get("name", "")): parameter.get("value") for parameter in parameters}
        return result

    def _resolve_mapping(self, value: Any, location: str) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return copy.deepcopy(dict(value))
        if isinstance(value, str):
            if self.resolver is None:
                self._error(
                    "TAS_RESOLVER_REQUIRED",
                    location,
                    f"URI value {value!r} requires an explicit caller resolver",
                )
                return {}
            try:
                resolved = self.resolver(value)
            except Exception as error:
                self._error(
                    "TAS_RESOLUTION_FAILED",
                    location,
                    f"Resolver failed for {value!r}: {error}",
                )
                return {}
            if not isinstance(resolved, Mapping):
                self._error(
                    "TAS_RESOLUTION_FAILED",
                    location,
                    f"Resolver returned {type(resolved).__name__}, expected an object",
                )
                return {}
            return copy.deepcopy(dict(resolved))
        self._error("TAS_MALFORMED_REFERENCE", location, "Expected an inline object or URI string")
        return {}

    def _diagnose_preserved_content(
        self, document: Mapping[str, Any], simulation: Mapping[str, Any]
    ) -> None:
        self._warning(
            "TAS_PARTIAL_PROJECTION",
            "$",
            "The complete TAS source is preserved, but only the documented Milestone 1 electrical projection affects execution",
        )
        consumed_root_fields = {"inputs", "topology", "simulation", "outputs"}
        for field in sorted(set(document) - consumed_root_fields):
            self._warning(
                "TAS_UNKNOWN_ROOT_CONTENT_PRESERVED",
                f"$.{field}",
                f"Root field {field!r} is preserved but does not affect the electrical projection",
            )
        for location in self._future_domain_locations(document):
            self._warning(
                "TAS_FUTURE_DOMAIN_PRESERVED",
                location,
                "Thermal, magnetic-construction, and mechanical content is preserved for a future projection and does not affect this run",
            )
        if "outputs" in document:
            self._warning(
                "TAS_OUTPUTS_PRESERVED",
                "$.outputs",
                "TAS computed outputs are preserved but not consumed by the electrical projection",
            )
        if simulation.get("models"):
            self._warning(
                "TAS_MODELS_PRESERVED",
                "$.simulation.models",
                "Simulation model-library entries are preserved but not consumed by the ideal Milestone 1 projection",
            )
        if simulation.get("initialConditions"):
            self._error(
                "TAS_UNSUPPORTED_INITIAL_CONDITION",
                "$.simulation.initialConditions",
                "Requested initial conditions affect execution and are not supported in Milestone 1",
            )

    @classmethod
    def _future_domain_locations(cls, value: Any, location: str = "$") -> list[str]:
        locations: list[str] = []
        if isinstance(value, Mapping):
            for key, child in value.items():
                child_location = f"{location}.{key}"
                normalized = str(key).lower()
                if normalized.startswith(("thermal", "magnetic", "mechanical")):
                    locations.append(child_location)
                    continue
                locations.extend(cls._future_domain_locations(child, child_location))
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for index, child in enumerate(value):
                locations.extend(cls._future_domain_locations(child, f"{location}[{index}]"))
        return locations

    def _binding_port(self, stage: Mapping[str, Any], key: str, stage_index: int) -> str:
        binding = self._mapping(stage.get(key), f"$.topology.stages[{stage_index}].{key}")
        return self._nonempty(binding.get("port"), f"$.topology.stages[{stage_index}].{key}.port")

    def _mapping(self, value: Any, location: str) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            self._error("TAS_MALFORMED_DOCUMENT", location, "Expected an object")
            return {}
        return dict(value)

    def _object_list(self, value: Any, location: str) -> list[dict[str, Any]]:
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            self._error("TAS_MALFORMED_DOCUMENT", location, "Expected an array")
            return []
        if any(not isinstance(item, Mapping) for item in value):
            self._error("TAS_MALFORMED_DOCUMENT", location, "Array entries must be objects")
            return []
        return [dict(item) for item in value]

    def _check_unique(
        self,
        records: Sequence[Mapping[str, Any]],
        field: str,
        code: str,
        location: str,
    ) -> None:
        values = [record.get(field) for record in records]
        duplicates = {value for value in values if values.count(value) > 1}
        if duplicates:
            self._error(code, location, f"Duplicate {field}: {sorted(map(str, duplicates))[0]}")

    def _nonempty(self, value: Any, location: str) -> str:
        if not isinstance(value, str) or not value:
            self._error("TAS_MALFORMED_DOCUMENT", location, "Expected a non-empty string")
            return ""
        return value

    def _positive_number(self, value: Any, location: str) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            self._error("TAS_INVALID_NUMBER", location, "Expected a positive number")
            return 0.0
        return float(value)

    @staticmethod
    def _dig(value: Mapping[str, Any], *path: str) -> Any:
        current: Any = value
        for key in path:
            if not isinstance(current, Mapping) or key not in current:
                return None
            current = current[key]
        return current

    @staticmethod
    def _parameter_alias(name: str) -> str:
        normalized = re.sub(r"[^a-z]", "", str(name).lower())
        return {
            "r": "R",
            "resistance": "R",
            "c": "C",
            "capacitance": "C",
            "l": "L",
            "inductance": "L",
            "magnetizinginductance": "L",
            "ron": "Ron",
            "onresistance": "Ron",
            "vf": "Vf",
            "forwardvoltage": "Vf",
        }.get(normalized, name)

    @staticmethod
    def _expression(value: Any) -> str:
        if isinstance(value, float):
            return format(value, ".12g")
        return str(value)

    @staticmethod
    def _identifier(value: Any) -> str:
        return re.sub(r"[^A-Za-z0-9_]+", "_", str(value)).strip("_") or "unnamed"

    @staticmethod
    def _resolved_capture(
        name: str,
        kind: str,
        target: str,
        signal: str,
        plecs_component: str,
        plecs_signal: str,
    ) -> TasCapture:
        return TasCapture(name, kind, target, signal, plecs_component, plecs_signal)

    def _net_containing(self, nets: Sequence[Net], pin: Pin, code: str) -> str:
        matches = [net.name for net in nets if pin in net.pins]
        if len(matches) == 1:
            return matches[0]
        self._error(
            code,
            "$.topology.stages[0].circuit.connections",
            f"Expected exactly one net for projected pin {pin.component}.{pin.terminal}",
        )
        return ""

    def _add_pins(self, nets: Sequence[Net], net_name: str, *pins: Pin) -> None:
        net = next((candidate for candidate in nets if candidate.name == net_name), None)
        if net is None:
            self._error("TAS_UNKNOWN_NET", "$.topology", f"Unknown projected net {net_name!r}")
            return
        net.pins.extend(pin for pin in pins if pin not in net.pins)
        net.pins.sort(key=lambda pin: (pin.component, pin.terminal))

    def _error(self, code: str, location: str, message: str) -> None:
        self._diagnostics.append(TasDiagnostic(code, location, DiagnosticSeverity.ERROR, message))

    def _warning(self, code: str, location: str, message: str) -> None:
        self._diagnostics.append(TasDiagnostic(code, location, DiagnosticSeverity.WARNING, message))

    def _raise_errors(self) -> None:
        errors = [
            diagnostic
            for diagnostic in self._diagnostics
            if diagnostic.severity == DiagnosticSeverity.ERROR
        ]
        if errors:
            raise TasCompilationError(errors)


__all__ = ["TasCompiler", "TasResolver"]
