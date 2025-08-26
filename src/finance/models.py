"""Finance data models for subscription and expense tracking."""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class SubscriptionStatus(str, Enum):
    """Subscription status enum."""

    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class SubscriptionFrequency(str, Enum):
    """Subscription billing frequency enum."""

    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class BudgetCategory(str, Enum):
    """Budget category enum with improved type safety."""

    SUBSCRIPTIONS = "subscriptions"
    FOOD = "food"
    TRANSPORTATION = "transportation"
    ENTERTAINMENT = "entertainment"
    UTILITIES = "utilities"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    SHOPPING = "shopping"
    OTHER = "other"

    @classmethod
    def from_string(cls, value: str) -> "BudgetCategory":
        """Convert string to BudgetCategory with validation."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.OTHER

    @property
    def display_name(self) -> str:
        """Get human-readable display name."""
        return self.value.replace("_", " ").title()


class Subscription(BaseModel):
    """Subscription data model with comprehensive type safety."""

    id: str = Field(..., description="Unique subscription ID")
    name: str = Field(..., description="Service name")
    amount: Decimal = Field(..., description="Subscription amount", gt=0)
    currency: str = Field(default="JPY", description="Currency code")
    frequency: SubscriptionFrequency = Field(..., description="Billing frequency")
    start_date: date = Field(..., description="Subscription start date")
    next_payment_date: date = Field(..., description="Next payment due date")
    status: SubscriptionStatus = Field(default=SubscriptionStatus.ACTIVE)
    category: str | None = Field(None, description="Service category")
    notes: str | None = Field(None, description="Additional notes")
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code with comprehensive support."""
        valid_currencies = ["JPY", "USD", "EUR", "GBP", "CAD", "AUD"]
        if v.upper() not in valid_currencies:
            raise ValueError(f"Currency must be one of {valid_currencies}")
        return v.upper()

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Validate subscription amount is positive."""
        if v <= 0:
            raise ValueError("Subscription amount must be positive")
        return v

    def calculate_next_payment_date(self, from_date: date | None = None) -> date:
        """Calculate next payment date based on frequency with proper type handling."""
        base_date = from_date or self.next_payment_date

        if self.frequency == SubscriptionFrequency.WEEKLY:
            from datetime import timedelta

            return base_date + timedelta(weeks=1)
        elif self.frequency == SubscriptionFrequency.MONTHLY:
            from dateutil.relativedelta import relativedelta

            return base_date + relativedelta(months=1)
        elif self.frequency == SubscriptionFrequency.QUARTERLY:
            from dateutil.relativedelta import relativedelta

            return base_date + relativedelta(months=3)
        elif self.frequency == SubscriptionFrequency.YEARLY:
            from dateutil.relativedelta import relativedelta

            return base_date + relativedelta(years=1)
        else:
            return base_date

    def get_monthly_amount(self) -> Decimal:
        """Get equivalent monthly amount regardless of billing frequency."""
        if self.frequency == SubscriptionFrequency.MONTHLY:
            return self.amount
        elif self.frequency == SubscriptionFrequency.YEARLY:
            return self.amount / 12
        elif self.frequency == SubscriptionFrequency.QUARTERLY:
            return self.amount / 3
        elif self.frequency == SubscriptionFrequency.WEEKLY:
            return self.amount * Decimal("4.33")  # Average weeks per month
        else:
            return self.amount

    def is_due_soon(self, days: int = 3) -> bool:
        """Check if payment is due within specified days."""
        from datetime import timedelta

        today = date.today()
        return self.next_payment_date <= today + timedelta(days=days)

    def is_overdue(self) -> bool:
        """Check if payment is overdue."""
        return self.next_payment_date < date.today()

    def is_active(self) -> bool:
        """Check if subscription is currently active."""
        return self.status == SubscriptionStatus.ACTIVE


class PaymentRecord(BaseModel):
    """Payment record for subscription."""

    id: str = Field(..., description="Unique payment record ID")
    subscription_id: str = Field(..., description="Related subscription ID")
    amount: Decimal = Field(..., description="Payment amount", gt=0)
    currency: str = Field(default="JPY", description="Currency code")
    payment_date: date = Field(..., description="Actual payment date")
    notes: str | None = Field(None, description="Payment notes")
    created_at: datetime = Field(default_factory=lambda: datetime.now())


class ExpenseRecord(BaseModel):
    """General expense record."""

    id: str = Field(..., description="Unique expense ID")
    description: str = Field(..., description="Expense description")
    amount: Decimal = Field(..., description="Expense amount", gt=0)
    currency: str = Field(default="JPY", description="Currency code")
    category: BudgetCategory = Field(..., description="Expense category")
    expense_date: date = Field(..., description="Expense date")
    notes: str | None = Field(None, description="Additional notes")
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    @property
    def date(self) -> date:
        """Alias for expense_date for backward compatibility."""
        return self.expense_date


class IncomeRecord(BaseModel):
    """Income record."""

    id: str = Field(..., description="Unique income ID")
    description: str = Field(..., description="Income description")
    amount: Decimal = Field(..., description="Income amount", gt=0)
    currency: str = Field(default="JPY", description="Currency code")
    income_date: date = Field(..., description="Income date")
    notes: str | None = Field(None, description="Additional notes")
    created_at: datetime = Field(default_factory=lambda: datetime.now())

    @property
    def date(self) -> date:
        """Alias for income_date for backward compatibility."""
        return self.income_date


class Budget(BaseModel):
    """Budget data model."""

    id: str = Field(..., description="Unique budget ID")
    category: BudgetCategory = Field(..., description="Budget category")
    amount: Decimal = Field(..., description="Budget amount", gt=0)
    currency: str = Field(default="JPY", description="Currency code")
    period_start: date = Field(..., description="Budget period start")
    period_end: date = Field(..., description="Budget period end")
    spent_amount: Decimal = Field(default=Decimal(0), description="Amount spent")
    created_at: datetime = Field(default_factory=lambda: datetime.now())
    updated_at: datetime = Field(default_factory=lambda: datetime.now())

    @property
    def remaining_amount(self) -> Decimal:
        """Calculate remaining budget amount."""
        return self.amount - self.spent_amount

    @property
    def percentage_used(self) -> float:
        """Calculate percentage of budget used."""
        if self.amount == 0:
            return 0.0
        return float(self.spent_amount / self.amount * 100)

    def is_near_limit(self, threshold: float = 80.0) -> bool:
        """Check if budget is near limit."""
        return self.percentage_used >= threshold

    def is_over_budget(self) -> bool:
        """Check if budget is exceeded."""
        return self.spent_amount > self.amount


class FinanceSummary(BaseModel):
    """Finance summary data model."""

    total_subscriptions: int = Field(default=0)
    total_subscription_cost: Decimal = Field(default=Decimal(0))
    total_expenses: Decimal = Field(default=Decimal(0))
    total_income: Decimal = Field(default=Decimal(0))
    net_balance: Decimal = Field(default=Decimal(0))
    budget_usage: dict[str, float] = Field(default_factory=dict)
    upcoming_payments: list[Subscription] = Field(default_factory=list)
    overdue_payments: list[Subscription] = Field(default_factory=list)
    period_start: date = Field(...)
    period_end: date = Field(...)
