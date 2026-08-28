"""Composite Cache Record identity: topology, parameters, solver, environment.

A Cache Record is addressed by four independently computed ids. A hit needs
all four to match, so a miss is diagnosable (which one differed?) and every
result of one topology is queryable together. Each id is conservative: a
field or construct whose effect on the waveform is unknown is *included*,
never ignored — the key never claims equality it cannot prove.
"""

import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..converter.parser import PlecsParseError, parse_plecs_text
from .topology import TopologyDocument, canonical_json, canonicalize_document, digest

logger = logging.getLogger(__name__)

KEY_FORMAT = "pyplecs-cache-key/1"

# Top-level Plecs{} fields that shape the run without changing the circuit.
SOLVER_FIELDS = frozenset(
    {
        "CircuitModel",
        "Solver",
        "StartTime",
        "TimeSpan",
        "StopTime",
        "Timeout",
        "MaxStep",
        "InitStep",
        "FixedStep",
        "Refine",
        "ZCStepSize",
        "RelTol",
        "AbsTol",
        "TurnOnThreshold",
        "SyncFixedStepTasks",
        "UseSingleCommonBaseRate",
        "MaxConsecutiveZCs",
        "ExtendedMatrixPrecision",
        "MatrixSignificanceCheck",
        "EnableStateSpaceSplitting",
        "DiscretizationMethod",
        "AlgebraicLoopMethod",
        "AlgebraicLoopTolerance",
        "TaskingMode",
        "TaskConfigurations",
        "InitialState",
        "SystemState",
        # Diagnostic severities decide whether a run aborts, so they decide
        # whether a result exists at all.
        "AssertionAction",
        "DivisionByZeroMsg",
        "StiffnessDetectionMsg",
        "NegativeSwitchLossMsg",
        "LossVariableLimitExceededMsg",
        "AlgebraicLoopWithStateMachineMsg",
        "DatatypeOverflowMsg",
        "DatatypeInheritanceConflictMsg",
        "ContinuousSampleTimeConflictMsg",
    }
)

# Top-level fields that provably do not touch a transient simulation.
IGNORED_FIELDS = frozenset(
    {
        "Name",
        "Version",
        "DisplayStateSpaceSplitting",
        "ExternalModeSettings",
        "ScriptsDialogGeometry",
        "ScriptsDialogSplitterPos",
    }
)
_IGNORED_PREFIXES = ("CodeGen",)

PARAMS_FIELDS = frozenset({"InitializationCommands"})
TOPOLOGY_FIELDS = frozenset({"Schematic", "Terminal"})

_ASSIGNMENT = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s*$")


@dataclass(frozen=True)
class CacheKey:
    """The four ids that together address one Cache Record."""

    topology_id: str
    params_id: str
    solver_id: str
    environment_id: str

    @property
    def record_id(self) -> str:
        return digest("\n".join((KEY_FORMAT, self.topology_id, self.params_id, self.solver_id, self.environment_id)))

    def to_dict(self) -> dict[str, str]:
        return {
            "topology_id": self.topology_id,
            "params_id": self.params_id,
            "solver_id": self.solver_id,
            "environment_id": self.environment_id,
            "record_id": self.record_id,
        }

    def differences(self, other: "CacheKey") -> list[str]:
        """Names of the ids that differ, in key order."""
        return [
            name
            for name in ("topology", "params", "solver", "environment")
            if getattr(self, f"{name}_id") != getattr(other, f"{name}_id")
        ]


@dataclass(frozen=True)
class PlecsEnvironment:
    """The PLECS installation whose results a Cache Record holds."""

    plecs_version: Optional[str]
    source: str = "explicit"

    @property
    def known(self) -> bool:
        return bool(self.plecs_version)

    @property
    def environment_id(self) -> Optional[str]:
        if not self.known:
            return None
        return digest(canonical_json({"plecs_version": self.plecs_version}))

    def to_dict(self) -> dict[str, Any]:
        return {"plecs_version": self.plecs_version, "source": self.source}

    @classmethod
    def detect(cls, plecs_config: Any) -> "PlecsEnvironment":
        """Resolve the installed PLECS version without starting PLECS.

        Order: the ``plecs.version`` configuration value, then the version
        resource of the configured executable, then a version in the
        executable's directory name. Anything else is unknown, and an unknown
        environment disables caching rather than pretending two unknowns are
        equal.
        """
        explicit = str(getattr(plecs_config, "version", "") or "").strip()
        if explicit:
            return cls(explicit, "config")
        for candidate in getattr(plecs_config, "executable_paths", None) or []:
            path = Path(str(candidate)).expanduser()
            if not path.is_file():
                continue
            version = _executable_version(path)
            if version:
                return cls(version, "executable")
            match = re.search(r"PLECS\s+(\d+(?:\.\d+)+)", str(path))
            if match:
                return cls(match.group(1), "path")
        return cls(None, "unknown")


def _executable_version(path: Path) -> Optional[str]:
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    version_dll = ctypes.windll.version  # type: ignore[attr-defined]
    size = version_dll.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        return None
    buffer = ctypes.create_string_buffer(size)
    if not version_dll.GetFileVersionInfoW(str(path), 0, size, buffer):
        return None
    pointer = ctypes.c_void_p()
    length = wintypes.UINT()
    if not version_dll.VerQueryValueW(buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)) or not pointer.value:
        return None

    class FixedFileInfo(ctypes.Structure):
        _fields_ = [
            ("signature", wintypes.DWORD),
            ("struct_version", wintypes.DWORD),
            ("file_version_ms", wintypes.DWORD),
            ("file_version_ls", wintypes.DWORD),
        ]

    info = ctypes.cast(pointer, ctypes.POINTER(FixedFileInfo)).contents
    return ".".join(
        str(part)
        for part in (
            info.file_version_ms >> 16,
            info.file_version_ms & 0xFFFF,
            info.file_version_ls >> 16,
            info.file_version_ls & 0xFFFF,
        )
    )


@dataclass(frozen=True)
class ModelIdentity:
    """Everything the cache learnt about one model-and-parameters request."""

    key: CacheKey
    environment: PlecsEnvironment
    topology: Optional[TopologyDocument]
    mode: str  # "canonical" | "bytes" | "missing"
    solver: dict[str, Any]
    params: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key.to_dict(),
            "environment": self.environment.to_dict(),
            "mode": self.mode,
            "coverage": self.topology.coverage if self.topology is not None else None,
        }


def identify(
    model_file: str,
    parameters: dict[str, Any],
    environment: PlecsEnvironment,
    exclude_fields: tuple[str, ...] = (),
) -> Optional[ModelIdentity]:
    """Compute the composite key, or ``None`` when the environment is unknown."""
    environment_id = environment.environment_id
    if environment_id is None:
        return None

    runtime = {
        key: _value_text(value) for key, value in sorted(parameters.items()) if key not in exclude_fields
    }
    text = _read_model_text(model_file)
    if text is None:
        # Nothing can be proven about a file that is not there; the path is
        # the only identity left.
        marker = {"missing": str(model_file)}
        return ModelIdentity(
            key=CacheKey(
                topology_id="missing-" + digest(canonical_json(marker)),
                params_id=digest(canonical_json(runtime)),
                solver_id="missing-" + digest(canonical_json(marker)),
                environment_id=environment_id,
            ),
            environment=environment,
            topology=None,
            mode="missing",
            solver={},
            params=runtime,
        )

    try:
        document = parse_plecs_text(text)
        topology = canonicalize_document(document)
    except (PlecsParseError, ValueError) as error:
        # Whole-file degrade: the normalized bytes are the identity.
        logger.warning("Canonicalization of %s failed (%s); keying on file bytes", model_file, error)
        bytes_id = "bytes-" + digest(text)
        return ModelIdentity(
            key=CacheKey(
                topology_id=bytes_id,
                params_id=digest(canonical_json(runtime)),
                solver_id=bytes_id,
                environment_id=environment_id,
            ),
            environment=environment,
            topology=None,
            mode="bytes",
            solver={},
            params=runtime,
        )

    root = document["Plecs"]
    solver = solver_bindings(root)
    params = parameter_bindings(str(root.get("InitializationCommands", "")), runtime)
    return ModelIdentity(
        key=CacheKey(
            topology_id=topology.topology_id,
            params_id=digest(canonical_json(params)),
            solver_id=digest(canonical_json(solver)),
            environment_id=environment_id,
        ),
        environment=environment,
        topology=topology,
        mode="canonical",
        solver=solver,
        params=params,
    )


def solver_bindings(root: dict[str, Any]) -> dict[str, Any]:
    """Classify every top-level field; unknown fields are kept under ``unclassified``."""
    solver: dict[str, Any] = {}
    unclassified: dict[str, Any] = {}
    for key, value in root.items():
        if key in SOLVER_FIELDS:
            solver[key] = _value_text(value)
        elif key in IGNORED_FIELDS or key in PARAMS_FIELDS or key in TOPOLOGY_FIELDS:
            continue
        elif key.startswith(_IGNORED_PREFIXES):
            continue
        else:
            unclassified[key] = _value_text(value)
    if unclassified:
        solver["unclassified"] = unclassified
    return solver


def parameter_bindings(initialization_commands: str, runtime: dict[str, str]) -> dict[str, Any]:
    """Symbol bindings from the init script with runtime ModelVars winning collisions.

    Only comments and scalar assignments are understood; any other statement
    makes the whole script part of the identity.
    """
    bindings: dict[str, str] = {}
    unrecognised = False
    without_comments = "\n".join(line.split("%", 1)[0] for line in initialization_commands.splitlines())
    for statement in re.split(r"[;\n]", without_comments):
        if not statement.strip():
            continue
        match = _ASSIGNMENT.match(statement)
        if match is None:
            unrecognised = True
            continue
        bindings[match.group(1)] = match.group(2)
    bindings.update(runtime)
    result: dict[str, Any] = {"bindings": bindings}
    if unrecognised:
        result["script"] = initialization_commands.strip()
    return result


def _read_model_text(model_file: str) -> Optional[str]:
    if not os.path.isfile(model_file):
        return None
    with open(model_file, "r", encoding="utf-8", errors="replace", newline=None) as handle:
        return handle.read()


def _value_text(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return "on" if value else "off"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, (dict, list, tuple)):
        return json.loads(canonical_json(value))
    return str(value)


__all__ = [
    "IGNORED_FIELDS",
    "PARAMS_FIELDS",
    "SOLVER_FIELDS",
    "TOPOLOGY_FIELDS",
    "CacheKey",
    "ModelIdentity",
    "PlecsEnvironment",
    "identify",
    "parameter_bindings",
    "solver_bindings",
]
