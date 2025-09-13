"""
Health data and Discord activity integrator
"""

import statistics
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.garmin.models import HealthData
from src.health_analysis.models import ActivityCorrelation
from src.obsidian.file_manager import ObsidianFileManager
from src.utils.mixins import LoggerMixin


class HealthActivityIntegrator(LoggerMixin):
    """健康データと Discord 活動の時系列統合システム"""

    def __init__(self, file_manager: ObsidianFileManager) -> None:
        """
        初期化処理

        Args:
            file_manager: ObsidianFileManager インスタンス
        """
        self.file_manager = file_manager
        self.logger.info("Health-Activity integrator initialized")

    async def analyze_activity_correlation(
        self, health_data_list: list[HealthData], start_date: date, end_date: date
    ) -> ActivityCorrelation:
        """
        健康データと Discord 活動の相関分析

        Args:
            health_data_list: 健康データリスト
            start_date: 分析開始日
            end_date: 分析終了日

        Returns:
            ActivityCorrelation: 相関分析結果
        """
        try:
            self.logger.info(
                "Analyzing health-activity correlation",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                health_data_count=len(health_data_list),
            )

            # Discord 活動データを収集
            discord_activity = await self._collect_discord_activity_data(
                start_date, end_date
            )

            # 健康データを日付別に整理
            health_by_date = {
                data.date: data for data in health_data_list if data.has_any_data
            }

            # 相関分析を実行
            correlation_analysis = self._calculate_correlations(
                health_by_date, discord_activity, start_date, end_date
            )

            # パターン分析
            patterns = await self._analyze_activity_patterns(
                health_by_date, discord_activity
            )

            # 推奨事項を生成
            recommendations = self._generate_correlation_recommendations(
                correlation_analysis, patterns
            )

            result = ActivityCorrelation(
                date_range=f"{start_date.isoformat()} - {end_date.isoformat()}",
                correlation_type="health_discord_activity",
                discord_activity_correlation=correlation_analysis[
                    "discord_correlations"
                ],
                sleep_steps_correlation=correlation_analysis.get("sleep_steps"),
                sleep_hr_correlation=correlation_analysis.get("sleep_hr"),
                steps_hr_correlation=correlation_analysis.get("steps_hr"),
                peak_activity_hours=patterns["peak_hours"],
                low_activity_hours=patterns["low_hours"],
                notable_patterns=patterns["notable_patterns"],
                recommendations=recommendations,
            )

            self.logger.info(
                "Activity correlation analysis completed",
                notable_patterns_count=len(patterns["notable_patterns"]),
                recommendations_count=len(recommendations),
            )

            return result

        except Exception as e:
            self.logger.error(
                "Failed to analyze activity correlation", error=str(e), exc_info=True
            )
            # エラー時は空の相関分析を返す
            return ActivityCorrelation(
                date_range=f"{start_date.isoformat()} - {end_date.isoformat()}",
                correlation_type="health_discord_activity",
                discord_activity_correlation={},
                notable_patterns=[f"分析中にエラーが発生しました: {str(e)}"],
                recommendations=[],
            )

    async def _collect_discord_activity_data(
        self, start_date: date, end_date: date
    ) -> dict[date, dict[str, Any]]:
        """Discord 活動データを収集"""

        activity_data: dict[date, dict[str, Any]] = {}

        try:
            # デイリーノートから活動データを抽出
            current_date = start_date
            while current_date <= end_date:
                daily_activity = await self._extract_daily_activity(current_date)
                if daily_activity:
                    activity_data[current_date] = daily_activity
                current_date += timedelta(days=1)

            self.logger.debug(
                f"Collected Discord activity for {len(activity_data)} days"
            )

        except Exception as e:
            self.logger.warning("Failed to collect Discord activity data", error=str(e))

        return activity_data

    async def _extract_daily_activity(self, target_date: date) -> dict[str, Any] | None:
        """指定日の Discord 活動を抽出"""

        try:
            # デイリーノートの検索
            daily_notes = await self.file_manager.search_notes(
                date_from=datetime.combine(
                    target_date, datetime.min.time()
                ).isoformat(),
                date_to=datetime.combine(target_date, datetime.max.time()).isoformat(),
                limit=100,
            )

            if not daily_notes:
                return None

            activity_summary: dict[str, Any] = {
                "message_count": len(daily_notes),
                "active_hours": set(),
                "channel_activity": defaultdict(int),
                "content_length_total": 0,
                "ai_processed_count": 0,
                "categories": defaultdict(int),
                "tags": set(),
            }

            for note_result in daily_notes:
                # Load the actual note object
                note = await self.file_manager.load_note(Path(note_result["file_path"]))
                if not note:
                    continue
                # メッセージ時間の抽出
                if (
                    hasattr(note.frontmatter, "created")
                    and note.frontmatter.created
                    and hasattr(note.frontmatter.created, "hour")
                ):
                    hour = note.frontmatter.created.hour
                    activity_summary["active_hours"].add(hour)

                # チャンネル活動
                if hasattr(note.frontmatter, "channel_name"):
                    channel = getattr(note.frontmatter, "channel_name", "unknown")
                    activity_summary["channel_activity"][channel] += 1

                # コンテンツ長
                if hasattr(note.frontmatter, "character_count"):
                    char_count = getattr(note.frontmatter, "character_count", 0)
                    activity_summary["content_length_total"] += char_count

                # AI 処理済み
                if (
                    hasattr(note.frontmatter, "ai_processed")
                    and note.frontmatter.ai_processed
                ):
                    activity_summary["ai_processed_count"] += 1

                # カテゴリとタグ
                if (
                    hasattr(note.frontmatter, "ai_category")
                    and note.frontmatter.ai_category
                ):
                    activity_summary["categories"][note.frontmatter.ai_category] += 1

                ai_tags = getattr(note.frontmatter, "ai_tags", [])
                tags = getattr(note.frontmatter, "tags", [])
                for tag in ai_tags + tags:
                    activity_summary["tags"].add(tag.lstrip("#"))

            # データ型を統一
            activity_summary["active_hours"] = list(activity_summary["active_hours"])
            activity_summary["channel_activity"] = dict(
                activity_summary["channel_activity"]
            )
            activity_summary["categories"] = dict(activity_summary["categories"])
            activity_summary["tags"] = list(activity_summary["tags"])

            return activity_summary

        except Exception as e:
            self.logger.warning(
                "Failed to extract daily activity",
                date=target_date.isoformat(),
                error=str(e),
            )
            return None

    def _calculate_correlations(
        self,
        health_by_date: dict[date, HealthData],
        discord_activity: dict[date, dict[str, Any]],
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """相関分析を実行"""

        correlations: dict[str, Any] = {
            "discord_correlations": {},
            "sleep_steps": None,
            "sleep_hr": None,
            "steps_hr": None,
        }

        try:
            # 共通の日付でデータをペアリング
            common_dates = set(health_by_date.keys()) & set(discord_activity.keys())

            if len(common_dates) < 3:  # 最低 3 日のデータが必要
                self.logger.warning("Insufficient data for correlation analysis")
                return correlations

            # Discord 活動指標を抽出
            discord_metrics = self._extract_discord_metrics(
                discord_activity, common_dates
            )

            # 健康指標を抽出
            health_metrics = self._extract_health_metrics(health_by_date, common_dates)

            # Discord 活動と健康データの相関
            for discord_metric, discord_values in discord_metrics.items():
                for health_metric, health_values in health_metrics.items():
                    if (
                        len(discord_values) == len(health_values)
                        and len(discord_values) >= 3
                    ):
                        correlation = self._calculate_correlation_coefficient(
                            discord_values, health_values
                        )
                        if correlation is not None:
                            correlations["discord_correlations"][
                                f"{discord_metric}_vs_{health_metric}"
                            ] = correlation

            # 健康データ内の相関
            if "sleep_hours" in health_metrics and "daily_steps" in health_metrics:
                correlations["sleep_steps"] = self._calculate_correlation_coefficient(
                    health_metrics["sleep_hours"], health_metrics["daily_steps"]
                )

            if "sleep_hours" in health_metrics and "resting_hr" in health_metrics:
                correlations["sleep_hr"] = self._calculate_correlation_coefficient(
                    health_metrics["sleep_hours"], health_metrics["resting_hr"]
                )

            if "daily_steps" in health_metrics and "resting_hr" in health_metrics:
                correlations["steps_hr"] = self._calculate_correlation_coefficient(
                    health_metrics["daily_steps"], health_metrics["resting_hr"]
                )

        except Exception as e:
            self.logger.error("Error calculating correlations", error=str(e))

        return correlations

    def _extract_discord_metrics(
        self, discord_activity: dict[date, dict[str, Any]], common_dates: set[date]
    ) -> dict[str, list[float]]:
        """Discord 活動指標を抽出"""

        metrics: dict[str, list[float]] = {
            "message_count": [],
            "active_hours_count": [],
            "content_length_avg": [],
            "ai_processing_ratio": [],
        }

        for current_date in sorted(common_dates):
            activity = discord_activity[current_date]

            metrics["message_count"].append(float(activity["message_count"]))
            metrics["active_hours_count"].append(float(len(activity["active_hours"])))

            # 平均コンテンツ長
            if activity["message_count"] > 0:
                avg_content_length = (
                    activity["content_length_total"] / activity["message_count"]
                )
                metrics["content_length_avg"].append(avg_content_length)
            else:
                metrics["content_length_avg"].append(0.0)

            # AI 処理率
            if activity["message_count"] > 0:
                ai_ratio = activity["ai_processed_count"] / activity["message_count"]
                metrics["ai_processing_ratio"].append(ai_ratio)
            else:
                metrics["ai_processing_ratio"].append(0.0)

        return metrics

    def _extract_health_metrics(
        self, health_by_date: dict[date, HealthData], common_dates: set[date]
    ) -> dict[str, list[float]]:
        """健康指標を抽出"""

        metrics: dict[str, list[float]] = {
            "sleep_hours": [],
            "sleep_score": [],
            "daily_steps": [],
            "resting_hr": [],
        }

        for current_date in sorted(common_dates):
            health_data = health_by_date[current_date]

            # 睡眠データ
            if health_data.sleep and health_data.sleep.is_valid:
                if health_data.sleep.total_sleep_hours:
                    metrics["sleep_hours"].append(health_data.sleep.total_sleep_hours)
                else:
                    metrics["sleep_hours"].append(0.0)

                if health_data.sleep.sleep_score:
                    metrics["sleep_score"].append(float(health_data.sleep.sleep_score))
                else:
                    metrics["sleep_score"].append(0.0)
            else:
                metrics["sleep_hours"].append(0.0)
                metrics["sleep_score"].append(0.0)

            # 歩数データ
            if health_data.steps and health_data.steps.is_valid:
                if health_data.steps.total_steps:
                    metrics["daily_steps"].append(float(health_data.steps.total_steps))
                else:
                    metrics["daily_steps"].append(0.0)
            else:
                metrics["daily_steps"].append(0.0)

            # 心拍数データ
            if health_data.heart_rate and health_data.heart_rate.is_valid:
                if health_data.heart_rate.resting_heart_rate:
                    metrics["resting_hr"].append(
                        float(health_data.heart_rate.resting_heart_rate)
                    )
                else:
                    metrics["resting_hr"].append(0.0)
            else:
                metrics["resting_hr"].append(0.0)

        # 空のリストを削除
        metrics = {
            k: v for k, v in metrics.items() if v and not all(x == 0.0 for x in v)
        }

        return metrics

    def _calculate_correlation_coefficient(
        self, values1: list[float], values2: list[float]
    ) -> float | None:
        """相関係数を計算"""

        if len(values1) != len(values2) or len(values1) < 3:
            return None

        try:
            # ゼロ分散のチェック
            if statistics.variance(values1) == 0 or statistics.variance(values2) == 0:
                return None

            # ピアソン相関係数を計算
            n = len(values1)
            sum_x = sum(values1)
            sum_y = sum(values2)
            sum_xy = sum(x * y for x, y in zip(values1, values2, strict=False))
            sum_x2 = sum(x * x for x in values1)
            sum_y2 = sum(y * y for y in values2)

            numerator = n * sum_xy - sum_x * sum_y
            denominator = ((n * sum_x2 - sum_x**2) * (n * sum_y2 - sum_y**2)) ** 0.5

            if denominator == 0:
                return None

            correlation = numerator / denominator
            return float(round(correlation, 3))

        except Exception as e:
            self.logger.warning(f"Error calculating correlation: {e}")
            return None

    async def _analyze_activity_patterns(
        self,
        health_by_date: dict[date, HealthData],
        discord_activity: dict[date, dict[str, Any]],
    ) -> dict[str, Any]:
        """活動パターンを分析"""

        patterns: dict[str, Any] = {
            "peak_hours": [],
            "low_hours": [],
            "notable_patterns": [],
        }

        try:
            # 時間別活動パターン
            hour_activity: dict[int, int] = defaultdict(int)

            for activity in discord_activity.values():
                for hour in activity["active_hours"]:
                    hour_activity[hour] += 1

            if hour_activity:
                # ピーク時間（上位 25% ）
                sorted_hours = sorted(
                    hour_activity.items(), key=lambda x: x[1], reverse=True
                )
                total_hours = len(sorted_hours)
                peak_count = max(1, total_hours // 4)
                patterns["peak_hours"] = [hour for hour, _ in sorted_hours[:peak_count]]

                # 低活動時間（下位 25% ）
                low_count = max(1, total_hours // 4)
                patterns["low_hours"] = [hour for hour, _ in sorted_hours[-low_count:]]

            # 注目すべきパターンの検出
            patterns["notable_patterns"] = await self._detect_notable_patterns(
                health_by_date, discord_activity
            )

        except Exception as e:
            self.logger.error("Error analyzing activity patterns", error=str(e))
            patterns["notable_patterns"].append(
                f"パターン分析中にエラーが発生しました: {str(e)}"
            )

        return patterns

    async def _detect_notable_patterns(
        self,
        health_by_date: dict[date, HealthData],
        discord_activity: dict[date, dict[str, Any]],
    ) -> list[str]:
        """注目すべきパターンを検出"""

        patterns: list[str] = []

        try:
            common_dates = set(health_by_date.keys()) & set(discord_activity.keys())

            if len(common_dates) < 5:  # 最低 5 日のデータが必要
                return patterns

            # 高活動日と低活動日の健康データ比較
            activity_levels = []
            for date in common_dates:
                activity_score = discord_activity[date]["message_count"]
                activity_levels.append((date, activity_score))

            # 活動レベルでソート
            activity_levels.sort(key=lambda x: x[1])
            n = len(activity_levels)

            # 高活動日（上位 1/3 ）と低活動日（下位 1/3 ）を比較
            low_activity_dates = [date for date, _ in activity_levels[: n // 3]]
            high_activity_dates = [date for date, _ in activity_levels[-n // 3 :]]

            # 睡眠時間の比較
            low_sleep_hours = []
            for date in low_activity_dates:
                sleep_data = health_by_date[date].sleep
                if (
                    sleep_data is not None
                    and sleep_data.is_valid
                    and sleep_data.total_sleep_hours is not None
                ):
                    low_sleep_hours.append(sleep_data.total_sleep_hours)

            high_sleep_hours = []
            for date in high_activity_dates:
                sleep_data = health_by_date[date].sleep
                if (
                    sleep_data is not None
                    and sleep_data.is_valid
                    and sleep_data.total_sleep_hours is not None
                ):
                    high_sleep_hours.append(sleep_data.total_sleep_hours)

            if len(low_sleep_hours) >= 2 and len(high_sleep_hours) >= 2:
                filtered_low = [h for h in low_sleep_hours if h is not None]
                filtered_high = [h for h in high_sleep_hours if h is not None]
                if filtered_low and filtered_high:
                    low_avg = statistics.mean(filtered_low)
                    high_avg = statistics.mean(filtered_high)

                    if abs(high_avg - low_avg) > 0.5:  # 30 分以上の差
                        if high_avg > low_avg:
                            patterns.append(
                                f"Discord 活動が活発な日は睡眠時間が長い傾向があります "
                                f"(高活動日: {high_avg:.1f}h, 低活動日: {low_avg:.1f}h)"
                            )
                        else:
                            patterns.append(
                                f"Discord 活動が活発な日は睡眠不足の傾向があります "
                                f"(高活動日: {high_avg:.1f}h, 低活動日: {low_avg:.1f}h)"
                            )

            # 歩数との関連性
            low_steps = []
            for date in low_activity_dates:
                steps_data = health_by_date[date].steps
                if (
                    steps_data is not None
                    and steps_data.is_valid
                    and steps_data.total_steps is not None
                ):
                    low_steps.append(steps_data.total_steps)

            high_steps = []
            for date in high_activity_dates:
                steps_data = health_by_date[date].steps
                if (
                    steps_data is not None
                    and steps_data.is_valid
                    and steps_data.total_steps is not None
                ):
                    high_steps.append(steps_data.total_steps)

            if len(low_steps) >= 2 and len(high_steps) >= 2:
                filtered_low_steps = [s for s in low_steps if s is not None]
                filtered_high_steps = [s for s in high_steps if s is not None]
                if filtered_low_steps and filtered_high_steps:
                    low_avg_steps = statistics.mean(filtered_low_steps)
                    high_avg_steps = statistics.mean(filtered_high_steps)

                    if abs(high_avg_steps - low_avg_steps) > 1000:  # 1000 歩以上の差
                        if high_avg_steps > low_avg_steps:
                            patterns.append(
                                f"Discord 活動が活発な日は歩数も多い傾向があります "
                                f"(高活動日: {high_avg_steps:.0f}歩, 低活動日: {low_avg_steps:.0f}歩)"
                            )
                        else:
                            patterns.append(
                                f"Discord 活動が活発な日は歩数が少ない傾向があります "
                                f"(高活動日: {high_avg_steps:.0f}歩, 低活動日: {low_avg_steps:.0f}歩)"
                            )

        except Exception as e:
            self.logger.error("Error detecting notable patterns", error=str(e))
            patterns.append("パターン検出中にエラーが発生しました")

        return patterns

    def _generate_correlation_recommendations(
        self, correlations: dict[str, Any], patterns: dict[str, Any]
    ) -> list[str]:
        """相関分析に基づく推奨事項を生成"""

        recommendations = []

        try:
            # Discord 活動との相関に基づく推奨事項
            discord_corr = correlations["discord_correlations"]

            for correlation_key, value in discord_corr.items():
                if (
                    abs(value) > 0.5  # 中程度以上の相関
                    and "message_count" in correlation_key
                    and "sleep" in correlation_key
                ):
                    if value > 0:
                        recommendations.append(
                            "Discord 活動と睡眠時間に正の相関があります。"
                            "適度な活動は良い睡眠につながっているようです。"
                        )
                    else:
                        recommendations.append(
                            "Discord 活動が多い日は睡眠不足になりがちです。"
                            "活動時間と就寝時間のバランスを見直しましょう。"
                        )

            # 健康データ内の相関に基づく推奨事項
            if correlations["sleep_steps"] and abs(correlations["sleep_steps"]) > 0.3:
                if correlations["sleep_steps"] > 0:
                    recommendations.append(
                        "睡眠時間と歩数に正の相関があります。"
                        "良い睡眠が日中の活動を促進しているようです。"
                    )
                else:
                    recommendations.append(
                        "睡眠不足の日は活動量が低下する傾向があります。"
                        "十分な睡眠を確保して活動的な一日を送りましょう。"
                    )

            # パターンに基づく推奨事項
            if patterns["notable_patterns"]:
                for pattern in patterns["notable_patterns"]:
                    if "睡眠不足" in pattern:
                        recommendations.append(
                            "活動的な日ほど睡眠時間が短くなる傾向があります。"
                            "活動量に応じて早めの就寝を心がけましょう。"
                        )

            # デフォルト推奨事項
            if not recommendations:
                recommendations.append(
                    "健康データと Discord 活動の継続的なモニタリングを行い、"
                    "自分なりの最適なバランスを見つけましょう。"
                )

        except Exception as e:
            self.logger.error("Error generating recommendations", error=str(e))
            recommendations.append("推奨事項の生成中にエラーが発生しました。")

        return recommendations
