"""
2-Agent System for FixionMail story generation.

This package implements the simplified 2-agent architecture:
- WriterAgent (Sonnet/Opus): Generates complete stories in one call
- JudgeAgent (Haiku): Validates stories against requirements

Model options for WriterAgent:
- "sonnet" (default): Claude Sonnet 4.5 - fast, high-quality
- "opus": Claude Opus 4.5 - premium quality, deeper creativity
"""

from backend.agents.writer import (
    WriterAgent,
    WriterResult,
    WriterModel,
    WRITER_MODELS,
    get_available_writer_models
)
from backend.agents.judge import JudgeAgent, JudgeResult

__all__ = [
    "WriterAgent",
    "WriterResult",
    "WriterModel",
    "WRITER_MODELS",
    "get_available_writer_models",
    "JudgeAgent",
    "JudgeResult"
]
