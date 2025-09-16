"""Task management commands."""

from datetime import date, datetime

import discord
import structlog
from discord import app_commands
from discord.ext import commands

from src.bot.mixins.command_base import CommandMixin
from src.config import get_settings
from src.obsidian import ObsidianFileManager
from src.tasks.models import TaskPriority, TaskStatus
from src.tasks.task_manager import TaskManager

logger = structlog.get_logger(__name__)
settings = get_settings()


class TaskCommands(commands.Cog, CommandMixin):
    """Task management commands."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logger
        self.task_manager = None

    async def _get_task_manager(self) -> TaskManager:
        """Get or create task manager instance."""
        if self.task_manager is None:
            file_manager = ObsidianFileManager(settings.obsidian_vault_path)
            self.task_manager = TaskManager(file_manager)
        return self.task_manager

    @app_commands.command(name="task_help", description="タスク管理機能のヘルプを表示")
    async def task_help(self, interaction: discord.Interaction) -> None:
        """Show task management help."""
        help_text = """
## 📋 タスク管理機能

**利用可能なコマンド:**
- `/task add` - 新しいタスクを作成
- `/task list` - タスク一覧を表示
- `/task done` - タスクを完了
- `/task progress` - タスクの進捗を更新
- `/task delete` - タスクを削除

**主な機能:**
- 優先度設定（低・中・高・緊急）
- 期限管理
- 進捗追跡
- プロジェクト分類
- Obsidian ノート自動生成

詳細は各コマンドをお試しください。
"""
        try:
            await self.defer_if_needed(interaction)

            embed = discord.Embed(
                title="📋 タスク管理ヘルプ",
                description=help_text,
                color=discord.Color.blue(),
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error("Failed to show task help", error=str(e))
            await self.send_error_response(
                interaction, "ヘルプの表示に失敗しました。", followup=True
            )

    @app_commands.command(name="task_add", description="新しいタスクを作成")
    @app_commands.describe(
        title="タスクのタイトル",
        description="タスクの詳細説明（オプション）",
        priority="優先度（ low/medium/high/urgent ）",
        due_date="期限日（ YYYY-MM-DD 形式）",
        estimated_hours="予想作業時間",
        project="プロジェクト名",
        tags="タグ（カンマ区切り）",
    )
    async def task_add(
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
        """Create a new task."""
        try:
            await self.defer_if_needed(interaction)

            # Parse priority
            try:
                task_priority = TaskPriority(priority.lower())
            except ValueError:
                await self.send_error_response(
                    interaction,
                    f"無効な優先度です: {priority}。 low, medium, high, urgent のいずれかを指定してください。",
                    followup=True,
                )
                return

            # Parse due date
            parsed_due_date = None
            if due_date:
                try:
                    parsed_due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
                except ValueError:
                    await self.send_error_response(
                        interaction,
                        f"無効な日付形式です: {due_date}。 YYYY-MM-DD 形式で指定してください。",
                        followup=True,
                    )
                    return

            # Parse tags
            parsed_tags = []
            if tags:
                parsed_tags = [tag.strip() for tag in tags.split(",") if tag.strip()]

            # Create task
            task_manager = await self._get_task_manager()
            task = await task_manager.create_task(
                title=title,
                description=description,
                priority=task_priority,
                due_date=parsed_due_date,
                estimated_hours=estimated_hours,
                project=project,
                tags=parsed_tags,
            )

            # Priority emoji mapping
            priority_emoji = {
                TaskPriority.LOW: "🔵",
                TaskPriority.MEDIUM: "🟡",
                TaskPriority.HIGH: "🟠",
                TaskPriority.URGENT: "🔴",
            }

            embed = discord.Embed(
                title="✅ タスクを作成しました",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )

            embed.add_field(name="タイトル", value=task.title, inline=False)
            embed.add_field(name="ID", value=f"`{task.id[:8]}...`", inline=True)
            embed.add_field(
                name="優先度",
                value=f"{priority_emoji.get(task.priority, '⚪')} {task.priority.value}",
                inline=True,
            )

            if task.due_date:
                embed.add_field(
                    name="期限", value=task.due_date.strftime("%Y-%m-%d"), inline=True
                )

            if task.estimated_hours:
                embed.add_field(
                    name="予想時間", value=f"{task.estimated_hours}時間", inline=True
                )

            if task.project:
                embed.add_field(name="プロジェクト", value=task.project, inline=True)

            if task.tags:
                embed.add_field(name="タグ", value=", ".join(task.tags), inline=False)

            if task.description:
                embed.add_field(name="説明", value=task.description, inline=False)

            embed.set_footer(text="Obsidian ノートが自動生成されました")

            await interaction.followup.send(embed=embed)

            self.logger.info(
                "Task created",
                task_id=task.id,
                title=title,
                priority=priority,
                user_id=interaction.user.id,
            )

        except Exception as e:
            self.logger.error("Failed to create task", error=str(e))
            await self.send_error_response(
                interaction, "タスクの作成に失敗しました。", followup=True
            )

    @app_commands.command(name="task_list", description="タスク一覧を表示")
    @app_commands.describe(
        status="ステータスでフィルタ（ todo/in_progress/waiting/done ）",
        priority="優先度でフィルタ（ low/medium/high/urgent ）",
        project="プロジェクトでフィルタ",
        active_only="アクティブなタスクのみ表示",
        limit="表示件数の上限",
    )
    async def task_list(
        self,
        interaction: discord.Interaction,
        status: str | None = None,
        priority: str | None = None,
        project: str | None = None,
        active_only: bool = True,
        limit: int = 10,
    ) -> None:
        """List tasks with optional filtering."""
        try:
            await self.defer_if_needed(interaction)

            # Parse filters
            task_status = None
            if status:
                try:
                    task_status = TaskStatus(status.lower())
                except ValueError:
                    await self.send_error_response(
                        interaction,
                        f"無効なステータスです: {status}。 todo, in_progress, waiting, done のいずれかを指定してください。",
                        followup=True,
                    )
                    return

            task_priority = None
            if priority:
                try:
                    task_priority = TaskPriority(priority.lower())
                except ValueError:
                    await self.send_error_response(
                        interaction,
                        f"無効な優先度です: {priority}。 low, medium, high, urgent のいずれかを指定してください。",
                        followup=True,
                    )
                    return

            # Get tasks
            task_manager = await self._get_task_manager()
            tasks = await task_manager.list_tasks(
                status=task_status,
                priority=task_priority,
                project=project,
                active_only=active_only,
            )

            if not tasks:
                embed = discord.Embed(
                    title="📝 タスク一覧",
                    description="条件に一致するタスクが見つかりませんでした。",
                    color=discord.Color.blue(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Limit results
            tasks = tasks[:limit]

            # Status and priority emoji mappings
            status_emoji = {
                TaskStatus.TODO: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.WAITING: "⏸️",
                TaskStatus.DONE: "✅",
                TaskStatus.CANCELLED: "❌",
            }

            priority_emoji = {
                TaskPriority.LOW: "🔵",
                TaskPriority.MEDIUM: "🟡",
                TaskPriority.HIGH: "🟠",
                TaskPriority.URGENT: "🔴",
            }

            embed = discord.Embed(
                title="📝 タスク一覧",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            # Add filter info
            filter_info = []
            if task_status:
                filter_info.append(f"ステータス: {task_status.value}")
            if task_priority:
                filter_info.append(f"優先度: {task_priority.value}")
            if project:
                filter_info.append(f"プロジェクト: {project}")
            if active_only:
                filter_info.append("アクティブのみ")

            if filter_info:
                embed.description = f"フィルタ: {', '.join(filter_info)}"

            # Add tasks to embed
            for i, task in enumerate(tasks):
                task_info = []

                # Status and priority
                task_info.append(
                    f"{status_emoji.get(task.status, '📋')} {task.status.value}"
                )
                task_info.append(
                    f"{priority_emoji.get(task.priority, '⚪')} {task.priority.value}"
                )

                # Progress
                if task.progress > 0:
                    task_info.append(f"進捗: {task.progress}%")

                # Due date
                if task.due_date:
                    days_until_due = (task.due_date - date.today()).days
                    if days_until_due < 0:
                        task_info.append(f"🔴 期限切れ ({abs(days_until_due)}日前)")
                    elif days_until_due == 0:
                        task_info.append("🟡 今日が期限")
                    elif days_until_due <= 3:
                        task_info.append(f"🟡 あと{days_until_due}日")
                    else:
                        task_info.append(f"期限: {task.due_date.strftime('%m/%d')}")

                # Project
                if task.project:
                    task_info.append(f"📁 {task.project}")

                field_name = f"{i + 1}. {task.title}"
                field_value = "\n".join(task_info)
                field_value += f"\n`ID: {task.id[:8]}...`"

                embed.add_field(name=field_name, value=field_value, inline=False)

            if len(tasks) == limit:
                embed.set_footer(text=f"最初の{limit}件を表示しています")
            else:
                embed.set_footer(text=f"{len(tasks)}件のタスクを表示")

            await interaction.followup.send(embed=embed)

            self.logger.info(
                "Task list displayed",
                task_count=len(tasks),
                user_id=interaction.user.id,
            )

        except Exception as e:
            self.logger.error("Failed to list tasks", error=str(e))
            await self.send_error_response(
                interaction, "タスク一覧の表示に失敗しました。", followup=True
            )

    @app_commands.command(name="task_done", description="タスクを完了としてマーク")
    @app_commands.describe(
        task_id="完了するタスクの ID （先頭 8 文字でも可）",
        actual_hours="実際の作業時間",
        notes="完了時のメモ",
    )
    async def task_done(
        self,
        interaction: discord.Interaction,
        task_id: str,
        actual_hours: float | None = None,
        notes: str | None = None,
    ) -> None:
        """Mark a task as complete."""
        try:
            await self.defer_if_needed(interaction)

            task_manager = await self._get_task_manager()

            # Find task by partial ID if needed
            if len(task_id) == 8:
                tasks = await task_manager.list_tasks()
                matching_tasks = [t for t in tasks if t.id.startswith(task_id)]

                if not matching_tasks:
                    await self.send_error_response(
                        interaction,
                        f"ID `{task_id}` に一致するタスクが見つかりませんでした。",
                        followup=True,
                    )
                    return
                elif len(matching_tasks) > 1:
                    await self.send_error_response(
                        interaction,
                        f"ID `{task_id}` に一致するタスクが複数見つかりました。より具体的な ID を指定してください。",
                        followup=True,
                    )
                    return

                task_id = matching_tasks[0].id

            # Complete the task
            task = await task_manager.complete_task(
                task_id=task_id, actual_hours=actual_hours, completion_notes=notes
            )

            if not task:
                await self.send_error_response(
                    interaction,
                    f"タスクが見つかりませんでした: {task_id}",
                    followup=True,
                )
                return

            embed = discord.Embed(
                title="✅ タスクを完了しました",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )

            embed.add_field(name="タイトル", value=task.title, inline=False)
            embed.add_field(name="ID", value=f"`{task.id[:8]}...`", inline=True)
            if task.completed_at:
                embed.add_field(
                    name="完了日時",
                    value=task.completed_at.strftime("%Y-%m-%d %H:%M"),
                    inline=True,
                )

            if task.estimated_hours and task.actual_hours:
                variance = task.actual_hours - task.estimated_hours
                variance_text = (
                    f"+{variance:.1f}h" if variance > 0 else f"{variance:.1f}h"
                )
                embed.add_field(
                    name="時間",
                    value=f"予想: {task.estimated_hours}h\n 実績: {task.actual_hours}h ({variance_text})",
                    inline=True,
                )
            elif task.actual_hours:
                embed.add_field(
                    name="実績時間", value=f"{task.actual_hours}時間", inline=True
                )

            if task.project:
                embed.add_field(name="プロジェクト", value=task.project, inline=True)

            if notes:
                embed.add_field(name="完了メモ", value=notes, inline=False)

            # Calculate duration
            if task.started_at and task.completed_at:
                duration = task.completed_at - task.started_at
                duration_text = f"{duration.days}日 {duration.seconds // 3600}時間"
                embed.add_field(name="作業期間", value=duration_text, inline=True)

            embed.set_footer(text="Obsidian ノートが更新されました")

            await interaction.followup.send(embed=embed)

            self.logger.info(
                "Task completed",
                task_id=task.id,
                title=task.title,
                actual_hours=actual_hours,
                user_id=interaction.user.id,
            )

        except Exception as e:
            self.logger.error("Failed to complete task", error=str(e))
            await self.send_error_response(
                interaction, "タスクの完了処理に失敗しました。", followup=True
            )

    @app_commands.command(name="task_progress", description="タスクの進捗を更新")
    @app_commands.describe(
        task_id="更新するタスクの ID （先頭 8 文字でも可）",
        progress="進捗パーセンテージ（ 0-100 ）",
        notes="進捗更新時のメモ",
    )
    async def task_progress(
        self,
        interaction: discord.Interaction,
        task_id: str,
        progress: int,
        notes: str | None = None,
    ) -> None:
        """Update task progress."""
        try:
            await self.defer_if_needed(interaction)

            # Validate progress
            if not 0 <= progress <= 100:
                await self.send_error_response(
                    interaction,
                    "進捗は 0 から 100 の間で指定してください。",
                    followup=True,
                )
                return

            task_manager = await self._get_task_manager()

            # Find task by partial ID if needed
            if len(task_id) == 8:
                tasks = await task_manager.list_tasks()
                matching_tasks = [t for t in tasks if t.id.startswith(task_id)]

                if not matching_tasks:
                    await self.send_error_response(
                        interaction,
                        f"ID `{task_id}` に一致するタスクが見つかりませんでした。",
                        followup=True,
                    )
                    return
                elif len(matching_tasks) > 1:
                    await self.send_error_response(
                        interaction,
                        f"ID `{task_id}` に一致するタスクが複数見つかりました。より具体的な ID を指定してください。",
                        followup=True,
                    )
                    return

                task_id = matching_tasks[0].id

            # Update progress
            task = await task_manager.update_progress(
                task_id=task_id, progress=progress, notes=notes
            )

            if not task:
                await self.send_error_response(
                    interaction,
                    f"タスクが見つかりませんでした: {task_id}",
                    followup=True,
                )
                return

            # Status emoji mapping
            status_emoji = {
                TaskStatus.TODO: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.WAITING: "⏸️",
                TaskStatus.DONE: "✅",
                TaskStatus.CANCELLED: "❌",
            }

            embed = discord.Embed(
                title="📈 タスクの進捗を更新しました",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            embed.add_field(name="タイトル", value=task.title, inline=False)
            embed.add_field(name="ID", value=f"`{task.id[:8]}...`", inline=True)
            embed.add_field(
                name="進捗",
                value=f"{progress}% {'（完了！）' if progress == 100 else ''}",
                inline=True,
            )
            embed.add_field(
                name="ステータス",
                value=f"{status_emoji.get(task.status, '📋')} {task.status.value}",
                inline=True,
            )

            if task.project:
                embed.add_field(name="プロジェクト", value=task.project, inline=True)

            if notes:
                embed.add_field(name="更新メモ", value=notes, inline=False)

            # Progress bar visualization
            progress_bar_length = 10
            filled_length = int(progress_bar_length * progress // 100)
            bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
            embed.add_field(name="進捗バー", value=f"`{bar}` {progress}%", inline=False)

            embed.set_footer(text="Obsidian ノートが更新されました")

            await interaction.followup.send(embed=embed)

            self.logger.info(
                "Task progress updated",
                task_id=task.id,
                title=task.title,
                progress=progress,
                user_id=interaction.user.id,
            )

        except Exception as e:
            self.logger.error("Failed to update task progress", error=str(e))
            await self.send_error_response(
                interaction, "タスクの進捗更新に失敗しました。", followup=True
            )

    @app_commands.command(name="task_delete", description="タスクを削除")
    @app_commands.describe(
        task_id="削除するタスクの ID （先頭 8 文字でも可）",
        confirm="削除を確認するため 'DELETE' と入力してください",
    )
    async def task_delete(
        self, interaction: discord.Interaction, task_id: str, confirm: str
    ) -> None:
        """Delete a task."""
        try:
            await self.defer_if_needed(interaction)

            # Require explicit confirmation
            if confirm != "DELETE":
                await self.send_error_response(
                    interaction,
                    "タスクの削除には確認が必要です。 `confirm` パラメータに 'DELETE' と入力してください。",
                    followup=True,
                )
                return

            task_manager = await self._get_task_manager()

            # Find task by partial ID if needed
            if len(task_id) == 8:
                tasks = await task_manager.list_tasks()
                matching_tasks = [t for t in tasks if t.id.startswith(task_id)]

                if not matching_tasks:
                    await self.send_error_response(
                        interaction,
                        f"ID `{task_id}` に一致するタスクが見つかりませんでした。",
                        followup=True,
                    )
                    return
                elif len(matching_tasks) > 1:
                    await self.send_error_response(
                        interaction,
                        f"ID `{task_id}` に一致するタスクが複数見つかりました。より具体的な ID を指定してください。",
                        followup=True,
                    )
                    return

                task_id = matching_tasks[0].id

            # Get task details before deletion
            task = await task_manager.get_task(task_id)
            if not task:
                await self.send_error_response(
                    interaction,
                    f"タスクが見つかりませんでした: {task_id}",
                    followup=True,
                )
                return

            # Check for subtasks
            subtasks = await task_manager.get_subtasks(task_id)
            if subtasks:
                await self.send_error_response(
                    interaction,
                    f"このタスクには {len(subtasks)} 個のサブタスクが存在するため削除できません。先にサブタスクを削除してください。",
                    followup=True,
                )
                return

            # Delete the task
            success = await task_manager.delete_task(task_id)

            if not success:
                await self.send_error_response(
                    interaction, "タスクの削除に失敗しました。", followup=True
                )
                return

            embed = discord.Embed(
                title="🗑️ タスクを削除しました",
                color=discord.Color.red(),
                timestamp=datetime.now(),
            )

            embed.add_field(name="削除されたタスク", value=task.title, inline=False)
            embed.add_field(name="ID", value=f"`{task.id[:8]}...`", inline=True)

            if task.project:
                embed.add_field(name="プロジェクト", value=task.project, inline=True)

            embed.set_footer(text="⚠️ この操作は元に戻せません")

            await interaction.followup.send(embed=embed)

            self.logger.info(
                "Task deleted",
                task_id=task.id,
                title=task.title,
                user_id=interaction.user.id,
            )

        except Exception as e:
            self.logger.error("Failed to delete task", error=str(e))
            await self.send_error_response(
                interaction, "タスクの削除に失敗しました。", followup=True
            )


async def setup(bot: commands.Bot) -> None:
    """Setup function for the cog."""
    await bot.add_cog(TaskCommands(bot))
