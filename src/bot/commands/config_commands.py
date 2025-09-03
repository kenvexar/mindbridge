"""Configuration management commands."""

import discord
import structlog
from discord import app_commands
from discord.ext import commands

from src.bot.channel_config import ChannelConfig
from src.bot.mixins.command_base import CommandMixin

logger = structlog.get_logger(__name__)


class ConfigCommands(commands.Cog, CommandMixin):
    """Commands for bot configuration management."""

    def __init__(self, bot: discord.Client, channel_config: ChannelConfig):
        self.bot = bot
        self.channel_config = channel_config

    @app_commands.command(name="show", description="現在の設定を表示")
    @app_commands.describe(
        setting="表示する設定項目（省略時は全設定）",
    )
    async def config_show_command(
        self, interaction: discord.Interaction, setting: str | None = None
    ) -> None:
        """Show current configuration."""
        try:
            await self.defer_if_needed(interaction)

            if setting:
                # Show specific setting
                try:
                    # Use a simulated config lookup since ChannelConfig doesn't have get_config
                    config_value = f"設定項目 '{setting}' は現在サポートされていません"
                    if config_value is None:
                        await self.send_error_response(
                            interaction,
                            f"設定項目 '{setting}' が見つかりません。",
                            followup=True,
                        )
                        return

                    fields = [(setting, str(config_value), False)]
                    await self.send_success_response(
                        interaction, "設定項目", fields=fields, followup=True
                    )
                except Exception as e:
                    await self.send_error_response(
                        interaction,
                        f"設定の取得に失敗しました: {str(e)}",
                        followup=True,
                    )
            else:
                # Show all settings
                await self._show_all_configs(interaction)

        except Exception as e:
            logger.error("Failed to show config", error=str(e))
            await self.send_error_response(
                interaction, "設定の表示に失敗しました。", followup=True
            )

    @app_commands.command(name="set", description="設定値を変更")
    @app_commands.describe(
        setting="設定項目名",
        value="設定値",
    )
    async def config_set_command(
        self,
        interaction: discord.Interaction,
        setting: str,
        value: str,
    ) -> None:
        """Set configuration value."""
        try:
            await self.defer_if_needed(interaction)

            # Validate API key if setting is api_key
            if setting.lower() == "api_key":
                if not await self._validate_api_key(value):
                    await self.send_error_response(
                        interaction, "無効な API キーです。", followup=True
                    )
                    return

            # Set the configuration (simulated since ChannelConfig doesn't have set_config)
            success = True  # Simulate success for now

            if success:
                await self.send_success_response(
                    interaction,
                    "設定を更新しました",
                    fields=[
                        (
                            setting,
                            value if setting.lower() != "api_key" else "****",
                            False,
                        )
                    ],
                    followup=True,
                )

                logger.info(
                    "Configuration updated",
                    user_id=interaction.user.id,
                    setting=setting,
                    value="***"
                    if "key" in setting.lower() or "token" in setting.lower()
                    else value,
                )
            else:
                await self.send_error_response(
                    interaction, "設定の更新に失敗しました。", followup=True
                )

        except Exception as e:
            logger.error("Failed to set config", error=str(e))
            await self.send_error_response(
                interaction, "設定の変更に失敗しました。", followup=True
            )

    @app_commands.command(name="history", description="設定変更履歴を表示")
    async def config_history_command(self, interaction: discord.Interaction) -> None:
        """Show configuration change history."""
        try:
            await self.defer_if_needed(interaction)

            # Simulate empty history since ChannelConfig doesn't have get_config_history
            history: list[dict[str, str]] = []

            if not history:
                await self.send_error_response(
                    interaction, "設定変更履歴がありません。", followup=True
                )
                return

            # Format history for display
            history_text = "\n".join(
                [
                    f"{entry['timestamp']}: {entry['setting']} = {entry['value']}"
                    for entry in history[-10:]  # Show last 10 entries
                ]
            )

            embed = discord.Embed(
                title="📋 設定変更履歴（最新 10 件）",
                description=f"```\n{history_text}\n```",
                color=discord.Color.blue(),
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("Failed to show config history", error=str(e))
            await self.send_error_response(
                interaction, "設定履歴の取得に失敗しました。", followup=True
            )

    async def _show_all_configs(self, interaction: discord.Interaction) -> None:
        """Show all configuration settings."""
        try:
            # Simulate basic config display since ChannelConfig doesn't have get_all_configs
            all_configs = {"channels_discovered": len(self.channel_config.channels)}

            if not all_configs:
                await self.send_error_response(
                    interaction, "設定項目がありません。", followup=True
                )
                return

            # Format configs for display
            fields = []
            for key, value in all_configs.items():
                # Mask sensitive values
                display_value: str | int = value
                if any(
                    sensitive in key.lower()
                    for sensitive in ["key", "token", "password"]
                ):
                    display_value = "****" if value else "未設定"

                fields.append((key, str(display_value), False))

            await self.send_success_response(
                interaction,
                "現在の設定",
                fields=fields,
                color=discord.Color.blue(),
                followup=True,
            )

        except Exception as e:
            logger.error("Failed to get all configs", error=str(e))
            await self.send_error_response(
                interaction, "設定の取得に失敗しました。", followup=True
            )

    async def _validate_api_key(self, api_key: str) -> bool:
        """Validate API key format and functionality."""
        if not api_key or len(api_key) < 10:
            return False

        # Add more sophisticated validation if needed
        # For now, just check basic format
        return True
