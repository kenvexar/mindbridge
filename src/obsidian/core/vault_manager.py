"""Vault structure and initialization management."""

from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)


class VaultManager:
    """Manages Obsidian vault structure and initialization."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self._folder_cache: dict[str, Path] = {}

    async def initialize_vault(self) -> bool:
        """Initialize vault structure and templates."""
        try:
            # Create vault directory
            self.vault_path.mkdir(parents=True, exist_ok=True)

            # Ensure basic folder structure
            await self._ensure_vault_structure()

            # Create template files
            await self._create_template_files()

            logger.info(
                "Vault initialized successfully", vault_path=str(self.vault_path)
            )
            return True

        except Exception as e:
            logger.error("Failed to initialize vault", error=str(e))
            return False

    async def ensure_folder_exists(self, folder_path: str | Path) -> Path:
        """Ensure folder exists and return Path object."""
        if isinstance(folder_path, str):
            folder_path = self.vault_path / folder_path

        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path

    def get_folder_path(self, folder_name: str) -> Path:
        """Get cached folder path."""
        if folder_name in self._folder_cache:
            return self._folder_cache[folder_name]

        folder_path = self.vault_path / folder_name
        self._folder_cache[folder_name] = folder_path
        return folder_path

    async def _ensure_vault_structure(self) -> None:
        """Create essential vault directories."""
        from src.obsidian.models import VaultFolder

        essential_folders = [
            VaultFolder.INBOX.value,
            VaultFolder.PROJECTS.value,
            VaultFolder.DAILY_NOTES.value,
            VaultFolder.IDEAS.value,
            VaultFolder.ARCHIVE.value,
            VaultFolder.RESOURCES.value,
            VaultFolder.FINANCE.value,
            VaultFolder.TASKS.value,
            VaultFolder.HEALTH.value,
            VaultFolder.KNOWLEDGE.value,
            VaultFolder.ATTACHMENTS.value,
            VaultFolder.META.value,
            VaultFolder.TEMPLATES.value,
        ]

        for folder_enum_value in essential_folders:
            folder_path = self.vault_path / folder_enum_value
            folder_path.mkdir(parents=True, exist_ok=True)
            self._folder_cache[folder_enum_value] = folder_path

        logger.info("Vault structure ensured", folders=essential_folders)

    async def _create_template_files(self) -> None:
        """Create default template files."""
        from src.obsidian.models import VaultFolder

        templates = {
            "Daily Note.md": self._get_daily_note_template(),
            "Meeting Note.md": self._get_meeting_note_template(),
            "Project Note.md": self._get_project_note_template(),
            "Inbox Item.md": self._get_inbox_template(),
        }

        template_dir = self.vault_path / VaultFolder.TEMPLATES.value

        for filename, content in templates.items():
            template_path = template_dir / filename
            if not template_path.exists():
                template_path.write_text(content, encoding="utf-8")
                logger.debug("Created template", template=filename)

    def _get_daily_note_template(self) -> str:
        """Get daily note template content."""
        return """# {{date:YYYY-MM-DD}} - Daily Note

## 📝 Tasks
- [ ]

## 💭 Thoughts
-

## 📚 Learning
-

## 🎯 Goals
- [ ]

## 📊 Reflection
-

---
Created: {{date:YYYY-MM-DD HH:mm}}
Tags: #daily-note
"""

    def _get_meeting_note_template(self) -> str:
        """Get meeting note template content."""
        return """# Meeting: {{title}}

## 📅 Details
- **Date**: {{date:YYYY-MM-DD}}
- **Time**: {{time:HH:mm}}
- **Attendees**:
- **Location**:

## 📋 Agenda
-

## 📝 Notes
-

## ✅ Action Items
- [ ]

## 🔗 Related
-

---
Created: {{date:YYYY-MM-DD HH:mm}}
Tags: #meeting
"""

    def _get_project_note_template(self) -> str:
        """Get project note template content."""
        return """# Project: {{title}}

## 🎯 Overview
**Goal**:
**Status**: Planning
**Priority**: Medium

## 📋 Tasks
- [ ]

## 📊 Progress
- **Started**: {{date:YYYY-MM-DD}}
- **Deadline**:
- **Progress**: 0%

## 📝 Notes
-

## 🔗 Resources
-

---
Created: {{date:YYYY-MM-DD HH:mm}}
Tags: #project
"""

    def _get_inbox_template(self) -> str:
        """Get inbox item template content."""
        return """# {{title}}

## 📥 Inbox Item
- **Created**: {{date:YYYY-MM-DD HH:mm}}
- **Source**:
- **Type**:

## 📝 Content
{{content}}

## 🚀 Next Actions
- [ ] Process this item
- [ ] Move to appropriate location

---
Tags: #inbox
"""
