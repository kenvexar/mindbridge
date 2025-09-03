"""Task and productivity report generation functionality."""

from datetime import date, datetime, timedelta

from structlog import get_logger

from src.ai import GeminiClient
from src.obsidian import ObsidianFileManager
from src.tasks.models import TaskStatus, TaskSummary
from src.tasks.schedule_manager import ScheduleManager
from src.tasks.task_manager import TaskManager

logger = get_logger(__name__)


class TaskReportGenerator:
    """Generate task and productivity reports with insights."""

    def __init__(
        self,
        file_manager: ObsidianFileManager,
        task_manager: TaskManager,
        schedule_manager: ScheduleManager,
        gemini_client: GeminiClient,
    ):
        self.file_manager = file_manager
        self.task_manager = task_manager
        self.schedule_manager = schedule_manager
        self.gemini_client = gemini_client

    async def generate_weekly_report(
        self,
        start_date: date,
        include_ai_insights: bool = True,
    ) -> str:
        """Generate comprehensive weekly productivity report."""
        end_date = start_date + timedelta(days=6)

        # Gather data
        summary = await self._generate_task_summary(start_date, end_date)

        # Generate base report
        report = await self._create_weekly_report_content(start_date, end_date, summary)

        # Add AI insights if requested
        if include_ai_insights:
            try:
                insights = await self._generate_ai_insights(summary)
                report += f"\n\n## AI分析・提案\n\n{insights}"
            except Exception as e:
                logger.error("Failed to generate AI insights", error=str(e))
                report += "\n\n## AI分析・提案\n\nAI分析の生成に失敗しました。"

        # Save report to Obsidian
        await self._save_weekly_report(start_date, report)

        return report

    async def generate_monthly_report(
        self,
        year: int,
        month: int,
        include_ai_insights: bool = True,
    ) -> str:
        """Generate comprehensive monthly productivity report."""
        from calendar import monthrange

        start_date = date(year, month, 1)
        end_date = date(year, month, monthrange(year, month)[1])

        # Gather data
        summary = await self._generate_task_summary(start_date, end_date)

        # Generate base report
        report = await self._create_monthly_report_content(year, month, summary)

        # Add AI insights if requested
        if include_ai_insights:
            try:
                insights = await self._generate_ai_insights(summary)
                report += f"\n\n## AI分析・提案\n\n{insights}"
            except Exception as e:
                logger.error("Failed to generate AI insights", error=str(e))
                report += "\n\n## AI分析・提案\n\nAI分析の生成に失敗しました。"

        # Save report to Obsidian
        await self._save_monthly_report(year, month, report)

        return report

    async def generate_task_stats(self) -> str:
        """Generate current task statistics."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

        # Get current tasks
        all_tasks = await self.task_manager.list_tasks()
        active_tasks = await self.task_manager.list_tasks(active_only=True)
        overdue_tasks = await self.task_manager.get_overdue_tasks()
        due_soon_tasks = await self.task_manager.get_due_soon_tasks(7)

        # Get this week's summary
        week_summary = await self._generate_task_summary(week_start, today)

        report = f"""# タスク統計情報

生成日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M")}

## 現在の状況
- **全タスク数**: {len(all_tasks)}個
- **アクティブタスク**: {len(active_tasks)}個
- **期限切れタスク**: {len(overdue_tasks)}個 ⚠️
- **7日以内期限**: {len(due_soon_tasks)}個

## 今週の実績 ({week_start} ～ {today})
- **完了タスク**: {week_summary.completed_tasks}個
- **完了率**: {week_summary.completion_rate:.1f}%
- **生産性スコア**: {week_summary.productivity_score:.1f}/100

## ステータス別内訳
"""

        for status, count in week_summary.status_breakdown.items():
            if count > 0:
                report += f"- **{status}**: {count}個\n"

        report += "\n## 優先度別内訳\n"

        for priority, count in week_summary.priority_breakdown.items():
            if count > 0:
                priority_emoji = {
                    "urgent": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🔵",
                }.get(priority, "⚪")
                report += f"- {priority_emoji} **{priority}**: {count}個\n"

        if week_summary.project_breakdown:
            report += "\n## プロジェクト別内訳\n"
            for project, count in week_summary.project_breakdown.items():
                if count > 0:
                    report += f"- **{project}**: {count}個\n"

        if week_summary.average_completion_time:
            report += "\n## パフォーマンス\n"
            report += (
                f"- **平均完了時間**: {week_summary.average_completion_time:.1f}時間\n"
            )

        return report

    async def _generate_task_summary(
        self,
        start_date: date,
        end_date: date,
    ) -> TaskSummary:
        """Generate task summary for period."""
        # Get all tasks
        all_tasks = await self.task_manager.list_tasks()

        # Filter tasks for the period
        period_tasks = []
        completed_tasks = []
        in_progress_tasks = []
        overdue_tasks = []
        due_soon_tasks = []

        total_completion_time = 0.0
        completion_count = 0

        status_breakdown: dict[str, int] = {}
        priority_breakdown: dict[str, int] = {}
        project_breakdown: dict[str, int] = {}

        for task in all_tasks:
            # Check if task is relevant to the period
            task_in_period = False

            # Include if created in period
            if start_date <= task.created_at.date() <= end_date:
                task_in_period = True

            # Include if completed in period
            if task.completed_at and start_date <= task.completed_at.date() <= end_date:
                task_in_period = True
                completed_tasks.append(task)

                # Calculate completion time
                duration = task.get_duration()
                if duration:
                    total_completion_time += duration
                    completion_count += 1

            # Include if due in period
            if task.due_date and start_date <= task.due_date <= end_date:
                task_in_period = True

            if not task_in_period:
                continue

            period_tasks.append(task)

            # Categorize tasks
            if task.status == TaskStatus.IN_PROGRESS:
                in_progress_tasks.append(task)

            if task.is_overdue():
                overdue_tasks.append(task)

            if task.is_due_soon(7):
                due_soon_tasks.append(task)

            # Count by status
            status_key = task.status.value
            status_breakdown[status_key] = status_breakdown.get(status_key, 0) + 1

            # Count by priority
            priority_key = task.priority.value
            priority_breakdown[priority_key] = (
                priority_breakdown.get(priority_key, 0) + 1
            )

            # Count by project
            if task.project:
                project_breakdown[task.project] = (
                    project_breakdown.get(task.project, 0) + 1
                )

        # Calculate completion rate
        completion_rate = 0.0
        if period_tasks:
            completion_rate = (len(completed_tasks) / len(period_tasks)) * 100

        # Calculate average completion time
        average_completion_time = None
        if completion_count > 0:
            average_completion_time = total_completion_time / completion_count

        # Get upcoming schedules
        upcoming_schedules = await self.schedule_manager.get_upcoming_schedules(7)

        return TaskSummary(
            total_tasks=len(period_tasks),
            completed_tasks=len(completed_tasks),
            in_progress_tasks=len(in_progress_tasks),
            overdue_tasks=len(overdue_tasks),
            due_soon_tasks=len(due_soon_tasks),
            completion_rate=completion_rate,
            average_completion_time=average_completion_time,
            priority_breakdown=priority_breakdown,
            status_breakdown=status_breakdown,
            project_breakdown=project_breakdown,
            upcoming_schedules=upcoming_schedules,
            period_start=start_date,
            period_end=end_date,
        )

    async def _create_weekly_report_content(
        self,
        start_date: date,
        end_date: date,
        summary: TaskSummary,
    ) -> str:
        """Create weekly report content."""
        week_num = start_date.isocalendar()[1]
        year = start_date.year

        report = f"""# {year}年 第{week_num}週 生産性レポート

期間: {start_date} ～ {end_date}
生成日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M")}

## 週間概要
- **総タスク数**: {summary.total_tasks}個
- **完了タスク**: {summary.completed_tasks}個
- **完了率**: {summary.completion_rate:.1f}%
- **進行中タスク**: {summary.in_progress_tasks}個
- **期限切れタスク**: {summary.overdue_tasks}個
- **生産性スコア**: {summary.productivity_score:.1f}/100

## パフォーマンス
"""

        if summary.average_completion_time:
            report += f"- **平均完了時間**: {summary.average_completion_time:.1f}時間\n"

        # Performance assessment
        if summary.productivity_score >= 80:
            report += "- **評価**: 🌟 優秀 - 非常に良いパフォーマンスです\n"
        elif summary.productivity_score >= 60:
            report += "- **評価**: 👍 良好 - 安定したパフォーマンスです\n"
        elif summary.productivity_score >= 40:
            report += "- **評価**: ⚠️ 改善の余地 - パフォーマンス向上が必要です\n"
        else:
            report += "- **評価**: 🔴 要改善 - パフォーマンスの大幅な改善が必要です\n"

        # Status breakdown
        report += "\n## ステータス別内訳\n"
        for status, count in summary.status_breakdown.items():
            if count > 0:
                report += f"- **{status}**: {count}個\n"

        # Priority breakdown
        report += "\n## 優先度別内訳\n"
        for priority, count in summary.priority_breakdown.items():
            if count > 0:
                priority_emoji = {
                    "urgent": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🔵",
                }.get(priority, "⚪")
                report += f"- {priority_emoji} **{priority}**: {count}個\n"

        # Project breakdown
        if summary.project_breakdown:
            report += "\n## プロジェクト別内訳\n"
            for project, count in summary.project_breakdown.items():
                if count > 0:
                    report += f"- **{project}**: {count}個\n"

        # Upcoming schedules
        if summary.upcoming_schedules:
            report += "\n## 来週の予定\n"
            for schedule in summary.upcoming_schedules:
                time_text = (
                    schedule.start_time.strftime("%H:%M")
                    if schedule.start_time
                    else "時間未設定"
                )
                report += f"- **{schedule.start_date}** {time_text}: {schedule.title}\n"

        return report

    async def _create_monthly_report_content(
        self,
        year: int,
        month: int,
        summary: TaskSummary,
    ) -> str:
        """Create monthly report content."""
        report = f"""# {year}年{month}月 生産性レポート

生成日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M")}

## 月間概要
- **総タスク数**: {summary.total_tasks}個
- **完了タスク**: {summary.completed_tasks}個
- **完了率**: {summary.completion_rate:.1f}%
- **残タスク**: {summary.remaining_tasks}個
- **期限切れタスク**: {summary.overdue_tasks}個
- **生産性スコア**: {summary.productivity_score:.1f}/100

## 月間パフォーマンス
"""

        if summary.average_completion_time:
            report += f"- **平均完了時間**: {summary.average_completion_time:.1f}時間\n"

        # Monthly trends would need historical data
        report += f"- **1日平均完了タスク**: {summary.completed_tasks / 30:.1f}個\n"

        # Status breakdown
        report += "\n## ステータス別内訳\n"
        for status, count in summary.status_breakdown.items():
            if count > 0:
                report += f"- **{status}**: {count}個\n"

        # Priority breakdown
        report += "\n## 優先度別内訳\n"
        for priority, count in summary.priority_breakdown.items():
            if count > 0:
                priority_emoji = {
                    "urgent": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🔵",
                }.get(priority, "⚪")
                report += f"- {priority_emoji} **{priority}**: {count}個\n"

        # Project breakdown
        if summary.project_breakdown:
            report += "\n## プロジェクト別実績\n"
            for project, count in summary.project_breakdown.items():
                if count > 0:
                    report += f"- **{project}**: {count}個\n"

        return report

    async def _generate_ai_insights(self, summary: TaskSummary) -> str:
        """Generate AI insights for the task data."""
        prompt = f"""
以下の生産性データを分析し、日本語で洞察と改善提案を提供してください：

タスクデータ:
- 総タスク数: {summary.total_tasks}個
- 完了タスク: {summary.completed_tasks}個
- 完了率: {summary.completion_rate:.1f}%
- 期限切れタスク: {summary.overdue_tasks}個
- 進行中タスク: {summary.in_progress_tasks}個
- 生産性スコア: {summary.productivity_score:.1f}/100

優先度別内訳: {summary.priority_breakdown}
ステータス別内訳: {summary.status_breakdown}
プロジェクト別内訳: {summary.project_breakdown}

以下の観点で分析してください：
1. 生産性パフォーマンスの評価
2. タスク管理の傾向分析
3. 時間管理の課題特定
4. 具体的な改善提案（3-5個）
5. 来週/来月への推奨アクション

簡潔で実用的なアドバイスを提供してください。
"""

        try:
            summary_result = await self.gemini_client.generate_summary(prompt)
            response = summary_result
            return str(response.summary)
        except Exception as e:
            logger.error("Failed to generate AI insights", error=str(e))
            return "AI分析の生成に失敗しました。"

    async def _save_weekly_report(self, start_date: date, content: str) -> None:
        """Save weekly report to Obsidian."""
        try:
            from pathlib import Path

            week_num = start_date.isocalendar()[1]
            year = start_date.year
            filename = f"{year}年第{week_num:02d}週_生産性レポート.md"
            file_path = Path("07_Tasks") / "Reports" / "Weekly" / str(year) / filename

            # Add metadata
            full_content = f"""---
type: productivity_report
period: weekly
year: {year}
week: {week_num}
start_date: {start_date}
generated: {datetime.now().isoformat()}
tags: [productivity, report, weekly]
---

{content}

## 関連リンク
- [[タスク管理システム]]
- [[週次レビュー]]
- [[生産性分析]]
"""

            # Create ObsidianNote and save it
            from src.obsidian.models import NoteFrontmatter, ObsidianNote

            note = ObsidianNote(
                filename=file_path.name,
                file_path=file_path,
                frontmatter=NoteFrontmatter(obsidian_folder="04_Tasks"),
                content=full_content,
            )
            await self.file_manager.save_note(note)

            logger.info(
                "Weekly productivity report saved",
                year=year,
                week=week_num,
                file_path=str(file_path),
            )

        except Exception as e:
            logger.error(
                "Failed to save weekly report",
                year=start_date.year,
                week=start_date.isocalendar()[1],
                error=str(e),
            )

    async def _save_monthly_report(self, year: int, month: int, content: str) -> None:
        """Save monthly report to Obsidian."""
        try:
            from pathlib import Path

            filename = f"{year}年{month:02d}月_生産性レポート.md"
            file_path = Path("07_Tasks") / "Reports" / "Monthly" / str(year) / filename

            # Add metadata
            full_content = f"""---
type: productivity_report
period: monthly
year: {year}
month: {month}
generated: {datetime.now().isoformat()}
tags: [productivity, report, monthly]
---

{content}

## 関連リンク
- [[タスク管理システム]]
- [[月次レビュー]]
- [[生産性分析]]
"""

            # Create ObsidianNote and save it
            from src.obsidian.models import NoteFrontmatter, ObsidianNote

            note = ObsidianNote(
                filename=file_path.name,
                file_path=file_path,
                frontmatter=NoteFrontmatter(obsidian_folder="04_Tasks"),
                content=full_content,
            )
            await self.file_manager.save_note(note)

            logger.info(
                "Monthly productivity report saved",
                year=year,
                month=month,
                file_path=str(file_path),
            )

        except Exception as e:
            logger.error(
                "Failed to save monthly report",
                year=year,
                month=month,
                error=str(e),
            )
