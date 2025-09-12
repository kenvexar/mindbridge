"""
Health analysis data models
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """変化の種類"""

    IMPROVEMENT = "improvement"
    DECLINE = "decline"
    SIGNIFICANT_CHANGE = "significant_change"
    NO_CHANGE = "no_change"


class AnalysisType(str, Enum):
    """分析の種類"""

    WEEKLY_SUMMARY = "weekly_summary"
    MONTHLY_SUMMARY = "monthly_summary"
    TREND_ANALYSIS = "trend_analysis"
    CHANGE_DETECTION = "change_detection"


class TrendAnalysis(BaseModel):
    """トレンド分析結果"""

    metric_name: str = Field(description="メトリクス名")
    period_days: int = Field(description="分析期間（日数）")
    trend_direction: str = Field(description="トレンドの方向（上昇/下降/安定）")
    change_percentage: float | None = Field(default=None, description="変化率（%）")
    average_value: float | None = Field(default=None, description="期間内の平均値")
    confidence_level: float = Field(description="信頼度（0.0-1.0）", ge=0.0, le=1.0)
    data_points: int = Field(description="分析に使用したデータポイント数")
    interpretation: str = Field(description="トレンドの解釈（日本語）")


class ChangeDetection(BaseModel):
    """重要な変化検知結果"""

    metric_name: str = Field(description="メトリクス名")
    change_type: ChangeType = Field(description="変化の種類")
    magnitude: float = Field(description="変化の大きさ")
    detection_date: date = Field(description="変化が検知された日付")
    baseline_period: int = Field(description="ベースライン期間（日数）")
    baseline_average: float | None = Field(
        default=None, description="ベースライン平均値"
    )
    current_value: float | None = Field(default=None, description="現在の値")
    significance_score: float = Field(
        description="重要度スコア（0.0-1.0）", ge=0.0, le=1.0
    )
    description: str = Field(description="変化の説明（日本語）")
    recommended_action: str | None = Field(default=None, description="推奨アクション")


class HealthInsight(BaseModel):
    """健康データの洞察"""

    category: str = Field(description="洞察のカテゴリ（睡眠、運動、心拍数など）")
    insight_type: str = Field(description="洞察のタイプ")
    title: str = Field(description="洞察のタイトル")
    description: str = Field(description="洞察の詳細説明")
    supporting_data: list[str] = Field(default_factory=list, description="裏付けデータ")
    confidence_score: float = Field(
        description="信頼度スコア（0.0-1.0）", ge=0.0, le=1.0
    )
    actionable: bool = Field(default=False, description="実行可能な洞察かどうか")
    recommended_actions: list[str] = Field(
        default_factory=list, description="推奨アクション"
    )
    priority: str = Field(description="優先度（high/medium/low）")


class AnalysisReport(BaseModel):
    """健康データ分析レポート"""

    report_id: str = Field(description="レポートID")
    analysis_type: AnalysisType = Field(description="分析タイプ")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成日時")

    # 対象期間
    start_date: date = Field(description="分析開始日")
    end_date: date = Field(description="分析終了日")

    # 分析結果
    summary: str = Field(description="全体サマリー（日本語）")
    key_findings: list[str] = Field(default_factory=list, description="主要な発見")
    insights: list[HealthInsight] = Field(
        default_factory=list, description="洞察リスト"
    )
    trends: list[TrendAnalysis] = Field(
        default_factory=list, description="トレンド分析"
    )
    changes: list[ChangeDetection] = Field(default_factory=list, description="変化検知")

    # メタデータ
    data_quality_score: float = Field(
        description="データ品質スコア（0.0-1.0）", ge=0.0, le=1.0
    )
    analyzed_days: int = Field(description="分析対象日数")
    missing_days: int = Field(description="欠損日数")

    # AI処理情報
    ai_processing_time: float | None = Field(
        default=None, description="AI処理時間（秒）"
    )
    gemini_tokens_used: int | None = Field(
        default=None, description="使用したGeminiトークン数"
    )

    def get_priority_insights(self, priority: str = "high") -> list[HealthInsight]:
        """指定した優先度の洞察を取得"""
        return [insight for insight in self.insights if insight.priority == priority]

    def get_actionable_insights(self) -> list[HealthInsight]:
        """実行可能な洞察を取得"""
        return [insight for insight in self.insights if insight.actionable]

    def get_significant_changes(
        self, min_significance: float = 0.7
    ) -> list[ChangeDetection]:
        """重要な変化を取得"""
        return [
            change
            for change in self.changes
            if change.significance_score >= min_significance
        ]


class WeeklyHealthSummary(BaseModel):
    """週次健康データサマリー"""

    week_start: date = Field(description="週の開始日（月曜日）")
    week_end: date = Field(description="週の終了日（日曜日）")

    # 睡眠データサマリー
    avg_sleep_hours: float | None = Field(default=None, description="平均睡眠時間")
    avg_sleep_score: float | None = Field(default=None, description="平均睡眠スコア")
    sleep_consistency: float | None = Field(
        default=None, description="睡眠時間の一貫性"
    )

    # 活動データサマリー
    total_steps: int | None = Field(default=None, description="週間総歩数")
    avg_daily_steps: float | None = Field(default=None, description="1日平均歩数")
    active_days: int = Field(default=0, description="アクティブ日数")

    # 心拍数データサマリー
    avg_resting_hr: float | None = Field(default=None, description="平均安静時心拍数")
    hr_variability: float | None = Field(default=None, description="心拍数の変動性")

    # 活動サマリー
    total_workouts: int = Field(default=0, description="ワークアウト回数")
    total_workout_minutes: int | None = Field(
        default=None, description="総ワークアウト時間"
    )

    # データ品質
    data_completeness: float = Field(
        description="データ完全性（0.0-1.0）", ge=0.0, le=1.0
    )
    missing_days: list[date] = Field(default_factory=list, description="データ欠損日")


class ActivityCorrelation(BaseModel):
    """活動相関分析"""

    date_range: str = Field(description="分析期間")
    correlation_type: str = Field(description="相関の種類")

    # Discord活動との相関
    discord_activity_correlation: dict[str, float] = Field(
        default_factory=dict, description="Discord活動との相関係数"
    )

    # 健康データ内相関
    sleep_steps_correlation: float | None = Field(
        default=None, description="睡眠と歩数の相関"
    )
    sleep_hr_correlation: float | None = Field(
        default=None, description="睡眠と心拍数の相関"
    )
    steps_hr_correlation: float | None = Field(
        default=None, description="歩数と心拍数の相関"
    )

    # 時間帯分析
    peak_activity_hours: list[int] = Field(
        default_factory=list, description="ピーク活動時間"
    )
    low_activity_hours: list[int] = Field(
        default_factory=list, description="低活動時間"
    )

    # 発見事項
    notable_patterns: list[str] = Field(
        default_factory=list, description="注目すべきパターン"
    )
    recommendations: list[str] = Field(default_factory=list, description="推奨事項")
