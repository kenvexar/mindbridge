"""
Obsidian vault organization and maintenance
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from src.obsidian.file_manager import ObsidianFileManager
from src.obsidian.models import (
    FolderMapping,
    NoteStatus,
    ObsidianNote,
    VaultFolder,
)
from src.utils.mixins import LoggerMixin

# 旧テンプレートシステムは削除済み
# from src.templates import DailyNoteTemplate


class VaultOrganizer(LoggerMixin):
    """Obsidian vault organization and maintenance"""

    def __init__(self, file_manager: ObsidianFileManager):
        """
        Initialize OrganizeManager

        Args:
            file_manager: ObsidianFileManager instance
        """
        self.file_manager = file_manager
        # TemplateEngine を使用するように変更
        from src.obsidian.daily_integration import DailyNoteIntegration
        from src.obsidian.template_system import TemplateEngine

        self.template_engine = TemplateEngine(file_manager.vault_path)
        self.daily_integration = DailyNoteIntegration(file_manager)
        self.logger.info("Organize manager initialized")

    async def organize_notes_by_category(self, dry_run: bool = False) -> dict[str, Any]:
        """
        カテゴリに基づいてノートを整理（改善版：階層構造対応）

        Args:
            dry_run: 実際の移動を行わずに計画のみ表示

        Returns:
            整理結果の統計
        """
        try:
            self.logger.info(
                "Starting enhanced note organization by category", dry_run=dry_run
            )

            results: dict[str, Any] = {
                "processed": 0,
                "moved": 0,
                "errors": 0,
                "movements": [],
                "hierarchical_moves": 0,
            }

            # 受信箱及び未処理フォルダのノートを取得
            folders_to_process = [
                VaultFolder.INBOX,
                VaultFolder.INBOX_UNPROCESSED,
                VaultFolder.INBOX_PENDING,
                VaultFolder.INBOX_STAGED,
            ]

            for folder in folders_to_process:
                try:
                    folder_notes = await self.file_manager.search_notes(
                        folder=folder.value, limit=1000
                    )
                except Exception:
                    # フォルダが存在しない場合はスキップ
                    continue

                for note_result in folder_notes:
                    results["processed"] += 1

                    try:
                        # Load the actual note object
                        note = await self.file_manager.load_note(
                            Path(note_result["file_path"])
                        )
                        if not note:
                            continue
                        # AI 分類結果に基づいて移動先を決定（改善版）
                        target_folder = None
                        subcategory = None

                        if note.frontmatter.ai_category:
                            # AI 分類結果からフォルダを決定
                            from src.ai.models import ProcessingCategory

                            try:
                                category = ProcessingCategory(
                                    note.frontmatter.ai_category
                                )

                                # サブカテゴリがある場合は優先
                                if (
                                    hasattr(note.frontmatter, "ai_subcategory")
                                    and note.frontmatter.ai_subcategory
                                ):
                                    subcategory = note.frontmatter.ai_subcategory

                                # 階層構造対応の分類
                                target_folder = FolderMapping.get_folder_for_category(
                                    category.value, subcategory
                                )

                                if subcategory:
                                    results["hierarchical_moves"] += 1

                            except ValueError:
                                self.logger.warning(
                                    "Unknown AI category",
                                    category=note.frontmatter.ai_category,
                                    note_path=str(note.file_path),
                                )

                        # タグベースの分類も考慮
                        if (
                            not target_folder
                            and hasattr(note.frontmatter, "ai_tags")
                            and note.frontmatter.ai_tags
                        ):
                            tags = note.frontmatter.ai_tags
                            if isinstance(tags, list) and tags:
                                # 最初のタグを使用してフォルダを決定
                                first_tag = tags[0].lstrip("#")
                                target_folder = FolderMapping.get_folder_for_category(
                                    first_tag
                                )

                        # 移動先が決定された場合
                        if target_folder and target_folder != VaultFolder.INBOX:
                            new_path = (
                                self.file_manager.vault_path
                                / target_folder.value
                                / note.filename
                            )

                            movement_info = {
                                "note_title": note.title,
                                "from_path": str(
                                    note.file_path.relative_to(
                                        self.file_manager.vault_path
                                    )
                                ),
                                "to_path": str(
                                    new_path.relative_to(self.file_manager.vault_path)
                                ),
                                "category": note.frontmatter.ai_category,
                                "subcategory": subcategory,
                                "confidence": note.frontmatter.ai_confidence,
                                "tags": getattr(note.frontmatter, "ai_tags", []),
                            }

                            results["movements"].append(movement_info)

                            if not dry_run:
                                # 実際の移動実行
                                success = await self._move_note_enhanced(
                                    note, new_path, target_folder
                                )
                                if success:
                                    results["moved"] += 1
                                else:
                                    results["errors"] += 1
                            else:
                                results["moved"] += 1

                    except Exception as e:
                        results["errors"] += 1
                        self.logger.error(
                            "Error processing note for organization",
                            note_path=str(note.file_path) if note else "Unknown",
                            error=str(e),
                            exc_info=True,
                        )

            self.logger.info(
                "Enhanced note organization completed",
                processed=results["processed"],
                moved=results["moved"],
                hierarchical_moves=results["hierarchical_moves"],
                errors=results["errors"],
                dry_run=dry_run,
            )

            return results

        except Exception as e:
            self.logger.error(
                "Failed to organize notes by category", error=str(e), exc_info=True
            )
            return {
                "processed": 0,
                "moved": 0,
                "errors": 1,
                "movements": [],
                "hierarchical_moves": 0,
            }

    async def create_daily_note(
        self, date: datetime | None = None
    ) -> ObsidianNote | None:
        """
        日次ノートを作成または更新

        Args:
            date: 対象日（指定されない場合は今日）

        Returns:
            作成された日次ノート
        """
        try:
            if not date:
                date = datetime.now()

            # その日の統計情報を収集
            daily_stats = await self._collect_daily_stats(date)

            # 日次ノートを生成 (新しい API に対応)
            date_str = date.strftime("%Y-%m-%d")
            daily_note_dict = await self.template_engine.generate_daily_note(date_str)

            if daily_note_dict is None:
                self.logger.error(
                    "Failed to generate daily note", date=date.strftime("%Y-%m-%d")
                )
                return None

            # Convert dict result to ObsidianNote
            from pathlib import Path

            from src.obsidian.models import NoteFrontmatter, ObsidianNote

            # Handle GeneratedNote object
            if hasattr(daily_note_dict, "filename"):
                note_filename = daily_note_dict.filename
                note_content = daily_note_dict.content
                note_folder = "01_DailyNotes"  # Default folder for daily notes
            else:
                # Fallback for dict format
                note_filename = f"{daily_note_dict.get('title', 'untitled')}.md"  # type: ignore
                note_content = daily_note_dict.get("content", "")  # type: ignore
                note_folder = daily_note_dict.get("folder", "01_DailyNotes")  # type: ignore

            daily_note_path = (
                Path(self.file_manager.vault_path) / note_folder / note_filename
            )
            daily_note = ObsidianNote(
                filename=note_filename,
                file_path=daily_note_path,
                frontmatter=NoteFrontmatter(obsidian_folder=note_folder),
                content=note_content,
            )

            # 既存の日次ノートをチェック
            existing_note = None
            if daily_note.file_path.exists():
                existing_note = await self.file_manager.load_note(daily_note.file_path)

            # ノートの保存/更新
            if existing_note is not None:
                # 既存ノートの更新
                existing_note.content = daily_note.content
                existing_note.frontmatter.modified = datetime.now().isoformat()

                # 統計情報の更新
                existing_note.frontmatter.total_messages = daily_stats.get(
                    "total_messages", 0
                )
                existing_note.frontmatter.processed_messages = daily_stats.get(
                    "processed_messages", 0
                )
                existing_note.frontmatter.ai_processing_time_total = daily_stats.get(
                    "ai_processing_time_total", 0
                )
                existing_note.frontmatter.categories = daily_stats.get("categories", {})

                success = await self.file_manager.update_note(
                    existing_note.file_path, existing_note
                )
                if success:
                    self.logger.info(
                        "Daily note updated", date=date.strftime("%Y-%m-%d")
                    )
                    return existing_note
            else:
                # 新規作成
                saved_path = await self.file_manager.save_note(daily_note)
                if saved_path:
                    self.logger.info(
                        "Daily note created", date=date.strftime("%Y-%m-%d")
                    )
                    return daily_note

            return None

        except Exception as e:
            self.logger.error(
                "Failed to create daily note",
                date=date.strftime("%Y-%m-%d") if date else "today",
                error=str(e),
                exc_info=True,
            )
            return None

    async def archive_old_notes(
        self, days_old: int = 365, dry_run: bool = False
    ) -> dict[str, Any]:
        """
        古いノートをアーカイブ

        Args:
            days_old: アーカイブ対象の日数
            dry_run: 実際のアーカイブを行わずに計画のみ表示

        Returns:
            アーカイブ結果の統計
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)

            self.logger.info(
                "Starting old notes archival",
                cutoff_date=cutoff_date.strftime("%Y-%m-%d"),
                dry_run=dry_run,
            )

            results: dict[str, Any] = {
                "processed": 0,
                "archived": 0,
                "errors": 0,
                "archived_notes": [],
            }

            # 全ノートを検索（アーカイブフォルダ以外）
            for folder in [
                VaultFolder.INBOX,
                VaultFolder.PROJECTS,
                VaultFolder.DAILY_NOTES,
                VaultFolder.IDEAS,
                VaultFolder.FINANCE,
                VaultFolder.TASKS,
                VaultFolder.HEALTH,
            ]:
                notes = await self.file_manager.search_notes(
                    folder=folder.value, date_to=cutoff_date.isoformat(), limit=1000
                )

                for note_result in notes:
                    results["processed"] += 1

                    try:
                        # Load the actual note object
                        note = await self.file_manager.load_note(
                            Path(note_result["file_path"])
                        )
                        if not note:
                            continue
                        # アクティブなノートのみアーカイブ対象
                        if note.frontmatter.status == NoteStatus.ACTIVE:
                            archive_info = {
                                "title": note.title,
                                "path": str(
                                    note.file_path.relative_to(
                                        self.file_manager.vault_path
                                    )
                                ),
                                "created_date": note.created_at.strftime("%Y-%m-%d"),
                                "category": note.frontmatter.ai_category,
                            }

                            results["archived_notes"].append(archive_info)

                            if not dry_run:
                                # ステータスをアーカイブに変更
                                note.frontmatter.status = NoteStatus.ARCHIVED

                                # アーカイブフォルダに移動
                                success = await self.file_manager.delete_note(
                                    note.file_path, backup=True
                                )

                                if success:
                                    results["archived"] += 1
                                else:
                                    results["errors"] += 1
                            else:
                                results["archived"] += 1

                    except Exception as e:
                        results["errors"] += 1
                        self.logger.error(
                            "Error processing note for archival",
                            note_path=str(note.file_path) if note else "Unknown",
                            error=str(e),
                            exc_info=True,
                        )

            self.logger.info(
                "Old notes archival completed",
                processed=results["processed"],
                archived=results["archived"],
                errors=results["errors"],
                dry_run=dry_run,
            )

            return results

        except Exception as e:
            self.logger.error(
                "Failed to archive old notes", error=str(e), exc_info=True
            )
            return {"processed": 0, "archived": 0, "errors": 1, "archived_notes": []}

    async def cleanup_empty_folders(self, dry_run: bool = False) -> dict[str, Any]:
        """
        空のフォルダを削除

        Args:
            dry_run: 実際の削除を行わずに計画のみ表示

        Returns:
            クリーンアップ結果
        """
        try:
            self.logger.info("Starting empty folder cleanup", dry_run=dry_run)

            results: dict[str, Any] = {
                "processed": 0,
                "removed": 0,
                "errors": 0,
                "removed_folders": [],
            }

            # Vault 内の全フォルダを検索
            for folder_path in self.file_manager.vault_path.rglob("*"):
                if not folder_path.is_dir():
                    continue

                # 重要なフォルダは除外
                if self._is_protected_folder(folder_path):
                    continue

                results["processed"] += 1

                try:
                    # フォルダが空かチェック
                    if self._is_folder_empty(folder_path):
                        folder_info = {
                            "path": str(
                                folder_path.relative_to(self.file_manager.vault_path)
                            )
                        }

                        results["removed_folders"].append(folder_info)

                        if not dry_run:
                            folder_path.rmdir()
                            self.logger.debug(
                                "Empty folder removed", path=str(folder_path)
                            )

                        results["removed"] += 1

                except Exception as e:
                    results["errors"] += 1
                    self.logger.error(
                        "Error processing folder for cleanup",
                        folder_path=str(folder_path),
                        error=str(e),
                        exc_info=True,
                    )

            self.logger.info(
                "Empty folder cleanup completed",
                processed=results["processed"],
                removed=results["removed"],
                errors=results["errors"],
                dry_run=dry_run,
            )

            return results

        except Exception as e:
            self.logger.error(
                "Failed to cleanup empty folders", error=str(e), exc_info=True
            )
            return {"processed": 0, "removed": 0, "errors": 1, "removed_folders": []}

    async def optimize_vault_structure(self, dry_run: bool = False) -> dict[str, Any]:
        """
        Vault 構造の最適化

        Args:
            dry_run: 実際の最適化を行わずに計画のみ表示

        Returns:
            最適化結果
        """
        try:
            self.logger.info("Starting vault structure optimization", dry_run=dry_run)

            results: dict[str, Any] = {
                "organization": {},
                "archival": {},
                "cleanup": {},
                "daily_notes_created": 0,
            }

            # 1. ノートの整理
            results["organization"] = await self.organize_notes_by_category(
                dry_run=dry_run
            )

            # 2. 古いノートのアーカイブ
            results["archival"] = await self.archive_old_notes(
                days_old=365, dry_run=dry_run
            )

            # 3. 空フォルダのクリーンアップ
            results["cleanup"] = await self.cleanup_empty_folders(dry_run=dry_run)

            # 4. 過去 1 週間の日次ノート作成
            for i in range(7):
                date = datetime.now() - timedelta(days=i)
                daily_note = await self.create_daily_note(date)
                if daily_note:
                    results["daily_notes_created"] += 1

            self.logger.info(
                "Vault optimization completed",
                organization_moved=results["organization"]["moved"],
                archived=results["archival"]["archived"],
                cleaned_folders=results["cleanup"]["removed"],
                daily_notes=results["daily_notes_created"],
                dry_run=dry_run,
            )

            return results

        except Exception as e:
            self.logger.error(
                "Failed to optimize vault structure", error=str(e), exc_info=True
            )
            return {
                "organization": {"moved": 0, "errors": 1},
                "archival": {"archived": 0, "errors": 1},
                "cleanup": {"removed": 0, "errors": 1},
                "daily_notes_created": 0,
            }

    async def create_folder_structure(self, dry_run: bool = False) -> dict[str, Any]:
        """
        新しいフォルダ構造を作成

        Args:
            dry_run: 実際の作成を行わずに計画のみ表示

        Returns:
            作成結果の統計
        """
        try:
            self.logger.info("Creating enhanced folder structure", dry_run=dry_run)

            results: dict[str, Any] = {
                "created_folders": [],
                "existing_folders": [],
                "errors": 0,
            }

            # 作成するフォルダリスト
            folders_to_create = [
                # Enhanced Inbox structure
                VaultFolder.INBOX_UNPROCESSED,
                VaultFolder.INBOX_PENDING,
                VaultFolder.INBOX_STAGED,
                # Enhanced Projects structure
                VaultFolder.PROJECTS_ACTIVE,
                VaultFolder.PROJECTS_PLANNING,
                VaultFolder.PROJECTS_ON_HOLD,
                VaultFolder.PROJECTS_COMPLETED,
                # Enhanced Finance structure
                VaultFolder.FINANCE_EXPENSES,
                VaultFolder.FINANCE_INCOME,
                VaultFolder.FINANCE_SUBSCRIPTIONS,
                VaultFolder.FINANCE_BUDGETS,
                VaultFolder.FINANCE_REPORTS,
                # Enhanced Tasks structure
                VaultFolder.TASKS_BACKLOG,
                VaultFolder.TASKS_ACTIVE,
                VaultFolder.TASKS_WAITING,
                VaultFolder.TASKS_COMPLETED,
                VaultFolder.TASKS_TEMPLATES,
                # Enhanced Health structure
                VaultFolder.HEALTH_ACTIVITIES,
                VaultFolder.HEALTH_SLEEP,
                VaultFolder.HEALTH_WELLNESS,
                VaultFolder.HEALTH_MEDICAL,
                VaultFolder.HEALTH_ANALYTICS,
                # New Knowledge structure
                VaultFolder.KNOWLEDGE,
                VaultFolder.KNOWLEDGE_TECHNICAL,
                VaultFolder.KNOWLEDGE_PROCESSES,
                VaultFolder.KNOWLEDGE_TOOLS,
                VaultFolder.KNOWLEDGE_LEARNINGS,
            ]

            for folder in folders_to_create:
                try:
                    folder_path = self.file_manager.vault_path / folder.value

                    if folder_path.exists():
                        results["existing_folders"].append(folder.value)
                        self.logger.debug("Folder already exists", path=folder.value)
                    else:
                        if not dry_run:
                            folder_path.mkdir(parents=True, exist_ok=True)
                            # .gitkeep ファイルを作成して空フォルダを保持
                            gitkeep_path = folder_path / ".gitkeep"
                            gitkeep_path.touch()

                        results["created_folders"].append(folder.value)
                        self.logger.info("Created folder", path=folder.value)

                except Exception as e:
                    results["errors"] += 1
                    self.logger.error(
                        "Failed to create folder",
                        folder=folder.value,
                        error=str(e),
                        exc_info=True,
                    )

            self.logger.info(
                "Folder structure creation completed",
                created=len(results["created_folders"]),
                existing=len(results["existing_folders"]),
                errors=results["errors"],
                dry_run=dry_run,
            )

            return results

        except Exception as e:
            self.logger.error(
                "Failed to create folder structure", error=str(e), exc_info=True
            )
            return {
                "created_folders": [],
                "existing_folders": [],
                "errors": 1,
            }

    async def _move_note(self, note: ObsidianNote, new_path: Path) -> bool:
        """ノートを移動"""
        try:
            # 移動先ディレクトリの作成
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # ファイル移動
            note.file_path.rename(new_path)

            # ノートオブジェクトのパス更新
            note.file_path = new_path
            note.frontmatter.obsidian_folder = str(
                new_path.parent.relative_to(self.file_manager.vault_path)
            )
            note.frontmatter.modified = datetime.now().isoformat()

            # フロントマターの更新
            await self.file_manager.update_note(note.file_path, note)

            self.logger.debug(
                "Note moved successfully",
                old_path=str(note.file_path),
                new_path=str(new_path),
            )
            return True

        except Exception as e:
            self.logger.error(
                "Failed to move note",
                note_path=str(note.file_path),
                new_path=str(new_path),
                error=str(e),
                exc_info=True,
            )
            return False

    async def _move_note_enhanced(
        self, note: ObsidianNote, new_path: Path, target_folder: VaultFolder
    ) -> bool:
        """ノートを移動（階層構造対応版）"""
        try:
            # 移動先ディレクトリの作成（階層構造も含む）
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # ファイル移動
            note.file_path.rename(new_path)

            # ノートオブジェクトのパス更新
            note.file_path = new_path
            note.frontmatter.obsidian_folder = str(
                new_path.parent.relative_to(self.file_manager.vault_path)
            )
            note.frontmatter.modified = datetime.now().isoformat()

            # 階層構造メタデータの追加
            note.frontmatter.vault_hierarchy = target_folder.value
            if (
                hasattr(note.frontmatter, "ai_subcategory")
                and note.frontmatter.ai_subcategory
            ):
                note.frontmatter.organization_level = "subcategory"
            else:
                note.frontmatter.organization_level = "category"

            # フロントマターの更新
            await self.file_manager.update_note(note.file_path, note)

            self.logger.debug(
                "Note moved successfully with enhanced structure",
                old_path=str(note.file_path),
                new_path=str(new_path),
                hierarchy=target_folder.value,
            )
            return True

        except Exception as e:
            self.logger.error(
                "Failed to move note with enhanced structure",
                note_path=str(note.file_path),
                new_path=str(new_path),
                error=str(e),
                exc_info=True,
            )
            return False

    async def _collect_daily_stats(self, date: datetime) -> dict[str, Any]:
        """指定日の統計情報を収集"""
        try:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)

            # その日のノートを検索
            daily_notes = await self.file_manager.search_notes(
                date_from=start_date.isoformat(),
                date_to=end_date.isoformat(),
                limit=1000,
            )

            stats = {
                "total_messages": len(daily_notes),
                "processed_messages": 0,
                "ai_processing_time_total": 0,
                "categories": {},
                "tags": {},
                "attachments": [],
            }

            for note_result in daily_notes:
                # Load the actual note object
                note = await self.file_manager.load_note(Path(note_result["file_path"]))
                if not note:
                    continue
                # AI 処理済みノートの統計
                if (
                    hasattr(note.frontmatter, "ai_processed")
                    and note.frontmatter.ai_processed
                ):
                    if isinstance(stats["processed_messages"], int):
                        stats["processed_messages"] += 1

                    if (
                        hasattr(note.frontmatter, "ai_processing_time")
                        and note.frontmatter.ai_processing_time
                        and isinstance(stats["ai_processing_time_total"], int)
                    ):
                        stats["ai_processing_time_total"] += int(
                            note.frontmatter.ai_processing_time
                        )

                # カテゴリ統計
                if (
                    hasattr(note.frontmatter, "ai_category")
                    and note.frontmatter.ai_category
                ):
                    category = str(note.frontmatter.ai_category)
                    if isinstance(stats["categories"], dict):
                        stats["categories"][category] = (
                            stats["categories"].get(category, 0) + 1
                        )

                # タグ統計
                ai_tags = getattr(note.frontmatter, "ai_tags", []) or []
                tags = getattr(note.frontmatter, "tags", []) or []
                for tag in ai_tags + tags:
                    clean_tag = str(tag).lstrip("#")
                    if isinstance(stats["tags"], dict):
                        stats["tags"][clean_tag] = stats["tags"].get(clean_tag, 0) + 1

            # タグを頻度順にソート
            if isinstance(stats["tags"], dict):
                sorted_tags = sorted(
                    stats["tags"].items(), key=lambda x: x[1], reverse=True
                )[:10]
                stats["tags"] = [f"{tag}({count})" for tag, count in sorted_tags]

            return stats

        except Exception as e:
            self.logger.error(
                "Failed to collect daily stats",
                date=date.strftime("%Y-%m-%d"),
                error=str(e),
                exc_info=True,
            )
            return {
                "total_messages": 0,
                "processed_messages": 0,
                "ai_processing_time_total": 0,
                "categories": {},
                "tags": [],
                "attachments": [],
            }

    def _is_protected_folder(self, folder_path: Path) -> bool:
        """保護されたフォルダかチェック"""
        protected_folders = {
            VaultFolder.INBOX.value,
            VaultFolder.PROJECTS.value,
            VaultFolder.DAILY_NOTES.value,
            VaultFolder.IDEAS.value,
            VaultFolder.ARCHIVE.value,
            VaultFolder.RESOURCES.value,
            VaultFolder.FINANCE.value,
            VaultFolder.TASKS.value,
            VaultFolder.HEALTH.value,
            VaultFolder.META.value,
            VaultFolder.TEMPLATES.value,
            VaultFolder.ATTACHMENTS.value,
        }

        relative_path = str(folder_path.relative_to(self.file_manager.vault_path))

        # 保護されたフォルダまたはその直下のフォルダ
        for protected in protected_folders:
            if relative_path == protected or relative_path.startswith(f"{protected}/"):
                return True

        return False

    def _is_folder_empty(self, folder_path: Path) -> bool:
        """フォルダが空かチェック"""
        try:
            # フォルダ内にファイルまたはフォルダがあるかチェック
            for _item in folder_path.iterdir():
                return False  # 何かがあれば空ではない
            return True  # 何もなければ空
        except OSError:
            return False  # アクセスエラーの場合は空ではないとみなす
