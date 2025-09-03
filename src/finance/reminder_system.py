"""Finance reminder system for subscription and budget alerts."""

import asyncio
import contextlib
from datetime import date, datetime
from typing import Any

import discord
from structlog import get_logger

from src.bot.channel_config import ChannelConfig
from src.finance.budget_manager import BudgetManager
from src.finance.models import Budget, Subscription
from src.finance.subscription_manager import SubscriptionManager

logger = get_logger(__name__)


class FinanceReminderSystem:
    """Finance reminder system for automated notifications."""

    def __init__(
        self,
        bot: discord.Client,
        channel_config: ChannelConfig,
        subscription_manager: SubscriptionManager,
        budget_manager: BudgetManager,
    ):
        self.bot = bot
        self.channel_config = channel_config
        self.subscription_manager = subscription_manager
        self.budget_manager = budget_manager
        self._reminder_task: asyncio.Task[Any] | None = None
        self._is_running = False

    async def start(self) -> None:
        """Start the reminder system."""
        if self._is_running:
            return

        self._is_running = True
        self._reminder_task = asyncio.create_task(self._run_reminder_loop())

        logger.info("Finance reminder system started")

    async def stop(self) -> None:
        """Stop the reminder system."""
        self._is_running = False

        if self._reminder_task:
            self._reminder_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._reminder_task

        logger.info("Finance reminder system stopped")

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
                logger.error("Error in reminder loop", error=str(e))
                await asyncio.sleep(60)

    async def _run_daily_checks(self) -> None:
        """Run all daily finance checks."""
        try:
            logger.info("Running daily finance checks")

            # Check for upcoming subscription payments
            await self._check_upcoming_payments()

            # Check for overdue payments
            await self._check_overdue_payments()

            # Check budget alerts
            await self._check_budget_alerts()

        except Exception as e:
            logger.error("Error in daily finance checks", error=str(e))

    async def _check_upcoming_payments(self) -> None:
        """Check for upcoming subscription payments."""
        try:
            due_subscriptions = await self.subscription_manager.get_due_subscriptions(3)

            if not due_subscriptions:
                return

            # Group by days until due
            today_payments = []
            tomorrow_payments = []
            soon_payments = []

            today = date.today()

            for sub in due_subscriptions:
                days_until = (sub.next_payment_date - today).days
                if days_until == 0:
                    today_payments.append(sub)
                elif days_until == 1:
                    tomorrow_payments.append(sub)
                else:
                    soon_payments.append(sub)

            # Send notifications
            await self._send_payment_reminders(today_payments, "今日", "🔔")
            await self._send_payment_reminders(tomorrow_payments, "明日", "📅")
            await self._send_payment_reminders(soon_payments, "3 日以内", "⏰")

        except Exception as e:
            logger.error("Error checking upcoming payments", error=str(e))

    async def _check_overdue_payments(self) -> None:
        """Check for overdue subscription payments."""
        try:
            overdue_subscriptions = (
                await self.subscription_manager.get_overdue_subscriptions()
            )

            if not overdue_subscriptions:
                return

            await self._send_overdue_reminders(overdue_subscriptions)

        except Exception as e:
            logger.error("Error checking overdue payments", error=str(e))

    async def _check_budget_alerts(self) -> None:
        """Check for budget alerts."""
        try:
            # Check for budgets near limit (80%)
            near_limit_budgets = await self.budget_manager.check_budget_alerts(80.0)

            # Check for budgets over limit
            over_limit_budgets = await self.budget_manager.check_budget_alerts(100.0)

            if near_limit_budgets or over_limit_budgets:
                await self._send_budget_alerts(near_limit_budgets, over_limit_budgets)

        except Exception as e:
            logger.error("Error checking budget alerts", error=str(e))

    async def _send_payment_reminders(
        self,
        subscriptions: list[Subscription],
        time_description: str,
        emoji: str,
    ) -> None:
        """Send payment reminder notifications."""
        if not subscriptions:
            return

        try:
            money_channel_id = self.channel_config.get_memo_channel()
            if not money_channel_id:
                logger.warning("Finance money channel not configured")
                return

            money_channel = self.bot.get_channel(money_channel_id)
            if not money_channel or not hasattr(money_channel, "send"):
                logger.warning(
                    f"Finance money channel not found or not a text channel: {money_channel_id}"
                )
                return

            embed = discord.Embed(
                title=f"{emoji} 定期購入支払いリマインダー ({time_description})",
                color=discord.Color.orange(),
                timestamp=datetime.now(),
            )

            total_amount = sum(sub.amount for sub in subscriptions)
            embed.add_field(
                name="合計金額",
                value=f"¥{total_amount:,}",
                inline=False,
            )

            for sub in subscriptions:
                days_info = ""
                if time_description == "3 日以内":
                    days_until = (sub.next_payment_date - date.today()).days
                    days_info = f" ({days_until}日後)"

                embed.add_field(
                    name=f"{sub.name}{days_info}",
                    value=f"¥{sub.amount:,}\n 支払い日: {sub.next_payment_date}",
                    inline=True,
                )

            embed.add_field(
                name="📝 支払い完了報告",
                value="支払いが完了したら `/sub_paid` コマンドで報告してください。",
                inline=False,
            )

            await money_channel.send(embed=embed)

            logger.info(
                "Payment reminders sent",
                count=len(subscriptions),
                time_description=time_description,
            )

        except Exception as e:
            logger.error("Error sending payment reminders", error=str(e))

    async def _send_overdue_reminders(
        self, overdue_subscriptions: list[Subscription]
    ) -> None:
        """Send overdue payment notifications."""
        try:
            money_channel_id = self.channel_config.get_memo_channel()
            if not money_channel_id:
                logger.warning("Finance money channel not configured")
                return

            money_channel = self.bot.get_channel(money_channel_id)
            if not money_channel or not hasattr(money_channel, "send"):
                logger.warning(
                    f"Finance money channel not found or not a text channel: {money_channel_id}"
                )
                return

            embed = discord.Embed(
                title="⚠️ 支払い遅延通知",
                description="以下の定期購入サービスの支払いが遅延しています。",
                color=discord.Color.red(),
                timestamp=datetime.now(),
            )

            total_overdue = sum(sub.amount for sub in overdue_subscriptions)
            embed.add_field(
                name="遅延金額合計",
                value=f"¥{total_overdue:,}",
                inline=False,
            )

            for sub in overdue_subscriptions:
                days_overdue = (date.today() - sub.next_payment_date).days
                embed.add_field(
                    name=f"🔴 {sub.name}",
                    value=f"¥{sub.amount:,}\n 予定日: {sub.next_payment_date}\n 遅延: {days_overdue}日",
                    inline=True,
                )

            embed.add_field(
                name="🚨 対応が必要",
                value="早急に支払いを行い、`/sub_paid` コマンドで報告してください。",
                inline=False,
            )

            await money_channel.send(embed=embed)

            logger.info(
                "Overdue reminders sent",
                count=len(overdue_subscriptions),
            )

        except Exception as e:
            logger.error("Error sending overdue reminders", error=str(e))

    async def _send_budget_alerts(
        self,
        near_limit_budgets: list[Budget],
        over_limit_budgets: list[Budget],
    ) -> None:
        """Send budget alert notifications."""
        try:
            money_channel_id = self.channel_config.get_memo_channel()
            if not money_channel_id:
                logger.warning("Finance money channel not configured")
                return

            money_channel = self.bot.get_channel(money_channel_id)
            if not money_channel or not hasattr(money_channel, "send"):
                logger.warning(
                    f"Finance money channel not found or not a text channel: {money_channel_id}"
                )
                return

            embed = discord.Embed(
                title="💰 予算アラート",
                color=discord.Color.yellow(),
                timestamp=datetime.now(),
            )

            if over_limit_budgets:
                over_limit_text = ""
                for budget in over_limit_budgets:
                    over_limit_text += f"- **{budget.category.value}**: ¥{budget.spent_amount:,} / ¥{budget.amount:,} ({budget.percentage_used:.1f}%)\n"

                embed.add_field(
                    name="🔴 予算超過",
                    value=over_limit_text,
                    inline=False,
                )

            if near_limit_budgets:
                near_limit_text = ""
                for budget in near_limit_budgets:
                    if budget not in over_limit_budgets:  # Avoid duplicates
                        near_limit_text += f"- **{budget.category.value}**: ¥{budget.spent_amount:,} / ¥{budget.amount:,} ({budget.percentage_used:.1f}%)\n"

                if near_limit_text:
                    embed.add_field(
                        name="🟠 予算 80% 到達",
                        value=near_limit_text,
                        inline=False,
                    )

            if over_limit_budgets or near_limit_budgets:
                embed.add_field(
                    name="💡 推奨アクション",
                    value="支出を見直すか、予算を調整することを検討してください。",
                    inline=False,
                )

                await money_channel.send(embed=embed)

                logger.info(
                    "Budget alerts sent",
                    over_limit_count=len(over_limit_budgets),
                    near_limit_count=len(near_limit_budgets),
                )

        except Exception as e:
            logger.error("Error sending budget alerts", error=str(e))

    async def send_manual_reminder_check(self) -> None:
        """Manually trigger reminder checks (for testing)."""
        try:
            await self._run_daily_checks()
            logger.info("Manual reminder check completed")
        except Exception as e:
            logger.error("Error in manual reminder check", error=str(e))
