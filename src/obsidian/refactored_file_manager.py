"""Refactored Obsidian file manager using modular components."""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import structlog

from ..config import get_settings
from ..utils.mixins import LoggerMixin
from .analytics import VaultStatistics
from .backup import BackupConfig, BackupManager
from .core import FileOperations, VaultManager
from .models import FileOperation, ObsidianNote
from .search import NoteSearch, SearchCriteria

logger = structlog.get_logger(__name__)


class ObsidianFileManager(LoggerMixin):
    """
    Unified file manager that orchestrates modular components.

    This class follows the Single Responsibility Principle by delegating
    specific tasks to specialized components while maintaining backward compatibility.
    """

    def __init__(
        self, vault_path: Path | str | None = None, enable_local_data: bool = True
    ):
        """
        Initialize Obsidian file manager with full backward compatibility.

        Args:
            vault_path: Path to Obsidian vault (defaults to settings)
            enable_local_data: ローカルデータ管理を有効にするか
        """
        if vault_path:
            self.vault_path = Path(vault_path)
        else:
            settings = get_settings()
            self.vault_path = settings.obsidian_vault_path

        # 操作履歴 (backward compatibility)
        self.operation_history: list[FileOperation] = []

        # キャッシュ (backward compatibility)
        self._folder_cache: set[Path] = set()
        self._stats_cache: Any | None = None
        self._stats_cache_time: datetime | None = None

        # ローカルデータ管理 (backward compatibility)
        self.local_data_manager = None
        if enable_local_data:
            try:
                from .local_data_manager import LocalDataManager

                self.local_data_manager = LocalDataManager(self.vault_path)
            except ImportError:
                self.logger.warning("Local data manager not available")

        # Initialize modern components
        self.file_operations = FileOperations(self.vault_path)
        self.vault_manager = VaultManager(self.vault_path)
        self.note_search = NoteSearch(self.vault_path)
        self.statistics = VaultStatistics(self.vault_path)

        # Initialize backup manager with default config
        backup_config = BackupConfig(
            backup_directory=self.vault_path.parent / "backups",
            max_backups=10,
            compress=True,
        )
        self.backup_manager = BackupManager(self.vault_path, backup_config)

        self.logger.info(
            "Unified Obsidian file manager initialized",
            vault_path=str(self.vault_path),
            local_data_enabled=enable_local_data,
        )

    # Vault Management
    async def initialize_vault(self) -> bool:
        """Initialize vault structure and templates."""
        return await self.vault_manager.initialize_vault()

    # File Operations
    async def save_note(
        self, note: ObsidianNote, subfolder: str | None = None, overwrite: bool = False
    ) -> bool:
        """Save a note to the vault."""
        try:
            # For now, ignore the overwrite parameter as the file_operations doesn't support it
            await self.file_operations.save_note(note, subfolder)
            # Invalidate stats cache when adding new notes
            self.statistics.invalidate_cache()
            return True
        except Exception:
            return False

    async def load_note(self, file_path: Path) -> ObsidianNote | None:
        """Load a note from the vault."""
        return await self.file_operations.load_note(file_path)

    async def update_note(self, file_path: Path, note: ObsidianNote) -> bool:
        """Update an existing note."""
        success = await self.file_operations.update_note(file_path, note)
        if success:
            self.statistics.invalidate_cache()
        return success

    async def append_to_note(
        self,
        file_path: Path,
        content: str,
        section_header: str | None = None,
    ) -> bool:
        """Append content to an existing note."""
        success = await self.file_operations.append_to_note(
            file_path, content, section_header
        )
        if success:
            self.statistics.invalidate_cache()
        return success

    async def delete_note(self, file_path: Path, backup: bool = True) -> bool:
        """Delete a note from the vault."""
        success = await self.file_operations.delete_note(file_path, backup)
        if success:
            self.statistics.invalidate_cache()
        return success

    # Daily Note Integration (preserved for compatibility)
    async def save_or_append_daily_note(
        self,
        note: ObsidianNote,
        target_date: str | None = None,
    ) -> Path:
        """Save or append to daily note."""
        from datetime import date

        # Use provided date or today
        if target_date:
            daily_date = target_date
        else:
            daily_date = date.today().strftime("%Y-%m-%d")

        # Ensure daily notes folder exists
        daily_folder = await self.vault_manager.ensure_folder_exists("Daily Notes")
        daily_file_path = daily_folder / f"{daily_date}.md"

        if daily_file_path.exists():
            # Append to existing daily note
            await self.append_to_note(daily_file_path, note.content, note.title)
            return daily_file_path
        else:
            # Create new daily note
            from .models import NoteFrontmatter

            daily_frontmatter = NoteFrontmatter(
                obsidian_folder="Daily Notes",
                created=daily_date,
                tags=["daily-note"] + (note.frontmatter.tags or []),
                ai_category="Daily",
            )

            daily_note = ObsidianNote(
                filename=f"daily-{daily_date}.md",
                file_path=Path(f"Daily Notes/daily-{daily_date}.md"),
                frontmatter=daily_frontmatter,
                content=f"## {note.title}\n\n{note.content}",
            )
            return await self.file_operations.save_note(daily_note, "Daily Notes")

    # Search Operations
    async def search_notes(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
        max_results: int = 50,
        folder: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Search notes in the vault."""
        # Use limit if provided, otherwise use max_results
        effective_limit = limit if limit is not None else max_results

        criteria = SearchCriteria(
            query=query,
            tags=tags,
            category=category,
            max_results=effective_limit,
            folder=folder,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )

        results = await self.note_search.search_notes(criteria)

        # Convert to dict format for compatibility
        return [result.to_dict() for result in results]

    # Statistics Operations
    async def get_vault_stats(self, force_refresh: bool = False) -> dict[str, Any]:
        """Get comprehensive vault statistics."""
        stats = await self.statistics.get_vault_stats(force_refresh)
        return stats.to_dict()

    # Backup Operations
    async def backup_vault(self, description: str | None = None) -> dict[str, Any]:
        """Create a backup of the vault."""
        result = await self.backup_manager.create_backup(description)
        return result.to_dict()

    async def list_backups(self) -> list[dict[str, Any]]:
        """List available backups."""
        return await self.backup_manager.list_backups()

    async def restore_backup(self, backup_name: str) -> bool:
        """Restore vault from backup."""
        backup_path = self.backup_manager.config.backup_directory / backup_name
        success = await self.backup_manager.restore_backup(backup_path)
        if success:
            self.statistics.invalidate_cache()
        return success

    # Operation History (preserved for compatibility)
    def get_operation_history(self) -> list[dict[str, Any]]:
        """Get file operation history."""
        return self.file_operations.get_operation_history()

    def clear_operation_history(self) -> None:
        """Clear file operation history."""
        self.file_operations.clear_operation_history()

    # Helper Methods for Backwards Compatibility
    async def _ensure_vault_structure(self) -> None:
        """Ensure vault structure (backwards compatibility)."""
        await self.vault_manager.initialize_vault()

    def _invalidate_stats_cache(self) -> None:
        """Invalidate stats cache (backwards compatibility)."""
        self.statistics.invalidate_cache()

    # Configuration
    def configure_backup(self, backup_config: BackupConfig) -> None:
        """Configure backup settings."""
        self.backup_manager = BackupManager(self.vault_path, backup_config)
        logger.info(
            "Backup configuration updated",
            backup_dir=str(backup_config.backup_directory),
        )

    def configure_statistics_cache(self, cache_duration: int) -> None:
        """Configure statistics cache duration."""
        self.statistics = VaultStatistics(self.vault_path, cache_duration)
        logger.info("Statistics cache duration updated", duration=cache_duration)

    # Critical missing methods from original file_manager.py

    def _clean_duplicate_sections(self, new_content: str, existing_content: str) -> str:
        """
        新しいコンテンツから重複するセクションを除去

        Args:
            new_content: 新しく追加するコンテンツ
            existing_content: 既存のコンテンツ

        Returns:
            重複除去後のコンテンツ
        """
        try:
            # 重複するセクションのパターン
            duplicate_patterns = [
                r"## 📅 メタデータ.*?(?=##|\Z)",  # メタデータセクション
                r"## 🔗 関連リンク.*?(?=##|\Z)",  # 関連リンクセクション
                r"# 📝\s*\n*",  # 重複するタイトル
            ]

            cleaned_content = new_content

            # 各パターンで重複を除去
            for pattern in duplicate_patterns:
                # 既存コンテンツに同じセクションがある場合、新しいコンテンツから除去
                if re.search(pattern, existing_content, re.DOTALL):
                    cleaned_content = re.sub(
                        pattern, "", cleaned_content, flags=re.DOTALL
                    )

            # URL 要約の重複を除去（同じ URL の場合）
            existing_urls = re.findall(r"🔗 (https?://[^\s]+)", existing_content)
            for url in existing_urls:
                # 同じ URL の要約セクションを除去
                url_section_pattern = (
                    rf"## 📎 URL 要約.*?### .*?\n 🔗 {re.escape(url)}.*?(?=##|\Z)"
                )
                cleaned_content = re.sub(
                    url_section_pattern, "", cleaned_content, flags=re.DOTALL
                )

            # 空行の整理
            cleaned_content = re.sub(r"\n{3,}", "\n\n", cleaned_content)
            cleaned_content = cleaned_content.strip()

            # 完全に空になった場合は元のタイトル部分のみ保持
            if not cleaned_content or cleaned_content.isspace():
                # 最小限のコンテンツ（時刻のみ）を抽出
                timestamp_match = re.search(r"## \d{2}:\d{2}", new_content)
                if timestamp_match:
                    cleaned_content = timestamp_match.group(0)
                else:
                    # タイムスタンプを生成
                    current_time = datetime.now().strftime("%H:%M")
                    cleaned_content = f"## {current_time}"

            return cleaned_content

        except Exception as e:
            self.logger.warning("Failed to clean duplicate sections", error=str(e))
            return new_content  # 失敗した場合は元のコンテンツを返す  # 失敗した場合は元のコンテンツを返す

    def _parse_markdown_file(self, content: str) -> tuple[dict[str, Any], str]:
        """
        Markdown ファイルをフロントマターとコンテンツに分離

        Args:
            content: ファイル全体の内容

        Returns:
            フロントマターの dict と マークダウンコンテンツのタプル
        """
        try:
            # YAML フロントマターの検出
            frontmatter_match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)

            if frontmatter_match:
                import yaml

                frontmatter_str = frontmatter_match.group(1)
                markdown_content = frontmatter_match.group(2).strip()

                # YAML の解析
                frontmatter_data = yaml.safe_load(frontmatter_str) or {}

                return frontmatter_data, markdown_content
            else:
                # フロントマターがない場合
                return {}, content.strip()

        except Exception as e:
            self.logger.warning("Failed to parse markdown file", error=str(e))
            return {}, content.strip()

    async def _restructure_daily_note(self, note: ObsidianNote) -> str:
        """日次ノートの構造を再構築（後方互換性のため）"""
        # 簡略化された実装
        return note.content

    async def _insert_before_metadata(self, content: str, metadata_content: str) -> str:
        """メタデータセクションの前にコンテンツを挿入（後方互換性のため）"""
        # メタデータセクションを検索
        metadata_pattern = r"## 📅 メタデータ"
        if re.search(metadata_pattern, content):
            return re.sub(
                metadata_pattern,
                f"{metadata_content}\n\n## 📅 メタデータ",
                content,
                count=1,
            )
        else:
            # メタデータセクションがない場合は末尾に追加
            return f"{content}\n\n{metadata_content}"

    # Enhanced vault structure management - removing duplicate definition

    async def _create_template_files(self) -> None:
        """テンプレートファイルを作成（後方互換性のため）"""
        from .models import VaultFolder

        templates_dir = self.vault_path / VaultFolder.TEMPLATES.value

        # メッセージノートテンプレート
        message_template_content = """# {{title}}

## 📝 要約
{{ai_summary}}

## 💬 元メッセージ
```
{{original_content}}
```

## 🏷️ タグ
{{ai_tags}}

## 📂 分類
- **カテゴリ**: {{ai_category}}
- **信頼度**: {{ai_confidence}}

## 📎 添付ファイル
{{attachments}}

## 🔗 関連リンク
- [Discord Message]({{discord_link}})
- **チャンネル**: #{{channel_name}}

## 📊 メタデータ
- **作成者**: {{author_name}}
- **作成日時**: {{created_time}}
- **AI 処理時間**: {{processing_time}}ms"""

        message_template_path = templates_dir / "message_note_template.md"
        if not message_template_path.exists():
            async with aiofiles.open(message_template_path, "w", encoding="utf-8") as f:
                await f.write(message_template_content)

        # 日次ノートテンプレート
        daily_template_content = """# Daily Note - {{date}}

## 📊 今日の統計
- **総メッセージ数**: {{total_messages}}
- **AI 処理済み**: {{processed_messages}}
- **処理時間合計**: {{ai_time_total}}ms

## 📝 今日のメモ

### 仕事 ({{work_count}}件)
{{work_notes}}

### 学習 ({{learning_count}}件)
{{learning_notes}}

### 生活 ({{life_count}}件)
{{life_notes}}

### アイデア ({{ideas_count}}件)
{{ideas_notes}}

## 🏷️ 今日のタグ
{{daily_tags}}

## 📎 添付ファイル
{{daily_attachments}}"""

        daily_template_path = templates_dir / "daily_note_template.md"
        if not daily_template_path.exists():
            async with aiofiles.open(daily_template_path, "w", encoding="utf-8") as f:
                await f.write(daily_template_content)

    def search_notes_fast(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        status: str | None = None,
        category: str | None = None,
        limit: int = 50,
    ) -> list[Path]:
        """高速ノート検索（ローカルインデックス使用・後方互換性のため）"""
        if not self.local_data_manager:
            self.logger.warning(
                "Local data manager not enabled, falling back to regular search"
            )
            return []

        # インデックスベースの検索
        file_keys = self.local_data_manager.data_index.search_notes(
            query=query, tags=tags, status=status, category=category, limit=limit
        )

        # 相対パスを絶対パスに変換
        return [self.vault_path / file_key for file_key in file_keys]

    # Local data management methods (backward compatibility)
    async def initialize_local_data(self) -> None:
        """ローカルデータを初期化"""
        if self.local_data_manager:
            await self.local_data_manager.initialize()

    async def create_vault_snapshot(self) -> dict[str, Any]:
        """Vault スナップショットを作成"""
        if self.local_data_manager:
            snapshot_path = await self.local_data_manager.create_snapshot()
            if snapshot_path:
                return {"snapshot_path": str(snapshot_path)}
        return {}

    async def restore_vault_snapshot(self, snapshot_path: str) -> bool:
        """Vault スナップショットを復元"""
        if self.local_data_manager:
            return await self.local_data_manager.restore_snapshot(Path(snapshot_path))
        return False

    async def export_vault_data(self, format: str = "json") -> Path | None:
        """Vault データをエクスポート"""
        if self.local_data_manager:
            return await self.local_data_manager.export_vault_data(format)
        return None

    async def sync_with_remote(self, remote_config: dict[str, Any]) -> bool:
        """リモートと同期"""
        if self.local_data_manager and "remote_path" in remote_config:
            return await self.local_data_manager.sync_with_remote(
                Path(remote_config["remote_path"]),
                remote_config.get("direction", "both"),
            )
        return False

    async def rebuild_local_index(self) -> None:
        """ローカルインデックスを再構築"""
        if self.local_data_manager:
            await self.local_data_manager.rebuild_index()

    async def get_local_data_stats(self) -> dict[str, Any]:
        """ローカルデータ統計を取得"""
        if self.local_data_manager:
            return await self.local_data_manager.get_local_stats()
        return {}

    async def auto_backup_if_needed(self) -> bool:
        """必要に応じて自動バックアップを実行"""
        try:
            # 最後のバックアップ時刻をチェック
            backups = await self.list_backups()

            if not backups:
                # バックアップが存在しない場合は作成
                await self.backup_vault("Auto backup - first backup")
                return True

            # 最新のバックアップが 24 時間以上前の場合は新しいバックアップを作成
            from datetime import timedelta

            latest_backup = max(backups, key=lambda x: x.get("created_at", ""))
            latest_time = datetime.fromisoformat(latest_backup.get("created_at", ""))

            if datetime.now() - latest_time > timedelta(days=1):
                await self.backup_vault("Auto backup - daily")
                return True

            return False
        except Exception as e:
            self.logger.error("Failed to perform auto backup", error=str(e))
            return False

    def _matches_search_criteria(
        self,
        note,  # ObsidianNote or dict
        query: str | None = None,
        status=None,  # NoteStatus | None
        tags: list[str] | None = None,
        date_from=None,  # datetime | None
        date_to=None,  # datetime | None
    ) -> bool:
        """検索条件にマッチするかチェック（後方互換性のため）"""

        # Note オブジェクトから必要な属性を取得
        if hasattr(note, "frontmatter"):
            frontmatter = note.frontmatter
            title = getattr(note, "title", "")
            content = getattr(note, "content", "")
            created_at = getattr(note, "created_at", None)
        elif isinstance(note, dict):
            frontmatter = note.get("frontmatter", {})
            title = note.get("title", "")
            content = note.get("content", "")
            created_at = note.get("created_at")
        else:
            return False

        # ステータスフィルタ
        if status and getattr(frontmatter, "status", None) != status:
            return False

        # 日付フィルタ
        if date_from and created_at and created_at < date_from:
            return False

        if date_to and created_at and created_at > date_to:
            return False

        # タグフィルタ
        if tags:
            note_tags = set()
            if hasattr(frontmatter, "tags") and frontmatter.tags:
                note_tags.update(frontmatter.tags)
            if hasattr(frontmatter, "ai_tags") and frontmatter.ai_tags:
                note_tags.update([tag.lstrip("#") for tag in frontmatter.ai_tags])

            if not any(tag in note_tags for tag in tags):
                return False

        # クエリフィルタ（タイトル、コンテンツ、タグ、要約を検索）
        if query:
            query_lower = query.lower()
            searchable_parts = [title.lower(), content.lower()]

            if hasattr(frontmatter, "tags") and frontmatter.tags:
                searchable_parts.append(" ".join(frontmatter.tags))
            if hasattr(frontmatter, "ai_tags") and frontmatter.ai_tags:
                searchable_parts.append(" ".join(frontmatter.ai_tags))
            if hasattr(frontmatter, "ai_summary") and frontmatter.ai_summary:
                searchable_parts.append(frontmatter.ai_summary)

            searchable_text = " ".join(searchable_parts)

            if query_lower not in searchable_text:
                return False

        return True
