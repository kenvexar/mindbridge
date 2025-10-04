"""
AI 処理用のデータモデル
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProcessingCategory(Enum):
    """メッセージカテゴリ"""

    WORK = "仕事"
    LEARNING = "学習"
    PROJECT = "プロジェクト"
    LIFE = "生活"
    IDEA = "アイデア"
    FINANCE = "金融"
    TASKS = "タスク"
    HEALTH = "健康"
    OTHER = "その他"


class ProcessingPriority(Enum):
    """処理優先度"""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class AIModelConfig(BaseModel):
    """AI モデル設定"""

    model_name: str = "models/gemini-2.5-flash"
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=1024, ge=1, le=8192)
    top_p: float = Field(default=0.8, ge=0.0, le=1.0)
    top_k: int = Field(default=40, ge=1, le=100)


class ProcessingSettings(BaseModel):
    """AI 処理設定"""

    min_text_length: int = Field(default=3, ge=1)  # 3 文字以上で処理
    max_text_length: int = Field(default=8000, ge=1)
    enable_summary: bool = True
    enable_tags: bool = True
    enable_categorization: bool = True
    max_keywords: int = Field(default=5, ge=1, le=10)
    cache_duration_hours: int = Field(default=24, ge=1)
    retry_count: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=30, ge=5, le=300)

    def __post_init__(self):
        """初期化後の設定検証と強制修正"""
        # 🔧 FORCE FIX: min_text_length が異常に大きい場合は強制的に 3 に設定
        if self.min_text_length > 20:
            print(
                f"⚠️ WARNING: min_text_length was {self.min_text_length}, forcing to 3"
            )
            object.__setattr__(self, "min_text_length", 3)


class SummaryResult(BaseModel):
    """要約結果"""

    summary: str
    key_points: list[str] = Field(default_factory=list)
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    processing_time_ms: int
    model_used: str


class TagResult(BaseModel):
    """タグ抽出結果"""

    tags: list[str] = Field(default_factory=list)
    raw_keywords: list[str] = Field(default_factory=list)
    confidence_scores: dict[str, float] = Field(default_factory=dict)
    processing_time_ms: int
    model_used: str

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: list[str]) -> list[str]:
        """タグが正しい形式かチェック"""
        validated_tags = []
        for tag in v:
            # #が付いていない場合は追加
            if not tag.startswith("#"):
                tag = f"#{tag}"
            # 無効な文字を除去
            clean_tag = "".join(
                c for c in tag if c.isalnum() or c in ["#", "_", "-", "あ-んア-ン一-龯"]
            )
            if len(clean_tag) > 1:  # #だけでない場合
                validated_tags.append(clean_tag)
        return validated_tags[:10]  # 最大 10 個まで


class CategoryResult(BaseModel):
    """カテゴリ分類結果"""

    category: ProcessingCategory
    confidence_score: float = Field(ge=0.0, le=1.0)
    alternative_categories: list[dict[str, float]] = Field(default_factory=list)
    reasoning: str | None = None
    processing_time_ms: int
    model_used: str


class AIProcessingResult(BaseModel):
    """AI 処理の統合結果"""

    message_id: int
    processed_at: datetime
    summary: SummaryResult | None = None
    tags: TagResult | None = None
    category: CategoryResult | None = None
    total_processing_time_ms: int
    cache_hit: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    model_config = ConfigDict()


class ProcessingRequest(BaseModel):
    """AI 処理リクエスト"""

    message_id: int
    text_content: str
    settings: ProcessingSettings
    priority: ProcessingPriority = ProcessingPriority.NORMAL
    force_reprocess: bool = False
    requested_at: datetime = Field(default_factory=datetime.now)

    @field_validator("text_content")
    @classmethod
    def validate_text_content(cls, v: str) -> str:
        """テキスト内容のバリデーション"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Text content cannot be empty")
        return v.strip()


class ProcessingStats(BaseModel):
    """処理統計情報（メモリ最適化）"""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    total_processing_time_ms: int = 0
    average_processing_time_ms: float = 0.0
    total_tokens_used: int = 0
    api_calls_made: int = 0
    error_counts: dict[str, int] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)

    # メモリ最適化のための制限設定
    max_error_entries: int = Field(default=100, exclude=True)  # エラー種別数の上限

    def update_stats(self, result: AIProcessingResult, tokens_used: int = 0) -> None:
        """統計情報を更新（メモリ制限付き）"""
        self.total_requests += 1

        if result.errors:
            self.failed_requests += 1
            for error in result.errors:
                # エラー種別の蓄積制限
                if len(self.error_counts) >= self.max_error_entries:
                    # 最も古いエラーを削除（簡易的に LRU ）
                    oldest_error = min(self.error_counts.items(), key=lambda x: x[1])
                    del self.error_counts[oldest_error[0]]

                self.error_counts[error] = self.error_counts.get(error, 0) + 1
        else:
            self.successful_requests += 1

        if result.cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1
            self.api_calls_made += 1

        self.total_processing_time_ms += result.total_processing_time_ms
        self.total_tokens_used += tokens_used

        # 平均処理時間を更新
        if self.total_requests > 0:
            self.average_processing_time_ms = (
                self.total_processing_time_ms / self.total_requests
            )

        self.last_updated = datetime.now()

    def cleanup_old_errors(self, max_entries: int = 50) -> int:
        """古いエラーエントリをクリーンアップ"""
        if len(self.error_counts) <= max_entries:
            return 0

        # 発生回数の少ないエラーを削除
        sorted_errors = sorted(self.error_counts.items(), key=lambda x: x[1])
        to_remove = len(self.error_counts) - max_entries

        removed_count = 0
        for error, _ in sorted_errors[:to_remove]:
            del self.error_counts[error]
            removed_count += 1

        return removed_count

    def get_memory_usage_estimate(self) -> dict[str, Any]:
        """メモリ使用量の推定値を取得"""
        # 簡易的なメモリ使用量推定
        error_memory_bytes = sum(
            len(error.encode("utf-8")) for error in self.error_counts.keys()
        )
        base_memory_bytes = 200  # 基本フィールドの推定サイズ

        return {
            "total_bytes_estimate": error_memory_bytes + base_memory_bytes,
            "error_entries_count": len(self.error_counts),
            "error_memory_bytes": error_memory_bytes,
            "base_memory_bytes": base_memory_bytes,
        }


class ProcessingCache(BaseModel):
    """処理結果キャッシュ"""

    content_hash: str
    result: AIProcessingResult
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: datetime = Field(default_factory=datetime.now)

    def is_expired(self) -> bool:
        """キャッシュが期限切れかチェック"""
        return datetime.now() > self.expires_at

    def access(self) -> None:
        """キャッシュアクセス情報を更新"""
        self.access_count += 1
        self.last_accessed = datetime.now()


class CacheInfo(BaseModel):
    """キャッシュ統計情報"""

    total_entries: int
    memory_usage: float  # MB
    hit_rate: float  # 0.0-1.0


class ProcessingError(BaseModel):
    """処理エラー情報"""

    error_type: str
    error_message: str
    error_code: str | None = None
    occurred_at: datetime = Field(default_factory=datetime.now)
    retry_count: int = 0
    is_retryable: bool = True
    context: dict[str, Any] = Field(default_factory=dict)


class APIUsageInfo(BaseModel):
    """API 使用量情報"""

    requests_count: int = 0
    tokens_used: int = 0
    cost_estimated: float = 0.0
    rate_limit_remaining: int | None = None
    rate_limit_reset_at: datetime | None = None
    quota_remaining: int | None = None
    last_updated: datetime = Field(default_factory=datetime.now)

    def add_usage(self, tokens: int, estimated_cost: float = 0.0) -> None:
        """使用量を追加"""
        self.requests_count += 1
        self.tokens_used += tokens
        self.cost_estimated += estimated_cost
        self.last_updated = datetime.now()
