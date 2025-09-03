"""Finance management Discord commands."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import discord
from discord import app_commands
from discord.ext import commands as discord_commands
from structlog import get_logger

from src.bot.channel_config import ChannelConfig
from src.budget_manager import BudgetManager
from src.expense_manager import ExpenseManager
from src.finance.models import BudgetCategory, SubscriptionFrequency
from src.obsidian import ObsidianFileManager
from src.report_generator import FinanceReportGenerator
from src.subscription_manager import SubscriptionManager

logger = get_logger(__name__)


class FinanceCommands(app_commands.Group):
    """Finance management Discord commands."""

    def __init__(
        self,
        bot: discord.Client | discord_commands.Bot,
        channel_config: ChannelConfig,
        file_manager: ObsidianFileManager,
        subscription_manager: SubscriptionManager,
        expense_manager: ExpenseManager,
        budget_manager: BudgetManager,
        report_generator: FinanceReportGenerator,
    ):
        super().__init__(name="finance", description="Financial management commands")
        self.bot = bot
        self.channel_config = channel_config
        self.file_manager = file_manager
        self.subscription_manager = subscription_manager
        self.expense_manager = expense_manager
        self.budget_manager = budget_manager
        self.report_generator = report_generator

    @app_commands.command(name="sub_add", description="新しい定期購入サービスを追加")
    @app_commands.describe(
        name="サービス名",
        amount="金額",
        frequency="支払い頻度 (weekly/monthly/quarterly/yearly)",
        start_date="開始日 (YYYY-MM-DD形式、省略時は今日)",
        category="カテゴリ",
        notes="メモ",
    )
    async def sub_add_command(
        self,
        interaction: discord.Interaction,
        name: str,
        amount: str,
        frequency: str,
        start_date: str | None = None,
        category: str | None = None,
        notes: str | None = None,
    ) -> None:
        """Add a new subscription service."""
        try:
            # Parse amount
            try:
                amount_decimal = Decimal(amount.replace(",", ""))
                if amount_decimal <= 0:
                    raise ValueError("金額は0より大きい必要があります")
            except (InvalidOperation, ValueError):
                await interaction.response.send_message(
                    "❌ 無効な金額です。数値を入力してください。",
                    ephemeral=True,
                )
                return

            # Parse frequency
            try:
                freq = SubscriptionFrequency(frequency.lower())
            except ValueError:
                await interaction.response.send_message(
                    "❌ 無効な支払い頻度です。weekly、monthly、quarterly、yearly のいずれかを指定してください。",
                    ephemeral=True,
                )
                return

            # Parse start date
            try:
                if start_date:
                    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                else:
                    start_date_obj = date.today()
            except ValueError:
                await interaction.response.send_message(
                    "❌ 無効な日付形式です。YYYY-MM-DD形式で入力してください。",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # Add subscription
            subscription = await self.subscription_manager.add_subscription(
                name=name,
                amount=amount_decimal,
                frequency=freq,
                start_date=start_date_obj,
                category=category,
                notes=notes,
            )

            # Create embed response
            embed = discord.Embed(
                title="✅ 定期購入サービスを追加しました",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="サービス名", value=subscription.name, inline=True)
            embed.add_field(name="金額", value=f"¥{subscription.amount:,}", inline=True)
            embed.add_field(
                name="支払い頻度", value=subscription.frequency.value, inline=True
            )
            embed.add_field(
                name="次回支払い日", value=subscription.next_payment_date, inline=True
            )
            if subscription.category:
                embed.add_field(
                    name="カテゴリ", value=subscription.category, inline=True
                )
            if subscription.notes:
                embed.add_field(name="メモ", value=subscription.notes, inline=False)

            await interaction.followup.send(embed=embed)

            logger.info(
                "Subscription added via command",
                user_id=interaction.user.id,
                subscription_id=subscription.id,
                name=name,
            )

        except Exception as e:
            logger.error("Failed to add subscription", error=str(e))
            await interaction.followup.send(
                "❌ 定期購入サービスの追加に失敗しました。",
                ephemeral=True,
            )

    @app_commands.command(name="sub_paid", description="定期購入の支払いを完了報告")
    @app_commands.describe(
        service_name="サービス名（部分一致）",
        payment_date="支払い日 (YYYY-MM-DD形式、省略時は今日)",
        notes="支払いメモ",
    )
    async def sub_paid_command(
        self,
        interaction: discord.Interaction,
        service_name: str,
        payment_date: str | None = None,
        notes: str | None = None,
    ) -> None:
        """Mark subscription payment as completed."""
        try:
            await interaction.response.defer()

            # Find matching subscriptions
            subscriptions = await self.subscription_manager.list_subscriptions(
                active_only=True
            )
            matches = [
                sub for sub in subscriptions if service_name.lower() in sub.name.lower()
            ]

            if not matches:
                await interaction.followup.send(
                    f"❌ '{service_name}' に一致する定期購入サービスが見つかりません。",
                    ephemeral=True,
                )
                return

            if len(matches) > 1:
                match_names = "\n".join([f"- {sub.name}" for sub in matches])
                await interaction.followup.send(
                    f"❌ 複数のサービスが見つかりました。より具体的な名前を指定してください：\n{match_names}",
                    ephemeral=True,
                )
                return

            subscription = matches[0]

            # Parse payment date
            try:
                if payment_date:
                    payment_date_obj = datetime.strptime(
                        payment_date, "%Y-%m-%d"
                    ).date()
                else:
                    payment_date_obj = date.today()
            except ValueError:
                await interaction.followup.send(
                    "❌ 無効な日付形式です。YYYY-MM-DD形式で入力してください。",
                    ephemeral=True,
                )
                return

            # Mark payment
            payment = await self.subscription_manager.mark_payment(
                subscription.id,
                payment_date=payment_date_obj,
                notes=notes,
            )

            if not payment:
                await interaction.followup.send(
                    "❌ 支払い記録の作成に失敗しました。",
                    ephemeral=True,
                )
                return

            # Get updated subscription
            updated_subscription = await self.subscription_manager.get_subscription(
                subscription.id
            )

            # Create embed response
            embed = discord.Embed(
                title="✅ 支払いを記録しました",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="サービス名", value=subscription.name, inline=True)
            embed.add_field(
                name="支払い金額", value=f"¥{payment.amount:,}", inline=True
            )
            embed.add_field(name="支払い日", value=payment.payment_date, inline=True)
            embed.add_field(
                name="次回支払い日",
                value=updated_subscription.next_payment_date
                if updated_subscription
                else "不明",
                inline=True,
            )
            if notes:
                embed.add_field(name="メモ", value=notes, inline=False)

            await interaction.followup.send(embed=embed)

            logger.info(
                "Payment marked via command",
                user_id=interaction.user.id,
                subscription_id=subscription.id,
                payment_id=payment.id,
            )

        except Exception as e:
            logger.error("Failed to mark payment", error=str(e))
            await interaction.followup.send(
                "❌ 支払い記録の作成に失敗しました。",
                ephemeral=True,
            )

    @app_commands.command(name="sub_list", description="定期購入サービス一覧を表示")
    @app_commands.describe(
        show_all="非アクティブなサービスも表示する",
    )
    async def sub_list_command(
        self,
        interaction: discord.Interaction,
        show_all: bool = False,
    ) -> None:
        """List all subscription services."""
        try:
            await interaction.response.defer()

            subscriptions = await self.subscription_manager.list_subscriptions(
                active_only=not show_all
            )

            if not subscriptions:
                await interaction.followup.send(
                    "📋 登録されている定期購入サービスはありません。",
                    ephemeral=True,
                )
                return

            # Create embed
            embed = discord.Embed(
                title="📋 定期購入サービス一覧",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            total_monthly_cost = Decimal(0)

            for i, sub in enumerate(subscriptions, 1):
                # Calculate monthly equivalent
                if sub.frequency == SubscriptionFrequency.MONTHLY:
                    monthly_cost = sub.amount
                elif sub.frequency == SubscriptionFrequency.YEARLY:
                    monthly_cost = sub.amount / 12
                elif sub.frequency == SubscriptionFrequency.WEEKLY:
                    monthly_cost = sub.amount * 52 / 12
                elif sub.frequency == SubscriptionFrequency.QUARTERLY:
                    monthly_cost = sub.amount * 4 / 12
                else:
                    monthly_cost = sub.amount

                total_monthly_cost += monthly_cost

                status_emoji = {
                    "active": "🟢",
                    "paused": "🟡",
                    "cancelled": "🔴",
                }.get(sub.status.value, "❓")

                days_until = (sub.next_payment_date - date.today()).days
                if days_until < 0:
                    next_payment_text = f"⚠️ {abs(days_until)}日遅延"
                elif days_until <= 3:
                    next_payment_text = f"🔔 {days_until}日後"
                else:
                    next_payment_text = f"{days_until}日後"

                field_value = (
                    f"¥{sub.amount:,}/{sub.frequency.value}\n"
                    f"次回: {sub.next_payment_date} ({next_payment_text})\n"
                    f"月額換算: ¥{monthly_cost:,.0f}"
                )

                embed.add_field(
                    name=f"{status_emoji} {sub.name}",
                    value=field_value,
                    inline=True,
                )

                # Add empty field for formatting every 2 items
                if i % 2 == 0:
                    embed.add_field(name="\u200b", value="\u200b", inline=True)

            embed.add_field(
                name="📊 合計",
                value=f"月額換算: ¥{total_monthly_cost:,.0f}\n年額換算: ¥{total_monthly_cost * 12:,.0f}",
                inline=False,
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("Failed to list subscriptions", error=str(e))
            await interaction.followup.send(
                "❌ 定期購入サービス一覧の取得に失敗しました。",
                ephemeral=True,
            )

    @app_commands.command(name="sub_stats", description="定期購入統計情報を表示")
    async def sub_stats_command(self, interaction: discord.Interaction) -> None:
        """Show subscription statistics."""
        try:
            await interaction.response.defer()

            # Generate subscription report
            report = await self.report_generator.generate_subscription_report()

            # Split report into chunks if too long
            if len(report) > 2000:
                # Send as file
                import io

                file_content = report.encode("utf-8")
                file = discord.File(
                    io.BytesIO(file_content), filename="subscription_report.md"
                )

                await interaction.followup.send(
                    "📊 定期購入統計レポート",
                    file=file,
                )
            else:
                embed = discord.Embed(
                    title="📊 定期購入統計情報",
                    description=report,
                    color=discord.Color.blue(),
                    timestamp=datetime.now(),
                )
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("Failed to generate subscription stats", error=str(e))
            await interaction.followup.send(
                "❌ 統計情報の生成に失敗しました。",
                ephemeral=True,
            )

    @app_commands.command(name="sub_pause", description="定期購入サービスを一時停止")
    @app_commands.describe(service_name="サービス名（部分一致）")
    async def sub_pause_command(
        self,
        interaction: discord.Interaction,
        service_name: str,
    ) -> None:
        """Pause a subscription service."""
        await self._update_subscription_status(
            interaction, service_name, "pause", "一時停止"
        )

    @app_commands.command(name="sub_resume", description="定期購入サービスを再開")
    @app_commands.describe(service_name="サービス名（部分一致）")
    async def sub_resume_command(
        self,
        interaction: discord.Interaction,
        service_name: str,
    ) -> None:
        """Resume a paused subscription service."""
        await self._update_subscription_status(
            interaction, service_name, "resume", "再開"
        )

    @app_commands.command(name="sub_cancel", description="定期購入サービスをキャンセル")
    @app_commands.describe(service_name="サービス名（部分一致）")
    async def sub_cancel_command(
        self,
        interaction: discord.Interaction,
        service_name: str,
    ) -> None:
        """Cancel a subscription service."""
        await self._update_subscription_status(
            interaction, service_name, "cancel", "キャンセル"
        )

    async def _update_subscription_status(
        self,
        interaction: discord.Interaction,
        service_name: str,
        action: str,
        action_jp: str,
    ) -> None:
        """Helper method to update subscription status."""
        try:
            await interaction.response.defer()

            # Find matching subscription
            subscriptions = await self.subscription_manager.list_subscriptions()
            matches = [
                sub for sub in subscriptions if service_name.lower() in sub.name.lower()
            ]

            if not matches:
                await interaction.followup.send(
                    f"❌ '{service_name}' に一致する定期購入サービスが見つかりません。",
                    ephemeral=True,
                )
                return

            if len(matches) > 1:
                match_names = "\n".join([f"- {sub.name}" for sub in matches])
                await interaction.followup.send(
                    f"❌ 複数のサービスが見つかりました。より具体的な名前を指定してください：\n{match_names}",
                    ephemeral=True,
                )
                return

            subscription = matches[0]

            # Update status
            if action == "pause":
                updated_sub = await self.subscription_manager.pause_subscription(
                    subscription.id
                )
            elif action == "resume":
                updated_sub = await self.subscription_manager.resume_subscription(
                    subscription.id
                )
            elif action == "cancel":
                updated_sub = await self.subscription_manager.cancel_subscription(
                    subscription.id
                )
            else:
                raise ValueError(f"Unknown action: {action}")

            if not updated_sub:
                await interaction.followup.send(
                    f"❌ サービスの{action_jp}に失敗しました。",
                    ephemeral=True,
                )
                return

            # Create response
            embed = discord.Embed(
                title=f"✅ サービスを{action_jp}しました",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="サービス名", value=updated_sub.name, inline=True)
            embed.add_field(
                name="ステータス", value=updated_sub.status.value, inline=True
            )

            await interaction.followup.send(embed=embed)

            logger.info(
                f"Subscription {action}ed via command",
                user_id=interaction.user.id,
                subscription_id=subscription.id,
                action=action,
            )

        except Exception as e:
            logger.error(f"Failed to {action} subscription", error=str(e))
            await interaction.followup.send(
                f"❌ サービスの{action_jp}に失敗しました。",
                ephemeral=True,
            )

    @app_commands.command(name="budget_set", description="カテゴリ別予算を設定")
    @app_commands.describe(
        category="予算カテゴリ",
        amount="予算金額",
        period="期間 (monthly/yearly)",
    )
    async def budget_set_command(
        self,
        interaction: discord.Interaction,
        category: str,
        amount: str,
        period: str = "monthly",
    ) -> None:
        """Set budget for a category."""
        try:
            # Parse amount
            try:
                amount_decimal = Decimal(amount.replace(",", ""))
                if amount_decimal <= 0:
                    raise ValueError("金額は0より大きい必要があります")
            except (InvalidOperation, ValueError):
                await interaction.response.send_message(
                    "❌ 無効な金額です。数値を入力してください。",
                    ephemeral=True,
                )
                return

            # Parse category
            budget_category: BudgetCategory | None = None
            try:
                budget_category = BudgetCategory(category.lower())
            except ValueError:
                # Try Japanese category names
                category_mapping = {
                    "定期購入": BudgetCategory.SUBSCRIPTIONS,
                    "食費": BudgetCategory.FOOD,
                    "交通費": BudgetCategory.TRANSPORTATION,
                    "娯楽": BudgetCategory.ENTERTAINMENT,
                    "光熱費": BudgetCategory.UTILITIES,
                    "医療": BudgetCategory.HEALTHCARE,
                    "教育": BudgetCategory.EDUCATION,
                    "買い物": BudgetCategory.SHOPPING,
                    "その他": BudgetCategory.OTHER,
                }

                budget_category = category_mapping.get(category)
                if budget_category is None:
                    await interaction.response.send_message(
                        "❌ 無効なカテゴリです。以下から選択してください：\n"
                        + "\n".join([f"- {k}" for k in category_mapping]),
                        ephemeral=True,
                    )
                    return
                    return

            # Calculate period dates
            today = date.today()
            if period.lower() == "monthly":
                from calendar import monthrange

                period_start = date(today.year, today.month, 1)
                period_end = date(
                    today.year, today.month, monthrange(today.year, today.month)[1]
                )
            elif period.lower() == "yearly":
                period_start = date(today.year, 1, 1)
                period_end = date(today.year, 12, 31)
            else:
                await interaction.response.send_message(
                    "❌ 無効な期間です。monthly または yearly を指定してください。",
                    ephemeral=True,
                )
                return

            await interaction.response.defer()

            # Set budget
            budget = await self.budget_manager.set_budget(
                category=budget_category,
                amount=amount_decimal,
                period_start=period_start,
                period_end=period_end,
            )

            # Create embed response
            embed = discord.Embed(
                title="✅ 予算を設定しました",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="カテゴリ", value=budget_category.value, inline=True)
            embed.add_field(name="予算金額", value=f"¥{budget.amount:,}", inline=True)
            embed.add_field(
                name="期間", value=f"{period_start} ～ {period_end}", inline=True
            )
            embed.add_field(
                name="使用済み", value=f"¥{budget.spent_amount:,}", inline=True
            )
            embed.add_field(
                name="残り", value=f"¥{budget.remaining_amount:,}", inline=True
            )
            embed.add_field(
                name="使用率", value=f"{budget.percentage_used:.1f}%", inline=True
            )

            await interaction.followup.send(embed=embed)

            logger.info(
                "Budget set via command",
                user_id=interaction.user.id,
                category=budget_category.value,
                amount=float(amount_decimal),
                period=period,
            )

        except Exception as e:
            logger.error("Failed to set budget", error=str(e))
            await interaction.followup.send(
                "❌ 予算の設定に失敗しました。",
                ephemeral=True,
            )

    @app_commands.command(name="finance_stats", description="家計統計情報を表示")
    @app_commands.describe(
        period="期間 (month/year)",
        year="年",
        month="月（期間がmonthの場合）",
    )
    async def finance_stats_command(
        self,
        interaction: discord.Interaction,
        period: str = "month",
        year: int | None = None,
        month: int | None = None,
    ) -> None:
        """Show finance statistics."""
        try:
            await interaction.response.defer()

            # Parse period
            today = date.today()
            current_year = year or today.year

            if period.lower() == "month":
                current_month = month or today.month

                if current_month < 1 or current_month > 12:
                    await interaction.followup.send(
                        "❌ 無効な月です。1-12の範囲で指定してください。",
                        ephemeral=True,
                    )
                    return

                # Generate monthly report
                report = await self.report_generator.generate_monthly_report(
                    current_year, current_month, include_ai_insights=False
                )

                # Get budget summary
                await self.budget_manager.get_monthly_budget_summary(
                    current_year, current_month
                )

                title = f"📊 {current_year}年{current_month}月 家計統計"

            elif period.lower() == "year":
                period_start = date(current_year, 1, 1)
                period_end = date(current_year, 12, 31)

                # Get yearly data
                total_income = await self.expense_manager.get_total_income(
                    period_start, period_end
                )
                total_expenses = await self.expense_manager.get_total_expenses(
                    period_start, period_end
                )
                expense_by_category = (
                    await self.expense_manager.get_total_expenses_by_category(
                        period_start, period_end
                    )
                )

                # Get subscriptions data
                subscriptions = await self.subscription_manager.list_subscriptions(
                    active_only=True
                )
                total_subscription_cost = sum(
                    sub.amount * (12 if sub.frequency.value == "monthly" else 1)
                    for sub in subscriptions
                )

                net_balance = total_income - total_expenses - total_subscription_cost

                report = f"""# {current_year}年 年間家計統計

## 収支概要
- **総収入**: ¥{total_income:,}
- **総支出**: ¥{total_expenses:,}
- **定期購入**: ¥{total_subscription_cost:,}
- **純収支**: ¥{net_balance:,}

## カテゴリ別支出
"""
                for category, amount in expense_by_category.items():
                    report += f"- **{category.value}**: ¥{amount:,}\n"

                title = f"📊 {current_year}年 年間家計統計"

            else:
                await interaction.followup.send(
                    "❌ 無効な期間です。month または year を指定してください。",
                    ephemeral=True,
                )
                return

            # Split report if too long
            if len(report) > 2000:
                # Send as file
                import io

                file_content = report.encode("utf-8")
                file = discord.File(
                    io.BytesIO(file_content),
                    filename=f"finance_stats_{period}_{current_year}.md",
                )

                await interaction.followup.send(
                    title,
                    file=file,
                )
            else:
                embed = discord.Embed(
                    title=title,
                    description=report,
                    color=discord.Color.blue(),
                    timestamp=datetime.now(),
                )
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("Failed to generate finance stats", error=str(e))
            await interaction.followup.send(
                "❌ 統計情報の生成に失敗しました。",
                ephemeral=True,
            )


def setup_finance_commands(
    bot: discord.Client | discord_commands.Bot,
    channel_config: ChannelConfig,
    file_manager: ObsidianFileManager,
    subscription_manager: SubscriptionManager,
    expense_manager: ExpenseManager,
    budget_manager: BudgetManager,
    report_generator: FinanceReportGenerator,
) -> FinanceCommands:
    """Setup finance commands and return the commands instance."""
    commands = FinanceCommands(
        bot,
        channel_config,
        file_manager,
        subscription_manager,
        expense_manager,
        budget_manager,
        report_generator,
    )

    # Register commands
    if hasattr(bot, "tree"):
        bot.tree.add_command(commands.sub_add_command)
        bot.tree.add_command(commands.sub_paid_command)
        bot.tree.add_command(commands.sub_list_command)
        bot.tree.add_command(commands.sub_stats_command)
        bot.tree.add_command(commands.sub_pause_command)
        bot.tree.add_command(commands.sub_resume_command)
        bot.tree.add_command(commands.sub_cancel_command)
        bot.tree.add_command(commands.budget_set_command)
        bot.tree.add_command(commands.finance_stats_command)

    return commands
