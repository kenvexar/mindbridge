"""Data models for backup functionality."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class BackupConfig:
    """Configuration for vault backup."""

    backup_directory: Path
    max_backups: int = 10
    compress: bool = True
    exclude_patterns: list[str] | None = None
    include_attachments: bool = True
    incremental: bool = False

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.exclude_patterns is None:
            self.exclude_patterns = [".obsidian", ".trash", "*.tmp"]


@dataclass
class BackupResult:
    """Result of a backup operation."""

    success: bool
    backup_path: Path | None
    files_backed_up: int
    total_size: int  # in bytes
    duration: float  # in seconds
    timestamp: datetime
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "success": self.success,
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "files_backed_up": self.files_backed_up,
            "total_size": self.total_size,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
        }
