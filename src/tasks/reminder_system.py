"""Task and schedule reminder system for automated notifications."""

import asyncio
import contextlib
from datetime import date, datetime, time
from typing import Any

import discord
from structlog import get_logger

from src.bot.channel_config import ChannelConfig
from src.tasks.models import Schedule, Task
from src.tasks.schedule_manager import ScheduleManager
from src.tasks.task_manager import TaskManager

logger = get_logger(__name__)


class TaskReminderSystem:
    """Task and schedule reminder system for automated notifications."""

    def __init__(
        self,
        bot: discord.Client,
        channel_config: ChannelConfig,
        task_manager: TaskManager,
        schedule_manager: ScheduleManager,
    ):
        self.bot = bot
        self.channel_config = channel_config
        self.task_manager = task_manager
        self.schedule_manager = schedule_manager
        self._reminder_task: asyncio.Task[Any] | None = None
        self._is_running = False

    async def start(self) -> None:
        """Start the reminder system."""
        if self._is_running:
            return

        self._is_running = True
        self._reminder_task = asyncio.create_task(self._run_reminder_loop())

        logger.info("Task reminder system started")

    async def stop(self) -> None:
        """Stop the reminder system."""
        self._is_running = False

        if self._reminder_task:
            self._reminder_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reminder_task

        logger.info("Task reminder system stopped")

    async def _run_reminder_loop(self) -> None:
        """Main reminder loop that runs daily at 8 AM."""
        while self._is_running:
            try:
                now = datetime.now()

                # Check if it's 8 AM
                if now.hour == 8 and now.minute == 0:
                    await self._run_daily_checks()

                    # Wait for 60 seconds to avoid running multiple times in the same minute
                    await asyncio.sleep(60)
                else:
                    # Check every minute
                    await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in task reminder loop", error=str(e))
                await asyncio.sleep(60)

    async def _run_daily_checks(self) -> None:
        """Run all daily task and schedule checks."""
        try:
            logger.info("Running daily task and schedule checks")

            # Check for overdue tasks
            await self._check_overdue_tasks()

            # Check for tasks due soon
            await self._check_due_soon_tasks()

            # Check today's schedule
            await self._check_today_schedule()

            # Check tomorrow's schedule
            await self._check_tomorrow_schedule()

            # Add task info to daily note
            await self._add_to_daily_note()

        except Exception as e:
            logger.error("Error in daily task checks", error=str(e))

    async def _check_overdue_tasks(self) -> None:
        """Check for overdue tasks."""
        try:
            overdue_tasks = await self.task_manager.get_overdue_tasks()

            if not overdue_tasks:
                return

            await self._send_overdue_task_reminders(overdue_tasks)

        except Exception as e:
            logger.error("Error checking overdue tasks", error=str(e))

    async def _check_due_soon_tasks(self) -> None:
        """Check for tasks due within 3 days."""
        try:
            due_soon_tasks = await self.task_manager.get_due_soon_tasks(3)

            if not due_soon_tasks:
                return

            await self._send_due_soon_task_reminders(due_soon_tasks)

        except Exception as e:
            logger.error("Error checking due soon tasks", error=str(e))

    async def _check_today_schedule(self) -> None:
        """Check today's schedule."""
        try:
            today_schedules = await self.schedule_manager.get_today_schedules()

            if not today_schedules:
                return

            await self._send_today_schedule_reminders(today_schedules)

        except Exception as e:
            logger.error("Error checking today schedule", error=str(e))

    async def _check_tomorrow_schedule(self) -> None:
        """Check tomorrow's schedule."""
        try:
            tomorrow_schedules = await self.schedule_manager.get_tomorrow_schedules()

            if not tomorrow_schedules:
                return

            await self._send_tomorrow_schedule_reminders(tomorrow_schedules)

        except Exception as e:
            logger.error("Error checking tomorrow schedule", error=str(e))

    async def _send_overdue_task_reminders(self, overdue_tasks: list[Task]) -> None:
        """Send overdue task notifications."""
        try:
            task_channel = self._get_task_channel()
            if not task_channel:
                logger.warning("Task channel not configured")
                return

            embed = discord.Embed(
                title="⚠️ 期限切れタスク通知",
                description="以下のタスクが期限を過ぎています。",
                color=discord.Color.red(),
                timestamp=datetime.now(),
            )

            for task in overdue_tasks:
                days_overdue = (
                    (date.today() - task.due_date).days if task.due_date else 0
                )
                embed.add_field(
                    name=f"🔴 {task.title}",
                    value=f"期限: {task.due_date}\n遅延: {days_overdue}日\n進捗: {task.progress}%",
                    inline=True,
                )

            embed.add_field(
                name="🚨 対応が必要",
                value="タスクの進捗を更新するか、期限を見直してください。",
                inline=False,
            )

            await task_channel.send(embed=embed)

            logger.info(
                "Overdue task reminders sent",
                count=len(overdue_tasks),
            )

        except Exception as e:
            logger.error("Error sending overdue task reminders", error=str(e))

    async def _send_due_soon_task_reminders(self, due_soon_tasks: list[Task]) -> None:
        """Send due soon task notifications."""
        try:
            task_channel = self._get_task_channel()
            if not task_channel:
                logger.warning("Task channel not configured")
                return

            # Group tasks by days until due
            today_tasks = []
            tomorrow_tasks = []
            soon_tasks = []

            today = date.today()

            for task in due_soon_tasks:
                days_until = (task.due_date - today).days if task.due_date else 0
                if days_until == 0:
                    today_tasks.append(task)
                elif days_until == 1:
                    tomorrow_tasks.append(task)
                else:
                    soon_tasks.append(task)

            # Send notifications for each group
            if today_tasks:
                await self._send_task_group_reminder(
                    today_tasks, "今日期限", "🔔", discord.Color.orange()
                )

            if tomorrow_tasks:
                await self._send_task_group_reminder(
                    tomorrow_tasks, "明日期限", "📅", discord.Color.yellow()
                )

            if soon_tasks:
                await self._send_task_group_reminder(
                    soon_tasks, "3日以内期限", "⏰", discord.Color.blue()
                )

        except Exception as e:
            logger.error("Error sending due soon task reminders", error=str(e))

    async def _send_task_group_reminder(
        self,
        tasks: list[Task],
        time_description: str,
        emoji: str,
        color: discord.Color,
    ) -> None:
        """Send reminder for a group of tasks."""
        try:
            task_channel = self._get_task_channel()
            if not task_channel:
                return

            embed = discord.Embed(
                title=f"{emoji} {time_description}のタスク",
                color=color,
                timestamp=datetime.now(),
            )

            for task in tasks:
                priority_emoji = {
                    "urgent": "🔴",
                    "high": "🟠",
                    "medium": "🟡",
                    "low": "🔵",
                }.get(task.priority.value, "⚪")

                embed.add_field(
                    name=f"{priority_emoji} {task.title}",
                    value=f"期限: {task.due_date}\n進捗: {task.progress}%\n優先度: {task.priority.value}",
                    inline=True,
                )

            await task_channel.send(embed=embed)

        except Exception as e:
            logger.error("Error sending task group reminder", error=str(e))

    async def _send_today_schedule_reminders(self, schedules: list[Schedule]) -> None:
        """Send today's schedule notifications."""
        try:
            task_channel = self._get_task_channel()
            if not task_channel:
                logger.warning("Task channel not configured")
                return

            embed = discord.Embed(
                title="📅 今日の予定",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )

            # Sort by start time
            sorted_schedules = sorted(schedules, key=lambda x: x.start_time or time.min)

            for schedule in sorted_schedules:
                time_text = (
                    schedule.start_time.strftime("%H:%M")
                    if schedule.start_time
                    else "時間未設定"
                )
                if schedule.end_time:
                    time_text += f" - {schedule.end_time.strftime('%H:%M')}"

                location_text = f"\n📍 {schedule.location}" if schedule.location else ""

                embed.add_field(
                    name=f"🕐 {time_text}",
                    value=f"{schedule.title}{location_text}",
                    inline=False,
                )

            await task_channel.send(embed=embed)

            logger.info(
                "Today schedule reminders sent",
                count=len(schedules),
            )

        except Exception as e:
            logger.error("Error sending today schedule reminders", error=str(e))

    async def _send_tomorrow_schedule_reminders(
        self, schedules: list[Schedule]
    ) -> None:
        """Send tomorrow's schedule notifications."""
        try:
            task_channel = self._get_task_channel()
            if not task_channel:
                logger.warning("Task channel not configured")
                return

            embed = discord.Embed(
                title="📅 明日の予定",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            # Sort by start time
            sorted_schedules = sorted(schedules, key=lambda x: x.start_time or time.min)

            for schedule in sorted_schedules:
                time_text = (
                    schedule.start_time.strftime("%H:%M")
                    if schedule.start_time
                    else "時間未設定"
                )
                if schedule.end_time:
                    time_text += f" - {schedule.end_time.strftime('%H:%M')}"

                location_text = f"\n📍 {schedule.location}" if schedule.location else ""

                embed.add_field(
                    name=f"🕐 {time_text}",
                    value=f"{schedule.title}{location_text}",
                    inline=False,
                )

            await task_channel.send(embed=embed)

            logger.info(
                "Tomorrow schedule reminders sent",
                count=len(schedules),
            )

        except Exception as e:
            logger.error("Error sending tomorrow schedule reminders", error=str(e))

    async def _add_to_daily_note(self) -> None:
        """Add task and schedule information to daily note."""
        try:
            from src.obsidian import ObsidianFileManager
            from src.obsidian.daily_integration import (
                DailyNoteIntegration as DailyNoteIntegrator,
            )

            # Get tasks and schedules
            overdue_tasks = await self.task_manager.get_overdue_tasks()
            due_today_tasks = await self.task_manager.get_due_soon_tasks(0)
            today_schedules = await self.schedule_manager.get_today_schedules()

            # Create content
            content = "## タスク・スケジュール\n\n"

            if today_schedules:
                content += "### 今日の予定\n"
                for schedule in sorted(
                    today_schedules, key=lambda x: x.start_time or time.min
                ):
                    time_text = (
                        schedule.start_time.strftime("%H:%M")
                        if schedule.start_time
                        else "時間未設定"
                    )
                    content += f"- {time_text}: {schedule.title}\n"
                content += "\n"

            if due_today_tasks:
                content += "### 今日期限のタスク\n"
                for task in due_today_tasks:
                    content += f"- {task.title} ({task.progress}%)\n"
                content += "\n"

            if overdue_tasks:
                content += "### 期限切れタスク ⚠️\n"
                for task in overdue_tasks:
                    days_overdue = (
                        (date.today() - task.due_date).days if task.due_date else 0
                    )
                    content += f"- {task.title} ({days_overdue}日遅延)\n"
                content += "\n"

            if not today_schedules and not due_today_tasks and not overdue_tasks:
                content += "特に予定やタスクはありません。\n"

            # Add to daily note
            daily_integrator = DailyNoteIntegrator(ObsidianFileManager())
            # Add to daily note using activity log
            message_data = {
                "content": content,
                "category": "Daily Overview",
                "type": "reminder_summary",
            }
            await daily_integrator.add_activity_log_entry(
                message_data, datetime.combine(date.today(), datetime.min.time())
            )

        except Exception as e:
            logger.error("Error adding to daily note", error=str(e))

    def _get_task_channel(self) -> discord.TextChannel | None:
        """Get task channel for notifications."""
        # This would need to be implemented based on your channel configuration
        # For now, return None to avoid errors
        return None

    async def send_manual_reminder_check(self) -> None:
        """Manually trigger reminder checks (for testing)."""
        try:
            await self._run_daily_checks()
            logger.info("Manual task reminder check completed")
        except Exception as e:
            logger.error("Error in manual task reminder check", error=str(e))
