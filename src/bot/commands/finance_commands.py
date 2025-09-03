"""Finance management Discord commands."""

from typing import Any

import discord
import structlog
from discord.ext import commands

logger = structlog.get_logger(__name__)


class FinanceCommands(commands.Cog):
    """Finance management commands for Discord bot."""

    def __init__(self, bot: Any):
        self.bot = bot
        self.logger = logger.bind(component="FinanceCommands")

    @commands.command(name="finance_help")
    async def finance_help(self, ctx: commands.Context) -> None:
        """Show finance management help."""
        embed = discord.Embed(
            title="💰 Finance Management Commands",
            description="Available finance commands",
            color=discord.Color.gold(),
        )

        embed.add_field(
            name="!expense_add",
            value="Add an expense record",
            inline=False,
        )
        embed.add_field(
            name="!expense_list",
            value="List recent expenses",
            inline=False,
        )
        embed.add_field(
            name="!budget_status",
            value="Check budget status",
            inline=False,
        )

        await ctx.send(embed=embed)

    @commands.command(name="expense_add")
    async def expense_add(
        self, ctx: commands.Context, amount: float, *, description: str
    ) -> None:
        """Add an expense record."""
        try:
            # Expense creation logic would go here
            embed = discord.Embed(
                title="💰 Expense Added",
                description=f"Expense recorded: ¥{amount:,.0f} - {description}",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            self.logger.info("Expense added", amount=amount, description=description)
        except Exception as e:
            self.logger.error("Failed to add expense", error=str(e))
            await ctx.send("❌ Failed to add expense")

    @commands.command(name="expense_list")
    async def expense_list(self, ctx: commands.Context) -> None:
        """List recent expenses."""
        try:
            embed = discord.Embed(
                title="💰 Recent Expenses",
                description="No recent expenses found",
                color=discord.Color.gold(),
            )
            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error("Failed to list expenses", error=str(e))
            await ctx.send("❌ Failed to list expenses")

    @commands.command(name="budget_status")
    async def budget_status(self, ctx: commands.Context) -> None:
        """Check budget status."""
        try:
            embed = discord.Embed(
                title="📊 Budget Status",
                description="Budget information not available",
                color=discord.Color.blue(),
            )
            await ctx.send(embed=embed)
        except Exception as e:
            self.logger.error("Failed to check budget status", error=str(e))
            await ctx.send("❌ Failed to check budget status")
