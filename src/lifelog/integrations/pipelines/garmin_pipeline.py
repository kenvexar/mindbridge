"""Garmin 向け統合パイプライン"""

from __future__ import annotations

from structlog import get_logger

from ...models import LifelogCategory, LifelogEntry, LifelogType
from ..models import IntegrationData
from .base import IntegrationPipeline

logger = get_logger(__name__)


class GarminIntegrationPipeline(IntegrationPipeline):
    """Garmin データを LifelogEntry に変換するパイプライン"""

    async def convert(self, data: IntegrationData) -> LifelogEntry | None:
        processed = data.data or {}
        data_type = data.metadata.get("data_type", "unknown")

        if data_type == "activity":
            return self._convert_activity(data, processed)
        if data_type == "health":
            return self._convert_health(data, processed)

        logger.debug(
            "unsupported garmin data type",
            integration=data.integration_type,
            data_type=data_type,
        )
        return None

    def _convert_activity(
        self, data: IntegrationData, payload: dict
    ) -> LifelogEntry | None:
        activity_type = str(payload.get("activity_type", "運動")).lower()
        activity_name = payload.get("activity_name", "")
        duration_seconds = int(payload.get("duration", 0) or 0)
        distance_meters = float(payload.get("distance", 0) or 0.0)
        calories = payload.get("calories")

        distance_km = distance_meters / 1000 if distance_meters else 0.0
        duration_minutes = duration_seconds // 60

        title_parts = []
        if activity_name:
            title_parts.append(str(activity_name))
        else:
            title_parts.append(activity_type.replace("_", " ").title())

        if distance_km > 0:
            title_parts.append(f"{distance_km:.1f}km")
        if duration_minutes > 0:
            title_parts.append(f"{duration_minutes}分")

        title = " - ".join(title_parts)

        content_parts = [
            f"Garmin Connect から自動記録された{activity_type}アクティビティ",
        ]
        if duration_minutes > 0:
            content_parts.append(f"時間: {duration_minutes}分")
        if distance_km > 0:
            content_parts.append(f"距離: {distance_km:.2f}km")
        if calories:
            content_parts.append(f"消費カロリー: {calories}kcal")
        if payload.get("avg_heart_rate"):
            content_parts.append(f"平均心拍数: {payload['avg_heart_rate']}bpm")

        tags = ["運動", "Garmin", activity_type, "自動記録"]

        return LifelogEntry(
            category=LifelogCategory.HEALTH,
            type=LifelogType.EVENT,
            title=title,
            content="\n".join(content_parts),
            timestamp=data.timestamp,
            numeric_value=float(duration_seconds) if duration_seconds else None,
            unit="秒",
            tags=tags,
            source="garmin_integration",
            metadata={
                "external_id": data.source_id,
                "integration_name": data.integration_type,
                "garmin_data": payload,
            },
        )

    def _convert_health(
        self, data: IntegrationData, payload: dict
    ) -> LifelogEntry | None:
        steps = payload.get("steps")
        sleep_duration = payload.get("sleep_duration")
        resting_hr = payload.get("resting_heart_rate")
        weight = payload.get("weight")

        metrics = []
        if steps:
            metrics.append(f"歩数: {steps:,}歩")
        if sleep_duration:
            sleep_hours = float(sleep_duration) / 60
            metrics.append(f"睡眠: {sleep_hours:.1f}時間")
        if resting_hr:
            metrics.append(f"安静時心拍数: {resting_hr}bpm")
        if weight:
            metrics.append(f"体重: {float(weight):.1f}kg")

        date_str = data.timestamp.strftime("%Y 年%m 月%d 日")
        title = f"{date_str}の健康データ"
        if metrics:
            title = f"{title} - {metrics[0]}"

        content_sections = ["Garmin Connect から自動取得された健康データ"]
        if steps:
            content_sections.append(f"歩数: {steps:,}歩")
        if sleep_duration:
            sleep_hours = float(sleep_duration) / 60
            content_sections.append(f"睡眠: {sleep_hours:.1f}時間")
        if resting_hr:
            content_sections.append(f"安静時心拍数: {resting_hr}bpm")
        if payload.get("stress_level"):
            content_sections.append(f"ストレスレベル: {payload['stress_level']}")
        if weight:
            content_sections.append(f"体重: {float(weight):.1f}kg")

        numeric_value = float(steps) if steps else None

        return LifelogEntry(
            category=LifelogCategory.HEALTH,
            type=LifelogType.METRIC,
            title=title,
            content="\n".join(content_sections),
            timestamp=data.timestamp,
            numeric_value=numeric_value,
            unit="歩" if steps else None,
            tags=["Garmin", "健康", "自動記録"],
            source="garmin_integration",
            metadata={
                "external_id": data.source_id,
                "integration_name": data.integration_type,
                "garmin_data": payload,
            },
        )
