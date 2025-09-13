"""Task management Discord commands."""

from datetime import date, datetime

import discord
from discord import app_commands
from structlog import get_logger

from src.bot.channel_config import ChannelConfig
from src.obsidian import ObsidianFileManager
from src.tasks.models import ScheduleType, Task, TaskPriority, TaskStatus
from src.tasks.schedule_manager import ScheduleManager
from src.tasks.task_manager import TaskManager

logger = get_logger(__name__)


class TaskCommands:
    """Task management Discord commands."""

    def __init__(
        self,
        bot: discord.Client,
        channel_config: ChannelConfig,
        file_manager: ObsidianFileManager,
        task_manager: TaskManager,
        schedule_manager: ScheduleManager,
    ):
        self.bot = bot
        self.channel_config = channel_config
        self.file_manager = file_manager
        self.task_manager = task_manager
        self.schedule_manager = schedule_manager

    @app_commands.command(name="task_add", description="新しいタスクを追加")  # type: ignore[type-var]
    @app_commands.describe(
        title="タスクタイトル",
        description="タスクの詳細説明",
        priority="優先度 (low/medium/high/urgent)",
        due_date="期限 (YYYY-MM-DD形式)",
        estimated_hours="予想作業時間",
        project="プロジェクト名",
        tags="タグ（カンマ区切り）",
    )
    async def task_add_command(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str | None = None,
        priority: str = "medium",
        due_date: str | None = None,
        estimated_hours: float | None = None,
        project: str | None = None,
        tags: str | None = None,
    ) -> None:
        """Add a new task."""
        try:
            # Parse priority
            try:
                task_priority = TaskPriority(priority.lower())
            except ValueError:
                await interaction.response.send_message(
                    "❌ 無効な優先度です。low、medium、high、urgent のいずれかを指定してください。",
                    ephemeral=True,
                )
                return

            # Parse due date
            due_date_obj = None
            if due_date:
                try:
                    due_date_obj = datetime.strptime(due_date, "%Y-%m-%d").date()
                except ValueError:
                    await interaction.response.send_message(
                        "❌ 無効な日付形式です。YYYY-MM-DD形式で入力してください。",
                        ephemeral=True,
                    )
                    return

            # Parse tags
            tag_list = []
            if tags:
                tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

            await interaction.response.defer()

            # Create task
            task = await self.task_manager.create_task(
                title=title,
                description=description,
                priority=task_priority,
                due_date=due_date_obj,
                estimated_hours=estimated_hours,
                tags=tag_list,
                project=project,
            )

            # Create embed response
            embed = discord.Embed(
                title="✅ タスクを追加しました",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="タイトル", value=task.title, inline=True)
            embed.add_field(name="優先度", value=task.priority.value, inline=True)
            embed.add_field(name="ステータス", value=task.status.value, inline=True)

            if task.due_date:
                embed.add_field(name="期限", value=task.due_date, inline=True)
            if task.estimated_hours:
                embed.add_field(
                    name="予想時間", value=f"{task.estimated_hours}時間", inline=True
                )
            if task.project:
                embed.add_field(name="プロジェクト", value=task.project, inline=True)
            if task.description:
                embed.add_field(name="説明", value=task.description, inline=False)
            if task.tags:
                embed.add_field(name="タグ", value=", ".join(task.tags), inline=False)

            await interaction.followup.send(embed=embed)

            logger.info(
                "Task added via command",
                user_id=interaction.user.id,
                task_id=task.id,
                title=title,
            )

        except Exception as e:
            logger.error("Failed to add task", error=str(e))
            await interaction.followup.send(
                "❌ タスクの追加に失敗しました。",
                ephemeral=True,
            )

    @app_commands.command(name="task_update", description="タスクの進捗を更新")  # type: ignore[type-var]
    @app_commands.describe(
        task_title="タスクタイトル（部分一致）",
        progress="進捗率 (0-100)",
        notes="更新メモ",
    )
    async def task_update_command(
        self,
        interaction: discord.Interaction,
        task_title: str,
        progress: int,
        notes: str | None = None,
    ) -> None:
        """Update task progress."""
        try:
            if not 0 <= progress <= 100:
                await interaction.response.send_message(
                    "❌ 進捗率は0から100の間で指定してください。",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # Find matching tasks
            tasks = await self.task_manager.list_tasks(active_only=True)
            matches = [
                task for task in tasks if task_title.lower() in task.title.lower()
            ]

            if not matches:
                await interaction.followup.send(
                    f"❌ '{task_title}' に一致するタスクが見つかりません。",
                    ephemeral=True,
                )
                return

            if len(matches) > 1:
                match_titles = "\n".join([f"- {task.title}" for task in matches])
                await interaction.followup.send(
                    f"❌ 複数のタスクが見つかりました。より具体的なタイトルを指定してください：\n{match_titles}",
                    ephemeral=True,
                )
                return

            task = matches[0]
            old_progress = task.progress

            # Update progress
            updated_task = await self.task_manager.update_progress(
                task.id,
                progress,
                notes,
            )

            if not updated_task:
                await interaction.followup.send(
                    "❌ タスクの更新に失敗しました。",
                    ephemeral=True,
                )
                return

            # Create embed response
            embed = discord.Embed(
                title="✅ タスクを更新しました",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="タスク", value=updated_task.title, inline=True)
            embed.add_field(
                name="進捗",
                value=f"{old_progress}% → {updated_task.progress}%",
                inline=True,
            )
            embed.add_field(
                name="ステータス", value=updated_task.status.value, inline=True
            )

            if notes:
                embed.add_field(name="メモ", value=notes, inline=False)

            if updated_task.status == TaskStatus.DONE:
                embed.add_field(name="🎉", value="タスクが完了しました！", inline=False)

            await interaction.followup.send(embed=embed)

            logger.info(
                "Task updated via command",
                user_id=interaction.user.id,
                task_id=task.id,
                old_progress=old_progress,
                new_progress=progress,
            )

        except Exception as e:
            logger.error("Failed to update task", error=str(e))
            await interaction.followup.send(
                "❌ タスクの更新に失敗しました。",
                ephemeral=True,
            )

    @app_commands.command(name="task_done", description="タスクを完了に設定")  # type: ignore[type-var]
    @app_commands.describe(
        task_title="タスクタイトル（部分一致）",
        actual_hours="実際の作業時間",
        completion_notes="完了メモ",
    )
    async def task_done_command(
        self,
        interaction: discord.Interaction,
        task_title: str,
        actual_hours: float | None = None,
        completion_notes: str | None = None,
    ) -> None:
        """Mark task as completed."""
        try:
            await interaction.response.defer()

            # Find matching tasks
            tasks = await self.task_manager.list_tasks(active_only=True)
            matches = [
                task for task in tasks if task_title.lower() in task.title.lower()
            ]

            if not matches:
                await interaction.followup.send(
                    f"❌ '{task_title}' に一致するタスクが見つかりません。",
                    ephemeral=True,
                )
                return

            if len(matches) > 1:
                match_titles = "\n".join([f"- {task.title}" for task in matches])
                await interaction.followup.send(
                    f"❌ 複数のタスクが見つかりました。より具体的なタイトルを指定してください：\n{match_titles}",
                    ephemeral=True,
                )
                return

            task = matches[0]

            # Complete task
            completed_task = await self.task_manager.complete_task(
                task.id,
                actual_hours=actual_hours,
                completion_notes=completion_notes,
            )

            if not completed_task:
                await interaction.followup.send(
                    "❌ タスクの完了処理に失敗しました。",
                    ephemeral=True,
                )
                return

            # Create embed response
            embed = discord.Embed(
                title="🎉 タスクを完了しました",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="タスク", value=completed_task.title, inline=True)
            embed.add_field(
                name="完了日時",
                value=completed_task.completed_at.strftime("%Y-%m-%d %H:%M")
                if completed_task.completed_at
                else "不明",
                inline=True,
            )

            if completed_task.estimated_hours and completed_task.actual_hours:
                embed.add_field(
                    name="作業時間",
                    value=f"予想: {completed_task.estimated_hours}h / 実績: {completed_task.actual_hours}h",
                    inline=True,
                )
            elif completed_task.actual_hours:
                embed.add_field(
                    name="実績時間",
                    value=f"{completed_task.actual_hours}時間",
                    inline=True,
                )

            if completion_notes:
                embed.add_field(name="完了メモ", value=completion_notes, inline=False)

            await interaction.followup.send(embed=embed)

            logger.info(
                "Task completed via command",
                user_id=interaction.user.id,
                task_id=task.id,
                actual_hours=actual_hours,
            )

        except Exception as e:
            logger.error("Failed to complete task", error=str(e))
            await interaction.followup.send(
                "❌ タスクの完了処理に失敗しました。",
                ephemeral=True,
            )

    @app_commands.command(name="task_list", description="タスク一覧を表示")  # type: ignore[type-var]
    @app_commands.describe(
        status="ステータスフィルター",
        priority="優先度フィルター",
        project="プロジェクトフィルター",
        show_completed="完了済みタスクも表示する",
    )
    async def task_list_command(
        self,
        interaction: discord.Interaction,
        status: str | None = None,
        priority: str | None = None,
        project: str | None = None,
        show_completed: bool = False,
    ) -> None:
        """List tasks with optional filtering."""
        try:
            await interaction.response.defer()

            # Parse filters
            status_filter = None
            if status:
                try:
                    status_filter = TaskStatus(status.lower())
                except ValueError:
                    await interaction.followup.send(
                        "❌ 無効なステータスです。todo、in_progress、waiting、done、cancelled のいずれかを指定してください。",
                        ephemeral=True,
                    )
                    return

            priority_filter = None
            if priority:
                try:
                    priority_filter = TaskPriority(priority.lower())
                except ValueError:
                    await interaction.followup.send(
                        "❌ 無効な優先度です。low、medium、high、urgent のいずれかを指定してください。",
                        ephemeral=True,
                    )
                    return

            # Get tasks
            tasks = await self.task_manager.list_tasks(
                status=status_filter,
                priority=priority_filter,
                project=project,
                active_only=not show_completed,
            )

            if not tasks:
                await interaction.followup.send(
                    "📋 該当するタスクはありません。",
                    ephemeral=True,
                )
                return

            # Create embed
            embed = discord.Embed(
                title="📋 タスク一覧",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            # Group tasks by status
            status_groups: dict[TaskStatus, list[Task]] = {}
            for task in tasks:
                if task.status not in status_groups:
                    status_groups[task.status] = []
                status_groups[task.status].append(task)

            # Status emoji mapping
            status_emoji = {
                TaskStatus.TODO: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.WAITING: "⏸️",
                TaskStatus.DONE: "✅",
                TaskStatus.CANCELLED: "❌",
            }

            # Priority emoji mapping
            priority_emoji = {
                TaskPriority.LOW: "🔵",
                TaskPriority.MEDIUM: "🟡",
                TaskPriority.HIGH: "🟠",
                TaskPriority.URGENT: "🔴",
            }

            for task_status, task_list in status_groups.items():
                if len(task_list) == 0:
                    continue

                status_text = ""
                for task in task_list[:10]:  # Limit to 10 tasks per status
                    due_text = ""
                    if task.due_date:
                        days_until = (task.due_date - date.today()).days
                        if days_until < 0:
                            due_text = f" (⚠️ {abs(days_until)}日遅延)"
                        elif days_until <= 3:
                            due_text = f" (📅 {days_until}日後)"

                    progress_text = (
                        f" ({task.progress}%)"
                        if task.progress and task.progress > 0
                        else ""
                    )

                    status_text += f"{priority_emoji.get(task.priority, '⚪')} {task.title}{progress_text}{due_text}\n"

                if len(task_list) > 10:
                    status_text += f"... および他{len(task_list) - 10}件\n"

                embed.add_field(
                    name=f"{status_emoji.get(task_status, '📋')} {task_status.value if hasattr(task_status, 'value') else task_status} ({len(task_list)}件)",
                    value=status_text or "なし",
                    inline=False,
                )

            # Add summary
            total_tasks = len(tasks)
            completed_tasks = len([t for t in tasks if t.status == TaskStatus.DONE])
            overdue_tasks = len([t for t in tasks if t.is_overdue()])

            embed.add_field(
                name="📊 概要",
                value=f"総タスク数: {total_tasks}\n完了率: {(completed_tasks / total_tasks * 100):.1f}%\n遅延タスク: {overdue_tasks}件",
                inline=False,
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("Failed to list tasks", error=str(e))
            await interaction.followup.send(
                "❌ タスク一覧の取得に失敗しました。",
                ephemeral=True,
            )

    @app_commands.command(name="schedule_add", description="新しいスケジュールを追加")  # type: ignore[type-var]
    @app_commands.describe(
        title="イベントタイトル",
        start_date="開始日 (YYYY-MM-DD形式)",
        start_time="開始時間 (HH:MM形式)",
        end_time="終了時間 (HH:MM形式)",
        description="詳細説明",
        location="場所",
        schedule_type="種類 (appointment/meeting/event/deadline/reminder)",
        reminder_minutes="リマインダー（分前）",
    )
    async def schedule_add_command(
        self,
        interaction: discord.Interaction,
        title: str,
        start_date: str,
        start_time: str | None = None,
        end_time: str | None = None,
        description: str | None = None,
        location: str | None = None,
        schedule_type: str = "event",
        reminder_minutes: int | None = None,
    ) -> None:
        """Add a new schedule/event."""
        try:
            # Parse start date
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            except ValueError:
                await interaction.response.send_message(
                    "❌ 無効な開始日形式です。YYYY-MM-DD形式で入力してください。",
                    ephemeral=True,
                )
                return

            # Parse times
            start_time_obj = None
            end_time_obj = None

            if start_time:
                try:
                    start_time_obj = datetime.strptime(start_time, "%H:%M").time()
                except ValueError:
                    await interaction.response.send_message(
                        "❌ 無効な開始時間形式です。HH:MM形式で入力してください。",
                        ephemeral=True,
                    )
                    return

            if end_time:
                try:
                    end_time_obj = datetime.strptime(end_time, "%H:%M").time()
                except ValueError:
                    await interaction.response.send_message(
                        "❌ 無効な終了時間形式です。HH:MM形式で入力してください。",
                        ephemeral=True,
                    )
                    return

            # Parse schedule type
            try:
                schedule_type_obj = ScheduleType(schedule_type.lower())
            except ValueError:
                await interaction.response.send_message(
                    "❌ 無効なスケジュール種類です。appointment、meeting、event、deadline、reminder のいずれかを指定してください。",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # Create schedule
            schedule = await self.schedule_manager.create_schedule(
                title=title,
                start_date=start_date_obj,
                description=description,
                schedule_type=schedule_type_obj,
                start_time=start_time_obj,
                end_time=end_time_obj,
                location=location,
                reminder_minutes=reminder_minutes,
            )

            # Create embed response
            embed = discord.Embed(
                title="✅ スケジュールを追加しました",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="タイトル", value=schedule.title, inline=True)
            embed.add_field(
                name="種類", value=schedule.schedule_type.value, inline=True
            )
            embed.add_field(name="開始日", value=schedule.start_date, inline=True)

            if schedule.start_time:
                embed.add_field(name="開始時間", value=schedule.start_time, inline=True)
            if schedule.end_time:
                embed.add_field(name="終了時間", value=schedule.end_time, inline=True)
            if schedule.location:
                embed.add_field(name="場所", value=schedule.location, inline=True)
            if schedule.description:
                embed.add_field(name="説明", value=schedule.description, inline=False)
            if schedule.reminder_minutes:
                embed.add_field(
                    name="リマインダー",
                    value=f"{schedule.reminder_minutes}分前",
                    inline=True,
                )

            await interaction.followup.send(embed=embed)

            logger.info(
                "Schedule added via command",
                user_id=interaction.user.id,
                schedule_id=schedule.id,
                title=title,
            )

        except Exception as e:
            logger.error("Failed to add schedule", error=str(e))
            await interaction.followup.send(
                "❌ スケジュールの追加に失敗しました。",
                ephemeral=True,
            )

    @app_commands.command(name="task_stats", description="タスクの統計情報を表示")  # type: ignore[type-var]
    async def task_stats_command(self, interaction: discord.Interaction) -> None:
        """Display task statistics and analytics."""
        await interaction.response.defer()

        try:
            # Import report generator (absolute import)
            from src.tasks.report_generator import TaskReportGenerator

            # Generate comprehensive task statistics
            report_generator = TaskReportGenerator(
                self.file_manager,
                self.task_manager,
                self.schedule_manager,
                gemini_client=None,
            )

            stats_report = await report_generator.generate_task_stats()

            # Create a formatted Discord embed
            embed = discord.Embed(
                title="📊 タスク統計情報",
                description="現在のタスク統計とパフォーマンス分析",
                color=0x00D4AA,
                timestamp=datetime.now(),
            )

            # Parse the stats report and create a more Discord-friendly format
            lines = stats_report.split("\n")
            current_section = ""
            section_content = ""

            for line in lines:
                if line.startswith("##"):
                    # Add previous section to embed if it exists
                    if current_section and section_content.strip():
                        embed.add_field(
                            name=current_section.replace("##", "").strip(),
                            value=section_content.strip()[:1024],  # Discord field limit
                            inline=False,
                        )

                    # Start new section
                    current_section = line
                    section_content = ""
                elif line.startswith("#"):
                    continue  # Skip main title
                elif line.strip():
                    section_content += f"{line}\n"

            # Add last section
            if current_section and section_content.strip():
                embed.add_field(
                    name=current_section.replace("##", "").strip(),
                    value=section_content.strip()[:1024],
                    inline=False,
                )

            embed.set_footer(text="📋 タスク管理システム")

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error(
                "Error in task_stats_command",
                error=str(e),
                user_id=interaction.user.id,
                exc_info=True,
            )
            await interaction.followup.send(
                "❌ タスク統計の取得中にエラーが発生しました。管理者にお問い合わせください。",
                ephemeral=True,
            )


def setup_task_commands(
    bot: discord.Client,
    channel_config: ChannelConfig,
    file_manager: ObsidianFileManager,
    task_manager: TaskManager,
    schedule_manager: ScheduleManager,
) -> TaskCommands:
    """Setup task commands and return the commands instance."""
    commands = TaskCommands(
        bot,
        channel_config,
        file_manager,
        task_manager,
        schedule_manager,
    )

    # Register commands - type ignore for bot.tree access
    bot.tree.add_command(commands.task_add_command)  # type: ignore[attr-defined]
    bot.tree.add_command(commands.task_update_command)  # type: ignore[attr-defined]
    bot.tree.add_command(commands.task_done_command)  # type: ignore[attr-defined]
    bot.tree.add_command(commands.task_list_command)  # type: ignore[attr-defined]
    bot.tree.add_command(commands.task_stats_command)  # type: ignore[attr-defined]
    bot.tree.add_command(commands.schedule_add_command)  # type: ignore[attr-defined]

    return commands
