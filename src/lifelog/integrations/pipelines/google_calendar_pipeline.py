"""Google Calendar 向け統合パイプライン"""

from __future__ import annotations

from structlog import get_logger

from ...models import LifelogCategory, LifelogEntry, LifelogType
from ..models import IntegrationData
from .base import IntegrationPipeline

logger = get_logger(__name__)


class GoogleCalendarPipeline(IntegrationPipeline):
    """Google Calendar データを LifelogEntry に変換するパイプライン"""

    async def convert(self, data: IntegrationData) -> LifelogEntry | None:
        payload = data.data or {}

        summary = payload.get("summary", "カレンダーイベント")
        description = payload.get("description", "")
        duration_minutes = int(payload.get("duration_minutes", 0) or 0)
        attendees = payload.get("attendees", [])
        location = payload.get("location")
        is_all_day = bool(payload.get("all_day", False))

        category = self._estimate_category(str(summary), str(description))

        title = f"📅 {summary}"
        content_parts = ["Google Calendar から自動記録されたイベント"]

        if description:
            content_parts.append(f"説明: {description}")

        if is_all_day:
            content_parts.append("終日イベント")
        elif duration_minutes:
            hours = duration_minutes // 60
            minutes = duration_minutes % 60
            if hours > 0:
                content_parts.append(f"時間: {hours}時間{minutes}分")
            else:
                content_parts.append(f"時間: {minutes}分")

        if attendees:
            content_parts.append(f"参加者: {len(attendees)}人")
        if location:
            content_parts.append(f"場所: {location}")

        tags = ["カレンダー", "Google Calendar", "自動記録"]
        tags.extend(self._category_tags(category))

        numeric_value = (
            float(duration_minutes) if duration_minutes and not is_all_day else None
        )

        return LifelogEntry(
            category=category,
            type=LifelogType.EVENT,
            title=title,
            content="\n".join(content_parts),
            timestamp=data.timestamp,
            numeric_value=numeric_value,
            unit="分" if numeric_value else None,
            tags=tags,
            location=location,
            source="google_calendar_integration",
            metadata={
                "external_id": data.source_id,
                "integration_name": data.integration_type,
                "calendar_data": payload,
            },
        )

    def _estimate_category(self, summary: str, description: str) -> LifelogCategory:
        text = f"{summary} {description}".lower()

        keyword_map = {
            LifelogCategory.WORK: [
                "会議",
                "ミーティング",
                "打ち合わせ",
                "プレゼン",
                "レビュー",
                "作業",
                "meeting",
                "work",
                "project",
                "presentation",
                "review",
            ],
            LifelogCategory.LEARNING: [
                "勉強",
                "学習",
                "セミナー",
                "講座",
                "研修",
                "トレーニング",
                "study",
                "learning",
                "seminar",
                "training",
                "course",
            ],
            LifelogCategory.HEALTH: [
                "ジム",
                "運動",
                "病院",
                "診察",
                "健康",
                "フィットネス",
                "gym",
                "exercise",
                "hospital",
                "health",
                "fitness",
                "workout",
            ],
            LifelogCategory.RELATIONSHIP: [
                "飲み会",
                "パーティー",
                "友達",
                "家族",
                "デート",
                "食事会",
                "party",
                "friend",
                "family",
                "date",
                "dinner",
                "lunch",
            ],
            LifelogCategory.ENTERTAINMENT: [
                "映画",
                "コンサート",
                "旅行",
                "観光",
                "ショッピング",
                "ゲーム",
                "movie",
                "concert",
                "travel",
                "shopping",
                "game",
                "entertainment",
            ],
        }

        for category, keywords in keyword_map.items():
            if any(keyword in text for keyword in keywords):
                return category

        return LifelogCategory.ROUTINE

    def _category_tags(self, category: LifelogCategory) -> list[str]:
        mapping = {
            LifelogCategory.WORK: ["会議", "仕事"],
            LifelogCategory.RELATIONSHIP: ["人間関係", "ミーティング"],
            LifelogCategory.LEARNING: ["学習", "勉強"],
            LifelogCategory.ENTERTAINMENT: ["娯楽", "イベント"],
        }
        return mapping.get(category, [])
