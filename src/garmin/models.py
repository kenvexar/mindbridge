"""
Garmin health data models
"""

from datetime import date as date_type
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, computed_field


class DataSource(str, Enum):
    """データソース種別"""

    SLEEP = "sleep"
    STEPS = "steps"
    HEART_RATE = "heart_rate"
    ACTIVITIES = "activities"


class DataError(BaseModel):
    """データ取得エラー詳細"""

    source: DataSource = Field(description="エラーが発生したデータソース")
    error_type: str = Field(description="エラー種別")
    message: str = Field(description="エラーメッセージ")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="エラー発生時刻"
    )
    is_recoverable: bool = Field(default=True, description="回復可能なエラーかどうか")
    user_message: str | None = Field(default=None, description="ユーザー向けメッセージ")


class SleepData(BaseModel):
    """睡眠データモデル"""

    model_config = ConfigDict()

    date: date_type = Field(description="睡眠データの日付")
    total_sleep_hours: float | None = Field(
        default=None, description="総睡眠時間（時間）"
    )
    deep_sleep_hours: float | None = Field(
        default=None, description="深い睡眠時間（時間）"
    )
    light_sleep_hours: float | None = Field(
        default=None, description="浅い睡眠時間（時間）"
    )
    rem_sleep_hours: float | None = Field(
        default=None, description="REM睡眠時間（時間）"
    )
    awake_hours: float | None = Field(default=None, description="覚醒時間（時間）")
    sleep_score: int | None = Field(
        default=None, description="睡眠スコア", ge=0, le=100
    )
    bedtime: datetime | None = Field(default=None, description="就寝時刻")
    wake_time: datetime | None = Field(default=None, description="起床時刻")

    @property
    def is_valid(self) -> bool:
        """有効な睡眠データかどうかを判定"""
        return self.total_sleep_hours is not None and self.total_sleep_hours > 0


class StepsData(BaseModel):
    """歩数データモデル"""

    model_config = ConfigDict()

    date: date_type = Field(description="歩数データの日付")
    total_steps: int | None = Field(default=None, description="総歩数")
    distance_km: float | None = Field(default=None, description="移動距離（km）")
    calories_burned: int | None = Field(default=None, description="消費カロリー")
    floors_climbed: int | None = Field(default=None, description="上った階数")
    active_minutes: int | None = Field(default=None, description="アクティブ時間（分）")

    @property
    def is_valid(self) -> bool:
        """有効な歩数データかどうかを判定"""
        return self.total_steps is not None and self.total_steps > 0


class HeartRateData(BaseModel):
    """心拍数データモデル"""

    model_config = ConfigDict()

    date: date_type = Field(description="心拍数データの日付")
    resting_heart_rate: int | None = Field(
        default=None, description="安静時心拍数（bpm）"
    )
    max_heart_rate: int | None = Field(default=None, description="最大心拍数（bpm）")
    average_heart_rate: int | None = Field(
        default=None, description="平均心拍数（bpm）"
    )
    heart_rate_zones: dict[str, int] | None = Field(
        default=None, description="心拍数ゾーン時間（分）"
    )

    @property
    def is_valid(self) -> bool:
        """有効な心拍数データかどうかを判定"""
        return self.resting_heart_rate is not None and self.resting_heart_rate > 0


class ActivityData(BaseModel):
    """活動データモデル"""

    model_config = ConfigDict()

    date: date_type = Field(description="活動データの日付")
    activity_type: str = Field(description="活動タイプ（ランニング、ウォーキング等）")
    activity_name: str | None = Field(default=None, description="活動名")
    duration_minutes: int | None = Field(default=None, description="活動時間（分）")
    distance_km: float | None = Field(default=None, description="距離（km）")
    calories: int | None = Field(default=None, description="消費カロリー")
    average_pace: str | None = Field(default=None, description="平均ペース")
    average_heart_rate: int | None = Field(
        default=None, description="平均心拍数（bpm）"
    )
    start_time: datetime | None = Field(default=None, description="活動開始時刻")
    end_time: datetime | None = Field(default=None, description="活動終了時刻")

    @property
    def is_valid(self) -> bool:
        """有効な活動データかどうかを判定"""
        return self.duration_minutes is not None and self.duration_minutes > 0


class HealthData(BaseModel):
    """統合健康データモデル"""

    model_config = ConfigDict()

    date: date_type = Field(description="健康データの日付")
    sleep: SleepData | None = Field(default=None, description="睡眠データ")
    steps: StepsData | None = Field(default=None, description="歩数データ")
    heart_rate: HeartRateData | None = Field(default=None, description="心拍数データ")
    activities: list[ActivityData] = Field(
        default_factory=list, description="活動データリスト"
    )

    # メタデータ
    retrieved_at: datetime = Field(
        default_factory=datetime.now, description="データ取得時刻"
    )
    data_quality: str = Field(
        default="unknown", description="データ品質（good, partial, poor）"
    )
    errors: list[str] = Field(
        default_factory=list, description="取得時のエラーリスト（後方互換性）"
    )
    detailed_errors: list[DataError] = Field(
        default_factory=list, description="詳細なエラー情報"
    )
    is_cached_data: bool = Field(
        default=False, description="キャッシュされたデータかどうか"
    )
    cache_age_hours: float | None = Field(
        default=None, description="キャッシュの経過時間（時間）"
    )

    @property
    def has_any_data(self) -> bool:
        """何らかの有効なデータがあるかを判定"""
        return (
            (self.sleep and self.sleep.is_valid)
            or (self.steps and self.steps.is_valid)
            or (self.heart_rate and self.heart_rate.is_valid)
            or any(activity.is_valid for activity in self.activities)
        )

    @property
    def available_data_types(self) -> list[str]:
        """利用可能なデータタイプのリストを取得"""
        data_types = []
        if self.sleep and self.sleep.is_valid:
            data_types.append("sleep")
        if self.steps and self.steps.is_valid:
            data_types.append("steps")
        if self.heart_rate and self.heart_rate.is_valid:
            data_types.append("heart_rate")
        if self.activities:
            data_types.append("activities")
        return data_types

    @computed_field
    def failed_data_sources(self) -> list[DataSource]:
        """取得に失敗したデータソースのリスト"""
        return [error.source for error in self.detailed_errors]

    @computed_field
    def recoverable_errors(self) -> list[DataError]:
        """回復可能なエラーのリスト"""
        return [error for error in self.detailed_errors if error.is_recoverable]

    @computed_field
    def user_friendly_error_messages(self) -> list[str]:
        """ユーザー向けエラーメッセージのリスト"""
        messages = []
        for error in self.detailed_errors:
            if error.user_message:
                messages.append(error.user_message)
            else:
                # デフォルトのユーザー向けメッセージを生成
                source_names = {
                    DataSource.SLEEP: "睡眠データ",
                    DataSource.STEPS: "歩数データ",
                    DataSource.HEART_RATE: "心拍数データ",
                    DataSource.ACTIVITIES: "活動データ",
                }
                source_name = source_names.get(error.source, "健康データ")
                messages.append(f"{source_name}の取得に失敗しました")
        return messages

    def assess_data_quality(self) -> str:
        """データ品質を自動評価"""
        # Get available data types (computed field)
        available_data_list = self.available_data_types
        available_count = len(available_data_list)

        if available_count >= 3:
            return "good"
        if available_count >= 2:
            return "partial"
        if available_count >= 1:
            return "poor"
        return "no_data"


class GarminConnectionError(Exception):
    """Garmin Connect接続エラー"""


class GarminAuthenticationError(Exception):
    """Garmin Connect認証エラー"""


class GarminDataRetrievalError(Exception):
    """Garminデータ取得エラー"""


class GarminRateLimitError(Exception):
    """Garmin APIレート制限エラー"""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class GarminTimeoutError(Exception):
    """Garmin APIタイムアウトエラー"""


class GarminOfflineError(Exception):
    """オフライン・ネットワーク切断エラー"""
