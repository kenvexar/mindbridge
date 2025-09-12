"""Search-related data models."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


@dataclass
class SearchCriteria:
    """Criteria for searching notes."""

    query: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    date_from: date | str | None = None
    date_to: date | str | None = None
    content_type: str | None = None  # "markdown", "link", etc.
    exclude_folders: list[str] | None = None
    max_results: int = 100
    folder: str | None = None
    status: str | None = None


@dataclass
class SearchResult:
    """Result of a note search."""

    file_path: Path
    title: str
    content_preview: str
    relevance_score: float
    tags: list[str]
    created_date: date | None
    category: str | None
    match_highlights: list[str]  # Highlighted matching text snippets

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "file_path": str(self.file_path),
            "title": self.title,
            "content_preview": self.content_preview,
            "relevance_score": self.relevance_score,
            "tags": self.tags,
            "created_date": self.created_date.isoformat()
            if self.created_date
            else None,
            "category": self.category,
            "match_highlights": self.match_highlights,
        }
