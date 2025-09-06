"""Template system for Obsidian notes"""

from .base import GeneratedNote, ITemplateProcessor
from .engine import TemplateEngine
from .generator import NoteGenerator
from .loader import TemplateLoader
from .processor import CustomFunctionProcessor, TemplateProcessor
from .validator import TemplateValidator

__all__ = [
    "GeneratedNote",
    "ITemplateProcessor",
    "TemplateEngine",
    "NoteGenerator",
    "TemplateLoader",
    "TemplateProcessor",
    "CustomFunctionProcessor",
    "TemplateValidator",
]
