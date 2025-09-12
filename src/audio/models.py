"""
Audio processing data models
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AudioFormat(Enum):
    """サポートされる音声フォーマット"""

    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    OGG = "ogg"
    M4A = "m4a"
    WEBM = "webm"


class TranscriptionConfidence(Enum):
    """文字起こしの信頼度レベル"""

    HIGH = "high"  # 0.9以上
    MEDIUM = "medium"  # 0.7-0.89
    LOW = "low"  # 0.5-0.69
    VERY_LOW = "very_low"  # 0.5未満


class TranscriptionResult(BaseModel):
    """音声文字起こし結果"""

    transcript: str = Field(description="文字起こしされたテキスト")
    confidence: float = Field(description="信頼度スコア", ge=0.0, le=1.0)
    confidence_level: TranscriptionConfidence = Field(description="信頼度レベル")
    language_code: str = Field(description="検出された言語コード", default="ja-JP")

    # 詳細情報
    words: list[dict[str, Any]] | None = Field(
        default=None, description="単語レベルの詳細情報"
    )
    alternatives: list[dict[str, Any]] | None = Field(
        default=None, description="代替候補"
    )

    # メタデータ
    processing_time_ms: int = Field(description="処理時間（ミリ秒）")
    audio_duration_seconds: float | None = Field(
        default=None, description="音声の長さ（秒）"
    )
    api_used: str = Field(description="使用したAPI", default="google-speech")
    model_used: str = Field(description="使用したモデル")

    @classmethod
    def create_from_confidence(
        cls, transcript: str, confidence: float, **kwargs: Any
    ) -> "TranscriptionResult":
        """信頼度から適切なレベルを設定して作成"""
        if confidence >= 0.9:
            level = TranscriptionConfidence.HIGH
        elif confidence >= 0.7:
            level = TranscriptionConfidence.MEDIUM
        elif confidence >= 0.5:
            level = TranscriptionConfidence.LOW
        else:
            level = TranscriptionConfidence.VERY_LOW

        return cls(
            transcript=transcript,
            confidence=confidence,
            confidence_level=level,
            **kwargs,
        )


class AudioProcessingResult(BaseModel):
    """音声処理の全体結果"""

    # 基本情報
    success: bool = Field(description="処理が成功したか")
    transcription: TranscriptionResult | None = Field(
        default=None, description="文字起こし結果"
    )
    error_message: str | None = Field(default=None, description="エラーメッセージ")

    # ファイル情報
    original_filename: str = Field(description="元のファイル名")
    file_size_bytes: int = Field(description="ファイルサイズ（バイト）")
    audio_format: AudioFormat = Field(description="音声フォーマット")
    duration_seconds: float | None = Field(default=None, description="音声の長さ（秒）")

    # 処理情報
    processed_at: datetime = Field(default_factory=datetime.now, description="処理日時")
    processing_time_ms: int = Field(description="総処理時間（ミリ秒）")
    api_usage_minutes: float = Field(description="API使用量（分）", default=0.0)

    # フォールバック情報
    fallback_used: bool = Field(
        default=False, description="フォールバック処理が使用されたか"
    )
    fallback_reason: str | None = Field(default=None, description="フォールバック理由")
    saved_file_path: str | None = Field(
        default=None, description="保存されたファイルパス"
    )


class SpeechAPIUsage(BaseModel):
    """Speech API使用量追跡"""

    # 使用量情報
    monthly_usage_minutes: float = Field(description="月間使用量（分）", default=0.0)
    daily_usage_minutes: float = Field(description="日間使用量（分）", default=0.0)
    monthly_limit_minutes: int = Field(description="月間制限（分）", default=60)

    # 統計
    total_requests: int = Field(description="総リクエスト数", default=0)
    successful_requests: int = Field(description="成功リクエスト数", default=0)
    failed_requests: int = Field(description="失敗リクエスト数", default=0)

    # 日時
    last_reset_date: datetime = Field(
        default_factory=datetime.now, description="最後のリセット日"
    )
    last_updated: datetime = Field(
        default_factory=datetime.now, description="最終更新日時"
    )

    @property
    def usage_percentage(self) -> float:
        """使用率（パーセント）"""
        if self.monthly_limit_minutes == 0:
            return 0.0
        return (self.monthly_usage_minutes / self.monthly_limit_minutes) * 100

    @property
    def remaining_minutes(self) -> float:
        """残り時間（分）"""
        return max(0, self.monthly_limit_minutes - self.monthly_usage_minutes)

    @property
    def is_limit_exceeded(self) -> bool:
        """制限を超過しているか"""
        return self.monthly_usage_minutes >= self.monthly_limit_minutes

    def add_usage(self, duration_minutes: float, success: bool = True) -> None:
        """使用量を追加"""
        self.monthly_usage_minutes += duration_minutes
        self.daily_usage_minutes += duration_minutes
        self.total_requests += 1

        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1

        self.last_updated = datetime.now()

    def reset_monthly_usage(self) -> None:
        """月間使用量をリセット"""
        self.monthly_usage_minutes = 0.0
        self.last_reset_date = datetime.now()
        self.last_updated = datetime.now()

    def reset_daily_usage(self) -> None:
        """日間使用量をリセット"""
        self.daily_usage_minutes = 0.0
        self.last_updated = datetime.now()
