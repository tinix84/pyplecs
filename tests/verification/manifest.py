"""The canonical Operating Point as data, plus the live-PLECS availability gate."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import pytest

from pyplecs.config import ConfigManager

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures"
EVIDENCE_ROOT = REPO_ROOT / "tests" / "evidence"
CANONICAL_BUCK = FIXTURES / "canonical_buck.json"


@dataclass(frozen=True)
class Manifest:
    """One tracked acceptance manifest: model, Operating Point, Signal Map, window, tolerances."""

    data: Mapping[str, Any]
    path: Path

    @property
    def model_file(self) -> Path:
        return REPO_ROOT / self.data["model_file"]

    @property
    def model_name(self) -> str:
        return self.model_file.stem

    @property
    def operating_point_name(self) -> str:
        return self.data["operating_point"]["name"]

    @property
    def parameters(self) -> dict[str, float]:
        return {key: float(value) for key, value in self.data["operating_point"]["parameters"].items()}

    @property
    def signals(self) -> list[str]:
        return list(self.data["signals"])

    @property
    def required_signals(self) -> list[str]:
        return list(self.data["required_signals"])

    @property
    def signal_map(self) -> dict[str, Any]:
        return json.loads(json.dumps(self.data["signal_map"]))

    @property
    def switching_frequency(self) -> float:
        return self.parameters[self.data["window"]["switching_frequency_parameter"]]

    @property
    def periods(self) -> int:
        return int(self.data["window"]["periods"])

    @property
    def tolerances(self) -> Mapping[str, Any]:
        return self.data["tolerances"]

    @property
    def units(self) -> Mapping[str, str]:
        return self.data["units"]

    @property
    def plecs_version(self) -> str:
        return self.data["plecs"]["version"]

    @property
    def endpoint(self) -> tuple[str, int]:
        xmlrpc = self.data["plecs"]["xmlrpc"]
        return str(xmlrpc["host"]), int(xmlrpc["port"])

    def derived(self) -> dict[str, float]:
        """Analytic buck values from the Operating Point (duty ratio, load, inductor ripple)."""
        p = self.parameters
        duty = p["Vo_ref"] / p["Vi"]
        return {
            "duty_ratio": duty,
            "load_resistance": p["Vo_ref"] ** 2 / (p["Vi"] * p["Ii_max"]),
            "inductor_ripple": (p["Vi"] - p["Vo_ref"]) * duty / (p["fs"] * p["Lo"]),
        }

    def reference_path(self) -> Path:
        return FIXTURES / f"{self.model_name}.{self.operating_point_name}.reference.json"

    def evidence_directory(self, stamp: str) -> Path:
        return EVIDENCE_ROOT / self.model_name / self.operating_point_name / stamp


def load_manifest(path: Path = CANONICAL_BUCK) -> Manifest:
    return Manifest(data=json.loads(path.read_text(encoding="utf-8")), path=path)


def require_live_plecs(host: str, port: int, probe: Callable[[str, int, float], bool], timeout: float = 3.0) -> None:
    """Skip — never fail, never launch — when the configured endpoint does not answer."""
    if not probe(host, port, timeout):
        pytest.skip(f"live PLECS XML-RPC unavailable at {host}:{port}; start PLECS or unset -m live_plecs")


def isolated_config(tmp_path: Path, manifest: Manifest, *, batch_size: int = 4) -> ConfigManager:
    """Temporary configuration: no discovery, private cache, pinned PLECS Environment, no auto-launch."""
    host, port = manifest.endpoint
    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("plecs.version", manifest.plecs_version)
    config.update("plecs.xmlrpc.host", host)
    config.update("plecs.xmlrpc.port", port)
    config.update("plecs.auto_launch", False)
    config.update("orchestration.retry_attempts", 1)
    config.update("orchestration.retry_delay", 0)
    config.update("orchestration.max_concurrent_simulations", batch_size)
    return config
