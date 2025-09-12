"""
Template processing interfaces for dependency inversion and interface segregation.
Follows SOLID principles for better testability and maintainability.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Protocol


class ITemplateLoader(Protocol):
    """Interface for template loading operations."""

    async def load_template(self, template_name: str) -> str | None:
        """Load a template by name."""
        ...


class ITemplateProcessor(Protocol):
    """Interface for template content processing."""

    async def process(self, content: str, context: dict[str, Any]) -> str:
        """Process template content with given context."""
        ...


class ITemplateValidator(Protocol):
    """Interface for template validation."""

    async def validate_template(self, content: str) -> list[str]:
        """Validate template and return list of issues."""
        ...


class IConditionalProcessor(Protocol):
    """Interface for conditional section processing."""

    async def process(self, content: str, context: dict[str, Any]) -> str:
        """Process conditional sections in template."""
        ...


class ICustomFunctionProcessor(Protocol):
    """Interface for custom function processing."""

    async def process(self, content: str, context: dict[str, Any]) -> str:
        """Process custom functions in template."""
        ...


class IFileStorage(Protocol):
    """Interface for file operations."""

    async def save(self, path: str, content: str) -> None:
        """Save content to file."""
        ...

    async def load(self, path: str) -> str | None:
        """Load content from file."""
        ...

    async def exists(self, path: str) -> bool:
        """Check if file exists."""
        ...


class IVaultOperations(Protocol):
    """Interface for Obsidian vault operations."""

    async def save_note(self, note_path: str, content: str) -> None:
        """Save a note to the vault."""
        ...

    async def load_note(self, note_path: str) -> str | None:
        """Load a note from the vault."""
        ...

    async def search_notes(self, query: str) -> list[str]:
        """Search notes in the vault."""
        ...


class ITemplateEngine(Protocol):
    """Main template engine interface."""

    async def load_template(self, template_name: str) -> str | None:
        """Load a template."""
        ...

    async def render_template(
        self, template_content: str, context: dict[str, Any]
    ) -> str:
        """Render template with context."""
        ...

    async def validate_template(self, content: str) -> list[str]:
        """Validate template syntax."""
        ...


# Abstract base classes for implementation guidance


class TemplateProcessorBase(ABC):
    """Base class for template processors."""

    def __init__(self, logger):
        self.logger = logger

    @abstractmethod
    async def process(self, content: str, context: dict[str, Any]) -> str:
        """Process template content."""
        pass


class FileOperationsBase(ABC):
    """Base class for file operations."""

    def __init__(self, base_path: Path, logger):
        self.base_path = base_path
        self.logger = logger

    @abstractmethod
    async def save(self, path: str, content: str) -> None:
        """Save file."""
        pass

    @abstractmethod
    async def load(self, path: str) -> str | None:
        """Load file."""
        pass
