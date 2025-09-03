"""
Obsidian vault management module
"""

from src.obsidian.daily_integration import DailyNoteIntegration
from src.obsidian.metadata import MetadataManager
from src.obsidian.models import (
    FileOperation,
    NoteFrontmatter,
    ObsidianNote,
    OperationType,
    VaultStats,
)
from src.obsidian.organizer import VaultOrganizer
from src.obsidian.refactored_file_manager import ObsidianFileManager
from src.obsidian.template_system import TemplateEngine

# 古いテンプレートシステムは非推奨、 TemplateEngine を使用
# from src.templates import DailyNoteTemplate, MessageNoteTemplate, NoteTemplate

__all__ = [
    # File management
    "ObsidianFileManager",
    # Templates (new system)
    "TemplateEngine",
    # Templates (legacy - deprecated)
    # "NoteTemplate",
    # "MessageNoteTemplate",
    # "DailyNoteTemplate",
    # Models
    "ObsidianNote",
    "NoteFrontmatter",
    "VaultStats",
    "FileOperation",
    "OperationType",
    # Organization
    "VaultOrganizer",
    "MetadataManager",
    "DailyNoteIntegration",
]
