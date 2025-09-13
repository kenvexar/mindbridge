"""Budget management functionality."""

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import aiofiles
from structlog import get_logger

from src.config import get_settings
from src.finance.expense_manager import ExpenseManager
from src.finance.models import Budget, BudgetCategory
from src.obsidian import ObsidianFileManager

logger = get_logger(__name__)
settings = get_settings()


class BudgetManager:
    """Manage budget tracking and alerts."""

    def __init__(
        self, file_manager: ObsidianFileManager, expense_manager: ExpenseManager
    ):
        self.file_manager = file_manager
        self.expense_manager = expense_manager
        self.budgets_file = settings.obsidian_vault_path / "20_Finance" / "budgets.json"

        # Ensure finance directory exists
        self.budgets_file.parent.mkdir(parents=True, exist_ok=True)

    async def set_budget(
        self,
        category: BudgetCategory,
        amount: Decimal,
        period_start: date,
        period_end: date,
        currency: str = "JPY",
    ) -> Budget:
        """Set budget for a category and period."""
        # Calculate current spent amount
        spent_amount = await self._calculate_spent_amount(
            category, period_start, period_end
        )

        budget = Budget(
            id=str(uuid.uuid4()),
            category=category,
            amount=amount,
            currency=currency,
            period_start=period_start,
            period_end=period_end,
            spent_amount=spent_amount,
        )

        budgets = await self._load_budgets()

        # Remove existing budget for same category and period
        existing_key = None
        for budget_id, existing_budget in budgets.items():
            if (
                isinstance(existing_budget, dict)
                and existing_budget.get("category") == category.value
                and existing_budget.get("period_start") == period_start.isoformat()
                and existing_budget.get("period_end") == period_end.isoformat()
            ) or (
                hasattr(existing_budget, "category")
                and existing_budget.category == category
                and existing_budget.period_start == period_start
                and existing_budget.period_end == period_end
            ):
                existing_key = budget_id
                break

        if existing_key:
            del budgets[existing_key]

        budgets[budget.id] = budget
        await self._save_budgets(budgets)

        logger.info(
            "Budget set",
            budget_id=budget.id,
            category=category.value,
            amount=float(amount),
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
        )

        return budget

    async def get_budget(
        self,
        category: BudgetCategory,
        period_start: date,
        period_end: date,
    ) -> Budget | None:
        """Get budget for a category and period."""
        budgets = await self._load_budgets()

        for budget_data in budgets.values():
            budget = (
                Budget(**budget_data) if isinstance(budget_data, dict) else budget_data
            )

            if (
                budget.category == category
                and budget.period_start == period_start
                and budget.period_end == period_end
            ):
                # Update spent amount
                budget.spent_amount = await self._calculate_spent_amount(
                    category, period_start, period_end
                )
                return budget

        return None

    async def get_all_budgets(
        self,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> list[Budget]:
        """Get all budgets with enhanced type safety and validation."""
        if period_start and period_end and period_start > period_end:
            raise ValueError("Period start date must be before or equal to end date")

        budgets = await self._load_budgets()

        result: list[Budget] = []
        for budget_data in budgets.values():
            budget = (
                Budget(**budget_data) if isinstance(budget_data, dict) else budget_data
            )

            # Enhanced period filtering with proper type checking
            if period_start and budget.period_end < period_start:
                continue
            if period_end and budget.period_start > period_end:
                continue

            # Update spent amount with error handling
            try:
                budget.spent_amount = await self._calculate_spent_amount(
                    budget.category, budget.period_start, budget.period_end
                )
            except Exception as e:
                logger.warning(
                    f"Failed to calculate spent amount for budget {budget.category.value}",
                    error=str(e),
                )
                budget.spent_amount = Decimal(0)

            result.append(budget)

        return sorted(result, key=lambda x: (x.period_start, x.category.value))

    async def update_budget_spending(
        self,
        category: BudgetCategory,
        period_start: date,
        period_end: date,
    ) -> Budget | None:
        """Update budget spending amount."""
        budget = await self.get_budget(category, period_start, period_end)
        if not budget:
            return None

        budget.spent_amount = await self._calculate_spent_amount(
            category, period_start, period_end
        )
        budget.updated_at = datetime.now()

        budgets = await self._load_budgets()
        budgets[budget.id] = budget
        await self._save_budgets(budgets)

        return budget

    async def check_budget_alerts(
        self,
        threshold: float = 80.0,
    ) -> list[Budget]:
        """Check for budgets that are near or over limit."""
        today = date.today()
        budgets = await self.get_all_budgets()

        alerts = []
        for budget in budgets:
            # Only check active budgets
            if budget.period_start <= today <= budget.period_end and (
                budget.is_near_limit(threshold) or budget.is_over_budget()
            ):
                alerts.append(budget)

        return alerts

    async def get_monthly_budget_summary(
        self,
        year: int,
        month: int,
    ) -> dict[str, Any]:
        """Get budget summary for a specific month."""
        from calendar import monthrange

        period_start = date(year, month, 1)
        period_end = date(year, month, monthrange(year, month)[1])

        budgets = await self.get_all_budgets(period_start, period_end)

        total_budget = Decimal(0)
        total_spent = Decimal(0)
        over_budget_categories = []
        near_limit_categories = []

        category_details = {}

        for budget in budgets:
            if budget.period_start <= period_end and budget.period_end >= period_start:
                total_budget += budget.amount
                total_spent += budget.spent_amount

                category_details[budget.category.value] = {
                    "budgeted": budget.amount,
                    "spent": budget.spent_amount,
                    "remaining": budget.remaining_amount,
                    "percentage": budget.percentage_used,
                }

                if budget.is_over_budget():
                    over_budget_categories.append(budget.category.value)
                elif budget.is_near_limit():
                    near_limit_categories.append(budget.category.value)

        return {
            "period_start": period_start,
            "period_end": period_end,
            "total_budget": total_budget,
            "total_spent": total_spent,
            "remaining_budget": total_budget - total_spent,
            "overall_percentage": (
                float(total_spent / total_budget * 100) if total_budget > 0 else 0
            ),
            "category_details": category_details,
            "over_budget_categories": over_budget_categories,
            "near_limit_categories": near_limit_categories,
        }

    async def _calculate_spent_amount(
        self,
        category: BudgetCategory,
        period_start: date,
        period_end: date,
    ) -> Decimal:
        """Calculate spent amount for a category in a period."""
        expenses = await self.expense_manager.get_expenses_by_period(
            period_start, period_end, category
        )
        total = sum(expense.amount for expense in expenses)
        return total or Decimal(0)

    async def _load_budgets(self) -> dict[str, Budget]:
        """Load budgets from JSON file."""
        if not self.budgets_file.exists():
            return {}

        try:
            async with aiofiles.open(self.budgets_file, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

                budgets = {}
                for budget_id, budget_data in data.items():
                    if isinstance(budget_data, dict):
                        budgets[budget_id] = Budget(**budget_data)
                    else:
                        budgets[budget_id] = budget_data

                return budgets
        except Exception as e:
            logger.error("Failed to load budgets", error=str(e))
            return {}

    async def _save_budgets(self, budgets: dict[str, Budget]) -> None:
        """Save budgets to JSON file."""
        try:
            data = {}
            for budget_id, budget in budgets.items():
                if isinstance(budget, Budget):
                    data[budget_id] = budget.dict()
                else:
                    data[budget_id] = budget

            async with aiofiles.open(self.budgets_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(data, indent=2, default=str, ensure_ascii=False)
                )
        except Exception as e:
            logger.error("Failed to save budgets", error=str(e))
