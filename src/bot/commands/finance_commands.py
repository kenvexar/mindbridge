"""Finance management Discord commands."""

from datetime import date, datetime
from decimal import Decimal

import discord
import structlog
from discord import app_commands
from discord.ext import commands

from src.bot.mixins.command_base import CommandMixin
from src.config import get_settings
from src.finance.expense_manager import ExpenseManager
from src.finance.models import BudgetCategory, SubscriptionFrequency
from src.finance.subscription_manager import SubscriptionManager
from src.obsidian import ObsidianFileManager

logger = structlog.get_logger(__name__)
settings = get_settings()


class FinanceCommands(commands.Cog, CommandMixin):
    """Finance management commands."""

    def __init__(self, bot):
        self.bot = bot
        self.logger = logger
        self.expense_manager = None
        self.subscription_manager = None

    async def _get_expense_manager(self) -> ExpenseManager:
        """Get or create expense manager instance."""
        if self.expense_manager is None:
            file_manager = ObsidianFileManager(settings.obsidian_vault_path)
            self.expense_manager = ExpenseManager(file_manager)
        return self.expense_manager

    async def _get_subscription_manager(self) -> SubscriptionManager:
        """Get or create subscription manager instance."""
        if self.subscription_manager is None:
            file_manager = ObsidianFileManager(settings.obsidian_vault_path)
            self.subscription_manager = SubscriptionManager(file_manager)
        return self.subscription_manager

    @app_commands.command(name="finance_help", description="家計管理機能のヘルプを表示")
    async def finance_help(self, interaction: discord.Interaction) -> None:
        """Show finance management help."""
        help_text = """
## 💰 家計管理機能

**支出管理:**
- `/expense_add` - 支出を記録
- `/expense_list` - 支出履歴を表示
- `/income_add` - 収入を記録

**定期購入管理:**
- `/subscription_add` - 定期購入を追加
- `/subscription_list` - 定期購入一覧を表示
- `/subscription_pay` - 支払いを記録

**レポート:**
- `/finance_summary` - 家計サマリーを表示

**主な機能:**
- 支出カテゴリ別追跡
- 定期購入の自動管理
- Obsidian ノート自動生成
- 月次・年次レポート
"""
        try:
            await self.defer_if_needed(interaction)

            embed = discord.Embed(
                title="💰 家計管理ヘルプ",
                description=help_text,
                color=discord.Color.gold(),
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            self.logger.error("Failed to show finance help", error=str(e))
            await self.send_error_response(
                interaction, "ヘルプの表示に失敗しました。", followup=True
            )

    @app_commands.command(name="expense_add", description="支出を記録")
    @app_commands.describe(
        amount="支出金額",
        description="支出の説明",
        category="支出カテゴリ（ food/transportation/entertainment/utilities/healthcare/education/shopping/other ）",
        notes="メモ（オプション）",
    )
    async def expense_add(
        self,
        interaction: discord.Interaction,
        amount: float,
        description: str,
        category: str = "other",
        notes: str | None = None,
    ) -> None:
        """Add an expense record."""
        try:
            await self.defer_if_needed(interaction)

            # Validate amount
            if amount <= 0:
                await self.send_error_response(
                    interaction,
                    "金額は 0 より大きい値を指定してください。",
                    followup=True,
                )
                return

            # Parse category
            try:
                budget_category = BudgetCategory.from_string(category)
            except ValueError:
                await self.send_error_response(
                    interaction,
                    f"無効なカテゴリです: {category}。有効なカテゴリ: food, transportation, entertainment, utilities, healthcare, education, shopping, other",
                    followup=True,
                )
                return

            # Create expense
            expense_manager = await self._get_expense_manager()
            expense = await expense_manager.add_expense(
                description=description,
                amount=Decimal(str(amount)),
                category=budget_category,
                notes=notes,
            )

            # Category emoji mapping
            category_emoji = {
                BudgetCategory.FOOD: "🍽️",
                BudgetCategory.TRANSPORTATION: "🚗",
                BudgetCategory.ENTERTAINMENT: "🎬",
                BudgetCategory.UTILITIES: "💡",
                BudgetCategory.HEALTHCARE: "🏥",
                BudgetCategory.EDUCATION: "📚",
                BudgetCategory.SHOPPING: "🛍️",
                BudgetCategory.OTHER: "📝",
            }

            embed = discord.Embed(
                title="💸 支出を記録しました",
                color=discord.Color.red(),
                timestamp=datetime.now(),
            )

            embed.add_field(name="説明", value=expense.description, inline=False)
            embed.add_field(name="金額", value=f"¥{expense.amount:,}", inline=True)
            embed.add_field(
                name="カテゴリ",
                value=f"{category_emoji.get(expense.category, '📝')} {expense.category.value}",
                inline=True,
            )
            embed.add_field(
                name="日付",
                value=expense.expense_date.strftime("%Y-%m-%d"),
                inline=True,
            )

            if expense.notes:
                embed.add_field(name="メモ", value=expense.notes, inline=False)

            embed.add_field(name="ID", value=f"`{expense.id[:8]}...`", inline=True)
            embed.set_footer(text="Obsidian ノートに記録されました")

            await interaction.followup.send(embed=embed)

            self.logger.info(
                "Expense added",
                expense_id=expense.id,
                amount=float(amount),
                category=category,
                user_id=interaction.user.id,
            )

        except Exception as e:
            self.logger.error("Failed to add expense", error=str(e))
            await self.send_error_response(
                interaction, "支出の記録に失敗しました。", followup=True
            )

    @app_commands.command(name="income_add", description="収入を記録")
    @app_commands.describe(
        amount="収入金額", description="収入の説明", notes="メモ（オプション）"
    )
    async def income_add(
        self,
        interaction: discord.Interaction,
        amount: float,
        description: str,
        notes: str | None = None,
    ) -> None:
        """Add an income record."""
        try:
            await self.defer_if_needed(interaction)

            # Validate amount
            if amount <= 0:
                await self.send_error_response(
                    interaction,
                    "金額は 0 より大きい値を指定してください。",
                    followup=True,
                )
                return

            # Create income
            expense_manager = await self._get_expense_manager()
            income = await expense_manager.add_income(
                description=description, amount=Decimal(str(amount)), notes=notes
            )

            embed = discord.Embed(
                title="💰 収入を記録しました",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )

            embed.add_field(name="説明", value=income.description, inline=False)
            embed.add_field(name="金額", value=f"¥{income.amount:,}", inline=True)
            embed.add_field(
                name="日付", value=income.income_date.strftime("%Y-%m-%d"), inline=True
            )

            if income.notes:
                embed.add_field(name="メモ", value=income.notes, inline=False)

            embed.add_field(name="ID", value=f"`{income.id[:8]}...`", inline=True)
            embed.set_footer(text="Obsidian ノートに記録されました")

            await interaction.followup.send(embed=embed)

            self.logger.info(
                "Income added",
                income_id=income.id,
                amount=float(amount),
                user_id=interaction.user.id,
            )

        except Exception as e:
            self.logger.error("Failed to add income", error=str(e))
            await self.send_error_response(
                interaction, "収入の記録に失敗しました。", followup=True
            )

    @app_commands.command(name="expense_list", description="支出履歴を表示")
    @app_commands.describe(
        category="カテゴリでフィルタ（オプション）",
        days="過去何日分を表示するか（デフォルト: 30 ）",
    )
    async def expense_list(
        self,
        interaction: discord.Interaction,
        category: str | None = None,
        days: int = 30,
    ) -> None:
        """List recent expenses."""
        try:
            await self.defer_if_needed(interaction)

            # Validate days
            if days <= 0 or days > 365:
                await self.send_error_response(
                    interaction,
                    "日数は 1 から 365 の間で指定してください。",
                    followup=True,
                )
                return

            expense_manager = await self._get_expense_manager()

            from datetime import timedelta

            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            # Parse category filter
            budget_category = None
            if category:
                try:
                    budget_category = BudgetCategory.from_string(category)
                except ValueError:
                    await self.send_error_response(
                        interaction, f"無効なカテゴリです: {category}", followup=True
                    )
                    return

            expenses = await expense_manager.get_expenses_by_period(
                start_date=start_date, end_date=end_date, category=budget_category
            )

            if not expenses:
                embed = discord.Embed(
                    title="💸 支出履歴",
                    description="指定期間内の支出が見つかりませんでした。",
                    color=discord.Color.blue(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Limit to 10 most recent
            expenses = expenses[:10]

            # Category emoji mapping
            category_emoji = {
                BudgetCategory.FOOD: "🍽️",
                BudgetCategory.TRANSPORTATION: "🚗",
                BudgetCategory.ENTERTAINMENT: "🎬",
                BudgetCategory.UTILITIES: "💡",
                BudgetCategory.HEALTHCARE: "🏥",
                BudgetCategory.EDUCATION: "📚",
                BudgetCategory.SHOPPING: "🛍️",
                BudgetCategory.OTHER: "📝",
            }

            embed = discord.Embed(
                title="💸 支出履歴", color=discord.Color.red(), timestamp=datetime.now()
            )

            # Add filter info
            filter_info = f"過去 {days} 日間"
            if budget_category:
                filter_info += f" / カテゴリ: {budget_category.value}"
            embed.description = filter_info

            # Calculate total
            total_amount = sum(expense.amount for expense in expenses)
            embed.add_field(name="合計金額", value=f"¥{total_amount:,}", inline=False)

            # Add expense entries
            for i, expense in enumerate(expenses):
                emoji = category_emoji.get(expense.category, "📝")
                field_name = f"{i + 1}. {expense.description}"
                field_value = (
                    f"{emoji} {expense.category.value} - ¥{expense.amount:,}\n"
                )
                field_value += f"📅 {expense.expense_date.strftime('%m/%d')}"
                if expense.notes:
                    field_value += f"\n 💭 {expense.notes[:50]}{'...' if len(expense.notes) > 50 else ''}"

                embed.add_field(name=field_name, value=field_value, inline=False)

            embed.set_footer(text=f"{len(expenses)} 件の支出を表示")

            await interaction.followup.send(embed=embed)

            self.logger.info(
                "Expense list displayed",
                expense_count=len(expenses),
                total_amount=float(total_amount),
                user_id=interaction.user.id,
            )

        except Exception as e:
            self.logger.error("Failed to list expenses", error=str(e))
            await self.send_error_response(
                interaction, "支出履歴の表示に失敗しました。", followup=True
            )

    @app_commands.command(name="subscription_add", description="定期購入を追加")
    @app_commands.describe(
        name="サービス名",
        amount="金額",
        frequency="支払い頻度（ weekly/monthly/quarterly/yearly ）",
        start_date="開始日（ YYYY-MM-DD 形式、オプション）",
        category="カテゴリ（オプション）",
    )
    async def subscription_add(
        self,
        interaction: discord.Interaction,
        name: str,
        amount: float,
        frequency: str,
        start_date: str | None = None,
        category: str | None = None,
    ) -> None:
        """Add a new subscription."""
        try:
            await self.defer_if_needed(interaction)

            # Validate amount
            if amount <= 0:
                await self.send_error_response(
                    interaction,
                    "金額は 0 より大きい値を指定してください。",
                    followup=True,
                )
                return

            # Parse frequency
            try:
                subscription_frequency = SubscriptionFrequency(frequency.lower())
            except ValueError:
                await self.send_error_response(
                    interaction,
                    f"無効な支払い頻度です: {frequency}。 weekly, monthly, quarterly, yearly のいずれかを指定してください。",
                    followup=True,
                )
                return

            # Parse start date
            parsed_start_date = date.today()
            if start_date:
                try:
                    parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                except ValueError:
                    await self.send_error_response(
                        interaction,
                        f"無効な日付形式です: {start_date}。 YYYY-MM-DD 形式で指定してください。",
                        followup=True,
                    )
                    return

            # Create subscription
            subscription_manager = await self._get_subscription_manager()
            subscription = await subscription_manager.add_subscription(
                name=name,
                amount=Decimal(str(amount)),
                frequency=subscription_frequency,
                start_date=parsed_start_date,
                category=category,
            )

            # Frequency emoji mapping
            frequency_emoji = {
                SubscriptionFrequency.WEEKLY: "📅",
                SubscriptionFrequency.MONTHLY: "🗓️",
                SubscriptionFrequency.QUARTERLY: "📆",
                SubscriptionFrequency.YEARLY: "🗓",
            }

            embed = discord.Embed(
                title="📱 定期購入を追加しました",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            embed.add_field(name="サービス名", value=subscription.name, inline=False)
            embed.add_field(name="金額", value=f"¥{subscription.amount:,}", inline=True)
            embed.add_field(
                name="支払い頻度",
                value=f"{frequency_emoji.get(subscription.frequency, '📅')} {subscription.frequency.value}",
                inline=True,
            )
            embed.add_field(
                name="開始日",
                value=subscription.start_date.strftime("%Y-%m-%d"),
                inline=True,
            )
            embed.add_field(
                name="次回支払日",
                value=subscription.next_payment_date.strftime("%Y-%m-%d"),
                inline=True,
            )

            if subscription.category:
                embed.add_field(
                    name="カテゴリ", value=subscription.category, inline=True
                )

            # Calculate monthly equivalent
            monthly_amount = subscription.get_monthly_amount()
            embed.add_field(name="月額換算", value=f"¥{monthly_amount:,}", inline=True)

            embed.add_field(name="ID", value=f"`{subscription.id[:8]}...`", inline=True)
            embed.set_footer(text="Obsidian ノートが作成されました")

            await interaction.followup.send(embed=embed)

            self.logger.info(
                "Subscription added",
                subscription_id=subscription.id,
                name=name,
                amount=float(amount),
                frequency=frequency,
                user_id=interaction.user.id,
            )

        except Exception as e:
            self.logger.error("Failed to add subscription", error=str(e))
            await self.send_error_response(
                interaction, "定期購入の追加に失敗しました。", followup=True
            )

    @app_commands.command(name="subscription_list", description="定期購入一覧を表示")
    @app_commands.describe(active_only="アクティブな定期購入のみ表示")
    async def subscription_list(
        self, interaction: discord.Interaction, active_only: bool = True
    ) -> None:
        """List subscriptions."""
        try:
            await self.defer_if_needed(interaction)

            subscription_manager = await self._get_subscription_manager()
            subscriptions = await subscription_manager.list_subscriptions(
                active_only=active_only
            )

            if not subscriptions:
                embed = discord.Embed(
                    title="📱 定期購入一覧",
                    description="定期購入が見つかりませんでした。",
                    color=discord.Color.blue(),
                )
                await interaction.followup.send(embed=embed)
                return

            # Frequency emoji mapping
            frequency_emoji = {
                SubscriptionFrequency.WEEKLY: "📅",
                SubscriptionFrequency.MONTHLY: "🗓️",
                SubscriptionFrequency.QUARTERLY: "📆",
                SubscriptionFrequency.YEARLY: "🗓",
            }

            embed = discord.Embed(
                title="📱 定期購入一覧",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            if active_only:
                embed.description = "アクティブな定期購入のみ表示"

            # Calculate total monthly cost
            total_monthly = sum(sub.get_monthly_amount() for sub in subscriptions)
            embed.add_field(name="月額合計", value=f"¥{total_monthly:,}", inline=False)

            # Add subscription entries (limit to 10)
            for i, subscription in enumerate(subscriptions[:10]):
                # Check if due soon or overdue
                status_indicator = ""
                if subscription.is_overdue():
                    status_indicator = "🔴 期限切れ"
                elif subscription.is_due_soon():
                    status_indicator = "🟡 支払い期限間近"

                field_name = f"{i + 1}. {subscription.name}"
                field_value = f"{frequency_emoji.get(subscription.frequency, '📅')} ¥{subscription.amount:,} ({subscription.frequency.value})\n"
                field_value += (
                    f"次回: {subscription.next_payment_date.strftime('%m/%d')}"
                )

                if status_indicator:
                    field_value += f"\n{status_indicator}"

                if subscription.category:
                    field_value += f"\n 📂 {subscription.category}"

                embed.add_field(name=field_name, value=field_value, inline=False)

            if len(subscriptions) > 10:
                embed.set_footer(text=f"最初の 10 件を表示（全{len(subscriptions)}件）")
            else:
                embed.set_footer(text=f"{len(subscriptions)}件の定期購入を表示")

            await interaction.followup.send(embed=embed)

            self.logger.info(
                "Subscription list displayed",
                subscription_count=len(subscriptions),
                total_monthly=float(total_monthly),
                user_id=interaction.user.id,
            )

        except Exception as e:
            self.logger.error("Failed to list subscriptions", error=str(e))
            await self.send_error_response(
                interaction, "定期購入一覧の表示に失敗しました。", followup=True
            )

    @app_commands.command(name="finance_summary", description="家計サマリーを表示")
    @app_commands.describe(days="過去何日分を表示するか（デフォルト: 30 ）")
    async def finance_summary(
        self, interaction: discord.Interaction, days: int = 30
    ) -> None:
        """Show finance summary."""
        try:
            await self.defer_if_needed(interaction)

            # Validate days
            if days <= 0 or days > 365:
                await self.send_error_response(
                    interaction,
                    "日数は 1 から 365 の間で指定してください。",
                    followup=True,
                )
                return

            expense_manager = await self._get_expense_manager()
            subscription_manager = await self._get_subscription_manager()

            from datetime import timedelta

            end_date = date.today()
            start_date = end_date - timedelta(days=days)

            # Get financial data
            total_expenses = await expense_manager.get_total_expenses(
                start_date, end_date
            )
            total_income = await expense_manager.get_total_income(start_date, end_date)
            net_balance = total_income - total_expenses

            expenses_by_category = await expense_manager.get_total_expenses_by_category(
                start_date, end_date
            )
            active_subscriptions = await subscription_manager.get_active_subscriptions()
            monthly_subscription_cost = await subscription_manager.get_monthly_cost()

            embed = discord.Embed(
                title="📊 家計サマリー",
                color=discord.Color.gold(),
                timestamp=datetime.now(),
            )

            embed.description = f"過去 {days} 日間の財務状況"

            # Balance overview
            balance_color = "🟢" if net_balance >= 0 else "🔴"
            embed.add_field(
                name="💰 収支概要",
                value=f"収入: ¥{total_income:,}\n 支出: ¥{total_expenses:,}\n{balance_color} 収支: ¥{net_balance:,}",
                inline=False,
            )

            # Subscription summary
            embed.add_field(
                name="📱 定期購入",
                value=f"アクティブ: {len(active_subscriptions)}件\n 月額合計: ¥{monthly_subscription_cost:,}",
                inline=True,
            )

            # Top expense categories
            if expenses_by_category:
                sorted_categories = sorted(
                    expenses_by_category.items(), key=lambda x: x[1], reverse=True
                )
                top_categories = sorted_categories[:3]

                category_emoji = {
                    BudgetCategory.FOOD: "🍽️",
                    BudgetCategory.TRANSPORTATION: "🚗",
                    BudgetCategory.ENTERTAINMENT: "🎬",
                    BudgetCategory.UTILITIES: "💡",
                    BudgetCategory.HEALTHCARE: "🏥",
                    BudgetCategory.EDUCATION: "📚",
                    BudgetCategory.SHOPPING: "🛍️",
                    BudgetCategory.OTHER: "📝",
                }

                category_text = ""
                for category, amount in top_categories:
                    emoji = category_emoji.get(category, "📝")
                    category_text += f"{emoji} {category.value}: ¥{amount:,}\n"

                embed.add_field(
                    name="💸 支出カテゴリ（上位 3 位）",
                    value=category_text,
                    inline=True,
                )

            # Due payments
            due_subscriptions = await subscription_manager.get_due_subscriptions(7)
            if due_subscriptions:
                due_text = ""
                for sub in due_subscriptions[:3]:
                    due_text += (
                        f"• {sub.name}: {sub.next_payment_date.strftime('%m/%d')}\n"
                    )

                embed.add_field(
                    name="⏰ 今後 7 日間の支払い予定", value=due_text, inline=False
                )

            embed.set_footer(text="詳細は各コマンドで確認できます")

            await interaction.followup.send(embed=embed)

            self.logger.info(
                "Finance summary displayed",
                days=days,
                total_income=float(total_income),
                total_expenses=float(total_expenses),
                net_balance=float(net_balance),
                user_id=interaction.user.id,
            )

        except Exception as e:
            self.logger.error("Failed to show finance summary", error=str(e))
            await self.send_error_response(
                interaction, "家計サマリーの表示に失敗しました。", followup=True
            )


async def setup(bot: commands.Bot) -> None:
    """Setup function for the cog."""
    await bot.add_cog(FinanceCommands(bot))
