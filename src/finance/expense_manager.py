"""Expense and income management functionality."""

import json
import uuid
from datetime import date
from decimal import Decimal

import aiofiles
from structlog import get_logger

from src.config import get_settings
from src.finance.models import (
    BudgetCategory,
    ExpenseRecord,
    IncomeRecord,
)
from src.obsidian import ObsidianFileManager

logger = get_logger(__name__)
settings = get_settings()


class ExpenseManager:
    """Manage expense and income tracking."""

    def __init__(self, file_manager: ObsidianFileManager):
        self.file_manager = file_manager
        self.expenses_file = (
            settings.obsidian_vault_path / "20_Finance" / "expenses.json"
        )
        self.income_file = settings.obsidian_vault_path / "20_Finance" / "income.json"

        # Ensure finance directory exists
        self.expenses_file.parent.mkdir(parents=True, exist_ok=True)

    async def add_expense(
        self,
        description: str,
        amount: Decimal,
        category: BudgetCategory,
        expense_date: date | None = None,
        currency: str = "JPY",
        notes: str | None = None,
    ) -> ExpenseRecord:
        """Add a new expense record."""
        expense = ExpenseRecord(
            id=str(uuid.uuid4()),
            description=description,
            amount=amount,
            currency=currency,
            category=category,
            expense_date=expense_date or date.today(),
            notes=notes,
        )

        expenses = await self._load_expenses()
        expenses[expense.id] = expense
        await self._save_expenses(expenses)

        # Add to daily note
        await self._add_to_daily_note(expense, "expense")

        logger.info(
            "Expense added",
            expense_id=expense.id,
            description=description,
            amount=float(amount),
            category=category.value,
        )

        return expense

    async def add_income(
        self,
        description: str,
        amount: Decimal,
        income_date: date | None = None,
        currency: str = "JPY",
        notes: str | None = None,
    ) -> IncomeRecord:
        """Add a new income record."""
        income = IncomeRecord(
            id=str(uuid.uuid4()),
            description=description,
            amount=amount,
            currency=currency,
            income_date=income_date or date.today(),
            notes=notes,
        )

        incomes = await self._load_incomes()
        incomes[income.id] = income
        await self._save_incomes(incomes)

        # Add to daily note
        await self._add_to_daily_note(income, "income")

        logger.info(
            "Income added",
            income_id=income.id,
            description=description,
            amount=float(amount),
        )

        return income

    async def get_expenses_by_period(
        self,
        start_date: date,
        end_date: date,
        category: BudgetCategory | None = None,
    ) -> list[ExpenseRecord]:
        """Get expenses for a specific period with enhanced type safety."""
        if start_date > end_date:
            raise ValueError("Start date must be before or equal to end date")

        expenses = await self._load_expenses()

        result: list[ExpenseRecord] = []
        for expense_data in expenses.values():
            expense = (
                ExpenseRecord(**expense_data)
                if isinstance(expense_data, dict)
                else expense_data
            )

            # Enhanced filtering with proper type checking
            date_match = start_date <= expense.date <= end_date
            category_match = category is None or expense.category == category

            if date_match and category_match:
                result.append(expense)

        return sorted(result, key=lambda x: x.date, reverse=True)

    async def get_income_by_period(
        self,
        start_date: date,
        end_date: date,
    ) -> list[IncomeRecord]:
        """Get income for a specific period."""
        incomes = await self._load_incomes()

        result = []
        for income_data in incomes.values():
            income = (
                IncomeRecord(**income_data)
                if isinstance(income_data, dict)
                else income_data
            )

            if start_date <= income.date <= end_date:
                result.append(income)

        return sorted(result, key=lambda x: x.date, reverse=True)

    async def get_total_expenses_by_category(
        self,
        start_date: date,
        end_date: date,
    ) -> dict[BudgetCategory, Decimal]:
        """Get total expenses by category for a period."""
        expenses = await self.get_expenses_by_period(start_date, end_date)

        totals = {}
        for expense in expenses:
            if expense.category not in totals:
                totals[expense.category] = Decimal(0)
            totals[expense.category] += expense.amount

        return totals

    async def get_total_income(
        self,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        """Get total income for a period."""
        incomes = await self.get_income_by_period(start_date, end_date)
        return sum(income.amount for income in incomes) or Decimal(0)

    async def get_total_expenses(
        self,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        """Get total expenses for a period."""
        expenses = await self.get_expenses_by_period(start_date, end_date)
        return sum(expense.amount for expense in expenses) or Decimal(0)

    async def get_net_balance(
        self,
        start_date: date,
        end_date: date,
    ) -> Decimal:
        """Get net balance (income - expenses) for a period."""
        total_income = await self.get_total_income(start_date, end_date)
        total_expenses = await self.get_total_expenses(start_date, end_date)
        return total_income - total_expenses

    async def _load_expenses(self) -> dict[str, ExpenseRecord]:
        """Load expenses from JSON file."""
        if not self.expenses_file.exists():
            return {}

        try:
            async with aiofiles.open(self.expenses_file, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

                expenses = {}
                for expense_id, expense_data in data.items():
                    if isinstance(expense_data, dict):
                        expenses[expense_id] = ExpenseRecord(**expense_data)
                    else:
                        expenses[expense_id] = expense_data

                return expenses
        except Exception as e:
            logger.error("Failed to load expenses", error=str(e))
            return {}

    async def _save_expenses(self, expenses: dict[str, ExpenseRecord]) -> None:
        """Save expenses to JSON file."""
        try:
            data = {}
            for expense_id, expense in expenses.items():
                if isinstance(expense, ExpenseRecord):
                    data[expense_id] = expense.dict()
                else:
                    data[expense_id] = expense

            async with aiofiles.open(self.expenses_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(data, indent=2, default=str, ensure_ascii=False)
                )
        except Exception as e:
            logger.error("Failed to save expenses", error=str(e))

    async def _load_incomes(self) -> dict[str, IncomeRecord]:
        """Load incomes from JSON file."""
        if not self.income_file.exists():
            return {}

        try:
            async with aiofiles.open(self.income_file, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

                incomes = {}
                for income_id, income_data in data.items():
                    if isinstance(income_data, dict):
                        incomes[income_id] = IncomeRecord(**income_data)
                    else:
                        incomes[income_id] = income_data

                return incomes
        except Exception as e:
            logger.error("Failed to load incomes", error=str(e))
            return {}

    async def _save_incomes(self, incomes: dict[str, IncomeRecord]) -> None:
        """Save incomes to JSON file."""
        try:
            data = {}
            for income_id, income in incomes.items():
                if isinstance(income, IncomeRecord):
                    data[income_id] = income.dict()
                else:
                    data[income_id] = income

            async with aiofiles.open(self.income_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(data, indent=2, default=str, ensure_ascii=False)
                )
        except Exception as e:
            logger.error("Failed to save incomes", error=str(e))

    async def _add_to_daily_note(
        self,
        record: ExpenseRecord | IncomeRecord,
        record_type: str,
    ) -> None:
        """Add expense/income to daily note."""
        try:
            from src.obsidian.daily_integration import (
                DailyNoteIntegration as DailyNoteIntegrator,
            )
            from src.obsidian.models import VaultFolder

            daily_integrator = DailyNoteIntegrator(self.file_manager)

            if record_type == "expense":
                from src.finance.models import ExpenseRecord

                assert isinstance(record, ExpenseRecord)
                content = f"- **支出**: {record.description} - ¥{record.amount:,} ({record.category.value})"
                if record.notes:
                    content += f" - {record.notes}"
            else:  # income
                content = f"- **収入**: {record.description} - ¥{record.amount:,}"
                if record.notes:
                    content += f" - {record.notes}"

            # Add to daily note using activity log
            message_data = {
                "content": f"Finance: {content}",
                "category": VaultFolder.FINANCE.value,
                "type": record_type,
            }
            from datetime import datetime as dt

            await daily_integrator.add_activity_log_entry(
                message_data, dt.combine(record.date, dt.min.time())
            )

        except Exception as e:
            logger.error(
                "Failed to add to daily note",
                record_type=record_type,
                error=str(e),
            )
