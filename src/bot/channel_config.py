"""
Channel configuration and categorization for Discord bot
"""

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from src.bot.client import DiscordBot

from src.utils.mixins import LoggerMixin


class ChannelCategory(Enum):
    """Simplified channel categories"""

    CAPTURE = "capture"  # memo （統合：テキスト・音声・ファイル）
    SYSTEM = "system"  # notifications, commands  # notifications, commands


@dataclass
class ChannelInfo:
    """Information about a Discord channel"""

    id: int
    name: str
    category: ChannelCategory
    description: str


class ChannelConfig(LoggerMixin):
    """Manages Discord channel configuration and categorization"""

    def __init__(self) -> None:
        """Initialize with empty channel config - will be populated when bot is set"""
        super().__init__()
        self.channels: dict[int, ChannelInfo] = {}
        self.bot: DiscordBot | None = None
        self.guild: discord.Guild | None = None

        # Simplified channel names for auto-discovery (3 channels only)
        self.standard_channel_names = {
            "memo": ChannelCategory.CAPTURE,  # 統合メイン入力チャンネル
            "notifications": ChannelCategory.SYSTEM,  # システム通知
            "commands": ChannelCategory.SYSTEM,  # ボットコマンド
        }

    async def set_bot(self, bot: "DiscordBot") -> None:
        """Set the bot instance and discover channels"""
        self.bot = bot
        # Get the guild from bot's client guilds
        self.guild = bot.client.guilds[0] if bot.client.guilds else None

        if self._discover_channels_by_names():
            self.logger.info("Successfully initialized channels using channel names")
        else:
            self.logger.warning("Failed to discover required channels by name")

    async def initialize_channels(self, guild: discord.Guild) -> None:
        """Initialize ChannelConfig with Discord guild channels"""
        self.guild = guild

        if self._discover_channels_by_names():
            self.logger.info(
                f"Successfully initialized channels from guild: {guild.name}"
            )
        else:
            self.logger.warning(
                f"Failed to discover required channels in guild: {guild.name}"
            )

    def _load_channel_config(self) -> dict[int, ChannelInfo]:
        """Load channel configuration from standard channel names"""
        # Return empty dict - channels will be discovered by name when bot is set
        return {}

    def _discover_channels_by_names(self) -> bool:
        """Discover channels by their standard names"""
        if not self.guild:
            self.logger.warning("No guild available for channel discovery")
            return False

        discovered_channels = {}
        required_channels = ["memo", "notifications", "commands"]
        found_required = 0

        for channel in self.guild.text_channels:
            channel_name = channel.name.lower().replace("-", "").replace("_", "")

            # Check for exact matches only
            if channel_name in self.standard_channel_names:
                category = self.standard_channel_names[channel_name]
                discovered_channels[channel.id] = ChannelInfo(
                    id=channel.id,
                    name=channel.name,
                    category=category,
                    description=f"Auto-discovered {category.value} channel",
                )
                self.logger.debug(
                    "Discovered channel",
                    channel_name=channel.name,
                    channel_id=channel.id,
                    category=category.value,
                )

                if channel_name in required_channels:
                    found_required += 1
            else:
                self.logger.debug(
                    "Channel ignored during discovery",
                    channel_name=channel_name,
                    standard_names=list(self.standard_channel_names.keys()),
                )

        # Update the channels dict
        self.channels.update(discovered_channels)

        # Check if we found the minimum required channels
        success = found_required >= len(required_channels)
        if success:
            self.logger.info(
                "Channel discovery completed",
                discovered=len(discovered_channels),
                required_found=found_required,
                required_total=len(required_channels),
            )
        else:
            self.logger.warning(
                f"Only found {found_required}/{len(required_channels)} required channels. "
                f"Please create channels: {', '.join(f'#{name}' for name in required_channels)}"
            )

        return success

    def get_channel_info(self, channel_id: int) -> ChannelInfo:
        """Get channel information by ID"""
        return self.channels.get(
            channel_id,
            ChannelInfo(
                id=channel_id,
                name="unknown",
                category=ChannelCategory.CAPTURE,  # Default to CAPTURE
                description="Unknown channel",
            ),
        )

    def is_monitored_channel(self, channel_id: int) -> bool:
        """Check if a channel is being monitored by the bot"""
        return channel_id in self.channels

    def get_channels_by_category(self, category: ChannelCategory) -> set[int]:
        """Get all channel IDs for a specific category"""
        return {
            channel_id
            for channel_id, info in self.channels.items()
            if info.category == category
        }

    def get_channel_by_name(self, name: str) -> int | None:
        """Get channel ID by standard name"""
        name_lower = name.lower().replace("-", "").replace("_", "")
        for channel_id, info in self.channels.items():
            channel_name = info.name.lower().replace("-", "").replace("_", "")
            if channel_name == name_lower:
                return channel_id
        return None

    def get_channel(self, channel_name: str) -> discord.TextChannel | None:
        """Get channel object by name."""
        channel_id = self.get_channel_by_name(channel_name)
        if channel_id is None or self.guild is None:
            return None

        channel = self.guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel
        return None

    def get_all_monitored_channel_names(self) -> list[str]:
        """Get list of all monitored channel names"""
        return [info.name for info in self.channels.values()]

    def get_channel_purpose(self, channel_id: int) -> str:
        """Get human-readable purpose of a channel"""
        info = self.get_channel_info(channel_id)
        return f"{info.category.value.title()}: {info.description}"

    def get_memo_channel(self) -> int | None:
        """Get unified memo channel ID"""
        return self.get_channel_by_name("memo")

    def get_capture_channels(self) -> set[int]:
        """Get capture category channel IDs"""
        return self.get_channels_by_category(ChannelCategory.CAPTURE)

    def get_system_channels(self) -> set[int]:
        """Get system category channel IDs"""
        return self.get_channels_by_category(ChannelCategory.SYSTEM)

    def __str__(self) -> str:
        """String representation of channel configuration"""
        return f"ChannelConfig({len(self.channels)} channels configured)"

    def __repr__(self) -> str:
        """Detailed representation of channel configuration"""
        channels_by_category: dict[ChannelCategory, list[str]] = {}
        for info in self.channels.values():
            if info.category not in channels_by_category:
                channels_by_category[info.category] = []
            channels_by_category[info.category].append(info.name)

        return f"ChannelConfig({channels_by_category})"
