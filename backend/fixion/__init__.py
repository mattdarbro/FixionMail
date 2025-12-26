"""
Fixion Chat Module

Fixion is the AI character that guides users through FixionMail.
A struggling actor in their 40s-50s working reception at FixionMail,
Fixion takes on genre-specific personas when helping users.
"""

from .service import FixionService
from .prompts import get_fixion_system_prompt, FIXION_PERSONAS

__all__ = [
    "FixionService",
    "get_fixion_system_prompt",
    "FIXION_PERSONAS",
]
