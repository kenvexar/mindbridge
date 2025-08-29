"""
Data backup and storage management system
"""

import zipfile
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from discord.ext import commands, tasks

from ..config.settings import get_settings
from ..obsidian.github_sync import GitHubObsidianSync
from ..utils.mixins import LoggerMixin
from .notification_system import NotificationCategory, NotificationLevel


class BackupType(str, Enum):
    """バックアップタイプ"""

    FULL = "full"
    INCREMENTAL = "incremental"
    OBSIDIAN_ONLY = "obsidian_only"
    CONFIG_ONLY = "config_only"


class BackupDestination(str, Enum):
    """バックアップ先"""

    LOCAL = "local"
    CLOUD_STORAGE = "cloud_storage"
    GITHUB = "github"


class BackupStatus(str, Enum):
    """バックアップ状態"""

    SUCCESS = "success"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    PARTIAL = "partial"


class DataBackupSystem(LoggerMixin):
    """データバックアップとストレージ管理システム"""

    def __init__(
        self, bot: commands.Bot, notification_system: Any | None = None
    ) -> None:
        self.bot = bot
        self.notification_system = notification_system

        # バックアップ設定
        self.backup_dir = Path.cwd() / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        # バックアップ履歴
        self.backup_history: list[dict[str, Any]] = []

        # 設定
        self.auto_backup_enabled = False
        self.backup_interval_hours = 24
        self.max_backup_files = 30
        self.backup_destinations = [BackupDestination.LOCAL]

        # settings インスタンスを取得
        settings = get_settings()

        # GitHub 同期システム
        self.github_sync = GitHubObsidianSync(
            vault_path=settings.obsidian_vault_path,
            github_token=settings.github_token,
            github_repo_url=settings.obsidian_backup_repo,
            github_branch=settings.obsidian_backup_branch,
            git_user_name=settings.git_user_name,
            git_user_email=settings.git_user_email,
        )

        # バックアップ対象ディレクトリ
        self.backup_sources = {
            "obsidian_vault": settings.obsidian_vault_path,
            "config": Path.cwd() / ".config",
            "logs": Path.cwd() / "logs",
        }

        # スケジューラータスクの初期化
        self._setup_scheduled_backup()

    def _setup_scheduled_backup(self) -> None:
        """定期バックアップスケジューラーセットアップ"""
        try:

            @tasks.loop(hours=self.backup_interval_hours)
            async def scheduled_backup() -> None:
                if self.auto_backup_enabled:
                    await self.run_backup(BackupType.INCREMENTAL, auto_triggered=True)

            self.scheduled_backup_task = scheduled_backup
            self.logger.info("Backup scheduler configured")

        except Exception as e:
            self.logger.error("Failed to setup backup scheduler", error=str(e))

    async def start(self) -> None:
        """バックアップシステム開始"""
        try:
            if self.auto_backup_enabled:
                self.scheduled_backup_task.start()
                self.logger.info("Automatic backup system started")
            else:
                self.logger.info("Backup system started (manual mode)")

        except Exception as e:
            self.logger.error(
                "Failed to start backup system", error=str(e), exc_info=True
            )

    async def stop(self) -> None:
        """バックアップシステム停止"""
        try:
            if hasattr(self, "scheduled_backup_task"):
                self.scheduled_backup_task.cancel()

            self.logger.info("Backup system stopped")

        except Exception as e:
            self.logger.error("Failed to stop backup system", error=str(e))

    async def run_backup(
        self,
        backup_type: BackupType = BackupType.FULL,
        destinations: list[BackupDestination] | None = None,
        auto_triggered: bool = False,
    ) -> dict[str, Any]:
        """バックアップ実行"""
        backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # 通知送信（開始）
            if self.notification_system and not auto_triggered:
                await self.notification_system.send_notification(
                    level=NotificationLevel.INFO,
                    category=NotificationCategory.SYSTEM_EVENTS,
                    title="💾 バックアップ開始",
                    message=f"データバックアップを開始します ({backup_type.value})",
                    details={"backup_id": backup_id, "type": backup_type.value},
                )

            backup_destinations = destinations or self.backup_destinations
            backup_result: dict[str, Any] = {
                "backup_id": backup_id,
                "type": backup_type.value,
                "start_time": datetime.now(),
                "status": BackupStatus.IN_PROGRESS.value,
                "destinations": [dest.value for dest in backup_destinations],
                "files_backed_up": 0,
                "total_size_mb": 0,
                "errors": [],
            }

            # バックアップ実行
            if backup_type == BackupType.FULL:
                backup_result.update(await self._run_full_backup(backup_id))
            elif backup_type == BackupType.INCREMENTAL:
                backup_result.update(await self._run_incremental_backup(backup_id))
            elif backup_type == BackupType.OBSIDIAN_ONLY:
                backup_result.update(await self._run_obsidian_backup(backup_id))
            elif backup_type == BackupType.CONFIG_ONLY:
                backup_result.update(await self._run_config_backup(backup_id))

            backup_result["end_time"] = datetime.now()
            end_time = backup_result["end_time"]
            start_time = backup_result["start_time"]
            if isinstance(end_time, datetime) and isinstance(start_time, datetime):
                backup_result["duration_seconds"] = (
                    end_time - start_time
                ).total_seconds()
            else:
                backup_result["duration_seconds"] = 0.0

            # バックアップ先への保存
            for destination in backup_destinations:
                try:
                    await self._save_to_destination(
                        backup_id, destination, backup_result
                    )
                except Exception as e:
                    errors = backup_result.get("errors", [])
                    if isinstance(errors, list):
                        errors.append(f"Destination {destination.value}: {str(e)}")
                        backup_result["errors"] = errors

            # 結果判定
            if backup_result["errors"]:
                backup_result["status"] = BackupStatus.PARTIAL.value
            else:
                backup_result["status"] = BackupStatus.SUCCESS.value

            # 履歴に記録
            self._record_backup(backup_result)

            # 古いバックアップファイルをクリーンアップ
            await self._cleanup_old_backups()

            # 通知送信（完了）
            if self.notification_system:
                await self._send_backup_completion_notification(
                    backup_result, auto_triggered
                )

            self.logger.info(
                "Backup completed",
                backup_id=backup_id,
                status=backup_result["status"],
                files_count=backup_result["files_backed_up"],
                size_mb=backup_result["total_size_mb"],
            )

            return backup_result

        except Exception as e:
            error_result = {
                "backup_id": backup_id,
                "type": backup_type.value,
                "start_time": datetime.now(),
                "status": BackupStatus.FAILED.value,
                "error": str(e),
            }

            self._record_backup(error_result)

            # エラー通知
            if self.notification_system:
                await self.notification_system.send_error_notification(
                    error_type="Backup Failed",
                    error_message=f"バックアップに失敗しました: {str(e)}",
                    context={"backup_id": backup_id, "type": backup_type.value},
                )

            self.logger.error(
                "Backup failed", backup_id=backup_id, error=str(e), exc_info=True
            )

            return error_result

    async def _run_full_backup(self, backup_id: str) -> dict[str, Any]:
        """フルバックアップ実行"""
        backup_path = self.backup_dir / f"{backup_id}_full.zip"
        files_backed_up = 0
        total_size = 0

        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for source_name, source_path in self.backup_sources.items():
                if source_path.exists():
                    if source_path.is_dir():
                        for file_path in source_path.rglob("*"):
                            if file_path.is_file():
                                try:
                                    arc_name = f"{source_name}/{file_path.relative_to(source_path)}"
                                    zip_file.write(file_path, arc_name)
                                    files_backed_up += 1
                                    total_size += file_path.stat().st_size
                                except Exception as e:
                                    self.logger.warning(
                                        f"Failed to backup file {file_path}: {e}"
                                    )
                    else:
                        try:
                            arc_name = f"{source_name}/{source_path.name}"
                            zip_file.write(source_path, arc_name)
                            files_backed_up += 1
                            total_size += source_path.stat().st_size
                        except Exception as e:
                            self.logger.warning(
                                f"Failed to backup file {source_path}: {e}"
                            )

        return {
            "backup_file": str(backup_path),
            "files_backed_up": files_backed_up,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }

    async def _run_incremental_backup(self, backup_id: str) -> dict[str, Any]:
        """増分バックアップ実行"""
        # 前回のバックアップ時間を取得
        last_backup_time = self._get_last_backup_time()

        backup_path = self.backup_dir / f"{backup_id}_incremental.zip"
        files_backed_up = 0
        total_size = 0

        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for source_name, source_path in self.backup_sources.items():
                if source_path.exists() and source_path.is_dir():
                    for file_path in source_path.rglob("*"):
                        if file_path.is_file():
                            try:
                                # ファイルの更新時間をチェック
                                file_mtime = datetime.fromtimestamp(
                                    file_path.stat().st_mtime
                                )
                                if (
                                    last_backup_time is None
                                    or file_mtime > last_backup_time
                                ):
                                    arc_name = f"{source_name}/{file_path.relative_to(source_path)}"
                                    zip_file.write(file_path, arc_name)
                                    files_backed_up += 1
                                    total_size += file_path.stat().st_size
                            except Exception as e:
                                self.logger.warning(
                                    f"Failed to backup file {file_path}: {e}"
                                )

        return {
            "backup_file": str(backup_path),
            "files_backed_up": files_backed_up,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "last_backup_time": (
                last_backup_time.isoformat() if last_backup_time else None
            ),
        }

    async def _run_obsidian_backup(self, backup_id: str) -> dict[str, Any]:
        """Obsidian 専用バックアップ"""
        backup_path = self.backup_dir / f"{backup_id}_obsidian.zip"
        files_backed_up = 0
        total_size = 0

        obsidian_path = self.backup_sources.get("obsidian_vault")
        if not obsidian_path or not obsidian_path.exists():
            return {
                "backup_file": str(backup_path),
                "files_backed_up": 0,
                "total_size_mb": 0,
                "error": "Obsidian vault path not found",
            }

        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in obsidian_path.rglob("*"):
                if file_path.is_file():
                    try:
                        arc_name = str(file_path.relative_to(obsidian_path))
                        zip_file.write(file_path, arc_name)
                        files_backed_up += 1
                        total_size += file_path.stat().st_size
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to backup Obsidian file {file_path}: {e}"
                        )

        return {
            "backup_file": str(backup_path),
            "files_backed_up": files_backed_up,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }

    async def _run_config_backup(self, backup_id: str) -> dict[str, Any]:
        """設定専用バックアップ"""
        backup_path = self.backup_dir / f"{backup_id}_config.zip"
        files_backed_up = 0
        total_size = 0

        config_path = self.backup_sources.get("config")
        if not config_path or not config_path.exists():
            return {
                "backup_file": str(backup_path),
                "files_backed_up": 0,
                "total_size_mb": 0,
                "error": "Config path not found",
            }

        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in config_path.rglob("*"):
                if file_path.is_file():
                    try:
                        arc_name = str(file_path.relative_to(config_path))
                        zip_file.write(file_path, arc_name)
                        files_backed_up += 1
                        total_size += file_path.stat().st_size
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to backup config file {file_path}: {e}"
                        )

        # 追加設定ファイル
        additional_configs = [".env", ".env.development", "pyproject.toml"]
        for config_file in additional_configs:
            config_file_path = Path.cwd() / config_file
            if config_file_path.exists():
                try:
                    zip_file.write(config_file_path, config_file)
                    files_backed_up += 1
                    total_size += config_file_path.stat().st_size
                except Exception as e:
                    self.logger.warning(
                        f"Failed to backup config file {config_file_path}: {e}"
                    )

        return {
            "backup_file": str(backup_path),
            "files_backed_up": files_backed_up,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }

    async def _save_to_destination(
        self,
        backup_id: str,
        destination: BackupDestination,
        backup_result: dict[str, Any],
    ) -> None:
        """バックアップ先への保存"""
        if destination == BackupDestination.LOCAL:
            # ローカル保存は既に完了
            pass
        elif destination == BackupDestination.CLOUD_STORAGE:
            # クラウドストレージへの保存（未実装）
            self.logger.info(f"Cloud storage backup not implemented for {backup_id}")
        elif destination == BackupDestination.GITHUB:
            # GitHub への保存
            await self._save_to_github(backup_id, backup_result)

    async def restore_backup(
        self, backup_id: str, target_directory: Path | None = None
    ) -> dict[str, Any]:
        """バックアップからの復元"""
        try:
            # バックアップファイルを検索
            backup_files = list(self.backup_dir.glob(f"{backup_id}*"))
            if not backup_files:
                return {"error": f"Backup {backup_id} not found"}

            backup_file = backup_files[0]
            restore_target = target_directory or Path.cwd() / "restore" / backup_id
            restore_target.mkdir(parents=True, exist_ok=True)

            files_restored = 0

            with zipfile.ZipFile(backup_file, "r") as zip_file:
                zip_file.extractall(restore_target)
                files_restored = len(zip_file.namelist())

            restore_result = {
                "backup_id": backup_id,
                "restore_path": str(restore_target),
                "files_restored": files_restored,
                "status": "success",
                "timestamp": datetime.now().isoformat(),
            }

            self.logger.info(
                "Backup restored",
                backup_id=backup_id,
                files_restored=files_restored,
                restore_path=str(restore_target),
            )

            return restore_result

        except Exception as e:
            self.logger.error(f"Backup restore failed: {e}", exc_info=True)
            return {"error": str(e)}

    async def _cleanup_old_backups(self) -> None:
        """古いバックアップファイルのクリーンアップ"""
        try:
            backup_files = sorted(
                self.backup_dir.glob("backup_*.zip"),
                key=lambda f: f.stat().st_mtime,
                reverse=True,
            )

            if len(backup_files) > self.max_backup_files:
                files_to_remove = backup_files[self.max_backup_files :]
                for file_to_remove in files_to_remove:
                    try:
                        file_to_remove.unlink()
                        self.logger.info(f"Removed old backup: {file_to_remove.name}")
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to remove old backup {file_to_remove}: {e}"
                        )

        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}")

    def _get_last_backup_time(self) -> datetime | None:
        """最後のバックアップ時間を取得"""
        if not self.backup_history:
            return None

        successful_backups = [
            backup
            for backup in self.backup_history
            if backup.get("status") == BackupStatus.SUCCESS.value
        ]

        if not successful_backups:
            return None

        last_backup = max(successful_backups, key=lambda x: x["start_time"])
        start_time = last_backup["start_time"]
        if isinstance(start_time, datetime):
            return start_time
        if isinstance(start_time, str):
            return datetime.fromisoformat(start_time)
        return None

    async def _send_backup_completion_notification(
        self, backup_result: dict[str, Any], auto_triggered: bool
    ) -> None:
        """バックアップ完了通知"""
        if auto_triggered and backup_result["status"] == BackupStatus.SUCCESS.value:
            # 自動バックアップが成功した場合は詳細通知をスキップ
            return

        if not self.notification_system:
            return

        if backup_result["status"] == BackupStatus.SUCCESS.value:
            title = "✅ バックアップ完了"
            message = "データバックアップが正常に完了しました。"
            level = NotificationLevel.SUCCESS
        elif backup_result["status"] == BackupStatus.PARTIAL.value:
            title = "⚠️ バックアップ部分完了"
            message = "データバックアップが部分的に完了しました（一部エラーあり）。"
            level = NotificationLevel.WARNING
        else:
            title = "❌ バックアップ失敗"
            message = "データバックアップに失敗しました。"
            level = NotificationLevel.ERROR

        embed_fields = [
            {
                "name": "📊 統計情報",
                "value": (
                    f"ファイル数: {backup_result.get('files_backed_up', 0)}件\n"
                    f"サイズ: {backup_result.get('total_size_mb', 0)}MB\n"
                    f"所要時間: {backup_result.get('duration_seconds', 0):.1f}秒"
                ),
                "inline": False,
            }
        ]

        if backup_result.get("errors"):
            embed_fields.append(
                {
                    "name": "⚠️ エラー詳細",
                    "value": "\n".join(backup_result["errors"][:3]),
                    "inline": False,
                }
            )

        await self.notification_system.send_notification(
            level=level,
            category=NotificationCategory.SYSTEM_EVENTS,
            title=title,
            message=message,
            details=backup_result,
            embed_fields=embed_fields,
        )

    def _record_backup(self, backup_result: dict[str, Any]) -> None:
        """バックアップ履歴記録"""
        # datetime オブジェクトを文字列に変換
        serializable_result = backup_result.copy()
        for key in ["start_time", "end_time"]:
            if key in serializable_result and isinstance(
                serializable_result[key], datetime
            ):
                serializable_result[key] = serializable_result[key].isoformat()

        self.backup_history.append(serializable_result)

    async def _save_to_github(
        self, backup_id: str, backup_result: dict[str, Any]
    ) -> None:
        """GitHub への保存"""
        try:
            commit_message = (
                f"Backup: {backup_id} - {backup_result.get('files_backed_up', 0)} files"
            )
            success = await self.github_sync.sync_to_github(commit_message)

            if success:
                self.logger.info(f"Successfully saved backup {backup_id} to GitHub")
            else:
                self.logger.warning(f"Failed to save backup {backup_id} to GitHub")

        except Exception as e:
            self.logger.error(f"GitHub backup failed for {backup_id}: {e}")
            raise

        # 履歴サイズ制限
        if len(self.backup_history) > 50:
            self.backup_history = self.backup_history[-50:]

    def get_backup_status(self) -> dict[str, Any]:
        """バックアップシステムの状態取得"""
        try:
            recent_backups = self.backup_history[-5:] if self.backup_history else []
            successful_backups = len(
                [
                    b
                    for b in self.backup_history
                    if b.get("status") == BackupStatus.SUCCESS.value
                ]
            )

            backup_files = list(self.backup_dir.glob("backup_*.zip"))
            total_backup_size = sum([f.stat().st_size for f in backup_files]) / (
                1024 * 1024
            )

            return {
                "auto_backup_enabled": self.auto_backup_enabled,
                "backup_interval_hours": self.backup_interval_hours,
                "total_backups": len(self.backup_history),
                "successful_backups": successful_backups,
                "recent_backups": recent_backups,
                "backup_files_count": len(backup_files),
                "total_backup_size_mb": round(total_backup_size, 2),
                "last_backup": self.backup_history[-1] if self.backup_history else None,
                "backup_destinations": [
                    dest.value for dest in self.backup_destinations
                ],
            }

        except Exception as e:
            self.logger.error("Failed to get backup status", error=str(e))
            return {"error": "バックアップ状態の取得に失敗しました"}

    def get_backup_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """バックアップ履歴取得"""
        return self.backup_history[-limit:] if self.backup_history else []

    async def configure_backup(self, config: dict[str, Any]) -> bool:
        """バックアップ設定更新"""
        try:
            if "auto_backup_enabled" in config:
                old_enabled = self.auto_backup_enabled
                self.auto_backup_enabled = config["auto_backup_enabled"]

                # 自動バックアップのスタート/ストップ
                if self.auto_backup_enabled and not old_enabled:
                    self.scheduled_backup_task.start()
                elif not self.auto_backup_enabled and old_enabled:
                    self.scheduled_backup_task.cancel()

            if "backup_interval_hours" in config:
                self.backup_interval_hours = max(
                    1, int(config["backup_interval_hours"])
                )
                # タスクを再起動
                if self.auto_backup_enabled:
                    self.scheduled_backup_task.cancel()
                    self._setup_scheduled_backup()
                    self.scheduled_backup_task.start()

            if "max_backup_files" in config:
                self.max_backup_files = max(1, int(config["max_backup_files"]))

            self.logger.info("Backup configuration updated", config=config)
            return True

        except Exception as e:
            self.logger.error("Failed to configure backup", error=str(e))
            return False
