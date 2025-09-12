"""
統合システム用データモデル

各種外部サービス統合のための共通データモデルを定義
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class IntegrationData(BaseModel):
    """外部サービス統合データの基底モデル"""

    integration_type: str = Field(
        ..., description="統合タイプ（例： garmin, google_calendar ）"
    )
    source_id: str = Field(..., description="ソースシステムでの ID")
    timestamp: datetime = Field(..., description="データの作成・更新日時")
    data: dict[str, Any] = Field(default_factory=dict, description="統合データの内容")
    metadata: dict[str, Any] = Field(default_factory=dict, description="メタデータ")

    model_config = ConfigDict()

    @field_serializer("timestamp")
    def serialize_timestamp(self, value: datetime) -> str:
        """datetime を ISO format で出力"""
        return value.isoformat()


class GarminIntegrationData(IntegrationData):
    """Garmin Connect 統合データ"""

    integration_type: str = Field(default="garmin", description="統合タイプ")
    activity_type: str | None = Field(None, description="アクティビティタイプ")
    duration_seconds: int | None = Field(None, description="持続時間（秒）")
    distance_meters: float | None = Field(None, description="距離（メートル）")
    calories: int | None = Field(None, description="消費カロリー")


class GoogleCalendarIntegrationData(IntegrationData):
    """Google Calendar 統合データ"""

    integration_type: str = Field(default="google_calendar", description="統合タイプ")
    event_id: str | None = Field(None, description="カレンダーイベント ID")
    title: str | None = Field(None, description="イベントタイトル")
    start_time: datetime | None = Field(None, description="開始時刻")
    end_time: datetime | None = Field(None, description="終了時刻")
    attendees: list[str] | None = Field(default_factory=list, description="参加者")
