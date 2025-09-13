"""Statistics and analytics commands."""

from datetime import datetime
from typing import Any

import discord
import structlog
from discord import app_commands
from discord.ext import commands

from src.bot.mixins.command_base import CommandMixin

logger = structlog.get_logger(__name__)


class StatsCommands(commands.Cog, CommandMixin):
    """Commands for displaying various statistics."""

    def __init__(self, bot: discord.Client):
        self.bot = bot
        self.startup_time = datetime.now()

    @app_commands.command(name="bot", description="ボットの統計情報を表示")
    async def stats_bot_command(self, interaction: discord.Interaction) -> None:
        """Display bot statistics."""
        try:
            await self.defer_if_needed(interaction)

            # Calculate uptime
            uptime = self._get_uptime()

            # Get basic bot stats
            guild_count = len(self.bot.guilds)
            user_count = sum(
                guild.member_count for guild in self.bot.guilds if guild.member_count
            )

            # Memory usage (if available)
            try:
                import psutil

                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_text = f"{memory_mb:.1f} MB"
            except ImportError:
                memory_text = "利用不可"

            fields = [
                ("アップタイム", uptime, True),
                ("サーバー数", str(guild_count), True),
                ("ユーザー数", str(user_count), True),
                ("メモリ使用量", memory_text, True),
                ("Python バージョン", self._get_python_version(), True),
                ("Discord.py バージョン", discord.__version__, True),
            ]

            await self.send_success_response(
                interaction,
                "ボット統計情報",
                fields=fields,
                color=discord.Color.blue(),
                followup=True,
            )

        except Exception as e:
            logger.error("Failed to get bot stats", error=str(e))
            await self.send_error_response(
                interaction, "統計情報の取得に失敗しました。", followup=True
            )

    @app_commands.command(
        name="obsidian", description="Obsidian vault の統計情報を表示"
    )
    async def obsidian_stats_command(self, interaction: discord.Interaction) -> None:
        """Display Obsidian vault statistics."""
        try:
            await self.defer_if_needed(interaction)

            # Try to get Obsidian stats from the bot's components
            obsidian_stats = await self._get_obsidian_stats()

            if not obsidian_stats:
                await self.send_error_response(
                    interaction,
                    "Obsidian の統計情報を取得できませんでした。",
                    followup=True,
                )
                return

            fields = [
                ("総ノート数", str(obsidian_stats.get("total_notes", 0)), True),
                ("今日作成", str(obsidian_stats.get("notes_today", 0)), True),
                ("今週作成", str(obsidian_stats.get("notes_this_week", 0)), True),
                ("総文字数", f"{obsidian_stats.get('total_characters', 0):,}", True),
                (
                    "平均ノートサイズ",
                    f"{obsidian_stats.get('avg_note_size', 0):.0f} 文字",
                    True,
                ),
                ("最終更新", obsidian_stats.get("last_updated", "不明"), True),
            ]

            await self.send_success_response(
                interaction,
                "Obsidian Vault 統計",
                fields=fields,
                color=discord.Color.purple(),
                followup=True,
            )

        except Exception as e:
            logger.error("Failed to get Obsidian stats", error=str(e))
            await self.send_error_response(
                interaction, "Obsidian 統計情報の取得に失敗しました。", followup=True
            )

    @app_commands.command(name="finance", description="家計管理統計情報を表示")
    async def finance_stats_command(self, interaction: discord.Interaction) -> None:
        """Display finance statistics."""
        try:
            await self.defer_if_needed(interaction)

            # Try to get finance stats
            finance_stats = await self._get_finance_stats()

            if not finance_stats:
                await self.send_error_response(
                    interaction, "家計統計情報を取得できませんでした。", followup=True
                )
                return

            fields = [
                ("今月の支出", f"¥{finance_stats.get('monthly_expenses', 0):,}", True),
                (
                    "定期購入",
                    f"¥{finance_stats.get('monthly_subscriptions', 0):,}/月",
                    True,
                ),
                ("今年の支出", f"¥{finance_stats.get('yearly_expenses', 0):,}", True),
                (
                    "アクティブ定期購入",
                    f"{finance_stats.get('active_subscriptions', 0)}件",
                    True,
                ),
                ("最大カテゴリ", finance_stats.get("top_category", "不明"), True),
                ("最終記録", finance_stats.get("last_expense_date", "不明"), True),
            ]

            await self.send_success_response(
                interaction,
                "家計管理統計",
                fields=fields,
                color=discord.Color.green(),
                followup=True,
            )

        except Exception as e:
            logger.error("Failed to get finance stats", error=str(e))
            await self.send_error_response(
                interaction, "家計統計情報の取得に失敗しました。", followup=True
            )

    @app_commands.command(name="tasks", description="タスク管理統計情報を表示")
    async def task_stats_command(self, interaction: discord.Interaction) -> None:
        """Display task management statistics."""
        try:
            await self.defer_if_needed(interaction)

            # Try to get task stats
            task_stats = await self._get_task_stats()

            if not task_stats:
                await self.send_error_response(
                    interaction, "タスク統計情報を取得できませんでした。", followup=True
                )
                return

            fields = [
                ("アクティブタスク", str(task_stats.get("active_tasks", 0)), True),
                (
                    "完了タスク（今月）",
                    str(task_stats.get("completed_this_month", 0)),
                    True,
                ),
                ("遅延タスク", str(task_stats.get("overdue_tasks", 0)), True),
                ("完了率", f"{task_stats.get('completion_rate', 0):.1f}%", True),
                (
                    "平均完了時間",
                    f"{task_stats.get('avg_completion_days', 0):.1f}日",
                    True,
                ),
                ("最終更新", task_stats.get("last_updated", "不明"), True),
            ]

            await self.send_success_response(
                interaction,
                "タスク管理統計",
                fields=fields,
                color=discord.Color.orange(),
                followup=True,
            )

        except Exception as e:
            logger.error("Failed to get task stats", error=str(e))
            await self.send_error_response(
                interaction, "タスク統計情報の取得に失敗しました。", followup=True
            )

    def _get_uptime(self) -> str:
        """Calculate bot uptime."""
        uptime_delta = datetime.now() - self.startup_time
        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return f"{days}日 {hours}時間 {minutes}分"
        elif hours > 0:
            return f"{hours}時間 {minutes}分"
        else:
            return f"{minutes}分"

    def _get_python_version(self) -> str:
        """Get Python version."""
        import sys

        return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    async def _get_obsidian_stats(self) -> dict[str, Any] | None:
        """Get Obsidian vault statistics."""
        try:
            from src.config import get_settings
            from src.obsidian.analytics.vault_statistics import VaultStatistics

            settings = get_settings()
            vault_stats = VaultStatistics(settings.obsidian_vault_path)
            stats = await vault_stats.get_vault_stats()

            return {
                "total_notes": stats.total_notes,
                "notes_today": stats.notes_today,
                "notes_this_week": stats.notes_this_week,
                "total_characters": stats.total_characters,
                "avg_note_size": stats.avg_note_size,
                "last_updated": stats.last_updated.strftime("%Y-%m-%d %H:%M")
                if stats.last_updated
                else "未取得",
            }
        except Exception as e:
            logger.error("Failed to get Obsidian stats", error=str(e))
            return None

    async def _get_finance_stats(self) -> dict[str, Any] | None:
        """Get financial statistics with improved type safety."""
        try:
            from datetime import date
            from decimal import Decimal

            from src.config import get_settings
            from src.finance.budget_manager import BudgetManager
            from src.finance.expense_manager import ExpenseManager
            from src.finance.subscription_manager import SubscriptionManager
            from src.obsidian.file_manager import ObsidianFileManager

            settings = get_settings()
            file_manager = ObsidianFileManager(settings.obsidian_vault_path)
            expense_manager = ExpenseManager(file_manager)
            subscription_manager = SubscriptionManager(file_manager)
            budget_manager = BudgetManager(file_manager, expense_manager)

            # Calculate date ranges
            today = date.today()
            month_start = today.replace(day=1)
            year_start = today.replace(month=1, day=1)

            # Get monthly expenses
            monthly_expenses_data = await expense_manager.get_expenses_by_period(
                month_start, today
            )
            monthly_expenses = sum(exp.amount for exp in monthly_expenses_data)

            # Get yearly expenses
            yearly_expenses_data = await expense_manager.get_expenses_by_period(
                year_start, today
            )
            yearly_expenses = sum(exp.amount for exp in yearly_expenses_data)

            # Get monthly subscription total using the new convenience method
            monthly_subscriptions = await subscription_manager.get_monthly_cost()
            active_subscriptions = await subscription_manager.get_active_subscriptions()

            # Get expense categories with proper type handling
            budget_categories = await budget_manager.get_all_budgets()
            category_totals: dict[str, Decimal] = {}

            for category_budget in budget_categories:
                category_expenses = [
                    exp
                    for exp in monthly_expenses_data
                    if exp.category == category_budget.category.value
                ]
                if category_expenses:
                    total_amount: Decimal = sum(
                        exp.amount for exp in category_expenses
                    ) or Decimal(0)
                    category_totals[category_budget.category.value] = total_amount

            # Get top category with proper type safety
            top_category_name = "未取得"
            if category_totals:
                top_category_key = max(category_totals, key=category_totals.__getitem__)
                # Convert to display format if it's a BudgetCategory
                from src.finance.models import BudgetCategory

                try:
                    budget_cat = BudgetCategory(top_category_key)
                    top_category_name = budget_cat.display_name
                except ValueError:
                    top_category_name = top_category_key.title()

            # Get last expense
            recent_expenses = await expense_manager.get_expenses_by_period(
                year_start, today
            )
            last_expense_date = (
                recent_expenses[0].date.strftime("%m/%d")
                if recent_expenses
                else "未取得"
            )

            return {
                "monthly_expenses": int(monthly_expenses),
                "monthly_subscriptions": int(monthly_subscriptions),
                "yearly_expenses": int(yearly_expenses),
                "active_subscriptions": len(active_subscriptions),
                "top_category": top_category_name,
                "last_expense_date": last_expense_date,
            }
        except Exception as e:
            logger.error("Failed to get finance stats", error=str(e))
            return None

    async def _get_task_stats(self) -> dict[str, Any] | None:
        """Get task management statistics."""
        try:
            from datetime import date

            from src.config import get_settings
            from src.obsidian.file_manager import ObsidianFileManager
            from src.tasks.models import TaskStatus
            from src.tasks.task_manager import TaskManager

            settings = get_settings()
            file_manager = ObsidianFileManager(settings.obsidian_vault_path)
            task_manager = TaskManager(file_manager)

            # Get all tasks
            all_tasks = await task_manager.list_tasks()
            active_tasks = await task_manager.list_tasks(active_only=True)
            overdue_tasks = await task_manager.get_overdue_tasks()

            # Calculate date ranges
            today = date.today()
            month_start = today.replace(day=1)

            # Count completed tasks this month
            completed_this_month = 0
            total_completion_days = 0
            completed_tasks = 0

            for task in all_tasks:
                if task.status == TaskStatus.DONE and task.completed_at:
                    if task.completed_at.date() >= month_start:
                        completed_this_month += 1

                    # Calculate completion time
                    if task.completed_at and task.created_at:
                        completion_days = (
                            task.completed_at.date() - task.created_at.date()
                        ).days
                        total_completion_days += completion_days
                        completed_tasks += 1

            # Calculate completion rate
            total_tasks = len(all_tasks)
            completed_total = len([t for t in all_tasks if t.status == TaskStatus.DONE])
            completion_rate = (
                (completed_total / total_tasks * 100) if total_tasks > 0 else 0
            )

            # Calculate average completion days
            avg_completion_days = (
                (total_completion_days / completed_tasks) if completed_tasks > 0 else 0
            )

            # Get last updated task
            last_updated = "未取得"
            if all_tasks:
                latest_task = max(all_tasks, key=lambda t: t.updated_at)
                last_updated = latest_task.updated_at.strftime("%m/%d")

            return {
                "active_tasks": len(active_tasks),
                "completed_this_month": completed_this_month,
                "overdue_tasks": len(overdue_tasks),
                "completion_rate": completion_rate,
                "avg_completion_days": avg_completion_days,
                "last_updated": last_updated,
            }
        except Exception as e:
            logger.error("Failed to get task stats", error=str(e))
            return None
