"""
Health data AI analyzer
"""

import uuid
from datetime import date, timedelta
from typing import Any

from src.ai.processor import AIProcessor
from src.health_analysis.models import (
    AnalysisReport,
    AnalysisType,
    ChangeDetection,
    ChangeType,
    HealthInsight,
    TrendAnalysis,
    WeeklyHealthSummary,
)
from src.integrations.garmin.models import HealthData
from src.utils.mixins import LoggerMixin

# Settings loaded lazily to avoid circular imports


class HealthDataAnalyzer(LoggerMixin):
    """健康データAI分析システム"""

    def __init__(self, ai_processor: AIProcessor | None = None):
        """
        初期化処理

        Args:
            ai_processor: AIProcessorインスタンス
        """
        self.ai_processor = ai_processor or AIProcessor()
        self.analysis_cache: dict[str, AnalysisReport] = {}
        self.last_weekly_analysis: date | None = None

        # 分析設定
        self.min_data_points = 3  # 最小データポイント数
        self.trend_threshold = 0.1  # トレンド検出閾値
        self.change_significance_threshold = 0.7  # 変化の有意性閾値

        self.logger.info("Health data analyzer initialized")

    async def generate_weekly_summary(
        self,
        health_data_list: list[HealthData],
        week_start: date,
        discord_activity_data: dict[str, Any] | None = None,
    ) -> AnalysisReport:
        """
        週次健康データサマリーを生成

        Args:
            health_data_list: 健康データのリスト
            week_start: 週の開始日
            discord_activity_data: Discord活動データ（オプション）

        Returns:
            AnalysisReport: 分析レポート
        """
        try:
            self.logger.info(
                "Generating weekly health summary", week_start=week_start.isoformat()
            )

            week_end = week_start + timedelta(days=6)
            report_id = f"weekly_{week_start.isoformat()}_{uuid.uuid4().hex[:8]}"

            # 週次サマリーを計算
            weekly_summary = self._calculate_weekly_summary(
                health_data_list, week_start, week_end
            )

            # トレンド分析
            trends = await self._analyze_trends(health_data_list, period_days=7)

            # 重要な変化を検出
            changes = await self.detect_significant_changes(health_data_list)

            # AI による洞察生成
            insights = await self._generate_ai_insights(
                weekly_summary, trends, changes, discord_activity_data
            )

            # レポート作成
            report = AnalysisReport(
                report_id=report_id,
                analysis_type=AnalysisType.WEEKLY_SUMMARY,
                start_date=week_start,
                end_date=week_end,
                summary=self._generate_summary_text(weekly_summary, insights),
                key_findings=self._extract_key_findings(insights, trends, changes),
                insights=insights,
                trends=trends,
                changes=changes,
                data_quality_score=self._calculate_data_quality_score(health_data_list),
                analyzed_days=len(health_data_list),
                missing_days=7 - len(health_data_list),
            )

            # キャッシュに保存
            self.analysis_cache[report_id] = report
            self.last_weekly_analysis = week_start

            self.logger.info(
                "Weekly health summary generated",
                report_id=report_id,
                insights_count=len(insights),
                trends_count=len(trends),
                changes_count=len(changes),
            )

            return report

        except Exception as e:
            self.logger.error(
                "Failed to generate weekly health summary",
                week_start=week_start.isoformat(),
                error=str(e),
                exc_info=True,
            )
            # エラー時は基本的なレポートを返す
            return self._create_error_report(week_start, week_end, str(e))

    def _calculate_weekly_summary(
        self, health_data_list: list[HealthData], week_start: date, week_end: date
    ) -> WeeklyHealthSummary:
        """週次サマリーを計算"""

        # 有効なデータをフィルタリング
        valid_data = [data for data in health_data_list if data.has_any_data]

        # 睡眠データの集計
        sleep_hours = []
        sleep_scores = []
        for data in valid_data:
            if data.sleep and data.sleep.is_valid:
                if data.sleep.total_sleep_hours:
                    sleep_hours.append(data.sleep.total_sleep_hours)
                if data.sleep.sleep_score:
                    sleep_scores.append(data.sleep.sleep_score)

        # 歩数データの集計
        daily_steps = []
        total_steps = 0
        active_days = 0
        for data in valid_data:
            if data.steps and data.steps.is_valid and data.steps.total_steps:
                daily_steps.append(data.steps.total_steps)
                total_steps += data.steps.total_steps
                if data.steps.total_steps >= 5000:  # アクティブ基準
                    active_days += 1

        # 心拍数データの集計
        resting_hrs = []
        for data in valid_data:
            if (
                data.heart_rate
                and data.heart_rate.is_valid
                and data.heart_rate.resting_heart_rate
            ):
                resting_hrs.append(data.heart_rate.resting_heart_rate)

        # ワークアウトデータの集計
        total_workouts = sum(len(data.activities) for data in valid_data)
        total_workout_minutes = 0
        for data in valid_data:
            for activity in data.activities:
                if activity.duration_minutes:
                    total_workout_minutes += activity.duration_minutes

        # データ完全性の計算
        expected_days = 7
        actual_days = len(valid_data)
        data_completeness = actual_days / expected_days

        # 欠損日の特定
        all_dates = set()
        current_date = week_start
        while current_date <= week_end:
            all_dates.add(current_date)
            current_date += timedelta(days=1)

        available_dates = set(
            data.date for data in health_data_list if data.has_any_data
        )
        missing_days = list(all_dates - available_dates)

        return WeeklyHealthSummary(
            week_start=week_start,
            week_end=week_end,
            avg_sleep_hours=(
                sum(sleep_hours) / len(sleep_hours) if sleep_hours else None
            ),
            avg_sleep_score=(
                sum(sleep_scores) / len(sleep_scores) if sleep_scores else None
            ),
            sleep_consistency=(
                self._calculate_consistency(sleep_hours)
                if len(sleep_hours) >= 3
                else None
            ),
            total_steps=total_steps if total_steps > 0 else None,
            avg_daily_steps=(
                sum(daily_steps) / len(daily_steps) if daily_steps else None
            ),
            active_days=active_days,
            avg_resting_hr=sum(resting_hrs) / len(resting_hrs) if resting_hrs else None,
            hr_variability=(
                self._calculate_variability([float(hr) for hr in resting_hrs])
                if len(resting_hrs) >= 3
                else None
            ),
            total_workouts=total_workouts,
            total_workout_minutes=(
                total_workout_minutes if total_workout_minutes > 0 else None
            ),
            data_completeness=data_completeness,
            missing_days=missing_days,
        )

    def _calculate_consistency(self, values: list[float]) -> float:
        """値の一貫性を計算（標準偏差の逆数）"""
        if len(values) < 2:
            return 1.0

        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance**0.5

        # 一貫性スコア: 標準偏差が小さいほど高い（0.0-1.0）
        if std_dev == 0:
            return 1.0
        return float(min(1.0, 1.0 / (1.0 + std_dev / mean)))

    def _calculate_variability(self, values: list[float]) -> float:
        """変動性を計算（変動係数）"""
        if len(values) < 2:
            return 0.0

        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0

        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance**0.5

        return float(std_dev / mean)  # 変動係数

    async def _analyze_trends(
        self, health_data_list: list[HealthData], period_days: int = 7
    ) -> list[TrendAnalysis]:
        """トレンド分析を実行"""
        trends = []

        # 各メトリクスのトレンド分析
        metrics = {
            "sleep_hours": lambda d: (
                d.sleep.total_sleep_hours if d.sleep and d.sleep.is_valid else None
            ),
            "sleep_score": lambda d: (
                d.sleep.sleep_score if d.sleep and d.sleep.is_valid else None
            ),
            "daily_steps": lambda d: (
                d.steps.total_steps if d.steps and d.steps.is_valid else None
            ),
            "resting_hr": lambda d: (
                d.heart_rate.resting_heart_rate
                if d.heart_rate and d.heart_rate.is_valid
                else None
            ),
        }

        for metric_name, extractor in metrics.items():
            values = []
            dates = []

            for data in health_data_list:
                value = extractor(data)
                if value is not None:
                    values.append(value)
                    dates.append(data.date)

            if len(values) >= self.min_data_points:
                trend = self._calculate_trend(metric_name, values, dates, period_days)
                if trend:
                    trends.append(trend)

        return trends

    def _calculate_trend(
        self, metric_name: str, values: list[float], dates: list[date], period_days: int
    ) -> TrendAnalysis | None:
        """単一メトリクスのトレンド計算"""
        if len(values) < 2:
            return None

        # 簡単な線形回帰でトレンドを計算
        n = len(values)
        x = list(range(n))
        y = values

        # 線形回帰の係数を計算
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x_val**2 for x_val in x)

        # 傾き（slope）を計算
        denominator = n * sum_x2 - sum_x**2
        slope = 0 if denominator == 0 else (n * sum_xy - sum_x * sum_y) / denominator

        # トレンド方向の判定
        trend_threshold = abs(sum_y / n) * self.trend_threshold  # 平均値の10%を閾値

        if slope > trend_threshold:
            trend_direction = "上昇"
        elif slope < -trend_threshold:
            trend_direction = "下降"
        else:
            trend_direction = "安定"

        # 変化率の計算
        first_value = values[0]
        last_value = values[-1]
        change_percentage = None
        if first_value != 0:
            change_percentage = ((last_value - first_value) / first_value) * 100

        # 信頼度の計算（データポイント数とトレンドの明確さに基づく）
        confidence = min(
            1.0, (len(values) / 7) * (abs(slope) / (trend_threshold + 0.001))
        )

        # 日本語での解釈を生成
        interpretation = self._interpret_trend(
            metric_name, trend_direction, change_percentage, confidence
        )

        return TrendAnalysis(
            metric_name=metric_name,
            period_days=period_days,
            trend_direction=trend_direction,
            change_percentage=change_percentage,
            average_value=sum(values) / len(values),
            confidence_level=confidence,
            data_points=len(values),
            interpretation=interpretation,
        )

    def _interpret_trend(
        self,
        metric_name: str,
        trend_direction: str,
        change_percentage: float | None,
        confidence: float,
    ) -> str:
        """トレンドの日本語解釈を生成"""

        # メトリクス名の日本語化
        metric_names_jp = {
            "sleep_hours": "睡眠時間",
            "sleep_score": "睡眠スコア",
            "daily_steps": "1日の歩数",
            "resting_hr": "安静時心拍数",
        }
        metric_jp = metric_names_jp.get(metric_name, metric_name)

        # 信頼度による修飾
        confidence_text = ""
        if confidence > 0.8:
            confidence_text = "明確な"
        elif confidence > 0.5:
            confidence_text = "やや"
        else:
            confidence_text = "わずかな"

        # 基本的な解釈
        base_interpretation = (
            f"{metric_jp}に{confidence_text}{trend_direction}傾向が見られます"
        )

        # 変化率による詳細化
        if change_percentage is not None and abs(change_percentage) > 10:
            intensity = "大きな" if abs(change_percentage) > 20 else "中程度の"
            base_interpretation += f"（{intensity}変化: {change_percentage:.1f}%）"

        return base_interpretation

    async def detect_significant_changes(
        self, health_data_list: list[HealthData]
    ) -> list[ChangeDetection]:
        """Public interface for significant change detection."""
        return await self._detect_significant_changes(health_data_list)

    async def _detect_significant_changes(
        self, health_data_list: list[HealthData]
    ) -> list[ChangeDetection]:
        """重要な変化を検出"""
        changes: list[ChangeDetection] = []

        if len(health_data_list) < 7:  # 最低1週間のデータが必要
            return changes

        # 最近3日と過去のベースライン（3-7日前）を比較
        recent_data = health_data_list[-3:]
        baseline_data = (
            health_data_list[-7:-3]
            if len(health_data_list) >= 7
            else health_data_list[:-3]
        )

        metrics = {
            "sleep_hours": lambda d: (
                d.sleep.total_sleep_hours if d.sleep and d.sleep.is_valid else None
            ),
            "daily_steps": lambda d: (
                d.steps.total_steps if d.steps and d.steps.is_valid else None
            ),
            "resting_hr": lambda d: (
                d.heart_rate.resting_heart_rate
                if d.heart_rate and d.heart_rate.is_valid
                else None
            ),
        }

        for metric_name, extractor in metrics.items():
            change = self._detect_metric_change(
                metric_name, extractor, recent_data, baseline_data
            )
            if change:
                changes.append(change)

        return changes

    def _detect_metric_change(
        self,
        metric_name: str,
        extractor: Any,
        recent_data: list[HealthData],
        baseline_data: list[HealthData],
    ) -> ChangeDetection | None:
        """個別メトリクスの変化検出"""

        # 最近のデータを抽出
        recent_values = [extractor(d) for d in recent_data if extractor(d) is not None]
        baseline_values = [
            extractor(d) for d in baseline_data if extractor(d) is not None
        ]

        if len(recent_values) < 2 or len(baseline_values) < 2:
            return None

        # 平均値を計算
        recent_avg = sum(recent_values) / len(recent_values)
        baseline_avg = sum(baseline_values) / len(baseline_values)

        # 変化量と変化率を計算
        magnitude = abs(recent_avg - baseline_avg)
        if baseline_avg == 0:
            return None

        change_ratio = abs((recent_avg - baseline_avg) / baseline_avg)

        # 有意な変化かどうかを判定
        if change_ratio < 0.1:  # 10%未満の変化は無視
            return None

        # 変化の種類を判定
        change_type = ChangeType.NO_CHANGE
        if recent_avg > baseline_avg:
            # 改善か悪化かはメトリクスによる
            if metric_name in ["sleep_hours", "daily_steps"]:  # 多い方が良い
                change_type = (
                    ChangeType.IMPROVEMENT
                    if change_ratio > 0.2
                    else ChangeType.SIGNIFICANT_CHANGE
                )
            else:  # resting_hr など、少ない方が良い場合
                change_type = (
                    ChangeType.DECLINE
                    if change_ratio > 0.2
                    else ChangeType.SIGNIFICANT_CHANGE
                )
        elif metric_name in ["sleep_hours", "daily_steps"]:  # 少ない方が悪い
            change_type = (
                ChangeType.DECLINE
                if change_ratio > 0.2
                else ChangeType.SIGNIFICANT_CHANGE
            )
        else:  # resting_hr など、少ない方が良い場合
            change_type = (
                ChangeType.IMPROVEMENT
                if change_ratio > 0.2
                else ChangeType.SIGNIFICANT_CHANGE
            )

        # 重要度スコアを計算
        significance_score = min(1.0, change_ratio * 2)  # 50%変化で最大スコア

        if significance_score < self.change_significance_threshold:
            return None

        # 検出日（最新データの日付）
        detection_date = recent_data[-1].date

        # 日本語説明を生成
        description = self._generate_change_description(
            metric_name, change_type, recent_avg, baseline_avg, change_ratio
        )

        # 推奨アクションを生成
        recommended_action = self._generate_recommended_action(metric_name, change_type)

        return ChangeDetection(
            metric_name=metric_name,
            change_type=change_type,
            magnitude=magnitude,
            detection_date=detection_date,
            baseline_period=len(baseline_data),
            baseline_average=baseline_avg,
            current_value=recent_avg,
            significance_score=significance_score,
            description=description,
            recommended_action=recommended_action,
        )

    def _generate_change_description(
        self,
        metric_name: str,
        change_type: ChangeType,
        recent_avg: float,
        baseline_avg: float,
        change_ratio: float,
    ) -> str:
        """変化の日本語説明を生成"""

        metric_names_jp = {
            "sleep_hours": "睡眠時間",
            "daily_steps": "1日の歩数",
            "resting_hr": "安静時心拍数",
        }
        metric_jp = metric_names_jp.get(metric_name, metric_name)

        change_direction = "増加" if recent_avg > baseline_avg else "減少"
        change_percentage = change_ratio * 100

        description = f"{metric_jp}が過去数日で{change_percentage:.1f}%{change_direction}しています"

        if change_type == ChangeType.IMPROVEMENT:
            description += "（改善傾向）"
        elif change_type == ChangeType.DECLINE:
            description += "（要注意）"

        return description

    def _generate_recommended_action(
        self, metric_name: str, change_type: ChangeType
    ) -> str | None:
        """推奨アクションを生成"""

        if change_type == ChangeType.IMPROVEMENT:
            return "この良い傾向を継続するよう心がけましょう"
        if change_type == ChangeType.DECLINE:
            action_map = {
                "sleep_hours": "十分な睡眠時間の確保を意識してください",
                "daily_steps": "日常的な歩行や運動を増やすことを検討してください",
                "resting_hr": "ストレス管理と適度な運動を心がけてください",
            }
            return action_map.get(
                metric_name, "生活習慣を見直してみることをお勧めします"
            )

        return None

    async def _generate_ai_insights(
        self,
        weekly_summary: WeeklyHealthSummary,
        trends: list[TrendAnalysis],
        changes: list[ChangeDetection],
        discord_activity_data: dict[str, Any] | None = None,
    ) -> list[HealthInsight]:
        """AIによる洞察生成"""
        try:
            # データを構造化してGemini APIに送信
            analysis_context = self._prepare_analysis_context(
                weekly_summary, trends, changes, discord_activity_data
            )

            # Gemini APIで分析
            ai_response = await self.ai_processor.process_text(
                text=analysis_context,
                message_id=0,  # Changed from string to int
            )

            # AI応答から洞察を抽出
            insights = self._parse_ai_insights(
                {
                    "content": ai_response.content
                    if hasattr(ai_response, "content")
                    else str(ai_response),
                    "ai_summary": ai_response.ai_summary
                    if hasattr(ai_response, "ai_summary")
                    else None,
                    "ai_tags": ai_response.ai_tags
                    if hasattr(ai_response, "ai_tags")
                    else [],
                    "ai_category": ai_response.ai_category
                    if hasattr(ai_response, "ai_category")
                    else None,
                }
            )

            return insights

        except Exception as e:
            self.logger.error("Failed to generate AI insights", error=str(e))
            # フォールバック: 基本的な洞察を生成
            return self._generate_fallback_insights(weekly_summary, trends, changes)

    def _prepare_analysis_context(
        self,
        weekly_summary: WeeklyHealthSummary,
        trends: list[TrendAnalysis],
        changes: list[ChangeDetection],
        discord_activity_data: dict[str, Any] | None = None,
    ) -> str:
        """AI分析用のコンテキストを準備"""

        context_parts = []

        # 週次サマリー
        context_parts.append("【週次健康データサマリー】")
        if weekly_summary.avg_sleep_hours:
            context_parts.append(
                f"平均睡眠時間: {weekly_summary.avg_sleep_hours:.1f}時間"
            )
        if weekly_summary.avg_sleep_score:
            context_parts.append(
                f"平均睡眠スコア: {weekly_summary.avg_sleep_score:.1f}"
            )
        if weekly_summary.avg_daily_steps:
            context_parts.append(f"平均歩数: {weekly_summary.avg_daily_steps:.0f}歩/日")
        if weekly_summary.avg_resting_hr:
            context_parts.append(
                f"平均安静時心拍数: {weekly_summary.avg_resting_hr:.0f}bpm"
            )

        context_parts.append(f"アクティブ日数: {weekly_summary.active_days}/7日")
        context_parts.append(f"データ完全性: {weekly_summary.data_completeness:.1%}")

        # トレンド情報
        if trends:
            context_parts.append("\n【トレンド分析】")
            for trend in trends:
                context_parts.append(f"- {trend.interpretation}")

        # 重要な変化
        if changes:
            context_parts.append("\n【重要な変化】")
            for change in changes:
                context_parts.append(f"- {change.description}")

        # Discord活動データ（もしあれば）
        if discord_activity_data:
            context_parts.append("\n【Discord活動パターン】")
            # 簡単な活動サマリーを追加
            # この部分は実装時に詳細化

        return "\n".join(context_parts)

    def _parse_ai_insights(self, ai_response: dict[str, Any]) -> list[HealthInsight]:
        """AI応答から洞察を抽出"""
        insights = []

        # AI応答の構造に依存するため、実装時に調整
        # ここでは基本的なパースロジックを示す
        try:
            processed_content = ai_response.get("processed_content", "")

            # 基本的な洞察を1つ作成（実際の実装では複数の洞察を抽出）
            insights.append(
                HealthInsight(
                    category="総合評価",
                    insight_type="ai_analysis",
                    title="週次健康データ分析",
                    description=processed_content,
                    confidence_score=0.8,
                    actionable=True,
                    recommended_actions=["継続的な健康データモニタリング"],
                    priority="medium",
                )
            )

        except Exception as e:
            self.logger.warning("Failed to parse AI insights", error=str(e))

        return insights

    def _generate_fallback_insights(
        self,
        weekly_summary: WeeklyHealthSummary,
        trends: list[TrendAnalysis],
        changes: list[ChangeDetection],
    ) -> list[HealthInsight]:
        """フォールバック洞察を生成"""
        insights = []

        # 睡眠に関する洞察
        if weekly_summary.avg_sleep_hours:
            if weekly_summary.avg_sleep_hours < 7:
                insights.append(
                    HealthInsight(
                        category="睡眠",
                        insight_type="sleep_duration",
                        title="睡眠不足の可能性",
                        description=f"平均睡眠時間が{weekly_summary.avg_sleep_hours:.1f}時間と、推奨される7-9時間を下回っています。",
                        confidence_score=0.9,
                        actionable=True,
                        recommended_actions=["就寝時間を早める", "睡眠環境を改善する"],
                        priority="high",
                    )
                )
            elif weekly_summary.avg_sleep_hours >= 8:
                insights.append(
                    HealthInsight(
                        category="睡眠",
                        insight_type="sleep_duration",
                        title="良好な睡眠時間",
                        description=f"平均睡眠時間が{weekly_summary.avg_sleep_hours:.1f}時間と適切な範囲内です。",
                        confidence_score=0.8,
                        actionable=False,
                        priority="low",
                    )
                )

        # 活動に関する洞察
        if weekly_summary.avg_daily_steps and weekly_summary.avg_daily_steps < 8000:
            insights.append(
                HealthInsight(
                    category="活動",
                    insight_type="daily_activity",
                    title="歩数不足の傾向",
                    description=f"1日平均{weekly_summary.avg_daily_steps:.0f}歩と、推奨される8000歩を下回っています。",
                    confidence_score=0.8,
                    actionable=True,
                    recommended_actions=[
                        "日常的な散歩を増やす",
                        "階段を使用する",
                        "通勤時に歩く距離を伸ばす",
                    ],
                    priority="medium",
                )
            )

        return insights

    def _generate_summary_text(
        self, weekly_summary: WeeklyHealthSummary, insights: list[HealthInsight]
    ) -> str:
        """サマリーテキストを生成"""

        summary_parts = []
        summary_parts.append(
            f"{weekly_summary.week_start.strftime('%Y年%m月%d日')}週の健康データ分析結果です。"
        )

        # データ完全性
        if weekly_summary.data_completeness >= 0.8:
            summary_parts.append("データの完全性は良好です。")
        else:
            summary_parts.append("一部データが欠損していますが、分析可能な範囲です。")

        # 主要な評価
        high_priority_insights = [i for i in insights if i.priority == "high"]
        if high_priority_insights:
            summary_parts.append(
                f"{len(high_priority_insights)}件の重要な課題が検出されました。"
            )
        else:
            summary_parts.append("重要な健康上の課題は検出されませんでした。")

        return " ".join(summary_parts)

    def _extract_key_findings(
        self,
        insights: list[HealthInsight],
        trends: list[TrendAnalysis],
        changes: list[ChangeDetection],
    ) -> list[str]:
        """主要な発見を抽出"""
        findings = []

        # 高優先度の洞察から
        for insight in insights:
            if insight.priority == "high":
                findings.append(insight.title)

        # 明確なトレンドから
        for trend in trends:
            if trend.confidence_level > 0.7:
                findings.append(trend.interpretation)

        # 重要な変化から
        for change in changes:
            if change.significance_score > 0.8:
                findings.append(change.description)

        return findings[:5]  # 最大5件

    def _calculate_data_quality_score(
        self, health_data_list: list[HealthData]
    ) -> float:
        """データ品質スコアを計算"""
        if not health_data_list:
            return 0.0

        total_data_points = 0
        available_data_points = 0

        for data in health_data_list:
            # 各データソースをチェック
            total_data_points += 4  # sleep, steps, heart_rate, activities

            if data.sleep and data.sleep.is_valid:
                available_data_points += 1
            if data.steps and data.steps.is_valid:
                available_data_points += 1
            if data.heart_rate and data.heart_rate.is_valid:
                available_data_points += 1
            if data.activities:
                available_data_points += 1

        return (
            available_data_points / total_data_points if total_data_points > 0 else 0.0
        )

    def _create_error_report(
        self, start_date: date, end_date: date, error_message: str
    ) -> AnalysisReport:
        """エラー時の基本レポートを作成"""
        return AnalysisReport(
            report_id=f"error_{start_date.isoformat()}",
            analysis_type=AnalysisType.WEEKLY_SUMMARY,
            start_date=start_date,
            end_date=end_date,
            summary=f"分析中にエラーが発生しました: {error_message}",
            key_findings=["データ分析エラー"],
            data_quality_score=0.0,
            analyzed_days=0,
            missing_days=7,
        )
