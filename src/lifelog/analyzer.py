"""
ライフログ アナライザー

ライフログデータの分析とインサイト生成
"""

from datetime import date, timedelta
from typing import Any, cast

import numpy as np
import structlog
from sklearn.linear_model import LinearRegression

from ..ai.processor import AIProcessor
from .manager import LifelogManager
from .models import (
    LifelogCategory,
    LifelogType,
    LifeTrend,
    MonthlyLifeReport,
    WeeklyLifeReport,
)

logger = structlog.get_logger(__name__)


class LifelogAnalyzer:
    """ライフログデータ分析システム"""

    def __init__(self, lifelog_manager: LifelogManager, ai_processor: AIProcessor):
        self.lifelog_manager = lifelog_manager
        self.ai_processor = ai_processor

    async def generate_weekly_report(self, week_start: date) -> WeeklyLifeReport:
        """週次レポートを生成"""
        week_end = week_start + timedelta(days=6)

        # 週間のエントリーを取得
        entries = await self.lifelog_manager.get_entries_by_date_range(
            week_start, week_end
        )

        # 基本統計
        total_entries = len(entries)
        daily_average = total_entries / 7.0

        # 日別エントリー数を計算
        daily_counts: dict[date, int] = {}
        for entry in entries:
            day = entry.timestamp.date()
            daily_counts[day] = daily_counts.get(day, 0) + 1

        most_active_day = (
            max(daily_counts, key=lambda x: daily_counts[x]).strftime("%A")
            if daily_counts
            else None
        )

        # 気分・エネルギートレンド
        mood_trend, energy_trend = self._calculate_mood_energy_trends(entries)

        # 習慣パフォーマンス
        habit_success_rates = await self._calculate_habit_success_rates(
            entries, week_start, week_end
        )
        improving_habits, declining_habits = await self._identify_habit_trends(
            habit_success_rates
        )

        # カテゴリ分析
        category_distribution = self._calculate_category_distribution(entries)
        focus_areas, neglected_areas = self._identify_focus_areas(category_distribution)

        # AI 生成のハイライトと学び
        achievements = await self._generate_weekly_achievements(entries)
        learnings = await self._generate_weekly_learnings(entries)
        next_week_goals = await self._generate_next_week_goals(entries)

        return WeeklyLifeReport(
            week_start=week_start,
            week_end=week_end,
            total_entries=total_entries,
            daily_average=daily_average,
            most_active_day=most_active_day,
            mood_trend=mood_trend,
            energy_trend=energy_trend,
            habit_success_rates=habit_success_rates,
            improving_habits=improving_habits,
            declining_habits=declining_habits,
            category_distribution=category_distribution,
            focus_areas=focus_areas,
            neglected_areas=neglected_areas,
            achievements=achievements,
            learnings=learnings,
            next_week_goals=next_week_goals,
        )

    async def generate_monthly_report(self, month: int, year: int) -> MonthlyLifeReport:
        """月次レポートを生成"""
        # 月の開始・終了日
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        # 月間のエントリーを取得
        entries = await self.lifelog_manager.get_entries_by_date_range(
            start_date, end_date
        )

        # 基本統計
        total_entries = len(entries)
        days_in_month = (end_date - start_date).days + 1
        daily_average = total_entries / days_in_month

        # 長期トレンド分析
        mood_trend_monthly = self._analyze_monthly_mood_trend(entries)
        energy_trend_monthly = self._analyze_monthly_energy_trend(entries)

        # 習慣マスタリー分析
        consistent_habits = await self._identify_consistent_habits(month, year)
        emerging_habits = await self._identify_emerging_habits(month, year)
        dropped_habits = await self._identify_dropped_habits(month, year)

        # AI 生成のまとめ
        major_achievements = await self._generate_major_achievements(entries)
        key_learnings = await self._generate_key_learnings(entries)
        recommendations = await self._generate_monthly_recommendations(entries)

        return MonthlyLifeReport(
            month=month,
            year=year,
            total_entries=total_entries,
            daily_average=daily_average,
            mood_trend_monthly=mood_trend_monthly,
            energy_trend_monthly=energy_trend_monthly,
            consistent_habits=consistent_habits,
            emerging_habits=emerging_habits,
            dropped_habits=dropped_habits,
            major_achievements=major_achievements,
            key_learnings=key_learnings,
            recommendations=recommendations,
        )

    async def analyze_life_trend(
        self, metric_name: str, start_date: date, end_date: date
    ) -> LifeTrend:
        """生活トレンドを分析"""
        entries = await self.lifelog_manager.get_entries_by_date_range(
            start_date, end_date
        )

        # メトリック別にデータポイントを収集
        data_points = []

        if metric_name == "mood":
            data_points = self._extract_mood_data_points(entries)
        elif metric_name == "energy":
            data_points = self._extract_energy_data_points(entries)
        elif metric_name == "activity_count":
            data_points = self._extract_activity_count_data_points(
                entries, start_date, end_date
            )

        if not data_points:
            # データなしの場合のデフォルト
            return LifeTrend(
                metric_name=metric_name,
                period_type="daily",
                start_date=start_date,
                end_date=end_date,
                data_points=[],
                trend_direction="stable",
                trend_strength=0.0,
                average_value=0.0,
                min_value=0.0,
                max_value=0.0,
                standard_deviation=0.0,
                insights=["データが不足しています"],
                recommendations=["もっとデータを記録してみましょう"],
            )

        # 統計計算
        values = [point["value"] for point in data_points]
        average_value = np.mean(values)
        min_value = np.min(values)
        max_value = np.max(values)
        std_dev = np.std(values)

        # トレンド分析
        trend_direction, trend_strength = self._calculate_trend_direction(data_points)

        # インサイトと推奨事項を生成
        insights = await self._generate_trend_insights(
            metric_name, data_points, trend_direction
        )
        recommendations = await self._generate_trend_recommendations(
            metric_name, trend_direction
        )

        return LifeTrend(
            metric_name=metric_name,
            period_type="daily",
            start_date=start_date,
            end_date=end_date,
            data_points=data_points,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            average_value=float(average_value),
            min_value=float(min_value),
            max_value=float(max_value),
            standard_deviation=float(std_dev),
            insights=insights,
            recommendations=recommendations,
        )

    async def find_correlations(
        self, start_date: date, end_date: date
    ) -> list[tuple[str, str, float]]:
        """メトリクス間の相関を発見"""
        entries = await self.lifelog_manager.get_entries_by_date_range(
            start_date, end_date
        )

        # 日別にメトリクスを集計
        daily_metrics: dict[date, dict[str, Any]] = {}
        for entry in entries:
            day = entry.timestamp.date()
            if day not in daily_metrics:
                daily_metrics[day] = {
                    "mood": [],
                    "energy": [],
                    "activity_count": 0,
                    "categories": set(),
                }

            daily_metrics[day]["activity_count"] += 1
            daily_metrics[day]["categories"].add(entry.category)

            if entry.mood:
                daily_metrics[day]["mood"].append(entry.mood.value)
            if entry.energy_level:
                daily_metrics[day]["energy"].append(entry.energy_level)

        # 相関を計算
        correlations = []

        # 気分とエネルギーの相関
        mood_energy_data = []
        for day_data in daily_metrics.values():
            if day_data["mood"] and day_data["energy"]:
                mood_values = cast(list[float], day_data["mood"])
                energy_values = cast(list[float], day_data["energy"])
                avg_mood = np.mean(mood_values)
                avg_energy = np.mean(energy_values)
                mood_energy_data.append((avg_mood, avg_energy))

        if len(mood_energy_data) > 3:
            moods, energies = zip(*mood_energy_data, strict=False)
            correlation = np.corrcoef(moods, energies)[0, 1]
            if not np.isnan(correlation):
                correlations.append(("mood", "energy", correlation))

        return correlations

    def _calculate_mood_energy_trends(self, entries) -> tuple[list[float], list[float]]:
        """気分・エネルギーのトレンドを計算"""
        # 日別に平均を計算
        daily_mood: dict[date, list[float]] = {}
        daily_energy: dict[date, list[float]] = {}

        for entry in entries:
            day = entry.timestamp.date()

            if entry.mood:
                if day not in daily_mood:
                    daily_mood[day] = []
                daily_mood[day].append(entry.mood.value)

            if entry.energy_level:
                if day not in daily_energy:
                    daily_energy[day] = []
                daily_energy[day].append(entry.energy_level)

        # 平均を計算
        mood_trend = []
        energy_trend = []

        # 過去 7 日間の順序で整列
        sorted_days = sorted(daily_mood.keys()) if daily_mood else []

        for day in sorted_days:
            if day in daily_mood and daily_mood[day]:
                mood_trend.append(float(np.mean(daily_mood[day])))
            if day in daily_energy and daily_energy[day]:
                energy_trend.append(float(np.mean(daily_energy[day])))

        return mood_trend, energy_trend

    async def _calculate_habit_success_rates(
        self, entries, week_start: date, week_end: date
    ) -> dict[str, float]:
        """習慣の成功率を計算"""
        # 習慣関連のエントリーを抽出
        habit_entries = [
            e for e in entries if e.type == LifelogType.HABIT and e.related_habit_id
        ]

        # 習慣別に成功回数をカウント
        habit_counts = {}
        for entry in habit_entries:
            habit_id = entry.related_habit_id
            if habit_id not in habit_counts:
                habit_counts[habit_id] = 0
            habit_counts[habit_id] += 1

        # 成功率を計算（週 7 日を基準）
        success_rates = {}
        active_habits = await self.lifelog_manager.get_active_habits()

        for habit in active_habits:
            if habit.id in habit_counts:
                # 習慣の頻度に基づいて期待値を計算
                expected_count = 7 if habit.target_frequency == "daily" else 1
                success_rate = min((habit_counts[habit.id] / expected_count) * 100, 100)
                success_rates[habit.name] = success_rate
            else:
                success_rates[habit.name] = 0.0

        return success_rates

    async def _identify_habit_trends(
        self, success_rates: dict[str, float]
    ) -> tuple[list[str], list[str]]:
        """習慣のトレンドを特定"""
        # 簡単な分類（実際はもっと複雑な分析が可能）
        improving_habits = [name for name, rate in success_rates.items() if rate >= 80]
        declining_habits = [name for name, rate in success_rates.items() if rate < 50]

        return improving_habits, declining_habits

    def _calculate_category_distribution(self, entries) -> dict[str, int]:
        """カテゴリ分布を計算"""
        category_counts: dict[str, int] = {}
        for entry in entries:
            category = entry.category.value
            category_counts[category] = category_counts.get(category, 0) + 1

        return category_counts

    def _identify_focus_areas(
        self, category_distribution: dict[str, int]
    ) -> tuple[list[str], list[str]]:
        """重点分野と軽視分野を特定"""
        if not category_distribution:
            return [], []

        total_entries = sum(category_distribution.values())

        # 上位 3 カテゴリを重点分野とする
        sorted_categories = sorted(
            category_distribution.items(), key=lambda x: x[1], reverse=True
        )
        focus_areas = [
            cat for cat, count in sorted_categories[:3] if count / total_entries > 0.1
        ]

        # 下位カテゴリまたはゼロのものを軽視分野とする
        all_categories = {"health", "work", "learning", "finance", "mood", "routine"}
        neglected_areas = []

        for category in all_categories:
            if category not in category_distribution:
                neglected_areas.append(category)
            elif category_distribution[category] / total_entries < 0.05:
                neglected_areas.append(category)

        return focus_areas, neglected_areas[:3]  # 最大 3 つ

    async def _generate_weekly_achievements(self, entries) -> list[str]:
        """週間の達成事項を AI 生成"""
        if not entries:
            return []

        # 主要なエントリーから成果を抽出
        achievement_entries = []
        for entry in entries:
            if any(
                keyword in entry.content.lower()
                for keyword in ["完了", "達成", "成功", "finish", "complete", "achieve"]
            ):
                achievement_entries.append(entry.content)

        if not achievement_entries:
            return ["この週は新しい記録を開始しました！"]

        try:
            prompt = f"""
以下の活動記録から週間の主要な達成事項を 3 つ抽出してください：

{chr(10).join(achievement_entries[:5])}

簡潔で前向きな表現で、箇条書きで返してください。
"""

            response = await self.ai_processor.process_text(prompt, 123456)
            if response:
                achievements = [
                    line.strip("- ")
                    for line in (
                        response.summary.summary if response.summary else ""
                    ).split("\n")
                    if line.strip()
                ]
                return achievements[:3]  # 最大 3 つ

        except Exception as e:
            logger.warning("週間達成事項生成でエラー", error=str(e))

        return ["この週も様々な活動に取り組みました"]

    async def _generate_weekly_learnings(self, entries) -> list[str]:
        """週間の学びを AI 生成"""
        if not entries:
            return []

        try:
            # 学習・反省関連のエントリーを抽出
            learning_entries = []
            for entry in entries:
                if entry.category in [
                    LifelogCategory.LEARNING,
                    LifelogCategory.REFLECTION,
                ]:
                    learning_entries.append(entry.content)

            if not learning_entries:
                return ["継続的な記録が学習につながります"]

            prompt = f"""
以下の記録から週間で得られた主要な学びや気づきを 2 つ抽出してください：

{chr(10).join(learning_entries[:5])}

洞察的で建設的な表現で返してください。
"""

            response = await self.ai_processor.process_text(prompt, 123456)
            if response:
                learnings = [
                    line.strip("- ")
                    for line in (
                        response.summary.summary if response.summary else ""
                    ).split("\n")
                    if line.strip()
                ]
                return learnings[:2]

        except Exception as e:
            logger.warning("週間学び生成でエラー", error=str(e))

        return ["記録を通じて新たな気づきを得ました"]

    async def _generate_next_week_goals(self, entries) -> list[str]:
        """来週の目標を AI 生成"""
        try:
            # カテゴリ分布を分析
            category_counts = self._calculate_category_distribution(entries)

            prompt = f"""
今週の活動分布を見て、来週の改善目標を 2-3 個提案してください：

活動分布: {category_counts}

バランスの取れた生活向上を目指す具体的な目標を提案してください。
"""

            response = await self.ai_processor.process_text(prompt, 123456)
            if response:
                goals = [
                    line.strip("- ")
                    for line in (
                        response.summary.summary if response.summary else ""
                    ).split("\n")
                    if line.strip()
                ]
                return goals[:3]

        except Exception as e:
            logger.warning("来週目標生成でエラー", error=str(e))

        return ["バランスの取れた活動を心がけましょう"]

    def _analyze_monthly_mood_trend(self, entries) -> str:
        """月間気分トレンドを分析"""
        mood_values = [entry.mood.value for entry in entries if entry.mood]

        if not mood_values:
            return "stable"

        if len(mood_values) < 5:
            return "insufficient_data"

        # 前半と後半で比較
        mid_point = len(mood_values) // 2
        first_half_avg = np.mean(mood_values[:mid_point])
        second_half_avg = np.mean(mood_values[mid_point:])

        diff = second_half_avg - first_half_avg

        if diff > 0.5:
            return "improving"
        elif diff < -0.5:
            return "declining"
        else:
            return "stable"

    def _analyze_monthly_energy_trend(self, entries) -> str:
        """月間エネルギートレンドを分析"""
        energy_values = [entry.energy_level for entry in entries if entry.energy_level]

        if not energy_values:
            return "stable"

        if len(energy_values) < 5:
            return "insufficient_data"

        # 線形回帰でトレンドを分析
        x = np.array(range(len(energy_values))).reshape(-1, 1)
        y = np.array(energy_values)

        try:
            model = LinearRegression().fit(x, y)
            slope = model.coef_[0]

            if slope > 0.1:
                return "improving"
            elif slope < -0.1:
                return "declining"
            else:
                return "stable"
        except Exception:
            return "stable"

    def _extract_mood_data_points(self, entries) -> list[dict]:
        """気分データポイントを抽出"""
        mood_points = []
        for entry in entries:
            if entry.mood:
                mood_points.append(
                    {"date": entry.timestamp.date(), "value": float(entry.mood.value)}
                )

        return mood_points

    def _extract_energy_data_points(self, entries) -> list[dict]:
        """エネルギーデータポイントを抽出"""
        energy_points = []
        for entry in entries:
            if entry.energy_level:
                energy_points.append(
                    {"date": entry.timestamp.date(), "value": float(entry.energy_level)}
                )

        return energy_points

    def _extract_activity_count_data_points(
        self, entries, start_date: date, end_date: date
    ) -> list[dict]:
        """活動数データポイントを抽出"""
        # 日別にカウント
        daily_counts = {}
        current_date = start_date

        # 全ての日を初期化
        while current_date <= end_date:
            daily_counts[current_date] = 0
            current_date += timedelta(days=1)

        # エントリーをカウント
        for entry in entries:
            day = entry.timestamp.date()
            if day in daily_counts:
                daily_counts[day] += 1

        # データポイントに変換
        points = []
        for day, count in daily_counts.items():
            points.append({"date": day, "value": float(count)})

        return sorted(points, key=lambda x: x["date"])

    def _calculate_trend_direction(self, data_points) -> tuple[str, float]:
        """トレンドの方向と強さを計算"""
        if len(data_points) < 3:
            return "stable", 0.0

        values = [point["value"] for point in data_points]
        x = np.array(range(len(values))).reshape(-1, 1)
        y = np.array(values)

        try:
            model = LinearRegression().fit(x, y)
            slope = model.coef_[0]
            r_squared = model.score(x, y)

            # 傾きから方向を判定
            if abs(slope) < 0.01:
                direction = "stable"
            elif slope > 0:
                direction = "upward"
            else:
                direction = "downward"

            # R²値を強さとして使用
            strength = max(0.0, min(1.0, r_squared))

            return direction, strength

        except Exception:
            return "stable", 0.0

    async def _generate_trend_insights(
        self, metric_name: str, data_points, trend_direction: str
    ) -> list[str]:
        """トレンドからインサイトを生成"""
        try:
            recent_values = [p["value"] for p in data_points[-5:]]
            avg_recent = np.mean(recent_values) if recent_values else 0

            prompt = f"""
{metric_name}のトレンド分析結果からインサイトを生成してください：

- トレンド方向: {trend_direction}
- 最近の平均値: {avg_recent:.1f}
- データ期間: {len(data_points)}日間

2-3 個の具体的で建設的な洞察を提供してください。
"""

            response = await self.ai_processor.process_text(prompt, 123456)
            if response:
                insights = [
                    line.strip("- ")
                    for line in (
                        response.summary.summary if response.summary else ""
                    ).split("\n")
                    if line.strip()
                ]
                return insights[:3]

        except Exception as e:
            logger.warning("トレンドインサイト生成でエラー", error=str(e))

        return [f"{metric_name}のトレンドは{trend_direction}を示しています"]

    async def _generate_trend_recommendations(
        self, metric_name: str, trend_direction: str
    ) -> list[str]:
        """トレンドベースの推奨事項を生成"""
        try:
            prompt = f"""
{metric_name}が{trend_direction}トレンドを示している場合の改善提案を 2-3 個生成してください。

実行可能で具体的な行動提案をお願いします。
"""

            response = await self.ai_processor.process_text(prompt, 123456)
            if response:
                recommendations = [
                    line.strip("- ")
                    for line in (
                        response.summary.summary if response.summary else ""
                    ).split("\n")
                    if line.strip()
                ]
                return recommendations[:3]

        except Exception as e:
            logger.warning("トレンド推奨事項生成でエラー", error=str(e))

        return ["継続的な記録と観察を心がけましょう"]

    async def _identify_consistent_habits(self, month: int, year: int) -> list[str]:
        """一貫した習慣を特定"""
        # この月の習慣エントリーを分析
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        entries = await self.lifelog_manager.get_entries_by_date_range(
            start_date, end_date
        )
        habit_entries = [e for e in entries if e.type == LifelogType.HABIT]

        # 習慣別の頻度を計算
        habit_counts: dict[str, int] = {}
        for entry in habit_entries:
            if entry.related_habit_id:
                habit_counts[entry.related_habit_id] = (
                    habit_counts.get(entry.related_habit_id, 0) + 1
                )

        # 一貫性の高い習慣を特定（月の 70% 以上実行）
        days_in_month = (end_date - start_date).days + 1
        threshold = days_in_month * 0.7

        consistent_habits = []
        active_habits = await self.lifelog_manager.get_active_habits()

        for habit in active_habits:
            if habit.id in habit_counts and habit_counts[habit.id] >= threshold:
                consistent_habits.append(habit.name)

        return consistent_habits

    async def _identify_emerging_habits(self, month: int, year: int) -> list[str]:
        """新しく始まった習慣を特定"""
        # 実装を簡略化
        return ["新しい習慣の分析機能は開発中です"]

    async def _identify_dropped_habits(self, month: int, year: int) -> list[str]:
        """中断された習慣を特定"""
        # 実装を簡略化
        return []

    async def _generate_major_achievements(self, entries) -> list[str]:
        """主要な達成事項を生成"""
        achievement_entries = [
            e for e in entries if "達成" in e.content or "完了" in e.content
        ]

        if not achievement_entries:
            return ["この月も様々な活動に継続的に取り組みました"]

        try:
            contents = [e.content for e in achievement_entries[:10]]
            prompt = f"""
以下の月間活動記録から主要な達成事項を 3-4 個抽出してください：

{chr(10).join(contents)}

重要度の高い達成事項を優先して選んでください。
"""

            response = await self.ai_processor.process_text(prompt, 123456)
            if response:
                achievements = [
                    line.strip("- ")
                    for line in (
                        response.summary.summary if response.summary else ""
                    ).split("\n")
                    if line.strip()
                ]
                return achievements[:4]

        except Exception as e:
            logger.warning("主要達成事項生成でエラー", error=str(e))

        return ["継続的な努力により多くのことを成し遂げました"]

    async def _generate_key_learnings(self, entries) -> list[str]:
        """主要な学びを生成"""
        learning_entries = [
            e
            for e in entries
            if e.category in [LifelogCategory.LEARNING, LifelogCategory.REFLECTION]
        ]

        if not learning_entries:
            return ["記録を通じて自己理解が深まりました"]

        try:
            contents = [e.content for e in learning_entries[:10]]
            prompt = f"""
以下の学習・振り返り記録から主要な学びを 2-3 個抽出してください：

{chr(10).join(contents)}

深い洞察や今後に活かせる学びを重視してください。
"""

            response = await self.ai_processor.process_text(prompt, 123456)
            if response:
                learnings = [
                    line.strip("- ")
                    for line in (
                        response.summary.summary if response.summary else ""
                    ).split("\n")
                    if line.strip()
                ]
                return learnings[:3]

        except Exception as e:
            logger.warning("主要学び生成でエラー", error=str(e))

        return ["多様な経験を通じて成長を続けています"]

    async def _generate_monthly_recommendations(self, entries) -> list[str]:
        """月間の推奨事項を生成"""
        try:
            category_dist = self._calculate_category_distribution(entries)

            prompt = f"""
月間活動分析結果から来月の改善提案を 3-4 個生成してください：

活動分布: {category_dist}
総エントリー数: {len(entries)}

バランスの改善と継続的成長を重視した提案をお願いします。
"""

            response = await self.ai_processor.process_text(prompt, 123456)
            if response:
                recommendations = [
                    line.strip("- ")
                    for line in (
                        response.summary.summary if response.summary else ""
                    ).split("\n")
                    if line.strip()
                ]
                return recommendations[:4]

        except Exception as e:
            logger.warning("月間推奨事項生成でエラー", error=str(e))

        return [
            "バランスの取れた活動を継続しましょう",
            "新しい分野への挑戦も検討してみてください",
        ]
