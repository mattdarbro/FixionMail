"""
2-Agent System for FixionMail story generation.

This package implements the simplified 2-agent architecture:
- WriterAgent (Sonnet): Generates complete stories in one call
- JudgeAgent (Haiku): Validates stories against requirements
"""

from backend.agents.writer import WriterAgent
from backend.agents.judge import JudgeAgent

__all__ = ["WriterAgent", "JudgeAgent"]
