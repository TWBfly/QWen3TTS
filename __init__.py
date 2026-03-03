"""
Story-Sisyphus 多智能体网文创作系统
"""

__version__ = "1.0.0"
__author__ = "Story-Sisyphus Team"

from .models import (
    StoryBible,
    CharacterCard,
    WorldSettings,
    PlotArc,
    ChapterOutline,
    OpenLoop,
    EventRecord,
    CharacterState,
    LoopStatus
)

from .storage import StorageManager
from .config import Config

__all__ = [
    "StoryBible",
    "CharacterCard",
    "WorldSettings",
    "PlotArc",
    "ChapterOutline",
    "OpenLoop",
    "EventRecord",
    "CharacterState",
    "LoopStatus",
    "StorageManager",
    "Config"
]
