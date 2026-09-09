"""Evidence Bundle: what a reviewer retains from one acceptance run."""

from __future__ import annotations

import csv
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import pyplecs


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


class EvidenceBundle:
    """One directory per run: tracked json/md, untracked raw series and overlays."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        (self.directory / "raw").mkdir(exist_ok=True)

    def write_json(self, name: str, payload: Any) -> Path:
        path = self.directory / f"{name}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=_jsonable) + "\n", encoding="utf-8")
        return path

    def write_text(self, name: str, text: str) -> Path:
        path = self.directory / name
        path.write_text(text, encoding="utf-8")
        return path

    def write_series(self, name: str, time: Sequence[float], signals: Mapping[str, Sequence[float]]) -> Path:
        path = self.directory / "raw" / f"{name}.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["Time", *signals])
            for index, t in enumerate(time):
                writer.writerow([repr(float(t)), *(repr(float(signals[k][index])) for k in signals)])
        return path

    def environment(self, **extra: Any) -> dict[str, Any]:
        return {
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "pyplecs": pyplecs.__version__,
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            **extra,
        }


def _jsonable(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serializable: {type(value).__name__}")
