"""Core file operations for Obsidian vault management."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import structlog

from src.obsidian.models import ObsidianNote

logger = structlog.get_logger(__name__)


class FileOperations:
    """Handles basic file I/O operations for Obsidian notes."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.operation_history: list[dict[str, Any]] = []

    async def save_note(self, note: ObsidianNote, subfolder: str | None = None) -> Path:
        """Save a note to the vault."""

        try:
            # 🔧 FIX: Cloud Run environment vault path validation
            if not self.vault_path.exists():
                logger.warning(
                    "Vault path does not exist, creating it",
                    vault_path=str(self.vault_path),
                )
                self.vault_path.mkdir(parents=True, exist_ok=True)

            # If the note already has a specific file_path set, use it
            if note.file_path and note.file_path != Path():
                file_path = note.file_path
                # Ensure the parent directory exists
                file_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                # Fallback to original logic for backward compatibility
                folder_path = self.vault_path
                if subfolder:
                    folder_path = folder_path / subfolder
                    folder_path.mkdir(parents=True, exist_ok=True)

                # Create filename from title
                safe_filename = self._sanitize_filename(note.title)
                file_path = folder_path / f"{safe_filename}.md"

                # Ensure unique filename
                file_path = await self._ensure_unique_filename(file_path)

            # Prepare content
            content = self._format_note_content(note)

            # 🔧 FIX: Add additional error handling for file operations
            try:
                # Write file
                async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                    await f.write(content)

                # Verify file was written
                if not file_path.exists():
                    raise FileNotFoundError(f"File was not created: {file_path}")

            except Exception as write_error:
                logger.error(
                    "🔧 ERROR: File write operation failed",
                    error=str(write_error),
                    file_path=str(file_path),
                    vault_exists=self.vault_path.exists(),
                    parent_exists=file_path.parent.exists(),
                )
                raise

            self._log_operation("save_note", str(file_path), note.title)

            logger.info(
                "Note saved successfully",
                file_path=str(file_path),
                title=note.title,
                size=len(content),
            )

            return file_path

        except Exception as e:
            logger.error(
                "Failed to save note",
                error=str(e),
                title=note.title,
                subfolder=subfolder,
                vault_path=str(self.vault_path),
                vault_exists=self.vault_path.exists() if self.vault_path else False,
            )
            raise

    async def load_note(self, file_path: Path) -> ObsidianNote | None:
        """Load a note from the vault."""
        try:
            if not file_path.exists():
                logger.warning("Note file not found", file_path=str(file_path))
                return None

            async with aiofiles.open(file_path, encoding="utf-8") as f:
                content = await f.read()

            # Parse the note content
            note = await self._parse_note_content(content, file_path)

            logger.info(
                "Note loaded successfully",
                file_path=str(file_path),
                title=note.title if note else "unknown",
            )

            return note

        except Exception as e:
            logger.error("Failed to load note", error=str(e), file_path=str(file_path))
            return None

    async def update_note(self, file_path: Path, note: ObsidianNote) -> bool:
        """Update an existing note."""
        try:
            content = self._format_note_content(note)

            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(content)

            self._log_operation("update_note", str(file_path), note.title)

            logger.info(
                "Note updated successfully",
                file_path=str(file_path),
                title=note.title,
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to update note",
                error=str(e),
                file_path=str(file_path),
                title=note.title,
            )
            return False

    async def append_to_note(
        self,
        file_path: Path,
        content: str,
        section_header: str | None = None,
    ) -> bool:
        """Append content to an existing note."""
        try:
            if not file_path.exists():
                logger.error(
                    "Cannot append to non-existent file", file_path=str(file_path)
                )
                return False

            # Read existing content
            async with aiofiles.open(file_path, encoding="utf-8") as f:
                existing_content = await f.read()

            # Prepare new content
            if section_header:
                append_content = f"\n\n## {section_header}\n\n{content}"
            else:
                append_content = f"\n\n{content}"

            # Clean duplicate sections if needed
            if section_header:
                existing_content = self._clean_duplicate_sections(
                    existing_content, section_header
                )

            # Combine content
            updated_content = existing_content.rstrip() + append_content

            # Write back to file
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(updated_content)

            self._log_operation(
                "append_note", str(file_path), section_header or "content"
            )

            logger.info(
                "Content appended to note",
                file_path=str(file_path),
                section=section_header,
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to append to note",
                error=str(e),
                file_path=str(file_path),
                section=section_header,
            )
            return False

    async def delete_note(self, file_path: Path, backup: bool = True) -> bool:
        """Delete a note from the vault."""
        try:
            if not file_path.exists():
                logger.warning(
                    "Note file not found for deletion", file_path=str(file_path)
                )
                return False

            if backup:
                await self._backup_before_delete(file_path)

            # Delete the file
            file_path.unlink()

            self._log_operation("delete_note", str(file_path), "deleted")

            logger.info("Note deleted successfully", file_path=str(file_path))

            return True

        except Exception as e:
            logger.error(
                "Failed to delete note", error=str(e), file_path=str(file_path)
            )
            return False

    def _sanitize_filename(self, title: str) -> str:
        """Convert note title to safe filename."""
        # Remove or replace invalid characters
        safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)
        safe_title = re.sub(r"\s+", "_", safe_title.strip())

        # Limit length
        if len(safe_title) > 200:
            safe_title = safe_title[:200]

        return safe_title

    async def _ensure_unique_filename(self, file_path: Path) -> Path:
        """Ensure filename is unique by adding counter if needed."""
        if not file_path.exists():
            return file_path

        base = file_path.stem
        suffix = file_path.suffix
        parent = file_path.parent

        counter = 1
        while True:
            new_path = parent / f"{base}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1

    def _format_note_content(self, note: ObsidianNote) -> str:
        """Format note content for markdown file."""
        content_parts = []

        # Add frontmatter section
        content_parts.append("---")

        # Add all frontmatter fields that have values
        frontmatter_dict = note.frontmatter.model_dump(
            exclude_none=True, exclude_unset=True
        )

        for key, value in frontmatter_dict.items():
            if value is not None:
                if isinstance(value, list):
                    if value:  # Only add non-empty lists
                        content_parts.append(
                            f"{key}: [{', '.join(str(v) for v in value)}]"
                        )
                elif isinstance(value, str) and value.strip():
                    content_parts.append(f"{key}: {value}")
                elif isinstance(value, int | float | bool):
                    content_parts.append(f"{key}: {value}")

        content_parts.append("---")
        content_parts.append("")

        # Add title if not in content already
        title_line = f"# {note.title}"
        if not note.content.startswith("# "):
            content_parts.append(title_line)
            content_parts.append("")

        # Add content
        if note.content:
            content_parts.append(note.content)

        return "\n".join(content_parts)

    async def _parse_note_content(self, content: str, file_path: Path) -> ObsidianNote:
        """Parse note content from markdown file."""
        from datetime import datetime

        from src.obsidian.models import NoteFrontmatter, ObsidianNote, VaultFolder

        lines = content.split("\n")

        # Extract frontmatter and content
        frontmatter_data: dict[str, Any] = {}
        content_start = 0

        if lines and lines[0].strip() == "---":
            # Parse frontmatter
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    content_start = i + 1
                    break
                elif ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    # Parse different types of values
                    if key == "discord_message_id":
                        frontmatter_data[key] = int(value) if value.isdigit() else None
                    elif key == "discord_author_id":
                        frontmatter_data[key] = int(value) if value.isdigit() else None
                    elif key == "ai_processed":
                        frontmatter_data[key] = value.lower() in ("true", "yes", "1")
                    elif key == "ai_processing_time":
                        frontmatter_data[key] = int(value) if value.isdigit() else None
                    elif key == "ai_confidence":
                        try:
                            frontmatter_data[key] = float(value)
                        except ValueError:
                            frontmatter_data[key] = None
                    elif key == "tags":
                        # Parse tags list
                        if value.startswith("[") and value.endswith("]"):
                            tags_str = value.strip("[]")
                            frontmatter_data[key] = [
                                tag.strip().strip("\"'")
                                for tag in tags_str.split(",")
                                if tag.strip()
                            ]
                        else:
                            frontmatter_data[key] = []
                    elif key in ("ai_tags", "aliases"):
                        # Parse list fields
                        if value.startswith("[") and value.endswith("]"):
                            tags_str = value.strip("[]")
                            frontmatter_data[key] = [
                                tag.strip().strip("\"'")
                                for tag in tags_str.split(",")
                                if tag.strip()
                            ]
                        else:
                            frontmatter_data[key] = []
                    else:
                        # String values
                        frontmatter_data[key] = value

        # Extract title from first h1 if present, otherwise use filename
        title = file_path.stem
        content_lines = lines[content_start:]

        for i, line in enumerate(content_lines):
            if line.startswith("# "):
                title = line[2:].strip()
                # Remove title line from content
                content_lines = content_lines[i + 1 :]
                break

        # Prepare content
        note_content = "\n".join(content_lines).strip()

        # Determine obsidian_folder from file path if not in frontmatter
        if not frontmatter_data.get("obsidian_folder"):
            # Try to determine folder based on file path
            relative_path = file_path.relative_to(self.vault_path)
            if len(relative_path.parts) > 1:
                # Use the first part of the path as folder
                frontmatter_data["obsidian_folder"] = relative_path.parts[0]
            else:
                # Default to INBOX if at root level
                frontmatter_data["obsidian_folder"] = VaultFolder.INBOX.value

        # Create frontmatter with defaults for required fields
        if not frontmatter_data.get("tags"):
            frontmatter_data["tags"] = []
        if not frontmatter_data.get("ai_tags"):
            frontmatter_data["ai_tags"] = []
        if not frontmatter_data.get("aliases"):
            frontmatter_data["aliases"] = []

        frontmatter = NoteFrontmatter(**frontmatter_data)

        # Create ObsidianNote
        note = ObsidianNote(
            filename=file_path.name,
            file_path=file_path,
            title=title,
            frontmatter=frontmatter,
            content=note_content,
            created_at=datetime.now(),
            modified_at=datetime.now(),
        )

        return note  # type: ignore[return-value]

    def _clean_duplicate_sections(self, content: str, section_header: str) -> str:
        """Remove duplicate sections with the same header."""
        # Pattern to match the section header
        pattern = rf"^## {re.escape(section_header)}$"

        lines = content.split("\n")
        result_lines = []
        skip_section = False

        for line in lines:
            if re.match(pattern, line):
                if skip_section:
                    # Skip this duplicate section
                    continue
                else:
                    skip_section = True
                    result_lines.append(line)
            elif line.startswith("## ") and skip_section:
                # End of section, stop skipping
                skip_section = False
                result_lines.append(line)
            elif not skip_section:
                result_lines.append(line)

        return "\n".join(result_lines)

    async def _backup_before_delete(self, file_path: Path) -> None:
        """Create backup before deleting file."""
        backup_dir = self.vault_path / ".trash"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}{file_path.suffix}"
        backup_path = backup_dir / backup_name

        # Copy file to backup location
        import shutil

        shutil.copy2(file_path, backup_path)

        logger.info(
            "File backed up before deletion",
            original=str(file_path),
            backup=str(backup_path),
        )

    def _log_operation(self, operation: str, file_path: str, details: str) -> None:
        """Log file operation to history."""
        self.operation_history.append(
            {
                "timestamp": datetime.now().isoformat(),
                "operation": operation,
                "file_path": file_path,
                "details": details,
            }
        )

        # Keep only last 1000 operations
        if len(self.operation_history) > 1000:
            self.operation_history = self.operation_history[-1000:]

    def get_operation_history(self) -> list[dict[str, Any]]:
        """Get file operation history."""
        return self.operation_history.copy()

    def clear_operation_history(self) -> None:
        """Clear file operation history."""
        self.operation_history.clear()
