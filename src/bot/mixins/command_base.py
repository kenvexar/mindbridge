"""Base classes and mixins for Discord commands."""

from datetime import datetime
from typing import Any

import discord
import structlog
from discord import app_commands

logger = structlog.get_logger(__name__)


class CommandMixin:
    """Mixin for common Discord command functionality."""

    async def send_error_response(
        self,
        interaction: discord.Interaction,
        message: str,
        ephemeral: bool = True,
        followup: bool = False,
    ) -> None:
        """Send error response to user."""
        error_message = f"❌ {message}"

        try:
            if followup or interaction.response.is_done():
                await interaction.followup.send(error_message, ephemeral=ephemeral)
            else:
                await interaction.response.send_message(
                    error_message, ephemeral=ephemeral
                )
        except Exception as e:
            logger.error("Failed to send error response", error=str(e))

    async def send_success_response(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str | None = None,
        fields: list[tuple[str, str, bool]] | None = None,
        color: discord.Color | None = None,
        followup: bool = False,
    ) -> None:
        """Send success response with embed."""
        embed = discord.Embed(
            title=f"✅ {title}",
            color=color or discord.Color.green(),
            timestamp=datetime.now(),
        )

        if description:
            embed.description = description

        if fields:
            for name, value, inline in fields:
                embed.add_field(name=name, value=value, inline=inline)

        try:
            if followup or interaction.response.is_done():
                await interaction.followup.send(embed=embed)
            else:
                await interaction.response.send_message(embed=embed)
        except Exception as e:
            logger.error("Failed to send success response", error=str(e))

    async def defer_if_needed(self, interaction: discord.Interaction) -> None:
        """Defer interaction if not already responded."""
        if not interaction.response.is_done():
            await interaction.response.defer()

    def validate_amount(self, amount_str: str) -> float | None:
        """Validate and convert amount string to float."""
        try:
            amount = float(amount_str.replace(",", ""))
            return amount if amount > 0 else None
        except (ValueError, TypeError):
            return None

    def validate_date_format(
        self, date_str: str, format_str: str = "%Y-%m-%d"
    ) -> datetime | None:
        """Validate date string format."""
        try:
            return datetime.strptime(date_str, format_str)
        except ValueError:
            return None

    def find_matching_items(
        self, items: list[Any], search_term: str, field_name: str = "name"
    ) -> list[Any]:
        """Find items matching search term."""
        search_lower = search_term.lower()
        return [
            item
            for item in items
            if search_lower in getattr(item, field_name, "").lower()
        ]

    async def handle_multiple_matches(
        self,
        interaction: discord.Interaction,
        matches: list[Any],
        search_term: str,
        item_type: str,
        field_name: str = "name",
    ) -> Any | None:
        """Handle multiple match scenario."""
        if not matches:
            await self.send_error_response(
                interaction, f"'{search_term}' に一致する{item_type}が見つかりません。"
            )
            return None

        if len(matches) > 1:
            match_list = "\n".join(
                [f"- {getattr(match, field_name, str(match))}" for match in matches]
            )
            await self.send_error_response(
                interaction,
                f"複数の{item_type}が見つかりました。より具体的な名前を指定してください：\n{match_list}",
            )
            return None

        return matches[0]


class BaseCommandGroup(app_commands.Group, CommandMixin):
    """Base class for command groups with common functionality."""

    def __init__(self, name: str, description: str):
        super().__init__(name=name, description=description)

    async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        """Handle command errors."""
        logger.error(
            "Command error",
            command=interaction.command.qualified_name
            if interaction.command
            else "unknown",
            error=str(error),
            user_id=interaction.user.id,
        )

        await self.send_error_response(
            interaction, "コマンドの実行中にエラーが発生しました。", followup=True
        )
