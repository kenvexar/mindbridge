"""
Automated review and organization suggestion system
"""

from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any

from discord.ext import commands, tasks

from src.bot.notification_system import NotificationCategory, NotificationLevel
from src.config import get_settings
from src.utils.mixins import LoggerMixin


class ReviewType(str, Enum):
    """レビュータイプ"""

    WEEKLY_UNORGANIZED = "weekly_unorganized"
    MONTHLY_SUMMARY = "monthly_summary"
    LONG_TERM_NOTES = "long_term_notes"
    RELATED_NOTES = "related_notes"
    TOPIC_CLASSIFICATION = "topic_classification"


class AutoReviewSystem(LoggerMixin):
    """自動レビューと整理提案システム"""

    def __init__(
        self, bot: commands.Bot, notification_system: Any | None = None
    ) -> None:
        self.bot = bot
        self.notification_system = notification_system
        self.obsidian_manager: Any | None = None
        self.ai_processor: Any | Any | None = None

        # レビュー実行履歴
        self.review_history: list[dict[str, Any]] = []

        # スケジューラー設定
        self.weekly_review_enabled = True
        self.monthly_summary_enabled = True
        self.long_term_reminder_enabled = True

        # タスクの初期化
        self._setup_scheduled_tasks()

    async def initialize_dependencies(self) -> None:
        """依存関係の初期化"""
        try:
            from src.ai import AIProcessor
            from src.obsidian import ObsidianFileManager

            self.obsidian_manager = ObsidianFileManager()

            # AIプロセッサーの初期化（モックモードかどうかで分岐）
            if get_settings().is_mock_mode:
                from src.ai.mock_processor import MockAIProcessor

                self.ai_processor = MockAIProcessor()
            else:
                self.ai_processor = AIProcessor()

            self.logger.info("Auto review system dependencies initialized")

        except Exception as e:
            self.logger.error(
                "Failed to initialize review system dependencies",
                error=str(e),
                exc_info=True,
            )

    def _setup_scheduled_tasks(self) -> None:
        """スケジュールされたタスクのセットアップ"""
        try:
            # 週次レビュー（毎週日曜日 9:00）
            @tasks.loop(hours=24)
            async def weekly_review() -> None:
                if (
                    datetime.now().weekday() == 6 and datetime.now().hour == 9
                ):  # Sunday 9 AM
                    await self.run_weekly_unorganized_review()

            # 月次サマリー（毎月1日 10:00）
            @tasks.loop(hours=24)
            async def monthly_summary() -> None:
                if (
                    datetime.now().day == 1 and datetime.now().hour == 10
                ):  # 1st of month 10 AM
                    await self.run_monthly_summary()

            # 長期滞在メモチェック（毎日 11:00）
            @tasks.loop(hours=24)
            async def long_term_check() -> None:
                if datetime.now().hour == 11:  # 11 AM daily
                    await self.run_long_term_notes_check()

            self.weekly_review_task = weekly_review
            self.monthly_summary_task = monthly_summary
            self.long_term_check_task = long_term_check

            self.logger.info("Scheduled review tasks configured")

        except Exception as e:
            self.logger.error("Failed to setup scheduled tasks", error=str(e))

    async def start(self) -> None:
        """レビューシステム開始"""
        try:
            await self.initialize_dependencies()

            if self.weekly_review_enabled:
                self.weekly_review_task.start()
            if self.monthly_summary_enabled:
                self.monthly_summary_task.start()
            if self.long_term_reminder_enabled:
                self.long_term_check_task.start()

            self.logger.info("Auto review system started")

        except Exception as e:
            self.logger.error(
                "Failed to start review system", error=str(e), exc_info=True
            )

    async def stop(self) -> None:
        """レビューシステム停止"""
        try:
            if hasattr(self, "weekly_review_task"):
                self.weekly_review_task.cancel()
            if hasattr(self, "monthly_summary_task"):
                self.monthly_summary_task.cancel()
            if hasattr(self, "long_term_check_task"):
                self.long_term_check_task.cancel()

            self.logger.info("Auto review system stopped")

        except Exception as e:
            self.logger.error("Failed to stop review system", error=str(e))

    async def run_weekly_unorganized_review(self) -> dict[str, Any]:
        """週次未整理メモレビュー実行"""
        try:
            if not self.obsidian_manager:
                return {"error": "Obsidian manager not initialized"}

            # 先週作成されたメモを検索
            one_week_ago = datetime.now() - timedelta(days=7)
            recent_notes = await self.obsidian_manager.search_notes(
                date_from=one_week_ago, limit=100
            )

            # 未整理メモを特定（Inboxにあるもの、またはstatusがdraftのもの）
            unorganized_notes = []
            for note in recent_notes:
                note_path_str = str(note.file_path)
                is_in_inbox = "00_Inbox" in note_path_str
                is_draft = (
                    note.frontmatter.status.value == "draft"
                    if note.frontmatter.status
                    else True
                )

                if is_in_inbox or is_draft:
                    unorganized_notes.append(note)

            if not unorganized_notes:
                await self._send_review_notification(
                    ReviewType.WEEKLY_UNORGANIZED,
                    "📝 週次レビュー: 整理済み",
                    "先週作成されたメモはすべて整理されています。素晴らしい！",
                    {"organized_count": len(recent_notes)},
                )
                return {
                    "status": "no_unorganized_notes",
                    "total_notes": len(recent_notes),
                }

            # 未整理メモの分析とカテゴリ提案
            suggestions = await self._analyze_unorganized_notes(unorganized_notes)

            # 通知送信
            await self._send_weekly_review_notification(unorganized_notes, suggestions)

            # 履歴記録
            self._record_review(
                ReviewType.WEEKLY_UNORGANIZED,
                {
                    "unorganized_count": len(unorganized_notes),
                    "total_notes": len(recent_notes),
                    "suggestions": len(suggestions),
                },
            )

            return {
                "status": "completed",
                "unorganized_count": len(unorganized_notes),
                "total_notes": len(recent_notes),
                "suggestions": suggestions,
            }

        except Exception as e:
            self.logger.error("Weekly review failed", error=str(e), exc_info=True)
            return {"error": str(e)}

    async def run_monthly_summary(self) -> dict[str, Any]:
        """月次活動サマリー生成"""
        try:
            if not self.obsidian_manager or not self.ai_processor:
                return {"error": "Dependencies not initialized"}

            # 先月のメモを取得
            today = date.today()
            first_of_month = date(today.year, today.month, 1)
            last_month = first_of_month - timedelta(days=1)
            first_of_last_month = date(last_month.year, last_month.month, 1)

            monthly_notes = await self.obsidian_manager.search_notes(
                date_from=datetime.combine(first_of_last_month, datetime.min.time()),
                date_to=datetime.combine(last_month, datetime.max.time()),
                limit=200,
            )

            if not monthly_notes:
                await self._send_review_notification(
                    ReviewType.MONTHLY_SUMMARY,
                    "📊 月次サマリー: データなし",
                    f"{last_month.strftime('%Y年%m月')}のアクティビティデータがありません。",
                    {"month": last_month.strftime("%Y-%m")},
                )
                return {"status": "no_data", "month": last_month.strftime("%Y-%m")}

            # AIでサマリー生成
            summary_data = await self._generate_monthly_ai_summary(
                monthly_notes, last_month
            )

            # 通知送信
            if summary_data:
                await self._send_monthly_summary_notification(summary_data, last_month)

            # 履歴記録
            self._record_review(
                ReviewType.MONTHLY_SUMMARY,
                {
                    "month": last_month.strftime("%Y-%m"),
                    "notes_analyzed": len(monthly_notes),
                    "ai_summary_generated": bool(summary_data),
                },
            )

            return {
                "status": "completed",
                "month": last_month.strftime("%Y-%m"),
                "notes_count": len(monthly_notes),
                "summary": summary_data,
            }

        except Exception as e:
            self.logger.error("Monthly summary failed", error=str(e), exc_info=True)
            return {"error": str(e)}

    async def run_long_term_notes_check(self) -> dict[str, Any]:
        """長期滞在メモチェック実行"""
        try:
            if not self.obsidian_manager:
                return {"error": "Obsidian manager not initialized"}

            # 30日以上前のメモを検索
            thirty_days_ago = datetime.now() - timedelta(days=30)
            old_notes = await self.obsidian_manager.search_notes(
                date_to=thirty_days_ago, limit=50
            )

            # Inboxにある古いメモを特定
            long_term_notes = []
            for note in old_notes:
                note_path_str = str(note.file_path)
                if "00_Inbox" in note_path_str:
                    days_old = (datetime.now() - note.created_at).days
                    long_term_notes.append({"note": note, "days_old": days_old})

            if not long_term_notes:
                return {"status": "no_long_term_notes"}

            # 通知送信
            await self._send_long_term_notes_notification(long_term_notes)

            # 履歴記録
            self._record_review(
                ReviewType.LONG_TERM_NOTES,
                {
                    "long_term_count": len(long_term_notes),
                    "oldest_days": (
                        max([item["days_old"] for item in long_term_notes])
                        if long_term_notes
                        else 0
                    ),
                },
            )

            return {"status": "completed", "long_term_count": len(long_term_notes)}

        except Exception as e:
            self.logger.error(
                "Long term notes check failed", error=str(e), exc_info=True
            )
            return {"error": str(e)}

    async def suggest_related_notes_integration(
        self, target_note_id: str
    ) -> dict[str, Any]:
        """関連メモ統合提案"""
        try:
            if not self.obsidian_manager:
                return {"error": "Obsidian manager not initialized"}

            # 対象ノートを取得
            target_note = await self.obsidian_manager.load_note(target_note_id)
            if not target_note:
                return {"error": "Target note not found"}

            # 関連ノートを検索（タグ、カテゴリ、キーワードベース）
            related_notes = await self._find_related_notes(target_note)

            if not related_notes:
                return {"status": "no_related_notes"}

            # 統合提案を生成
            integration_suggestions = await self._generate_integration_suggestions(
                target_note, related_notes
            )

            return {
                "status": "completed",
                "target_note": target_note.title,
                "related_count": len(related_notes),
                "suggestions": integration_suggestions,
            }

        except Exception as e:
            self.logger.error(
                "Related notes suggestion failed", error=str(e), exc_info=True
            )
            return {"error": str(e)}

    async def _analyze_unorganized_notes(self, notes: list) -> list[dict[str, Any]]:
        """未整理メモの分析とカテゴリ提案"""
        suggestions = []

        for note in notes[:10]:  # 最大10件を分析
            try:
                # タグやカテゴリから推定
                suggested_folder = "02_Areas"  # デフォルト
                reasoning = "一般的な整理が必要"

                if note.frontmatter.ai_category:
                    category = note.frontmatter.ai_category.lower()
                    if "task" in category or "todo" in category:
                        suggested_folder = "02_Tasks"
                        reasoning = "タスク関連の内容"
                    elif "finance" in category or "money" in category:
                        suggested_folder = "20_Finance"
                        reasoning = "家計・金融関連の内容"
                    elif "idea" in category or "insight" in category:
                        suggested_folder = "01_Projects"
                        reasoning = "アイデア・プロジェクト関連"

                suggestions.append(
                    {
                        "note_title": note.title or "Untitled",
                        "note_path": str(note.file_path),
                        "suggested_folder": suggested_folder,
                        "reasoning": reasoning,
                        "created_days_ago": (datetime.now() - note.created_at).days,
                    }
                )

            except Exception as e:
                self.logger.warning(
                    f"Failed to analyze note {note.title}", error=str(e)
                )
                continue

        return suggestions

    async def _generate_monthly_ai_summary(
        self, notes: list, month: date
    ) -> str | None:
        """AIによる月次サマリー生成"""
        try:
            if not self.ai_processor:
                return None

            # ノート内容を統合してプロンプトを作成
            categories: dict[str, int] = {}
            total_words = 0

            for note in notes[:50]:  # 最大50ノートを分析
                if note.content:
                    total_words += len(note.content.split())

                if note.frontmatter.ai_category:
                    category = note.frontmatter.ai_category
                    categories[category] = categories.get(category, 0) + 1

            prompt = f"""
{month.strftime("%Y年%m月")}の活動サマリーを生成してください。

統計情報:
- 総ノート数: {len(notes)}件
- 総文字数: 約{total_words}語
- 主要カテゴリ: {dict(list(categories.items())[:5])}

以下の観点でサマリーを作成してください:
1. 活動の概要
2. 主要なテーマやトピック
3. 生産性の傾向
4. 来月への提案

日本語で300文字程度で簡潔にまとめてください。
"""

            result = await self.ai_processor.process_text(prompt)
            return result.summary if result and result.summary else None

        except Exception as e:
            self.logger.error("AI summary generation failed", error=str(e))
            return None

    async def _find_related_notes(self, target_note: Any) -> list:
        """関連ノートを検索"""
        related_notes: list[Any] = []

        try:
            if not self.obsidian_manager:
                return related_notes

            # タグベースの検索
            if target_note.frontmatter.tags or target_note.frontmatter.ai_tags:
                all_tags = (
                    target_note.frontmatter.tags + target_note.frontmatter.ai_tags
                )
                for tag in all_tags[:3]:  # 最大3タグで検索
                    tag_notes = await self.obsidian_manager.search_notes(
                        tags=[tag.lstrip("#")], limit=5
                    )
                    related_notes.extend(
                        [n for n in tag_notes if n.file_path != target_note.file_path]
                    )

            # カテゴリベースの検索
            if target_note.frontmatter.ai_category:
                # 同じカテゴリのノートを検索（簡易実装）
                all_notes = await self.obsidian_manager.search_notes(limit=100)
                category_notes = [
                    n
                    for n in all_notes
                    if (
                        n.frontmatter.ai_category == target_note.frontmatter.ai_category
                        and n.file_path != target_note.file_path
                    )
                ]
                related_notes.extend(category_notes[:5])

            # 重複除去
            seen = set()
            unique_related = []
            for note in related_notes:
                if note.file_path not in seen:
                    seen.add(note.file_path)
                    unique_related.append(note)

            return unique_related[:10]  # 最大10件

        except Exception as e:
            self.logger.error("Related notes search failed", error=str(e))
            return []

    async def _generate_integration_suggestions(
        self, target_note: Any, related_notes: Any
    ) -> list[dict[str, str]]:
        """統合提案生成"""
        suggestions = []

        for related_note in related_notes[:5]:
            suggestion = {
                "related_note_title": related_note.title or "Untitled",
                "related_note_path": str(related_note.file_path),
                "integration_type": "merge",
                "reasoning": "関連するトピックまたはタグを共有",
            }

            # より具体的な統合理由を生成
            common_tags = set(
                target_note.frontmatter.tags + target_note.frontmatter.ai_tags
            ) & set(related_note.frontmatter.tags + related_note.frontmatter.ai_tags)

            if common_tags:
                suggestion["reasoning"] = (
                    f"共通タグ: {', '.join(list(common_tags)[:3])}"
                )
            elif (
                target_note.frontmatter.ai_category
                == related_note.frontmatter.ai_category
            ):
                suggestion["reasoning"] = (
                    f"同一カテゴリ: {target_note.frontmatter.ai_category}"
                )

            suggestions.append(suggestion)

        return suggestions

    async def _send_review_notification(
        self, review_type: ReviewType, title: str, message: str, details: dict[str, Any]
    ) -> None:
        """レビュー通知送信"""
        if self.notification_system:
            await self.notification_system.send_notification(
                level=NotificationLevel.INFO,
                category=NotificationCategory.SYSTEM_EVENTS,
                title=title,
                message=message,
                details=details,
            )

    async def _send_weekly_review_notification(
        self, unorganized_notes: Any, suggestions: Any
    ) -> None:
        """週次レビュー通知送信"""
        if not self.notification_system:
            return

        embed_fields = []

        # 未整理メモリスト（最大5件）
        for i, note in enumerate(unorganized_notes[:5], 1):
            title = note.title or note.file_path.stem
            days_old = (datetime.now() - note.created_at).days
            embed_fields.append(
                {
                    "name": f"{i}. {title}",
                    "value": f"作成: {days_old}日前 | パス: {note.file_path.parent.name}",
                    "inline": False,
                }
            )

        if len(unorganized_notes) > 5:
            embed_fields.append(
                {
                    "name": "その他",
                    "value": f"さらに{len(unorganized_notes) - 5}件の未整理メモがあります。",
                    "inline": False,
                }
            )

        await self.notification_system.send_notification(
            level=NotificationLevel.WARNING,
            category=NotificationCategory.REMINDERS,
            title="📝 週次レビュー: 未整理メモの確認",
            message=f"{len(unorganized_notes)}件の未整理メモが見つかりました。整理をお勧めします。",
            details={
                "unorganized_count": len(unorganized_notes),
                "suggestions_count": len(suggestions),
            },
            embed_fields=embed_fields,
        )

    async def _send_monthly_summary_notification(
        self, summary_data: str, month: date
    ) -> None:
        """月次サマリー通知送信"""
        if not self.notification_system:
            return

        await self.notification_system.send_notification(
            level=NotificationLevel.SUCCESS,
            category=NotificationCategory.REMINDERS,
            title=f"📊 {month.strftime('%Y年%m月')} 活動サマリー",
            message=summary_data
            or f"{month.strftime('%Y年%m月')}の活動サマリーが生成されました。",
            details={
                "month": month.strftime("%Y-%m"),
                "ai_generated": bool(summary_data),
            },
        )

    async def _send_long_term_notes_notification(self, long_term_notes: Any) -> None:
        """長期滞在メモ通知送信"""
        if not self.notification_system:
            return

        embed_fields = []

        for item in long_term_notes[:5]:
            note = item["note"]
            days_old = item["days_old"]
            title = note.title or note.file_path.stem

            embed_fields.append(
                {
                    "name": f"📋 {title}",
                    "value": f"Inboxに{days_old}日間滞在中",
                    "inline": False,
                }
            )

        await self.notification_system.send_notification(
            level=NotificationLevel.WARNING,
            category=NotificationCategory.REMINDERS,
            title="⏰ 長期滞在メモのリマインダー",
            message=f"{len(long_term_notes)}件のメモが30日以上Inboxに残っています。",
            details={
                "long_term_count": len(long_term_notes),
                "oldest_days": (
                    max([item["days_old"] for item in long_term_notes])
                    if long_term_notes
                    else 0
                ),
            },
            embed_fields=embed_fields,
        )

    def _record_review(self, review_type: ReviewType, data: dict[str, Any]) -> None:
        """レビュー履歴記録"""
        record = {
            "timestamp": datetime.now(),
            "review_type": review_type.value,
            "data": data,
        }

        self.review_history.append(record)

        # 履歴サイズ制限
        if len(self.review_history) > 100:
            self.review_history = self.review_history[-100:]

    def get_review_history(self, limit: int = 20) -> list[dict[str, Any]]:
        """レビュー履歴取得"""
        sorted_history = sorted(
            self.review_history, key=lambda x: x["timestamp"], reverse=True
        )

        # 日時を文字列に変換してシリアライズ可能にする
        serializable_history = []
        for record in sorted_history[:limit]:
            serializable_record = record.copy()
            serializable_record["timestamp"] = record["timestamp"].isoformat()
            serializable_history.append(serializable_record)

        return serializable_history
