"""Note generator using templates"""

from datetime import datetime
from typing import Any

from .base import GeneratedNote
from .processor import TemplateProcessor
from .validator import TemplateValidator


class NoteGenerator:
    """ノート生成エンジン"""

    def __init__(self, template_processor: TemplateProcessor):
        self.template_processor = template_processor
        self.validator = TemplateValidator()

    async def generate_message_note(
        self,
        template: str,
        content: str,
        author: str,
        channel: str,
        timestamp: datetime,
        additional_context: dict[str, Any] | None = None,
    ) -> GeneratedNote:
        """メッセージからノートを生成"""
        context = await self._create_message_context(
            content, author, channel, timestamp, additional_context
        )

        is_valid, errors = await self.validator.validate_template(template, context)
        if not is_valid:
            raise ValueError(f"Template validation failed: {errors}")

        compiled_content, frontmatter = await self.template_processor.render_template(
            template, context
        )

        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{author}.md"
        return GeneratedNote(
            filename=filename, content=compiled_content, frontmatter=frontmatter
        )

    async def generate_daily_note(
        self, template: str, date: datetime, tasks: list[Any] | None = None
    ) -> GeneratedNote:
        """デイリーノートを生成"""
        context = {
            "date": date.strftime("%Y-%m-%d"),
            "date_full": date.strftime("%Y 年%m 月%d 日"),
            "weekday": date.strftime("%A"),
            "weekday_jp": self._get_japanese_weekday(date),
            "month_name": date.strftime("%B"),
            "month_name_jp": self._get_japanese_month(date),
            "year": date.year,
            "month": date.month,
            "day": date.day,
            "week_number": date.isocalendar()[1],
            "day_of_year": date.timetuple().tm_yday,
            "timestamp": date.isoformat(),
            "tasks": tasks or [],
            "task_count": len(tasks) if tasks else 0,
        }

        is_valid, errors = await self.validator.validate_template(template, context)
        if not is_valid:
            raise ValueError(f"Template validation failed: {errors}")

        compiled_content, frontmatter = await self.template_processor.render_template(
            template, context
        )

        filename = f"{date.strftime('%Y-%m-%d')}.md"
        return GeneratedNote(
            filename=filename, content=compiled_content, frontmatter=frontmatter
        )

    async def _create_message_context(
        self,
        content: str,
        author: str,
        channel: str,
        timestamp: datetime,
        additional_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """メッセージコンテキストを作成"""
        context = {
            "content": content,
            "author": author,
            "channel": channel,
            "timestamp": timestamp.isoformat(),
            "date": timestamp.strftime("%Y-%m-%d"),
            "time": timestamp.strftime("%H:%M:%S"),
            "year": timestamp.year,
            "month": timestamp.month,
            "day": timestamp.day,
            "hour": timestamp.hour,
            "minute": timestamp.minute,
            "weekday": timestamp.strftime("%A"),
            "weekday_jp": self._get_japanese_weekday(timestamp),
            "month_name": timestamp.strftime("%B"),
            "month_name_jp": self._get_japanese_month(timestamp),
        }

        if additional_context:
            context.update(additional_context)

        return context

    def _get_japanese_weekday(self, date: datetime) -> str:
        """日本語の曜日を取得"""
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        return weekdays[date.weekday()]

    def _get_japanese_month(self, date: datetime) -> str:
        """日本語の月名を取得"""
        return f"{date.month}月"
