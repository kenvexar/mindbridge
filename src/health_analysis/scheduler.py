"""
Health analysis scheduler for automated weekly analysis
"""

import asyncio
from datetime import date, datetime, timedelta
from typing import Any

from ..garmin.client import GarminClient
from ..obsidian.daily_integration import DailyNoteIntegration

# LoggerMixin は使用しない - 直接 structlog を使用
from .analyzer import HealthDataAnalyzer
from .integrator import HealthActivityIntegrator
from .models import AnalysisReport, ChangeDetection, ChangeType

# Settings loaded lazily to avoid circular imports


class HealthAnalysisScheduler:
    """健康データ分析の自動スケジューラー"""

    def __init__(
        self,
        garmin_client: GarminClient,
        analyzer: HealthDataAnalyzer,
        integrator: HealthActivityIntegrator,
        daily_integration: DailyNoteIntegration,
    ) -> None:
        """
        初期化処理

        Args:
            garmin_client: Garminクライアント
            analyzer: 健康データ分析器
            integrator: 健康・活動統合器
            daily_integration: デイリーノート統合
        """
        # 直接 structlog でロガーを初期化
        import structlog

        self.logger = structlog.get_logger("HealthAnalysisScheduler")

        self.garmin_client = garmin_client
        self.analyzer = analyzer
        self.integrator = integrator
        self.daily_integration = daily_integration

        # スケジュール設定
        self.weekly_analysis_enabled = True
        self.weekly_analysis_day = 0  # 0=月曜日
        self.analysis_hour = 9  # 午前9時

        # 制限管理
        self.last_weekly_analysis: date | None = None
        self.analysis_in_progress = False

        self.logger.info("Health analysis scheduler initialized")

    async def start_scheduler(self) -> None:
        """スケジューラーを開始"""
        self.logger.info("Starting health analysis scheduler")

        # 無限ループでスケジュールをチェック
        while True:
            try:
                await self._check_and_run_scheduled_tasks()
                # 1時間ごとにチェック
                await asyncio.sleep(3600)

            except Exception as e:
                self.logger.error(
                    "Error in scheduler loop", error=str(e), exc_info=True
                )
                # エラー時は10分後に再試行
                await asyncio.sleep(600)

    async def _check_and_run_scheduled_tasks(self) -> None:
        """スケジュールされたタスクをチェックして実行"""
        now = datetime.now()

        # 週次分析のチェック
        if self._should_run_weekly_analysis(now):
            await self._run_weekly_analysis(now.date())

        # 重要な変化の検知とアラート
        await self._check_significant_changes()

    def _should_run_weekly_analysis(self, now: datetime) -> bool:
        """週次分析を実行すべきかチェック"""

        if not self.weekly_analysis_enabled:
            return False

        if self.analysis_in_progress:
            return False

        # 正しい曜日・時間かチェック
        if now.weekday() != self.weekly_analysis_day:
            return False

        if now.hour != self.analysis_hour:
            return False

        # 今週すでに実行済みかチェック
        week_start = now.date() - timedelta(days=now.weekday())

        return not (
            self.last_weekly_analysis and self.last_weekly_analysis >= week_start
        )

    async def _run_weekly_analysis(self, current_date: date) -> None:
        """週次分析を実行"""
        if self.analysis_in_progress:
            self.logger.warning("Weekly analysis already in progress, skipping")
            return

        self.analysis_in_progress = True

        try:
            self.logger.info(
                "Starting weekly health analysis", date=current_date.isoformat()
            )

            # 分析対象週を計算（前週）
            week_start = current_date - timedelta(days=current_date.weekday() + 7)
            week_end = week_start + timedelta(days=6)

            # 過去1週間の健康データを取得
            health_data_list = await self._collect_week_health_data(
                week_start, week_end
            )

            if not health_data_list:
                self.logger.warning("No health data available for weekly analysis")
                return

            # 週次サマリーを生成
            analysis_report = await self.analyzer.generate_weekly_summary(
                health_data_list=health_data_list,
                week_start=week_start,
                discord_activity_data=None,  # 将来の拡張用
            )

            # 活動相関分析
            correlation_analysis = await self.integrator.analyze_activity_correlation(
                health_data_list=health_data_list,
                start_date=week_start,
                end_date=week_end,
            )

            # 分析結果をデイリーノートに保存
            await self._save_analysis_to_daily_note(
                analysis_report, correlation_analysis, current_date
            )

            # 重要な変化があれば通知
            await self._check_and_notify_significant_changes(analysis_report)

            self.last_weekly_analysis = current_date

            self.logger.info(
                "Weekly health analysis completed",
                week_start=week_start.isoformat(),
                insights_count=len(analysis_report.insights),
                data_quality=analysis_report.data_quality_score,
            )

        except Exception as e:
            self.logger.error(
                "Failed to run weekly analysis", error=str(e), exc_info=True
            )
        finally:
            self.analysis_in_progress = False

    async def _collect_week_health_data(
        self, start_date: date, end_date: date
    ) -> list[Any]:  # HealthData型だが、importを避けるため Any使用
        """指定週の健康データを収集"""

        health_data_list = []

        try:
            current_date = start_date
            while current_date <= end_date:
                health_data = await self.garmin_client.get_health_data(
                    target_date=current_date,
                    use_cache=True,  # キャッシュを積極的に使用
                )

                if health_data and health_data.has_any_data:
                    health_data_list.append(health_data)

                current_date += timedelta(days=1)

            self.logger.debug(
                f"Collected {len(health_data_list)} days of health data",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )

        except Exception as e:
            self.logger.error(
                "Failed to collect week health data",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                error=str(e),
            )

        return health_data_list

    async def _save_analysis_to_daily_note(
        self,
        analysis_report: AnalysisReport,
        correlation_analysis: Any,  # ActivityCorrelation型だが、importを避けるため Any使用
        current_date: date,
    ) -> None:
        """分析結果をデイリーノートに保存"""

        try:
            # 分析結果のMarkdownを生成
            analysis_markdown = self._format_analysis_for_daily_note(
                analysis_report, correlation_analysis
            )

            # 当日のデイリーノートに健康分析セクションを追加
            await self.daily_integration.update_health_analysis_in_daily_note(
                target_date=current_date, analysis_markdown=analysis_markdown
            )

            self.logger.info(
                "Analysis saved to daily note", date=current_date.isoformat()
            )

        except Exception as e:
            self.logger.error(
                "Failed to save analysis to daily note", error=str(e), exc_info=True
            )

    def _format_analysis_for_daily_note(
        self, analysis_report: AnalysisReport, correlation_analysis: Any
    ) -> str:
        """分析結果をデイリーノート用Markdownに整形"""

        markdown_parts = []

        # ヘッダー
        week_range = f"{analysis_report.start_date.strftime('%m/%d')} - {analysis_report.end_date.strftime('%m/%d')}"
        markdown_parts.append(f"## 🔍 週次健康分析 ({week_range})")
        markdown_parts.append("")

        # サマリー
        markdown_parts.append("### 📊 サマリー")
        markdown_parts.append(analysis_report.summary)
        markdown_parts.append("")

        # 主要な発見
        if analysis_report.key_findings:
            markdown_parts.append("### 🎯 主要な発見")
            for finding in analysis_report.key_findings:
                markdown_parts.append(f"- {finding}")
            markdown_parts.append("")

        # 高優先度の洞察
        high_priority_insights = analysis_report.get_priority_insights("high")
        if high_priority_insights:
            markdown_parts.append("### ⚠️ 重要な洞察")
            for insight in high_priority_insights:
                markdown_parts.append(f"**{insight.title}**")
                markdown_parts.append(f"{insight.description}")
                if insight.recommended_actions:
                    markdown_parts.append("推奨アクション:")
                    for action in insight.recommended_actions:
                        markdown_parts.append(f"- {action}")
                markdown_parts.append("")

        # 実行可能な洞察
        actionable_insights = analysis_report.get_actionable_insights()
        if actionable_insights and not high_priority_insights:  # 高優先度がない場合のみ
            markdown_parts.append("### 💡 実行可能な改善提案")
            for insight in actionable_insights[:3]:  # 上位3つ
                markdown_parts.append(f"**{insight.title}**: {insight.description}")
                if insight.recommended_actions:
                    for action in insight.recommended_actions:
                        markdown_parts.append(f"  - {action}")
            markdown_parts.append("")

        # 相関分析結果
        if (
            hasattr(correlation_analysis, "notable_patterns")
            and correlation_analysis.notable_patterns
        ):
            markdown_parts.append("### 🔗 活動パターン分析")
            for pattern in correlation_analysis.notable_patterns:
                markdown_parts.append(f"- {pattern}")
            markdown_parts.append("")

        # 推奨事項
        if (
            hasattr(correlation_analysis, "recommendations")
            and correlation_analysis.recommendations
        ):
            markdown_parts.append("### 📝 推奨事項")
            for recommendation in correlation_analysis.recommendations:
                markdown_parts.append(f"- {recommendation}")
            markdown_parts.append("")

        # メタ情報
        markdown_parts.append("### 📈 分析情報")
        markdown_parts.append(f"- 分析対象日数: {analysis_report.analyzed_days}日")
        markdown_parts.append(
            f"- データ品質スコア: {analysis_report.data_quality_score:.1%}"
        )
        if analysis_report.missing_days > 0:
            markdown_parts.append(f"- 欠損日数: {analysis_report.missing_days}日")

        return "\n".join(markdown_parts)

    async def _check_and_notify_significant_changes(
        self, analysis_report: AnalysisReport
    ) -> None:
        """重要な変化をチェックして通知"""

        try:
            significant_changes = analysis_report.get_significant_changes(
                min_significance=0.8
            )

            if not significant_changes:
                return

            # 警告が必要な変化をフィルタリング
            warning_changes = [
                change
                for change in significant_changes
                if change.change_type == ChangeType.DECLINE
            ]

            if warning_changes:
                await self._send_health_warning_notification(warning_changes)

            # 改善の通知
            improvement_changes = [
                change
                for change in significant_changes
                if change.change_type == ChangeType.IMPROVEMENT
            ]

            if improvement_changes:
                await self._send_health_improvement_notification(improvement_changes)

        except Exception as e:
            self.logger.error("Failed to check significant changes", error=str(e))

    async def _send_health_warning_notification(
        self, warning_changes: list[ChangeDetection]
    ) -> None:
        """健康警告通知を送信"""

        try:
            # 通知メッセージを構築
            warning_messages = []
            for change in warning_changes:
                message = f"⚠️ {change.description}"
                if change.recommended_action:
                    message += f" - {change.recommended_action}"
                warning_messages.append(message)

            # 実際の通知送信はDiscordクライアントが必要なため、ログに記録
            self.logger.warning(
                "Health warning detected",
                changes_count=len(warning_changes),
                messages=warning_messages,
            )

            # 将来の実装: Discord通知チャンネルに送信
            # await self.discord_client.send_notification(...)

        except Exception as e:
            self.logger.error(
                "Failed to send health warning notification", error=str(e)
            )

    async def _send_health_improvement_notification(
        self, improvement_changes: list[ChangeDetection]
    ) -> None:
        """健康改善通知を送信"""

        try:
            # 改善通知メッセージを構築
            improvement_messages = []
            for change in improvement_changes:
                message = f"✅ {change.description}"
                improvement_messages.append(message)

            self.logger.info(
                "Health improvement detected",
                changes_count=len(improvement_changes),
                messages=improvement_messages,
            )

            # 将来の実装: Discord通知チャンネルに送信（低優先度）
            # await self.discord_client.send_notification(..., priority='low')

        except Exception as e:
            self.logger.error(
                "Failed to send health improvement notification", error=str(e)
            )

    async def _check_significant_changes(self) -> None:
        """重要な変化の日次チェック"""

        try:
            # 毎日の変化監視（週次分析とは別）
            current_date = date.today()

            # 過去7日間のデータで変化をチェック
            end_date = current_date - timedelta(days=1)  # 昨日まで
            start_date = end_date - timedelta(days=6)  # 7日間

            health_data_list = await self._collect_week_health_data(
                start_date, end_date
            )

            if len(health_data_list) >= 5:  # 最低5日のデータが必要
                # 重要な変化を検出
                changes = await self.analyzer._detect_significant_changes(
                    health_data_list
                )

                # 緊急度の高い変化のみ通知
                urgent_changes = [
                    change
                    for change in changes
                    if (
                        change.significance_score > 0.9
                        and change.change_type == ChangeType.DECLINE
                    )
                ]

                if urgent_changes:
                    await self._send_urgent_health_alert(urgent_changes)

        except Exception as e:
            self.logger.error("Failed to check daily significant changes", error=str(e))

    async def _send_urgent_health_alert(
        self, urgent_changes: list[ChangeDetection]
    ) -> None:
        """緊急健康アラートを送信"""

        try:
            alert_messages = []
            for change in urgent_changes:
                message = f"🚨 緊急: {change.description}"
                if change.recommended_action:
                    message += f"\n推奨: {change.recommended_action}"
                alert_messages.append(message)

            self.logger.critical(
                "Urgent health alert",
                changes_count=len(urgent_changes),
                messages=alert_messages,
            )

            # 将来の実装: 即座にDiscord通知
            # await self.discord_client.send_urgent_notification(...)

        except Exception as e:
            self.logger.error("Failed to send urgent health alert", error=str(e))

    def stop_scheduler(self) -> None:
        """スケジューラーを停止"""
        self.weekly_analysis_enabled = False
        self.logger.info("Health analysis scheduler stopped")
