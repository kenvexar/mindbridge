"""
Enhanced notification and feedback system for MindBridge
"""

from datetime import datetime
from enum import Enum
from typing import Any

import discord
from discord.ext import commands

from src.utils.mixins import LoggerMixin


class NotificationLevel(str, Enum):
    """通知レベル"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    SYSTEM = "system"


class NotificationCategory(str, Enum):
    """通知カテゴリ"""

    MESSAGE_PROCESSING = "message_processing"
    AI_PROCESSING = "ai_processing"
    FILE_OPERATIONS = "file_operations"
    SYSTEM_EVENTS = "system_events"
    REMINDERS = "reminders"
    ERRORS = "errors"


class NotificationSystem(LoggerMixin):
    """統合通知システム"""

    def __init__(self, bot: commands.Bot | Any, channel_config: Any) -> None:
        self.bot = bot
        self.channel_config = channel_config
        self.notification_history: list[dict[str, Any]] = []
        self.max_history = 1000

        # 通知レベル別の設定
        self.level_colors = {
            NotificationLevel.INFO: 0x5865F2,  # Discord Blue
            NotificationLevel.WARNING: 0xFF9500,  # Orange
            NotificationLevel.ERROR: 0xFF0000,  # Red
            NotificationLevel.SUCCESS: 0x00FF00,  # Green
            NotificationLevel.SYSTEM: 0x9932CC,  # Dark Orchid
        }

        self.level_emojis = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.SUCCESS: "✅",
            NotificationLevel.SYSTEM: "🔧",
        }

    async def send_notification(
        self,
        level: NotificationLevel,
        category: NotificationCategory,
        title: str,
        message: str,
        details: dict[str, Any] | None = None,
        user_mention: str | None = None,
        embed_fields: list[dict[str, str]] | None = None,
    ) -> bool:
        """
        統合通知送信機能

        Args:
            level: 通知レベル
            category: 通知カテゴリ
            title: 通知タイトル
            message: メッセージ本文
            details: 追加詳細情報
            user_mention: メンション対象ユーザー
            embed_fields: 埋め込みフィールド
        """
        try:
            # 通知先チャンネル決定（デフォルトチャンネルのみ使用）
            channel = self.channel_config.get_channel("notifications")

            if not channel:
                self.logger.warning("Notification channel not found")
                return False

            # 埋め込み作成
            embed = discord.Embed(
                title=f"{self.level_emojis[level]} {title}",
                description=message,
                color=self.level_colors[level],
                timestamp=datetime.now(),
            )

            # カテゴリ情報
            embed.add_field(name="カテゴリ", value=category.value, inline=True)

            # レベル情報
            embed.add_field(name="レベル", value=level.value.upper(), inline=True)

            # 追加フィールド
            if embed_fields:
                for field in embed_fields:
                    embed.add_field(
                        name=field.get("name", "情報"),
                        value=field.get("value", "N/A"),
                        inline=bool(field.get("inline", False)),
                    )

            # 詳細情報
            if details:
                details_text = ""
                for key, value in details.items():
                    if isinstance(value, dict | list):
                        details_text += f"**{key}**: `{str(value)[:100]}{'...' if len(str(value)) > 100 else ''}`\n"
                    else:
                        details_text += f"**{key}**: {value}\n"

                if details_text:
                    embed.add_field(name="詳細情報", value=details_text, inline=False)

            # フッター設定
            embed.set_footer(text="MindBridge 通知システム")

            # メッセージ送信
            content = user_mention if user_mention else None
            if hasattr(channel, "send"):
                await channel.send(content=content, embed=embed)
            else:
                self.logger.error(
                    "Channel does not support sending messages",
                    channel_type=type(channel).__name__,
                )

            # 履歴に記録
            self._record_notification(level, category, title, message, details)

            self.logger.info(
                "Notification sent",
                level=level.value,
                category=category.value,
                title=title,
                channel_id=channel.id if channel else None,
            )

            return True

        except Exception as e:
            self.logger.error(
                "Failed to send notification",
                level=level.value,
                category=category.value,
                title=title,
                error=str(e),
                exc_info=True,
            )
            return False

    async def send_processing_complete_notification(
        self,
        message_id: int,
        channel_name: str,
        note_path: str,
        processing_details: dict[str, Any],
    ) -> None:
        """メッセージ処理完了通知"""
        await self.send_notification(
            level=NotificationLevel.SUCCESS,
            category=NotificationCategory.MESSAGE_PROCESSING,
            title="メッセージ処理完了",
            message=f"#{channel_name} のメッセージが正常に処理されました。",
            details={
                "message_id": message_id,
                "note_path": note_path,
                "processing_time": processing_details.get("processing_time", "不明"),
                "ai_processed": processing_details.get("ai_processed", False),
                "categories": processing_details.get("categories", []),
            },
            embed_fields=[
                {"name": "📝 保存先", "value": f"`{note_path}`", "inline": "False"}
            ],
        )

    async def send_error_notification(
        self,
        error_type: str,
        error_message: str,
        context: dict[str, Any],
        user_mention: str | None = None,
    ) -> None:
        """エラー通知"""
        await self.send_notification(
            level=NotificationLevel.ERROR,
            category=NotificationCategory.ERRORS,
            title=f"システムエラー: {error_type}",
            message=error_message,
            details=context,
            user_mention=user_mention,
        )

    async def send_system_event_notification(
        self,
        event_type: str,
        description: str,
        system_info: dict[str, Any] | None = None,
    ) -> None:
        """システムイベント通知"""
        await self.send_notification(
            level=NotificationLevel.SYSTEM,
            category=NotificationCategory.SYSTEM_EVENTS,
            title=f"システムイベント: {event_type}",
            message=description,
            details=system_info or {},
        )

    async def send_reminder_notification(
        self,
        reminder_type: str,
        items: list[dict[str, Any]],
    ) -> None:
        """リマインダー通知"""
        if not items:
            return

        # リマインダー種別に応じたメッセージ作成
        if reminder_type == "subscription_payments":
            title = "💰 定期購入支払いリマインダー"
            message = f"{len(items)}件の支払い予定があります。"
        elif reminder_type == "task_deadlines":
            title = "📋 タスク期限リマインダー"
            message = f"{len(items)}件のタスクが期限間近です。"
        else:
            title = f"🔔 {reminder_type} リマインダー"
            message = f"{len(items)}件のリマインダーがあります。"

        # 項目詳細をフィールドとして追加
        fields = []
        for i, item in enumerate(items[:5], 1):  # 最大5件表示
            fields.append(
                {
                    "name": f"{i}. {item.get('title', '不明')}",
                    "value": item.get("description", "N/A"),
                    "inline": False,
                }
            )

        if len(items) > 5:
            fields.append(
                {
                    "name": "その他",
                    "value": f"さらに{len(items) - 5}件のアイテムがあります。",
                    "inline": False,
                }
            )

        await self.send_notification(
            level=NotificationLevel.WARNING,
            category=NotificationCategory.REMINDERS,
            title=title,
            message=message,
            embed_fields=fields,
        )

    async def send_ai_processing_notification(
        self, success: bool, processing_info: dict[str, Any]
    ) -> None:
        """AI処理結果通知"""
        level = NotificationLevel.SUCCESS if success else NotificationLevel.WARNING
        title = "🤖 AI処理完了" if success else "🤖 AI処理制限"

        message = (
            "メッセージのAI処理が完了しました。"
            if success
            else "AI処理がスキップされました（制限到達）。"
        )

        await self.send_notification(
            level=level,
            category=NotificationCategory.AI_PROCESSING,
            title=title,
            message=message,
            details=processing_info,
        )

    def _record_notification(
        self,
        level: NotificationLevel,
        category: NotificationCategory,
        title: str,
        message: str,
        details: dict[str, Any] | None,
    ) -> None:
        """通知履歴に記録"""
        record = {
            "timestamp": datetime.now(),
            "level": level.value,
            "category": category.value,
            "title": title,
            "message": message,
            "details": details or {},
        }

        self.notification_history.append(record)

        # 履歴サイズ制限
        if len(self.notification_history) > self.max_history:
            self.notification_history = self.notification_history[-self.max_history :]

    def get_notification_history(
        self,
        limit: int = 50,
        level_filter: NotificationLevel | None = None,
        category_filter: NotificationCategory | None = None,
    ) -> list[dict[str, Any]]:
        """通知履歴取得"""
        filtered_history = self.notification_history

        if level_filter:
            filtered_history = [
                record
                for record in filtered_history
                if record["level"] == level_filter.value
            ]

        if category_filter:
            filtered_history = [
                record
                for record in filtered_history
                if record["category"] == category_filter.value
            ]

        # 最新順でソート
        filtered_history.sort(key=lambda x: x["timestamp"], reverse=True)

        return filtered_history[:limit]

    async def get_system_health_status(self) -> dict[str, Any]:
        """システムヘルス状態取得"""
        try:
            # 通知履歴から最近のエラー統計
            recent_errors = len(
                [
                    record
                    for record in self.notification_history
                    if (datetime.now() - record["timestamp"]).total_seconds() < 3600
                    and record["level"] == NotificationLevel.ERROR.value
                ]
            )

            recent_warnings = len(
                [
                    record
                    for record in self.notification_history
                    if (datetime.now() - record["timestamp"]).total_seconds() < 3600
                    and record["level"] == NotificationLevel.WARNING.value
                ]
            )

            # Discord接続状態
            discord_status = "正常" if self.bot.is_ready else "切断"

            # 基本的な統計
            total_notifications = len(self.notification_history)

            return {
                "discord_status": discord_status,
                "recent_errors": recent_errors,
                "recent_warnings": recent_warnings,
                "total_notifications": total_notifications,
                "system_uptime": self._calculate_uptime(),
                "last_check": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(
                "Failed to get system health status", error=str(e), exc_info=True
            )
            return {"error": "ヘルス状態の取得に失敗しました"}

    def _calculate_uptime(self) -> str:
        """システム稼働時間計算"""
        try:
            if hasattr(self.bot, "_start_time"):
                uptime_delta = datetime.now() - self.bot._start_time
                hours = int(uptime_delta.total_seconds() // 3600)
                minutes = int((uptime_delta.total_seconds() % 3600) // 60)
                return f"{hours}時間{minutes}分"
            return "不明"
        except Exception:
            return "不明"
