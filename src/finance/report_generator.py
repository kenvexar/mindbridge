"""Finance report generation functionality."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from structlog import get_logger

from src.ai import GeminiClient
from src.finance.budget_manager import BudgetManager
from src.finance.expense_manager import ExpenseManager
from src.finance.models import FinanceSummary
from src.finance.subscription_manager import SubscriptionManager
from src.obsidian import ObsidianFileManager

logger = get_logger(__name__)


class FinanceReportGenerator:
    """Generate finance reports and insights."""

    def __init__(
        self,
        file_manager: ObsidianFileManager,
        subscription_manager: SubscriptionManager,
        expense_manager: ExpenseManager,
        budget_manager: BudgetManager,
        gemini_client: GeminiClient,
    ):
        self.file_manager = file_manager
        self.subscription_manager = subscription_manager
        self.expense_manager = expense_manager
        self.budget_manager = budget_manager
        self.gemini_client = gemini_client

    async def generate_monthly_report(
        self,
        year: int,
        month: int,
        include_ai_insights: bool = True,
    ) -> str:
        """Generate comprehensive monthly finance report."""
        from calendar import monthrange

        period_start = date(year, month, 1)
        period_end = date(year, month, monthrange(year, month)[1])

        # Gather data
        summary = await self._generate_finance_summary(period_start, period_end)
        budget_summary = await self.budget_manager.get_monthly_budget_summary(
            year, month
        )

        # Generate base report
        report = await self._create_monthly_report_content(
            year, month, summary, budget_summary
        )

        # Add AI insights if requested
        if include_ai_insights:
            try:
                insights = await self._generate_ai_insights(summary, budget_summary)
                report += f"\n\n## AI分析・提案\n\n{insights}"
            except Exception as e:
                logger.error("Failed to generate AI insights", error=str(e))
                report += "\n\n## AI分析・提案\n\nAI分析の生成に失敗しました。"

        # Save report to Obsidian
        await self._save_monthly_report(year, month, report)

        return report

    async def generate_subscription_report(self) -> str:
        """Generate subscription analysis report."""
        active_subscriptions = await self.subscription_manager.list_subscriptions(
            active_only=True
        )
        due_subscriptions = await self.subscription_manager.get_due_subscriptions(7)
        overdue_subscriptions = (
            await self.subscription_manager.get_overdue_subscriptions()
        )

        total_monthly_cost = Decimal(0)
        total_yearly_cost = Decimal(0)

        for sub in active_subscriptions:
            if sub.frequency.value == "monthly":
                total_monthly_cost += sub.amount
                total_yearly_cost += sub.amount * 12
            elif sub.frequency.value == "yearly":
                total_yearly_cost += sub.amount
                total_monthly_cost += sub.amount / 12
            elif sub.frequency.value == "weekly":
                weekly_cost = sub.amount * 52
                total_yearly_cost += weekly_cost
                total_monthly_cost += weekly_cost / 12
            elif sub.frequency.value == "quarterly":
                quarterly_cost = sub.amount * 4
                total_yearly_cost += quarterly_cost
                total_monthly_cost += quarterly_cost / 12

        report = f"""# 定期購入サービス分析レポート

生成日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M")}

## 概要
- **アクティブなサービス数**: {len(active_subscriptions)}個
- **月額総費用**: ¥{total_monthly_cost:,.0f}
- **年額総費用**: ¥{total_yearly_cost:,.0f}

## 支払い予定
### 7日以内に支払い予定 ({len(due_subscriptions)}件)
"""

        for sub in due_subscriptions:
            days_until = (sub.next_payment_date - date.today()).days
            report += f"- **{sub.name}**: ¥{sub.amount:,} ({days_until}日後: {sub.next_payment_date})\n"

        if overdue_subscriptions:
            report += f"\n### 支払い遅延 ({len(overdue_subscriptions)}件)\n"
            for sub in overdue_subscriptions:
                days_overdue = (date.today() - sub.next_payment_date).days
                report += f"- **{sub.name}**: ¥{sub.amount:,} ({days_overdue}日遅延)\n"

        # Group by category
        category_breakdown: dict[str, list[Any]] = {}
        for sub in active_subscriptions:
            category = sub.category or "その他"
            if category not in category_breakdown:
                category_breakdown[category] = []
            category_breakdown[category].append(sub)

        report += "\n## カテゴリ別内訳\n"
        for category, subs in category_breakdown.items():
            category_total = sum(
                sub.amount
                * (
                    12
                    if sub.frequency.value == "monthly"
                    else (
                        1
                        if sub.frequency.value == "yearly"
                        else (
                            52
                            if sub.frequency.value == "weekly"
                            else 4
                            if sub.frequency.value == "quarterly"
                            else 12
                        )
                    )
                )
                for sub in subs
            )
            report += f"\n### {category} (年額: ¥{category_total:,.0f})\n"
            for sub in subs:
                report += f"- {sub.name}: ¥{sub.amount:,}/{sub.frequency.value}\n"

        return report

    async def _generate_finance_summary(
        self,
        period_start: date,
        period_end: date,
    ) -> FinanceSummary:
        """Generate finance summary for period."""
        # Subscription data
        active_subscriptions = await self.subscription_manager.list_subscriptions(
            active_only=True
        )
        upcoming_payments = await self.subscription_manager.get_due_subscriptions(7)
        overdue_payments = await self.subscription_manager.get_overdue_subscriptions()

        # Calculate subscription costs for the period
        subscription_cost = Decimal(0)
        for sub in active_subscriptions:
            # Calculate how much this subscription costs in the given period
            if sub.frequency.value == "monthly":
                months_in_period = (
                    (period_end.year - period_start.year) * 12
                    + period_end.month
                    - period_start.month
                    + 1
                )
                subscription_cost += sub.amount * min(months_in_period, 1)
            elif sub.frequency.value == "yearly":
                if period_start.year == period_end.year:
                    subscription_cost += (
                        sub.amount / 12 * ((period_end.month - period_start.month) + 1)
                    )
            # Add other frequencies as needed

        # Expense and income data
        total_expenses = await self.expense_manager.get_total_expenses(
            period_start, period_end
        )
        total_income = await self.expense_manager.get_total_income(
            period_start, period_end
        )

        # Budget usage
        budgets = await self.budget_manager.get_all_budgets(period_start, period_end)
        budget_usage = {}
        for budget in budgets:
            budget_usage[budget.category.value] = budget.percentage_used

        return FinanceSummary(
            total_subscriptions=len(active_subscriptions),
            total_subscription_cost=subscription_cost,
            total_expenses=total_expenses,
            total_income=total_income,
            net_balance=total_income - total_expenses - subscription_cost,
            budget_usage=budget_usage,
            upcoming_payments=upcoming_payments,
            overdue_payments=overdue_payments,
            period_start=period_start,
            period_end=period_end,
        )

    async def _create_monthly_report_content(
        self,
        year: int,
        month: int,
        summary: FinanceSummary,
        budget_summary: dict[str, Any],
    ) -> str:
        """Create monthly report content."""
        report = f"""# {year}年{month}月 家計レポート

生成日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M")}

## 収支概要
- **総収入**: ¥{summary.total_income:,}
- **総支出**: ¥{summary.total_expenses:,}
- **定期購入**: ¥{summary.total_subscription_cost:,}
- **純収支**: ¥{summary.net_balance:,}

## 定期購入サービス
- **アクティブサービス数**: {summary.total_subscriptions}個
- **月額費用**: ¥{summary.total_subscription_cost:,}

### 今後の支払い予定
"""

        if summary.upcoming_payments:
            for payment in summary.upcoming_payments:
                days_until = (payment.next_payment_date - date.today()).days
                report += (
                    f"- **{payment.name}**: ¥{payment.amount:,} ({days_until}日後)\n"
                )
        else:
            report += "なし\n"

        if summary.overdue_payments:
            report += "\n### 支払い遅延⚠️\n"
            for payment in summary.overdue_payments:
                days_overdue = (date.today() - payment.next_payment_date).days
                report += f"- **{payment.name}**: ¥{payment.amount:,} ({days_overdue}日遅延)\n"

        # Budget section
        report += "\n## 予算管理\n"
        if budget_summary["category_details"]:
            for category, details in budget_summary["category_details"].items():
                percentage = details["percentage"]
                status = "🔴" if percentage > 100 else "🟠" if percentage > 80 else "🟢"
                report += f"- **{category}** {status}: ¥{details['spent']:,} / ¥{details['budgeted']:,} ({percentage:.1f}%)\n"
        else:
            report += "予算が設定されていません。\n"

        if budget_summary["over_budget_categories"]:
            report += "\n### 予算超過カテゴリ ⚠️\n"
            for category in budget_summary["over_budget_categories"]:
                report += f"- {category}\n"

        return report

    async def _generate_ai_insights(
        self,
        summary: FinanceSummary,
        budget_summary: dict[str, Any],
    ) -> str:
        """Generate AI insights for the financial data."""
        prompt = f"""
以下の家計データを分析し、日本語で洞察と改善提案を提供してください：

収支データ:
- 総収入: ¥{summary.total_income:,}
- 総支出: ¥{summary.total_expenses:,}
- 定期購入: ¥{summary.total_subscription_cost:,}
- 純収支: ¥{summary.net_balance:,}

予算データ:
{budget_summary}

以下の観点で分析してください：
1. 収支バランスの評価
2. 支出パターンの分析
3. 予算管理の状況
4. 具体的な改善提案（3-5個）
5. 注意すべきポイント

簡潔で実用的なアドバイスを提供してください。
"""

        try:
            summary_result = await self.gemini_client.generate_summary(prompt)
            return summary_result.summary
        except Exception as e:
            logger.error("Failed to generate AI insights", error=str(e))
            return "AI分析の生成に失敗しました。"

    async def _save_monthly_report(self, year: int, month: int, content: str) -> None:
        """Save monthly report to Obsidian."""
        try:
            from pathlib import Path

            filename = f"{year}年{month:02d}月_家計レポート.md"
            file_path = Path("20_Finance") / "Reports" / str(year) / filename

            # Add metadata
            full_content = f"""---
type: finance_report
year: {year}
month: {month}
generated: {datetime.now().isoformat()}
tags: [finance, report, monthly]
---

{content}

## 関連リンク
- [[定期購入サービス分析]]
- [[予算管理]]
- [[月次支出分析]]
"""

            # Create ObsidianNote and save it
            from src.obsidian.models import NoteFrontmatter, ObsidianNote

            note = ObsidianNote(
                filename=file_path.name,
                file_path=file_path,
                frontmatter=NoteFrontmatter(obsidian_folder="20_Finance"),
                content=full_content,
            )
            await self.file_manager.save_note(note)

            logger.info(
                "Monthly finance report saved",
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
