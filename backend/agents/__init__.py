"""
Agent System for FixionMail story generation.

This package implements the multi-agent architecture:

ACTIVE AGENTS (Single Stories - 3-Agent Flow):
- StructureAgent (SSBA): Creates story-specific beat structures (Sonnet)
- WriterAgent (PA): Generates first draft from beat plan (Sonnet)
- EditorAgent: Rewrites/polishes draft AND validates quality (Opus)

LEGACY (kept for compatibility):
- JudgeAgent: Standalone validation (Haiku) - replaced by EditorAgent

READY FOR PHASE 7 (Multi-Chapter Stories):
- ChapterBeatAgent (CBA): Creates 6-beat chapter structures from SSBA's story arc

Flow for Single Stories:
  Story Bible + Template → StructureAgent (Sonnet) → WriterAgent (Sonnet) → EditorAgent (Opus)

Flow for Multi-Chapter (Future):
  Story Bible → StructureAgent → ChapterBeatAgent → WriterAgent → EditorAgent

Model options:
- StructureAgent: "haiku" (fast) or "sonnet" (quality, default)
- WriterAgent: "sonnet" (default) - creates first draft
- EditorAgent: "opus" (default) - polishes and validates
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
from backend.agents.editor import (
    EditorAgent,
    EditorResult,
    EditorModel,
    EDITOR_MODELS
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
    # Writer Agent (PA) - First Draft
    "WriterAgent",
    "WriterResult",
    "WriterModel",
    "WRITER_MODELS",
    "get_available_writer_models",
    # Editor Agent - Polish + Validate (replaces Judge)
    "EditorAgent",
    "EditorResult",
    "EditorModel",
    "EDITOR_MODELS",
    # Judge Agent (legacy, kept for compatibility)
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
