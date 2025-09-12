"""Subscription management functionality."""

import json
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import aiofiles
from structlog import get_logger

from src.config import get_settings
from src.finance.models import (
    PaymentRecord,
    Subscription,
    SubscriptionFrequency,
    SubscriptionStatus,
)
from src.obsidian import ObsidianFileManager

logger = get_logger(__name__)
settings = get_settings()


class SubscriptionManager:
    """Manage subscription tracking and payments."""

    def __init__(self, file_manager: ObsidianFileManager):
        self.file_manager = file_manager
        self.data_file = (
            settings.obsidian_vault_path / "20_Finance" / "subscriptions.json"
        )
        self.payments_file = (
            settings.obsidian_vault_path / "20_Finance" / "payments.json"
        )

        # Ensure finance directory exists
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

    async def add_subscription(
        self,
        name: str,
        amount: Decimal,
        frequency: SubscriptionFrequency,
        start_date: date,
        currency: str = "JPY",
        category: str | None = None,
        notes: str | None = None,
    ) -> Subscription:
        """Add a new subscription."""
        subscription = Subscription(
            id=str(uuid.uuid4()),
            name=name,
            amount=amount,
            currency=currency,
            frequency=frequency,
            start_date=start_date,
            next_payment_date=start_date,
            category=category,
            notes=notes,
        )

        subscriptions = await self._load_subscriptions()
        subscriptions[subscription.id] = subscription
        await self._save_subscriptions(subscriptions)

        # Create Obsidian note for the subscription
        await self._create_subscription_note(subscription)

        logger.info(
            "Subscription added",
            subscription_id=subscription.id,
            name=name,
            amount=float(amount),
            frequency=frequency.value,
        )

        return subscription

    async def get_subscription(self, subscription_id: str) -> Subscription | None:
        """Get subscription by ID."""
        subscriptions = await self._load_subscriptions()
        subscription_data = subscriptions.get(subscription_id)

        if subscription_data:
            return (
                Subscription(**subscription_data)
                if isinstance(subscription_data, dict)
                else subscription_data
            )
        return None

    async def list_subscriptions(
        self,
        status: SubscriptionStatus | None = None,
        active_only: bool = False,
    ) -> list[Subscription]:
        """List all subscriptions with optional filtering."""
        subscriptions = await self._load_subscriptions()

        result = []
        for sub_data in subscriptions.values():
            subscription = (
                Subscription(**sub_data) if isinstance(sub_data, dict) else sub_data
            )

            if status and subscription.status != status:
                continue

            if active_only and subscription.status != SubscriptionStatus.ACTIVE:
                continue

            result.append(subscription)

        # Sort by next payment date
        return sorted(result, key=lambda x: x.next_payment_date)

    async def update_subscription(
        self,
        subscription_id: str,
        **updates: Any,
    ) -> Subscription | None:
        """Update subscription details."""
        subscriptions = await self._load_subscriptions()

        if subscription_id not in subscriptions:
            return None

        subscription_data = subscriptions[subscription_id]
        subscription = (
            Subscription(**subscription_data)
            if isinstance(subscription_data, dict)
            else subscription_data
        )

        # Update fields
        for field, value in updates.items():
            if hasattr(subscription, field):
                setattr(subscription, field, value)

        subscription.updated_at = datetime.now()
        subscriptions[subscription_id] = subscription
        await self._save_subscriptions(subscriptions)

        logger.info(
            "Subscription updated",
            subscription_id=subscription_id,
            updates=updates,
        )

        return subscription

    async def mark_payment(
        self,
        subscription_id: str,
        payment_date: date | None = None,
        amount: Decimal | None = None,
        notes: str | None = None,
    ) -> PaymentRecord | None:
        """Mark subscription payment as completed."""
        subscription = await self.get_subscription(subscription_id)
        if not subscription:
            return None

        payment_date = payment_date or date.today()
        amount = amount or subscription.amount

        # Create payment record
        payment = PaymentRecord(
            id=str(uuid.uuid4()),
            subscription_id=subscription_id,
            amount=amount,
            currency=subscription.currency,
            payment_date=payment_date,
            notes=notes,
        )

        # Save payment record
        await self._save_payment(payment)

        # Update subscription next payment date
        subscription.next_payment_date = subscription.calculate_next_payment_date(
            payment_date
        )
        subscription.updated_at = datetime.now()

        subscriptions = await self._load_subscriptions()
        subscriptions[subscription_id] = subscription
        await self._save_subscriptions(subscriptions)

        # Update Obsidian note
        await self._update_subscription_note(subscription, payment)

        logger.info(
            "Payment marked",
            subscription_id=subscription_id,
            payment_date=payment_date.isoformat(),
            amount=float(amount),
        )

        return payment

    async def pause_subscription(self, subscription_id: str) -> Subscription | None:
        """Pause a subscription."""
        return await self.update_subscription(
            subscription_id,
            status=SubscriptionStatus.PAUSED,
        )

    async def resume_subscription(self, subscription_id: str) -> Subscription | None:
        """Resume a paused subscription."""
        return await self.update_subscription(
            subscription_id,
            status=SubscriptionStatus.ACTIVE,
        )

    async def cancel_subscription(self, subscription_id: str) -> Subscription | None:
        """Cancel a subscription."""
        return await self.update_subscription(
            subscription_id,
            status=SubscriptionStatus.CANCELLED,
        )

    async def get_due_subscriptions(self, days_ahead: int = 3) -> list[Subscription]:
        """Get subscriptions due within specified days."""
        subscriptions = await self.list_subscriptions(active_only=True)
        return [sub for sub in subscriptions if sub.is_due_soon(days_ahead)]

    async def get_overdue_subscriptions(self) -> list[Subscription]:
        """Get overdue subscriptions."""
        subscriptions = await self.list_subscriptions(active_only=True)
        return [sub for sub in subscriptions if sub.is_overdue()]

    async def get_payment_history(self, subscription_id: str) -> list[PaymentRecord]:
        """Get payment history for a subscription."""
        payments = await self._load_payments()
        return [
            PaymentRecord(**payment) if isinstance(payment, dict) else payment
            for payment in payments.values()
            if (
                payment.get("subscription_id")
                if isinstance(payment, dict)
                else payment.subscription_id
            )
            == subscription_id
        ]

    async def get_active_subscriptions(self) -> list[Subscription]:
        """Get all active subscriptions.

        This is a convenience method that wraps list_subscriptions(active_only=True)
        for better API consistency and backward compatibility.
        """
        return await self.list_subscriptions(active_only=True)

    async def get_monthly_cost(self) -> Decimal:
        """Calculate total monthly cost of all active subscriptions."""
        from decimal import Decimal

        from src.finance.models import SubscriptionFrequency

        active_subscriptions = await self.get_active_subscriptions()
        monthly_cost = Decimal(0)

        for subscription in active_subscriptions:
            if subscription.frequency == SubscriptionFrequency.MONTHLY:
                monthly_cost += subscription.amount
            elif subscription.frequency == SubscriptionFrequency.YEARLY:
                monthly_cost += subscription.amount / 12
            elif subscription.frequency == "quarterly":
                monthly_cost += subscription.amount / 3
            elif subscription.frequency == SubscriptionFrequency.WEEKLY:
                monthly_cost += subscription.amount * Decimal(
                    "4.33"
                )  # Average weeks per month

        return monthly_cost

    async def _load_subscriptions(self) -> dict[str, Subscription]:
        """Load subscriptions from JSON file."""
        if not self.data_file.exists():
            return {}

        try:
            async with aiofiles.open(self.data_file, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

                # Convert dict data to Subscription objects
                subscriptions = {}
                for sub_id, sub_data in data.items():
                    if isinstance(sub_data, dict):
                        subscriptions[sub_id] = Subscription(**sub_data)
                    else:
                        subscriptions[sub_id] = sub_data

                return subscriptions
        except Exception as e:
            logger.error("Failed to load subscriptions", error=str(e))
            return {}

    async def _save_subscriptions(self, subscriptions: dict[str, Subscription]) -> None:
        """Save subscriptions to JSON file."""
        try:
            # Convert Subscription objects to dict for JSON serialization
            data = {}
            for sub_id, subscription in subscriptions.items():
                if isinstance(subscription, Subscription):
                    data[sub_id] = subscription.dict()
                else:
                    data[sub_id] = subscription

            async with aiofiles.open(self.data_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(data, indent=2, default=str, ensure_ascii=False)
                )
        except Exception as e:
            logger.error("Failed to save subscriptions", error=str(e))

    async def _load_payments(self) -> dict[str, PaymentRecord]:
        """Load payment records from JSON file."""
        if not self.payments_file.exists():
            return {}

        try:
            async with aiofiles.open(self.payments_file, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

                payments = {}
                for payment_id, payment_data in data.items():
                    if isinstance(payment_data, dict):
                        payments[payment_id] = PaymentRecord(**payment_data)
                    else:
                        payments[payment_id] = payment_data

                return payments
        except Exception as e:
            logger.error("Failed to load payments", error=str(e))
            return {}

    async def _save_payment(self, payment: PaymentRecord) -> None:
        """Save payment record to JSON file."""
        try:
            payments = await self._load_payments()
            payments[payment.id] = payment

            # Convert to dict for JSON serialization
            data = {}
            for payment_id, payment_obj in payments.items():
                if isinstance(payment_obj, PaymentRecord):
                    data[payment_id] = payment_obj.dict()
                else:
                    data[payment_id] = payment_obj

            async with aiofiles.open(self.payments_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(data, indent=2, default=str, ensure_ascii=False)
                )
        except Exception as e:
            logger.error("Failed to save payment", error=str(e))

    async def _create_subscription_note(self, subscription: Subscription) -> None:
        """Create Obsidian note for subscription."""
        try:
            filename = f"{subscription.name.replace(' ', '_')}_subscription.md"
            file_path = Path("20_Finance") / "Subscriptions" / filename

            content = f"""---
subscription_id: {subscription.id}
service_name: {subscription.name}
amount: {subscription.amount}
currency: {subscription.currency}
frequency: {subscription.frequency.value}
status: {subscription.status.value}
start_date: {subscription.start_date}
next_payment: {subscription.next_payment_date}
category: {subscription.category or "uncategorized"}
created: {subscription.created_at.isoformat()}
updated: {subscription.updated_at.isoformat()}
---

# {subscription.name} 定期購入

## 基本情報
- **サービス名**: {subscription.name}
- **金額**: ¥{subscription.amount:,} ({subscription.currency})
- **支払い頻度**: {subscription.frequency.value}
- **ステータス**: {subscription.status.value}
- **開始日**: {subscription.start_date}
- **次回支払い日**: {subscription.next_payment_date}

## カテゴリ
{subscription.category or "未分類"}

## メモ
{subscription.notes or "なし"}

## 支払い履歴
支払いが完了すると、ここに履歴が記録されます。

## 関連リンク
- [[Monthly Finance Report]]
- [[Budget Tracking]]
"""

            from src.obsidian.models import NoteFrontmatter, ObsidianNote

            frontmatter = NoteFrontmatter(
                ai_processed=True,
                ai_summary=f"Subscription: {subscription.name}",
                ai_tags=[],
                ai_category="finance",
                tags=[],
                obsidian_folder="20_Finance",
            )
            note = ObsidianNote(
                filename=file_path.name,
                file_path=file_path,
                content=content,
                frontmatter=frontmatter,
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            await self.file_manager.save_note(note)

        except Exception as e:
            logger.error(
                "Failed to create subscription note",
                subscription_id=subscription.id,
                error=str(e),
            )

    async def _update_subscription_note(
        self,
        subscription: Subscription,
        payment: PaymentRecord | None = None,
    ) -> None:
        """Update subscription note with payment information."""
        try:
            filename = f"{subscription.name.replace(' ', '_')}_subscription.md"
            file_path = Path("20_Finance") / "Subscriptions" / filename

            # Read existing content
            note = await self.file_manager.load_note(file_path)
            existing_content = note.content if note else None
            if not existing_content:
                await self._create_subscription_note(subscription)
                return

            # Update metadata
            lines = existing_content.split("\n")
            updated_lines = []
            in_frontmatter = False

            for line in lines:
                if line.strip() == "---":
                    in_frontmatter = not in_frontmatter
                    updated_lines.append(line)
                elif in_frontmatter:
                    if line.startswith("next_payment:"):
                        updated_lines.append(
                            f"next_payment: {subscription.next_payment_date}"
                        )
                    elif line.startswith("updated:"):
                        updated_lines.append(
                            f"updated: {subscription.updated_at.isoformat()}"
                        )
                    elif line.startswith("status:"):
                        updated_lines.append(f"status: {subscription.status.value}")
                    else:
                        updated_lines.append(line)
                else:
                    updated_lines.append(line)

            # Add payment record if provided
            if payment:
                payment_entry = f"\n### {payment.payment_date}\n- 金額: ¥{payment.amount:,}\n- 支払い日: {payment.payment_date}\n"
                if payment.notes:
                    payment_entry += f"- メモ: {payment.notes}\n"

                updated_lines.append(payment_entry)

            updated_content = "\n".join(updated_lines)
            # Create an ObsidianNote instance and save it
            from src.obsidian.models import NoteFrontmatter, ObsidianNote

            frontmatter = NoteFrontmatter(obsidian_folder="20_Finance")
            note = ObsidianNote(
                filename=file_path.name,
                file_path=file_path,
                frontmatter=frontmatter,
                content=updated_content,
            )
            await self.file_manager.save_note(note, overwrite=True)

        except Exception as e:
            logger.error(
                "Failed to update subscription note",
                subscription_id=subscription.id,
                error=str(e),
            )
