"""Finance message handler for processing expense and income messages."""

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import discord
from structlog import get_logger

from src.bot.channel_config import ChannelConfig
from src.finance.expense_manager import ExpenseManager
from src.finance.models import BudgetCategory

logger = get_logger(__name__)


class FinanceMessageHandler:
    """Handle finance-related messages in expense and income channels."""

    def __init__(
        self,
        channel_config: ChannelConfig,
        expense_manager: ExpenseManager,
    ):
        self.channel_config = channel_config
        self.expense_manager = expense_manager

    async def handle_message(self, message: discord.Message) -> bool:
        """Handle a finance-related message. Returns True if handled."""
        if message.author.bot:
            return False

        channel_id = message.channel.id

        # Check if it's a finance channel
        if self._is_expense_channel(channel_id):
            return await self._handle_expense_message(message)
        if self._is_income_channel(channel_id):
            return await self._handle_income_message(message)

        return False

    def _is_expense_channel(self, channel_id: int) -> bool:
        """Check if channel is an expense tracking channel."""
        memo_channel = self.channel_config.get_memo_channel()
        return channel_id == memo_channel if memo_channel else False

    def _is_income_channel(self, channel_id: int) -> bool:
        """Check if channel is an income tracking channel."""
        memo_channel = self.channel_config.get_memo_channel()
        return channel_id == memo_channel if memo_channel else False

    async def _handle_expense_message(self, message: discord.Message) -> bool:
        """Handle expense message."""
        try:
            # Parse expense from message
            expense_data = await self._parse_expense_message(message.content)
            if not expense_data:
                return False

            amount, description, category = expense_data

            # Add expense
            expense = await self.expense_manager.add_expense(
                description=description,
                amount=amount,
                category=category,
                expense_date=date.today(),
                notes=f"From Discord message by {message.author.display_name}",
            )

            # Send confirmation
            embed = discord.Embed(
                title="✅ 支出を記録しました",
                color=discord.Color.red(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="説明", value=expense.description, inline=True)
            embed.add_field(name="金額", value=f"¥{expense.amount:,}", inline=True)
            embed.add_field(name="カテゴリ", value=expense.category.value, inline=True)
            embed.add_field(name="日付", value=expense.date, inline=True)

            await message.reply(embed=embed)

            logger.info(
                "Expense recorded from message",
                user_id=message.author.id,
                expense_id=expense.id,
                amount=float(expense.amount),
                category=expense.category.value,
            )

            return True

        except Exception as e:
            logger.error("Failed to handle expense message", error=str(e))
            await message.reply("❌ 支出の記録に失敗しました。")
            return False

    async def _handle_income_message(self, message: discord.Message) -> bool:
        """Handle income message."""
        try:
            # Parse income from message
            income_data = await self._parse_income_message(message.content)
            if not income_data:
                return False

            amount, description = income_data

            # Add income
            income = await self.expense_manager.add_income(
                description=description,
                amount=amount,
                income_date=date.today(),
                notes=f"From Discord message by {message.author.display_name}",
            )

            # Send confirmation
            embed = discord.Embed(
                title="✅ 収入を記録しました",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )
            embed.add_field(name="説明", value=income.description, inline=True)
            embed.add_field(name="金額", value=f"¥{income.amount:,}", inline=True)
            embed.add_field(name="日付", value=income.date, inline=True)

            await message.reply(embed=embed)

            logger.info(
                "Income recorded from message",
                user_id=message.author.id,
                income_id=income.id,
                amount=float(income.amount),
            )

            return True

        except Exception as e:
            logger.error("Failed to handle income message", error=str(e))
            await message.reply("❌ 収入の記録に失敗しました。")
            return False

    async def _parse_expense_message(
        self, content: str
    ) -> tuple[Decimal, str, BudgetCategory] | None:
        """Parse expense information from message content."""
        # Pattern 1: "金額 説明 [カテゴリ]"
        # Examples: "1500 ランチ", "3000 本 教育", "500 コーヒー food"
        patterns = [
            r"(\d+(?:,\d{3})*)\s+(.+?)\s+(food|transportation|entertainment|utilities|healthcare|education|shopping|other)(?:\s|$)",
            r"(\d+(?:,\d{3})*)\s+(.+?)(?:\s+(食費|交通費|娯楽|光熱費|医療|教育|買い物|その他))?(?:\s|$)",
            r"(\d+(?:,\d{3})*)\s+(.+)$",
            r"¥(\d+(?:,\d{3})*)\s+(.+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, content.strip(), re.IGNORECASE)
            if match:
                try:
                    # Parse amount
                    amount_str = match.group(1).replace(",", "")
                    amount = Decimal(amount_str)

                    # Parse description
                    description = match.group(2).strip()

                    # Parse category
                    category = BudgetCategory.OTHER  # Default
                    if len(match.groups()) >= 3 and match.group(3):
                        category_str = match.group(3).lower()
                        category = self._parse_category(category_str)
                    else:
                        # Try to auto-detect category from description
                        category = self._auto_detect_category(description)

                    return amount, description, category

                except (InvalidOperation, ValueError):
                    continue

        return None

    async def _parse_income_message(self, content: str) -> tuple[Decimal, str] | None:
        """Parse income information from message content."""
        # Pattern: "金額 説明"
        # Examples: "50000 給料", "10000 副業", "¥5000 ボーナス"
        patterns = [
            r"(\d+(?:,\d{3})*)\s+(.+)$",
            r"¥(\d+(?:,\d{3})*)\s+(.+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, content.strip(), re.IGNORECASE)
            if match:
                try:
                    # Parse amount
                    amount_str = match.group(1).replace(",", "")
                    amount = Decimal(amount_str)

                    # Parse description
                    description = match.group(2).strip()

                    return amount, description

                except (InvalidOperation, ValueError):
                    continue

        return None

    def _parse_category(self, category_str: str) -> BudgetCategory:
        """Parse category from string."""
        category_mapping = {
            "food": BudgetCategory.FOOD,
            "食費": BudgetCategory.FOOD,
            "食事": BudgetCategory.FOOD,
            "transportation": BudgetCategory.TRANSPORTATION,
            "交通費": BudgetCategory.TRANSPORTATION,
            "交通": BudgetCategory.TRANSPORTATION,
            "entertainment": BudgetCategory.ENTERTAINMENT,
            "娯楽": BudgetCategory.ENTERTAINMENT,
            "エンタメ": BudgetCategory.ENTERTAINMENT,
            "utilities": BudgetCategory.UTILITIES,
            "光熱費": BudgetCategory.UTILITIES,
            "電気": BudgetCategory.UTILITIES,
            "ガス": BudgetCategory.UTILITIES,
            "水道": BudgetCategory.UTILITIES,
            "healthcare": BudgetCategory.HEALTHCARE,
            "医療": BudgetCategory.HEALTHCARE,
            "病院": BudgetCategory.HEALTHCARE,
            "education": BudgetCategory.EDUCATION,
            "教育": BudgetCategory.EDUCATION,
            "本": BudgetCategory.EDUCATION,
            "学習": BudgetCategory.EDUCATION,
            "shopping": BudgetCategory.SHOPPING,
            "買い物": BudgetCategory.SHOPPING,
            "購入": BudgetCategory.SHOPPING,
            "other": BudgetCategory.OTHER,
            "その他": BudgetCategory.OTHER,
            "雑費": BudgetCategory.OTHER,
        }

        return category_mapping.get(category_str.lower(), BudgetCategory.OTHER)

    def _auto_detect_category(self, description: str) -> BudgetCategory:
        """Auto-detect category from description."""
        description_lower = description.lower()

        # Food keywords
        food_keywords = [
            "ランチ",
            "昼食",
            "夕食",
            "朝食",
            "コーヒー",
            "カフェ",
            "レストラン",
            "食事",
            "弁当",
            "スーパー",
        ]
        if any(keyword in description_lower for keyword in food_keywords):
            return BudgetCategory.FOOD

        # Transportation keywords
        transport_keywords = [
            "電車",
            "バス",
            "タクシー",
            "ガソリン",
            "駐車場",
            "交通",
            "乗車",
        ]
        if any(keyword in description_lower for keyword in transport_keywords):
            return BudgetCategory.TRANSPORTATION

        # Entertainment keywords
        entertainment_keywords = ["映画", "ゲーム", "音楽", "娯楽", "趣味", "旅行"]
        if any(keyword in description_lower for keyword in entertainment_keywords):
            return BudgetCategory.ENTERTAINMENT

        # Education keywords
        education_keywords = ["本", "書籍", "セミナー", "講座", "教材", "学習"]
        if any(keyword in description_lower for keyword in education_keywords):
            return BudgetCategory.EDUCATION

        # Healthcare keywords
        healthcare_keywords = ["病院", "薬", "医療", "診察", "治療"]
        if any(keyword in description_lower for keyword in healthcare_keywords):
            return BudgetCategory.HEALTHCARE

        # Utilities keywords
        utilities_keywords = [
            "電気",
            "ガス",
            "水道",
            "光熱費",
            "通信費",
            "インターネット",
        ]
        if any(keyword in description_lower for keyword in utilities_keywords):
            return BudgetCategory.UTILITIES

        return BudgetCategory.OTHER
