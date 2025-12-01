"""
Agent System for FixionMail story generation.

This package implements the multi-agent architecture:

ACTIVE AGENTS (Single Stories):
- StructureAgent (SSBA): Creates story-specific beat structures from generic templates
- WriterAgent (PA): Generates complete stories from detailed beat plans
- JudgeAgent: Validates stories against requirements

READY FOR PHASE 7 (Multi-Chapter Stories):
- ChapterBeatAgent (CBA): Creates 6-beat chapter structures from SSBA's story arc

Flow for Single Stories:
  Story Bible + Generic Template → StructureAgent → Specific Beats → WriterAgent → JudgeAgent

Flow for Multi-Chapter (Future):
  Story Bible → StructureAgent (full arc) → ChapterBeatAgent (per chapter) → WriterAgent → JudgeAgent

Model options:
- StructureAgent: "haiku" (fast) or "sonnet" (quality, default)
- WriterAgent: "sonnet" (default) or "opus" (premium)
- JudgeAgent: Uses Haiku (fast validation)
"""

from backend.agents.writer import (
    WriterAgent,
    WriterResult,
    WriterModel,
    WRITER_MODELS,
    get_available_writer_models
)
from backend.agents.judge import JudgeAgent, JudgeResult
from backend.agents.structure import (
    StructureAgent,
    StructureResult,
    StoryStructure,
    StoryBeat,
    StructureModel,
    STRUCTURE_MODELS
)
from backend.agents.chapter_beat import (
    ChapterBeatAgent,
    ChapterBeatResult,
    ChapterStructure,
    ChapterBeat,
    CBAModel,
    CBA_MODELS,
    CHAPTER_BEAT_TEMPLATE,
    get_chapter_guidance_from_arc
)

__all__ = [
    # Structure Agent (SSBA)
    "StructureAgent",
    "StructureResult",
    "StoryStructure",
    "StoryBeat",
    "StructureModel",
    "STRUCTURE_MODELS",
    # Writer Agent (PA)
    "WriterAgent",
    "WriterResult",
    "WriterModel",
    "WRITER_MODELS",
    "get_available_writer_models",
    # Judge Agent
    "JudgeAgent",
    "JudgeResult",
    # Chapter Beat Agent (CBA) - Ready for Phase 7
    "ChapterBeatAgent",
    "ChapterBeatResult",
    "ChapterStructure",
    "ChapterBeat",
    "CBAModel",
    "CBA_MODELS",
    "CHAPTER_BEAT_TEMPLATE",
    "get_chapter_guidance_from_arc"
]
