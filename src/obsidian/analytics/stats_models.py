"""Data models for vault statistics."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass
class CategoryStats:
    """Statistics for a specific category."""

    category: str
    note_count: int
    total_characters: int
    total_words: int
    avg_note_size: float
    last_updated: datetime | None
    tags: list[str]


@dataclass
class VaultStats:
    """Comprehensive vault statistics."""

    # Basic counts
    total_notes: int
    total_characters: int
    total_words: int
    total_folders: int

    # Time-based stats
    notes_today: int
    notes_this_week: int
    notes_this_month: int
    notes_this_year: int

    # Averages
    avg_note_size: float
    avg_words_per_note: float

    # Category breakdown
    category_stats: list[CategoryStats]

    # Tag statistics
    most_used_tags: list[tuple[str, int]]
    total_unique_tags: int

    # Activity stats
    busiest_day: date | None
    creation_timeline: dict[str, int]  # date -> count

    # File stats
    largest_note: tuple[str, int] | None  # (filename, size)
    smallest_note: tuple[str, int] | None  # (filename, size)

    # Timestamps
    last_updated: datetime
    vault_created: datetime | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_notes": self.total_notes,
            "total_characters": self.total_characters,
            "total_words": self.total_words,
            "total_folders": self.total_folders,
            "notes_today": self.notes_today,
            "notes_this_week": self.notes_this_week,
            "notes_this_month": self.notes_this_month,
            "notes_this_year": self.notes_this_year,
            "avg_note_size": self.avg_note_size,
            "avg_words_per_note": self.avg_words_per_note,
            "category_stats": [
                {
                    "category": cat.category,
                    "note_count": cat.note_count,
                    "total_characters": cat.total_characters,
                    "avg_note_size": cat.avg_note_size,
                    "last_updated": cat.last_updated.isoformat()
                    if cat.last_updated
                    else None,
                    "tags": cat.tags,
                }
                for cat in self.category_stats
            ],
            "most_used_tags": self.most_used_tags,
            "total_unique_tags": self.total_unique_tags,
            "busiest_day": self.busiest_day.isoformat() if self.busiest_day else None,
            "creation_timeline": self.creation_timeline,
            "largest_note": self.largest_note,
            "smallest_note": self.smallest_note,
            "last_updated": self.last_updated.isoformat(),
            "vault_created": self.vault_created.isoformat()
            if self.vault_created
            else None,
        }
