"""Public result and diagnostic models for the TAS electrical projection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from pyplecs.converter.circuit import Circuit
from pyplecs.studies import (
    ParameterVector,
    ParametricPointOutcome,
    ParametricStudyStatus,
)


class DiagnosticSeverity(str, Enum):
    """Severity of one stable TAS compiler diagnostic."""

    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class TasDiagnostic:
    """One location-qualified compiler observation."""

    code: str
    location: str
    severity: DiagnosticSeverity
    message: str


@dataclass(frozen=True)
class TasCapture:
    """A requested or synthesized signal capture."""

    name: str
    kind: str
    target: str
    signal: str
    plecs_component: str | None = None
    plecs_signal: str | None = None


@dataclass(frozen=True)
class TasCompilation:
    """A supported electrical projection and its deterministic artifact."""

    source: Mapping[str, Any]
    circuit: Circuit
    operating_points: tuple[ParameterVector, ...]
    captures: tuple[TasCapture, ...]
    diagnostics: tuple[TasDiagnostic, ...]
    artifact_path: Path


@dataclass(frozen=True)
class TasExecutionEnvelope:
    """Terminal TAS answer; runtime truth remains outside TAS outputs."""

    source: Mapping[str, Any]
    status: ParametricStudyStatus
    points: tuple[ParametricPointOutcome, ...]
    aggregate: Any
    diagnostics: tuple[TasDiagnostic, ...]
    artifact_path: Path


class TasCompilationError(ValueError):
    """Raised when required TAS content cannot be compiled correctly."""

    def __init__(self, diagnostics: list[TasDiagnostic] | tuple[TasDiagnostic, ...]):
        self.diagnostics = tuple(diagnostics)
        message = "; ".join(
            f"{diagnostic.code} at {diagnostic.location}: {diagnostic.message}"
            for diagnostic in self.diagnostics
        )
        super().__init__(message or "TAS compilation failed")
