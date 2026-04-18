"""Async pipeline orchestrator for voice bot flow."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
import time
from typing import Callable, Any
from enum import Enum
from observability import get_logger

logger = get_logger("pipeline")

class Stage(str, Enum):
    RECEIVE = "receive"
    TRANSCRIBE = "transcribe"
    CHAT = "chat"
    SYNTHESIZE = "synthesize"
    DELIVER = "deliver"

class PipelineEvent:
    def __init__(self, data: Any, stage: Stage, duration_ms: float = None, error: str = None):
        self.data = data
        self.stage = stage
        self.duration_ms = duration_ms
        self.error = error
        self.timestamp = time.time()

class Pipeline:
    def __init__(self, stages: list[Callable]):
        self.stages = stages
        self.events: list[PipelineEvent] = []

    async def execute(self, initial_data: Any) -> Any:
        """Execute all stages sequentially, collecting metrics."""
        data = initial_data
        for stage in self.stages:
            start = time.time()
            try:
                if asyncio.iscoroutinefunction(stage):
                    data = await stage(data)
                else:
                    data = stage(data)
                duration = (time.time() - start) * 1000
                logger.info(f"Stage {stage.__name__}: {duration:.1f}ms")
                self.events.append(PipelineEvent(data, Stage.DELIVER, duration))
            except Exception as e:
                duration = (time.time() - start) * 1000
                logger.error(f"Stage {stage.__name__} failed after {duration:.1f}ms: {e}")
                self.events.append(PipelineEvent(data, stage.__name__, duration, str(e)))
                raise
        return data

    def get_metrics(self) -> dict:
        """Return pipeline performance metrics."""
        return {
            "total_events": len(self.events),
            "stages": [
                {"stage": e.stage, "duration_ms": e.duration_ms, "error": e.error}
                for e in self.events
            ]
        }