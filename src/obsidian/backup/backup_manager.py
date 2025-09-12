"""Backup manager for Obsidian vault."""

import shutil
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from src.obsidian.backup.backup_models import BackupConfig, BackupResult

logger = structlog.get_logger(__name__)


class BackupManager:
    """Manages vault backup operations."""

    def __init__(self, vault_path: Path, config: BackupConfig):
        self.vault_path = vault_path
        self.config = config

    async def create_backup(self, description: str | None = None) -> BackupResult:
        """Create a full backup of the vault."""
        start_time = time.time()
        timestamp = datetime.now()

        try:
            # Ensure backup directory exists
            self.config.backup_directory.mkdir(parents=True, exist_ok=True)

            # Generate backup filename
            backup_name = self._generate_backup_name(timestamp, description)
            backup_path = self.config.backup_directory / backup_name

            # Create backup
            files_backed_up, total_size = await self._create_backup_archive(backup_path)

            # Clean up old backups
            await self._cleanup_old_backups()

            duration = time.time() - start_time

            logger.info(
                "Backup created successfully",
                backup_path=str(backup_path),
                files_backed_up=files_backed_up,
                total_size=total_size,
                duration=duration,
            )

            return BackupResult(
                success=True,
                backup_path=backup_path,
                files_backed_up=files_backed_up,
                total_size=total_size,
                duration=duration,
                timestamp=timestamp,
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)

            logger.error("Backup failed", error=error_msg, duration=duration)

            return BackupResult(
                success=False,
                backup_path=None,
                files_backed_up=0,
                total_size=0,
                duration=duration,
                timestamp=timestamp,
                error_message=error_msg,
            )

    async def restore_backup(self, backup_path: Path) -> bool:
        """Restore vault from backup."""
        try:
            if not backup_path.exists():
                logger.error("Backup file not found", backup_path=str(backup_path))
                return False

            # Create temporary restoration directory
            temp_dir = self.vault_path.parent / f"temp_restore_{int(time.time())}"
            temp_dir.mkdir(exist_ok=True)

            try:
                # Extract backup
                if backup_path.suffix == ".zip":
                    with zipfile.ZipFile(backup_path, "r") as zip_ref:
                        zip_ref.extractall(temp_dir)
                else:
                    # Handle uncompressed backup (directory copy)
                    shutil.copytree(backup_path, temp_dir / "vault")

                # Backup current vault
                current_backup = (
                    self.vault_path.parent / f"current_vault_backup_{int(time.time())}"
                )
                if self.vault_path.exists():
                    shutil.move(str(self.vault_path), str(current_backup))

                # Move restored vault to correct location
                restored_vault = temp_dir / "vault"
                if not restored_vault.exists():
                    # Backup might be at root level
                    restored_vault = temp_dir

                shutil.move(str(restored_vault), str(self.vault_path))

                # Clean up with security check
                if current_backup.exists():
                    from ...utils.logger import secure_file_operation

                    if secure_file_operation(
                        "delete", current_backup, self.vault_path.parent
                    ):
                        shutil.rmtree(current_backup)
                    else:
                        logger.warning(
                            "Unsafe backup cleanup operation blocked",
                            path=str(current_backup),
                        )

                logger.info("Vault restored successfully", backup_path=str(backup_path))
                return True

            finally:
                # Clean up temp directory with security check
                if temp_dir.exists():
                    from ...utils.logger import secure_file_operation

                    if secure_file_operation(
                        "delete", temp_dir, self.vault_path.parent
                    ):
                        shutil.rmtree(temp_dir)
                    else:
                        logger.warning(
                            "Unsafe temp cleanup operation blocked", path=str(temp_dir)
                        )

        except Exception as e:
            logger.error(
                "Backup restoration failed", error=str(e), backup_path=str(backup_path)
            )
            return False

    async def list_backups(self) -> list[dict[str, Any]]:
        """List available backups."""
        try:
            if not self.config.backup_directory.exists():
                return []

            backups = []
            for backup_file in self.config.backup_directory.iterdir():
                if backup_file.is_file() and (
                    backup_file.suffix == ".zip"
                    or backup_file.name.startswith("vault_backup_")
                ):
                    stat = backup_file.stat()
                    backups.append(
                        {
                            "name": backup_file.name,
                            "path": str(backup_file),
                            "size": stat.st_size,
                            "created": datetime.fromtimestamp(stat.st_ctime),
                            "modified": datetime.fromtimestamp(stat.st_mtime),
                        }
                    )

            # Sort by creation time descending
            backups.sort(key=lambda x: x["created"], reverse=True)  # type: ignore[arg-type,return-value]
            return backups

        except Exception as e:
            logger.error("Failed to list backups", error=str(e))
            return []

    async def delete_backup(self, backup_name: str) -> bool:
        """Delete a specific backup."""
        try:
            backup_path = self.config.backup_directory / backup_name
            if backup_path.exists():
                if backup_path.is_file():
                    backup_path.unlink()
                else:
                    from ...utils.logger import secure_file_operation

                    if secure_file_operation(
                        "delete", backup_path, self.config.backup_directory
                    ):
                        shutil.rmtree(backup_path)
                    else:
                        logger.warning(
                            "Unsafe backup deletion blocked", path=str(backup_path)
                        )
                        return False

                logger.info("Backup deleted", backup_name=backup_name)
                return True
            else:
                logger.warning("Backup not found for deletion", backup_name=backup_name)
                return False

        except Exception as e:
            logger.error(
                "Failed to delete backup", error=str(e), backup_name=backup_name
            )
            return False

    async def _create_backup_archive(self, backup_path: Path) -> tuple[int, int]:
        """Create backup archive and return file count and size."""
        files_backed_up = 0
        total_size = 0

        if self.config.compress:
            # Create ZIP archive
            with zipfile.ZipFile(
                backup_path.with_suffix(".zip"), "w", zipfile.ZIP_DEFLATED
            ) as zipf:
                for file_path in self._get_files_to_backup():
                    archive_path = file_path.relative_to(self.vault_path)
                    zipf.write(file_path, archive_path)
                    files_backed_up += 1
                    total_size += file_path.stat().st_size
        else:
            # Create directory copy
            backup_path.mkdir(exist_ok=True)
            for file_path in self._get_files_to_backup():
                relative_path = file_path.relative_to(self.vault_path)
                dest_path = backup_path / relative_path
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest_path)
                files_backed_up += 1
                total_size += file_path.stat().st_size

        return files_backed_up, total_size

    def _get_files_to_backup(self) -> list[Path]:
        """Get list of files to backup based on configuration."""
        files_to_backup = []

        for path in self.vault_path.rglob("*"):
            if path.is_file():
                # Check exclusion patterns
                if self._should_exclude_file(path):
                    continue

                # Check attachment inclusion
                if not self.config.include_attachments and self._is_attachment(path):
                    continue

                files_to_backup.append(path)

        return files_to_backup

    def _should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded from backup."""
        if not self.config.exclude_patterns:
            return False

        relative_path = str(file_path.relative_to(self.vault_path))

        for pattern in self.config.exclude_patterns:
            import fnmatch

            if fnmatch.fnmatch(relative_path, pattern):
                return True

            # Also check individual path components
            for part in file_path.parts:
                if fnmatch.fnmatch(part, pattern):
                    return True

        return False

    def _is_attachment(self, file_path: Path) -> bool:
        """Check if file is an attachment (non-markdown file)."""
        attachment_extensions = {
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".pdf",
            ".doc",
            ".docx",
            ".mp3",
            ".mp4",
            ".mov",
            ".avi",
            ".zip",
            ".tar",
            ".gz",
        }
        return file_path.suffix.lower() in attachment_extensions

    def _generate_backup_name(
        self, timestamp: datetime, description: str | None = None
    ) -> str:
        """Generate backup filename."""
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")

        if description:
            # Sanitize description
            safe_desc = "".join(
                c for c in description if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            safe_desc = safe_desc.replace(" ", "_")[:50]
            base_name = f"vault_backup_{timestamp_str}_{safe_desc}"
        else:
            base_name = f"vault_backup_{timestamp_str}"

        if self.config.compress:
            return f"{base_name}.zip"
        else:
            return base_name

    async def _cleanup_old_backups(self) -> None:
        """Remove old backups to maintain max_backups limit."""
        try:
            backups = await self.list_backups()

            if len(backups) > self.config.max_backups:
                # Sort by creation time and remove oldest
                backups.sort(key=lambda x: x["created"])

                for backup in backups[self.config.max_backups :]:
                    backup_path = Path(backup["path"])
                    if backup_path.exists():
                        if backup_path.is_file():
                            backup_path.unlink()
                        else:
                            from ...utils.logger import secure_file_operation

                            if secure_file_operation(
                                "delete", backup_path, self.config.backup_directory
                            ):
                                shutil.rmtree(backup_path)
                            else:
                                logger.warning(
                                    "Unsafe old backup cleanup blocked",
                                    path=str(backup_path),
                                )
                                continue

                        logger.debug("Old backup removed", backup_name=backup["name"])

        except Exception as e:
            logger.warning("Failed to cleanup old backups", error=str(e))
