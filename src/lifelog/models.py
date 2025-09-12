"""
ライフログ データモデル

生活記録のための包括的なデータモデル定義
"""

from datetime import date, datetime, time
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LifelogCategory(str, Enum):
    """ライフログのカテゴリ"""

    HEALTH = "health"  # 健康・運動・睡眠
    WORK = "work"  # 仕事・プロジェクト
    LEARNING = "learning"  # 学習・スキル習得
    FINANCE = "finance"  # 財務・支出
    RELATIONSHIP = "relationship"  # 人間関係・社会活動
    ENTERTAINMENT = "entertainment"  # 娯楽・趣味
    ROUTINE = "routine"  # 日常的な活動
    REFLECTION = "reflection"  # 振り返り・感想
    GOAL = "goal"  # 目標・計画
    MOOD = "mood"  # 気分・感情


class LifelogType(str, Enum):
    """ライフログエントリーのタイプ"""

    EVENT = "event"  # 単発イベント
    HABIT = "habit"  # 習慣記録
    METRIC = "metric"  # 数値データ
    REFLECTION = "reflection"  # 振り返り・感想
    GOAL_PROGRESS = "goal_progress"  # 目標進捗


class MoodLevel(int, Enum):
    """気分レベル (1-5 スケール)"""

    VERY_BAD = 1
    BAD = 2
    NEUTRAL = 3
    GOOD = 4
    VERY_GOOD = 5


class LifelogEntry(BaseModel):
    """基本ライフログエントリー"""

    model_config = ConfigDict(use_enum_values=True)

    id: str | None = None
    timestamp: datetime = Field(default_factory=datetime.now)
    category: LifelogCategory
    type: LifelogType
    title: str
    content: str
    tags: list[str] = Field(default_factory=list)

    # 数値データ (メトリクス用)
    numeric_value: float | None = None
    unit: str | None = None

    # 気分・感情
    mood: MoodLevel | None = None
    energy_level: int | None = Field(None, ge=1, le=5)  # エネルギーレベル 1-5

    # 位置・場所情報
    location: str | None = None

    # 関連データ
    related_task_id: str | None = None
    related_goal_id: str | None = None
    related_habit_id: str | None = None

    # メタデータ
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = "manual"  # manual, discord, garmin, etc.

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class HabitTracker(BaseModel):
    """習慣追跡"""

    model_config = ConfigDict(use_enum_values=True)

    id: str | None = None
    name: str
    description: str | None = None
    category: LifelogCategory

    # 目標設定
    target_frequency: str  # daily, weekly, monthly
    target_value: float | None = None  # 数値目標 (例: 10000 歩)
    target_unit: str | None = None

    # 現在の状況
    current_streak: int = 0  # 連続達成日数
    best_streak: int = 0
    total_completions: int = 0

    # 日付範囲
    start_date: date
    end_date: date | None = None

    # 設定
    active: bool = True
    reminder_enabled: bool = True
    reminder_time: time | None = None

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class LifeGoal(BaseModel):
    """人生目標"""

    model_config = ConfigDict(use_enum_values=True)

    id: str | None = None
    title: str
    description: str
    category: LifelogCategory

    # 目標設定
    target_date: date | None = None
    target_value: float | None = None
    target_unit: str | None = None

    # 進捗
    current_value: float = 0
    progress_percentage: float = Field(0, ge=0, le=100)

    # ステータス
    status: str = "active"  # active, completed, paused, cancelled
    priority: int = Field(3, ge=1, le=5)  # 優先度 1-5

    # 関連
    parent_goal_id: str | None = None
    related_habits: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class LifelogMetrics(BaseModel):
    """ライフログ メトリクス"""

    # 期間
    date: date

    # 基本メトリクス
    total_entries: int = 0
    categories_used: list[LifelogCategory] = Field(default_factory=list)

    # 気分・エネルギー
    average_mood: float | None = None
    average_energy: float | None = None

    # 習慣達成率
    habits_completed: int = 0
    habits_total: int = 0
    habit_completion_rate: float = 0.0

    # 目標進捗
    goals_on_track: int = 0
    goals_behind: int = 0
    goals_completed: int = 0

    # カテゴリ別エントリー数
    category_counts: dict[str, int] = Field(default_factory=dict)


class DailyLifeSummary(BaseModel):
    """日次ライフ サマリー"""

    model_config = ConfigDict(use_enum_values=True)

    date: date

    # 基本統計
    total_entries: int
    categories_active: list[LifelogCategory]

    # 気分・エネルギー
    mood_average: float | None = None
    energy_average: float | None = None
    mood_trend: str | None = None  # improving, stable, declining

    # 習慣
    habits_completed: list[str] = Field(default_factory=list)
    habits_missed: list[str] = Field(default_factory=list)
    completion_rate: float = 0.0

    # 主要イベント
    key_events: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)

    # AI 分析
    ai_insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=datetime.now)


class WeeklyLifeReport(BaseModel):
    """週次ライフ レポート"""

    week_start: date
    week_end: date

    # 全体統計
    total_entries: int
    daily_average: float
    most_active_day: str | None = None

    # 気分・エネルギー トレンド
    mood_trend: list[float] = Field(default_factory=list)
    energy_trend: list[float] = Field(default_factory=list)
    mood_correlation: str | None = None

    # 習慣パフォーマンス
    habit_success_rates: dict[str, float] = Field(default_factory=dict)
    improving_habits: list[str] = Field(default_factory=list)
    declining_habits: list[str] = Field(default_factory=list)

    # 目標進捗
    goals_progress: dict[str, float] = Field(default_factory=dict)
    goals_achieved: list[str] = Field(default_factory=list)
    goals_at_risk: list[str] = Field(default_factory=list)

    # カテゴリ分析
    category_distribution: dict[str, int] = Field(default_factory=dict)
    focus_areas: list[str] = Field(default_factory=list)
    neglected_areas: list[str] = Field(default_factory=list)

    # 週間ハイライト
    achievements: list[str] = Field(default_factory=list)
    learnings: list[str] = Field(default_factory=list)
    next_week_goals: list[str] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=datetime.now)


class MonthlyLifeReport(BaseModel):
    """月次ライフ レポート"""

    month: int = Field(ge=1, le=12)
    year: int

    # 全体統計
    total_entries: int
    daily_average: float
    most_productive_week: str | None = None

    # 長期トレンド
    mood_trend_monthly: str  # improving, stable, declining
    energy_trend_monthly: str
    overall_life_satisfaction: float | None = Field(None, ge=1, le=10)

    # 習慣マスタリー
    consistent_habits: list[str] = Field(default_factory=list)
    emerging_habits: list[str] = Field(default_factory=list)
    dropped_habits: list[str] = Field(default_factory=list)
    habit_streak_records: dict[str, int] = Field(default_factory=dict)

    # 目標達成
    goals_completed: list[str] = Field(default_factory=list)
    goals_progress_summary: dict[str, str] = Field(default_factory=dict)
    new_goals_added: list[str] = Field(default_factory=list)

    # 月間振り返り
    major_achievements: list[str] = Field(default_factory=list)
    key_learnings: list[str] = Field(default_factory=list)
    challenges_overcome: list[str] = Field(default_factory=list)
    areas_for_improvement: list[str] = Field(default_factory=list)

    # 次月への提言
    recommendations: list[str] = Field(default_factory=list)
    focus_areas_next_month: list[str] = Field(default_factory=list)

    generated_at: datetime = Field(default_factory=datetime.now)


class LifeTrend(BaseModel):
    """生活トレンド分析"""

    metric_name: str
    period_type: str  # daily, weekly, monthly
    start_date: date
    end_date: date

    # データポイント
    data_points: list[dict[str, date | float]] = Field(default_factory=list)

    # トレンド分析
    trend_direction: str  # upward, downward, stable, fluctuating
    trend_strength: float = Field(ge=0, le=1)  # トレンドの強さ 0-1
    correlation_score: float | None = Field(None, ge=-1, le=1)

    # 統計
    average_value: float
    min_value: float
    max_value: float
    standard_deviation: float

    # 洞察
    insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # 関連要因
    correlated_metrics: list[str] = Field(default_factory=list)

    analyzed_at: datetime = Field(default_factory=datetime.now)
