"""End-to-end Python service for the supported TAS electrical projection."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from pyplecs.contracts import TaskPriority
from pyplecs.orchestration import SimulationOrchestrator
from pyplecs.studies import (
    ExplicitParameterVectorStrategy,
    ParametricPointOutcome,
    ParametricStudy,
    ResultReducer,
)

from .compiler import TasCompiler, TasResolver
from .models import TasCapture, TasCompilation, TasExecutionEnvelope


class TasExecutionService:
    """Compile TAS once and execute its Operating Points as one study."""

    def __init__(
        self,
        orchestrator: SimulationOrchestrator,
        *,
        artifact_directory: str | Path | None = None,
    ):
        self._orchestrator = orchestrator
        self._artifact_directory = artifact_directory

    async def execute(
        self,
        document: Mapping[str, Any],
        *,
        captures: Sequence[TasCapture] = (),
        resolver: TasResolver | None = None,
        reducer: ResultReducer | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        use_cache: bool = True,
        on_point_terminal: Callable[[ParametricPointOutcome], None] | None = None,
    ) -> TasExecutionEnvelope:
        """Return the terminal answer for every TAS Operating Point."""
        compilation = self.prepare(document, captures=captures, resolver=resolver)
        return await self.execute_prepared(
            compilation,
            reducer=reducer,
            priority=priority,
            use_cache=use_cache,
            on_point_terminal=on_point_terminal,
        )

    def prepare(
        self,
        document: Mapping[str, Any],
        *,
        captures: Sequence[TasCapture] = (),
        resolver: TasResolver | None = None,
    ) -> TasCompilation:
        """Validate and compile before asynchronous study acceptance."""
        return TasCompiler(self._artifact_directory, resolver=resolver).compile(
            document, captures=captures
        )

    async def execute_prepared(
        self,
        compilation: TasCompilation,
        *,
        reducer: ResultReducer | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        use_cache: bool = True,
        on_point_terminal: Callable[[ParametricPointOutcome], None] | None = None,
    ) -> TasExecutionEnvelope:
        """Execute a preflighted compilation through the ordinary study seam."""
        outcome = await ParametricStudy(self._orchestrator).run(
            compilation.artifact_path,
            ExplicitParameterVectorStrategy(compilation.operating_points),
            reducer=reducer,
            output_variables=[capture.name for capture in compilation.captures],
            metadata={"source": "tas-v2-electrical-projection"},
            priority=priority,
            use_cache=use_cache,
            on_point_terminal=on_point_terminal,
        )
        return TasExecutionEnvelope(
            source=compilation.source,
            status=outcome.status,
            points=outcome.points,
            aggregate=outcome.aggregate,
            diagnostics=compilation.diagnostics,
            artifact_path=compilation.artifact_path,
        )

    def execute_sync(
        self,
        document: Mapping[str, Any],
        *,
        timeout: float | None = None,
        captures: Sequence[TasCapture] = (),
        resolver: TasResolver | None = None,
        reducer: ResultReducer | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        use_cache: bool = True,
    ) -> TasExecutionEnvelope:
        """Wait synchronously on the same asynchronous execution behavior."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError(
                "execute_sync cannot run inside an active event loop; await execute instead"
            )

        was_running = self._orchestrator.is_running

        async def run() -> TasExecutionEnvelope:
            try:
                operation = self.execute(
                    document,
                    captures=captures,
                    resolver=resolver,
                    reducer=reducer,
                    priority=priority,
                    use_cache=use_cache,
                )
                return await asyncio.wait_for(operation, timeout=timeout)
            finally:
                if not was_running:
                    await self._orchestrator.stop()

        return asyncio.run(run())


__all__ = ["TasExecutionService"]
