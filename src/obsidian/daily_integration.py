"""
Daily note integration for Discord messages and health data
"""

import re
from datetime import date, datetime
from typing import Any

from src.obsidian.models import ObsidianNote, VaultFolder
from src.obsidian.refactored_file_manager import ObsidianFileManager
from src.utils.mixins import LoggerMixin

# 旧テンプレートシステムは削除済み
# from src.templates import DailyNoteTemplate


class DailyNoteIntegration(LoggerMixin):
    """デイリーノートの統合機能"""

    def __init__(self, file_manager: ObsidianFileManager):
        """
        Initialize DailyIntegration

        Args:
            file_manager: ObsidianFileManager instance
        """
        self.file_manager = file_manager
        # TemplateEngine を使用するように変更
        from src.obsidian.template_system import TemplateEngine

        self.template_engine = TemplateEngine(file_manager.vault_path)
        self.logger.info("Daily integration initialized")

    async def add_activity_log_entry(
        self, message_data: dict[str, Any], date: datetime | None = None
    ) -> bool:
        """
        activity log エントリをデイリーノートに追加

        Args:
            message_data: メッセージデータ
            date: 対象日（指定されない場合は今日）

        Returns:
            追加成功可否
        """
        try:
            if not date:
                date = datetime.now()

            # メッセージ内容の抽出
            metadata = message_data.get("metadata", {})
            content_info = metadata.get("content", {})
            timing_info = metadata.get("timing", {})
            raw_content = content_info.get("raw_content", "").strip()

            if not raw_content:
                self.logger.debug("Empty message content, skipping activity log entry")
                return False

            # デイリーノートの取得または作成
            daily_note = await self._get_or_create_daily_note(date)
            if not daily_note:
                return False

            # Activity Log セクションにエントリを追加
            timestamp = timing_info.get("created_at", {}).get(
                "iso", datetime.now().isoformat()
            )
            time_str = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            ).strftime("%H:%M")

            activity_entry = f"- **{time_str}** {raw_content}"

            # ノート内容を更新
            updated_content = self._add_to_section(
                daily_note.content, "## 📋 Activity Log", activity_entry
            )

            daily_note.content = updated_content
            daily_note.modified_at = datetime.now()

            # ノートを保存
            success = await self.file_manager.update_note(
                daily_note.file_path, daily_note
            )

            if success:
                self.logger.info(
                    "Activity log entry added to daily note",
                    date=date.strftime("%Y-%m-%d"),
                    entry_time=time_str,
                )

            return success

        except Exception as e:
            self.logger.error(
                "Failed to add activity log entry",
                date=date.strftime("%Y-%m-%d") if date else "today",
                error=str(e),
                exc_info=True,
            )
            return False

    async def add_daily_task_entry(
        self, message_data: dict[str, Any], date: datetime | None = None
    ) -> bool:
        """
        daily task エントリをデイリーノートに追加

        Args:
            message_data: メッセージデータ
            date: 対象日（指定されない場合は今日）

        Returns:
            追加成功可否
        """
        try:
            if not date:
                date = datetime.now()

            # メッセージ内容の抽出
            metadata = message_data.get("metadata", {})
            content_info = metadata.get("content", {})
            raw_content = content_info.get("raw_content", "").strip()

            if not raw_content:
                self.logger.debug("Empty message content, skipping daily task entry")
                return False

            # デイリーノートの取得または作成
            daily_note = await self._get_or_create_daily_note(date)
            if not daily_note:
                return False

            # タスクの解析とチェックボックス形式に変換
            task_entries = self._parse_tasks(raw_content)
            if not task_entries:
                # タスク形式でない場合は通常のエントリとして追加
                task_entries = [f"- [ ] {raw_content}"]

            # Daily Tasks セクションにエントリを追加
            updated_content = daily_note.content
            for task_entry in task_entries:
                updated_content = self._add_to_section(
                    updated_content, "## ✅ Daily Tasks", task_entry
                )

            daily_note.content = updated_content
            daily_note.modified_at = datetime.now()

            # ノートを保存
            success = await self.file_manager.update_note(
                daily_note.file_path, daily_note
            )

            if success:
                self.logger.info(
                    "Daily task entries added to daily note",
                    date=date.strftime("%Y-%m-%d"),
                    task_count=len(task_entries),
                )

            return success

        except Exception as e:
            self.logger.error(
                "Failed to add daily task entry",
                date=date.strftime("%Y-%m-%d") if date else "today",
                error=str(e),
                exc_info=True,
            )
            return False

    async def _get_or_create_daily_note(self, date: datetime) -> ObsidianNote | None:
        """デイリーノートを取得または作成"""
        try:
            # 既存のデイリーノートを検索
            year = date.strftime("%Y")
            month = date.strftime("%m-%B")
            filename = f"{date.strftime('%Y-%m-%d')}.md"

            daily_note_path = (
                self.file_manager.vault_path
                / VaultFolder.DAILY_NOTES.value
                / year
                / month
                / filename
            )

            # 既存ノートの読み込みを試行
            if daily_note_path.exists():
                existing_note = await self.file_manager.load_note(daily_note_path)
                if existing_note:
                    return existing_note

            # 新しいデイリーノートを作成
            daily_stats = await self._collect_daily_stats(date)
            new_note = await self.template_engine.generate_daily_note(date, daily_stats)

            if not new_note:
                self.logger.error("Failed to generate daily note from template")
                return None

            # ベースセクションを追加
            new_note.content = self._ensure_base_sections(new_note.content)

            # Vault の初期化
            await self.file_manager.initialize_vault()

            # ノートを保存
            success = await self.file_manager.save_note(new_note)
            if success:
                self.logger.info(
                    "New daily note created", date=date.strftime("%Y-%m-%d")
                )
                return new_note

            return None

        except Exception as e:
            self.logger.error(
                "Failed to get or create daily note",
                date=date.strftime("%Y-%m-%d"),
                error=str(e),
                exc_info=True,
            )
            return None

    def _ensure_base_sections(self, content: str) -> str:
        """デイリーノートの基本セクションが存在することを確認"""
        sections_to_ensure = ["## 📋 Activity Log", "## ✅ Daily Tasks"]

        # 各セクションの存在確認と追加
        for section in sections_to_ensure:
            if section not in content:
                content += f"\n\n{section}\n\n"

        return content

    def _add_to_section(self, content: str, section_header: str, entry: str) -> str:
        """指定されたセクションにエントリを追加"""
        return self._update_section(
            content, section_header, entry, replace_content=False
        )

    def _update_section(
        self,
        content: str,
        section_identifier: str,
        new_content: str,
        replace_content: bool = False,
    ) -> str:
        """
        統一されたセクション更新メソッド

        Args:
            content: 既存のノート内容
            section_identifier: セクション識別子（ヘッダー文字列またはセクション名）
            new_content: 追加/置換するコンテンツ
            replace_content: True=セクション内容を置換、 False=セクションに追加

        Returns:
            更新されたコンテンツ
        """
        lines = content.split("\n")
        section_start = None
        section_end = len(lines)

        # セクションヘッダーの形式を統一
        if not section_identifier.startswith("## "):
            # セクション名のみの場合、## プレフィックスを追加して検索
            search_patterns = [
                f"## {section_identifier}",
                f"## 📊 {section_identifier}",
                f"## 🔍 {section_identifier}",
            ]
        else:
            # 完全なヘッダーの場合
            search_patterns = [section_identifier]

        # セクションを検索
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped.startswith("## "):
                for pattern in search_patterns:
                    if pattern in line or line_stripped == pattern:
                        section_start = i
                        # 次のセクションを探す
                        for j in range(i + 1, len(lines)):
                            if lines[j].strip().startswith("## "):
                                section_end = j
                                break
                        break
                if section_start is not None:
                    break

        if section_start is not None:
            if replace_content:
                # セクション内容を完全に置換
                new_lines = (
                    lines[:section_start]
                    + new_content.split("\n")
                    + [""]  # 空行を追加
                    + lines[section_end:]
                )
            else:
                # セクション内の適切な位置に追加
                # 空行をスキップして最初の内容行を見つける
                content_start = None
                for k in range(section_start + 1, section_end):
                    if lines[k].strip():
                        content_start = k
                        break

                if content_start is None:
                    # セクションが空の場合
                    lines.insert(section_start + 1, "")
                    lines.insert(section_start + 2, new_content)
                else:
                    # 既存の内容の後に追加
                    lines.insert(section_end, new_content)

                new_lines = lines
        else:
            # セクションが存在しない場合は末尾に追加
            if replace_content:
                # セクションヘッダーと内容を新規作成
                section_header = (
                    search_patterns[0]
                    if search_patterns
                    else f"## {section_identifier}"
                )
                new_lines = lines + ["", section_header] + new_content.split("\n")
            else:
                # 従来の動作（セクションヘッダーと内容を追加）
                section_header = (
                    section_identifier
                    if section_identifier.startswith("## ")
                    else f"## {section_identifier}"
                )
                new_lines = lines + ["", section_header, "", new_content]

        return "\n".join(new_lines)

    def _parse_tasks(self, content: str) -> list[str]:
        """メッセージ内容からタスクを解析"""
        task_patterns = [
            r"^[-*+]\s+(.+)$",  # リスト形式
            r"^(\d+\.)\s+(.+)$",  # 番号付きリスト
            r"^[-*+]\s*\[[ x]\]\s+(.+)$",  # チェックボックス付き
            r"^TODO:\s*(.+)$",  # TODO 形式
            r"^タスク[:：]\s*(.+)$",  # 日本語タスク形式
        ]

        tasks = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            for pattern in task_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    if len(match.groups()) == 1:
                        task_content = match.group(1).strip()
                    else:
                        task_content = match.group(2).strip()

                    # チェックボックス形式に変換
                    if not task_content.startswith(
                        "[ ]"
                    ) and not task_content.startswith("[x]"):
                        tasks.append(f"- [ ] {task_content}")
                    else:
                        tasks.append(f"- {task_content}")
                    break
            else:
                # パターンにマッチしない場合、複数行の場合は全体を 1 つのタスクとして扱う
                if len(lines) == 1:
                    tasks.append(f"- [ ] {line}")

        return tasks

    async def update_health_data_in_daily_note(
        self, target_date: date, health_data_markdown: str
    ) -> bool:
        """
        デイリーノートに健康データを追加/更新

        Args:
            target_date: 対象日付
            health_data_markdown: 健康データの Markdown 形式

        Returns:
            bool: 更新成功フラグ
        """
        try:
            self.logger.info(
                "Updating health data in daily note", date=target_date.isoformat()
            )

            # デイリーノートを取得または作成
            daily_note = await self._get_or_create_daily_note(
                datetime.combine(target_date, datetime.min.time())
            )
            if not daily_note:
                self.logger.error(
                    "Failed to get or create daily note for health data update"
                )
                return False

            # 既存のコンテンツを読み込み
            content = daily_note.content

            # Health Data セクションを更新
            content = self._update_health_data_section(content, health_data_markdown)

            # ノートを更新
            updated_note = ObsidianNote(
                filename=daily_note.filename,
                file_path=daily_note.file_path,
                frontmatter=daily_note.frontmatter,
                content=content,
            )

            success = await self.file_manager.save_note(updated_note, overwrite=True)

            if success:
                self.logger.info(
                    "Successfully updated health data in daily note",
                    date=target_date.isoformat(),
                    file_path=str(
                        daily_note.file_path.relative_to(self.file_manager.vault_path)
                    ),
                )
                return True
            self.logger.error("Failed to save updated daily note with health data")
            return False

        except Exception as e:
            self.logger.error(
                "Error updating health data in daily note",
                date=target_date.isoformat(),
                error=str(e),
                exc_info=True,
            )
            return False

    def _update_health_data_section(
        self, content: str, health_data_markdown: str
    ) -> str:
        """Health Data セクションを更新"""
        return self._update_section(
            content, "Health Data", health_data_markdown, replace_content=True
        )

    async def update_health_analysis_in_daily_note(
        self, target_date: date, analysis_markdown: str
    ) -> bool:
        """
        デイリーノートに健康分析結果を追加/更新

        Args:
            target_date: 対象日付
            analysis_markdown: 健康分析の Markdown 形式

        Returns:
            bool: 更新成功フラグ
        """
        try:
            self.logger.info(
                "Updating health analysis in daily note", date=target_date.isoformat()
            )

            # デイリーノートを取得または作成
            daily_note = await self._get_or_create_daily_note(
                datetime.combine(target_date, datetime.min.time())
            )
            if not daily_note:
                self.logger.error(
                    "Failed to get or create daily note for health analysis update"
                )
                return False

            # 既存のコンテンツを読み込み
            content = daily_note.content

            # Health Analysis セクションを更新
            content = self._update_health_analysis_section(content, analysis_markdown)

            # ノートを更新
            updated_note = ObsidianNote(
                filename=daily_note.filename,
                file_path=daily_note.file_path,
                frontmatter=daily_note.frontmatter,
                content=content,
            )

            success = await self.file_manager.save_note(updated_note, overwrite=True)

            if success:
                self.logger.info(
                    "Successfully updated health analysis in daily note",
                    date=target_date.isoformat(),
                    file_path=str(
                        daily_note.file_path.relative_to(self.file_manager.vault_path)
                    ),
                )
                return True
            self.logger.error("Failed to save updated daily note with health analysis")
            return False

        except Exception as e:
            self.logger.error(
                "Error updating health analysis in daily note",
                date=target_date.isoformat(),
                error=str(e),
                exc_info=True,
            )
            return False

    def _update_health_analysis_section(
        self, content: str, analysis_markdown: str
    ) -> str:
        """Health Analysis セクションを更新"""
        return self._update_section(
            content, "Health Analysis", analysis_markdown, replace_content=True
        )

    async def get_health_data_for_date(self, target_date: date) -> str | None:
        """
        指定日のデイリーノートから Health Data セクションを抽出

        Args:
            target_date: 対象日付

        Returns:
            Health Data セクションの内容（存在しない場合は None ）
        """
        try:
            daily_note = await self._get_or_create_daily_note(
                datetime.combine(target_date, datetime.min.time())
            )
            if not daily_note:
                return None

            lines = daily_note.content.split("\n")
            health_section_start = None
            health_section_end = len(lines)

            # Health Data セクションを検索
            for i, line in enumerate(lines):
                if line.strip().startswith("## ") and "Health Data" in line:
                    health_section_start = i
                    # 次のセクションを探す
                    for j in range(i + 1, len(lines)):
                        if lines[j].strip().startswith("## "):
                            health_section_end = j
                            break
                    break

            if health_section_start is not None:
                health_section_lines = lines[health_section_start:health_section_end]
                return "\n".join(health_section_lines).strip()

            return None

        except Exception as e:
            self.logger.error(
                "Error retrieving health data from daily note",
                date=target_date.isoformat(),
                error=str(e),
            )
            return None

    async def _collect_daily_stats(self, date: datetime) -> dict[str, Any]:
        """指定日の統計情報を収集"""
        try:
            from datetime import timedelta

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
            }

            for note_dict in daily_notes:
                # AI 処理済みノートの統計
                ai_processed = note_dict.get("ai_processed", False)
                if ai_processed:
                    if isinstance(stats["processed_messages"], int):
                        stats["processed_messages"] += 1

                    ai_processing_time = note_dict.get("ai_processing_time")
                    if ai_processing_time and isinstance(
                        stats["ai_processing_time_total"], int
                    ):
                        stats["ai_processing_time_total"] += int(ai_processing_time)

                # カテゴリ統計
                ai_category = note_dict.get("ai_category")
                if ai_category:
                    category = str(ai_category)
                    if isinstance(stats["categories"], dict):
                        stats["categories"][category] = (
                            stats["categories"].get(category, 0) + 1
                        )

                # タグ統計
                ai_tags = note_dict.get("ai_tags", []) or []
                tags = note_dict.get("tags", []) or []
                for tag in ai_tags + tags:
                    clean_tag = str(tag).lstrip("#")
                    if isinstance(stats["tags"], dict):
                        stats["tags"][clean_tag] = stats["tags"].get(clean_tag, 0) + 1

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
                "tags": {},
            }

    async def create_daily_note_if_not_exists(
        self, date: datetime | None = None
    ) -> ObsidianNote | None:
        """指定日のデイリーノートが存在しない場合に作成"""
        if not date:
            date = datetime.now()

        return await self._get_or_create_daily_note(date)
