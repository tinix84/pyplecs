"""Opt-in live PLECS proof for the Band 1 TAS answer (``uv run pytest -m live_plecs``)."""

import json
from pathlib import Path

import numpy as np
import pytest

from pyplecs.config import ConfigManager
from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.pyplecs import PlecsServer
from pyplecs.studies import ParametricStudyStatus
from pyplecs.tas import TasCompiler, TasExecutionService

FIXTURE = Path(__file__).parent / "fixtures" / "tas_buck_inline.json"


pytestmark = pytest.mark.live_plecs


@pytest.mark.asyncio
async def test_live_tas_answer_arrives_for_every_operating_point(tmp_path, live_plecs):
    source = json.loads(FIXTURE.read_text(encoding="utf-8"))
    model = TasCompiler(tmp_path / "models").compile(source).artifact_path
    try:
        plecs = PlecsServer(model_file=model, auto_launch=False)
    except (ConnectionError, OSError) as error:
        pytest.skip(f"live PLECS XML-RPC unavailable: {error}")

    config = ConfigManager(search_paths=[])
    config.update("cache.directory", str(tmp_path / "cache"))
    config.update("plecs.version", "live")
    config.update("orchestration.retry_attempts", 1)
    orchestrator = SimulationOrchestrator(plecs, config=config)
    service = TasExecutionService(orchestrator, artifact_directory=tmp_path / "models")
    try:
        envelope = await service.execute(source, use_cache=False)

        assert envelope.status == ParametricStudyStatus.COMPLETED, [
            point.error for point in envelope.points
        ]
        assert [point.name for point in envelope.points] == [
            "nominal",
            "high_line",
        ]
        for point in envelope.points:
            data = point.result.timeseries_data
            assert data is not None and not data.empty
            assert np.isfinite(data.to_numpy(dtype=float)).all()
            assert "Time" in data
            assert len(data["Time"]) > 1
            assert np.all(np.diff(data["Time"].to_numpy(dtype=float)) > 0)
    finally:
        await orchestrator.stop()
        plecs.close()
