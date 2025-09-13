"""
Discord bot client implementation
"""

import os
from datetime import datetime, timedelta
from typing import Any

import discord
from discord.ext import commands

from src.bot.channel_config import ChannelConfig
from src.bot.handlers import MessageHandler
from src.bot.metrics import APIUsageMonitor, SystemMetrics
from src.config import get_settings
from src.utils.mixins import LoggerMixin


class DiscordBot(LoggerMixin):
    """Main Discord bot client"""

    def __init__(
        self,
        ai_processor,
        vault_manager,
        note_template: str,
        daily_integration,
        template_engine,
        note_analyzer,
        speech_processor=None,
    ) -> None:
        # Initialize components first
        self.channel_config = ChannelConfig()

        # 🔧 FIX: 同じ ChannelConfig インスタンスを MessageHandler に渡す
        # Create MessageHandler with all required dependencies and shared ChannelConfig
        self.message_handler = MessageHandler(
            ai_processor=ai_processor,
            obsidian_manager=vault_manager,
            note_template=note_template,
            daily_integration=daily_integration,
            template_engine=template_engine,
            note_analyzer=note_analyzer,
            speech_processor=speech_processor,
        )
        # Set channel config after initialization
        self.message_handler.channel_config = self.channel_config

        self.settings = get_settings()

        # Track bot state
        self.is_ready = False
        self.start_time: datetime | None = None
        self.last_activity: datetime | None = None

        # Initialize monitoring components
        self.system_metrics = SystemMetrics()
        self.api_usage_monitor = APIUsageMonitor()

        # Create Discord bot instance first
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        intents.guild_messages = True

        self.bot = commands.Bot(
            command_prefix="!",
            intents=intents,
            help_command=None,
        )

        # Initialize notification system with bot and channel config
        from src.bot.notification_system import NotificationSystem

        self.notification_system = NotificationSystem(self.bot, self.channel_config)

        # Setup event handlers
        self._setup_event_handlers()

        # Note: setup_commands is async - will be called in event handler

    def _setup_event_handlers(self) -> None:
        """Setup Discord bot event handlers"""

        @self.bot.event
        async def on_ready() -> None:
            """Bot ready event handler"""
            try:
                self.logger.info(f"Bot logged in as {self.bot.user}")
                self.is_ready = True
                self.start_time = datetime.now()
                self.last_activity = datetime.now()

                # Setup channel configuration and commands
                guild_id = int(str(self.settings.discord_guild_id))
                guild = discord.utils.get(self.bot.guilds, id=guild_id)
                if guild:
                    # Initialize ChannelConfig with guild channels
                    await self.channel_config.initialize_channels(guild)
                    self.logger.info(
                        f"ChannelConfig initialized with channels from guild: {guild.name}"
                    )

                    # Import here to avoid circular imports
                    from src.bot.commands import (
                        setup_commands,
                        setup_integration_commands,
                    )

                    try:
                        await setup_commands(self.bot, self.channel_config)
                        self.logger.info("基本コマンド登録完了")
                    except Exception as e:
                        self.logger.error(f"基本コマンド登録失敗: {e}", exc_info=True)

                    # IntegrationCommands を安全に登録
                    try:
                        await setup_integration_commands(self.bot, self.settings)
                        self.logger.info("IntegrationCommands 登録完了")
                    except Exception as e:
                        self.logger.error(
                            f"IntegrationCommands 登録失敗: {e}", exc_info=True
                        )

                    # Initialize lifelog system
                    try:
                        await self.message_handler.initialize_lifelog(self.settings)

                        # Register lifelog commands if available
                        if self.message_handler.lifelog_commands:
                            await (
                                self.message_handler.lifelog_commands.register_commands(
                                    self.bot
                                )
                            )
                            self.logger.info("ライフログコマンドを登録しました")

                    except Exception as e:
                        self.logger.error(f"ライフログ初期化失敗: {e}", exc_info=True)

                    # Slash Commands を Discord に同期（全コマンド登録後）
                    try:
                        # 登録済みコマンド数を確認
                        total_commands = len(self.bot.tree.get_commands())
                        guild_commands = len(self.bot.tree.get_commands(guild=guild))
                        self.logger.info(
                            f"同期前の状況 - グローバルコマンド: {total_commands}, ギルドコマンド: {guild_commands}"
                        )

                        self.logger.info("Discord に Slash Commands を同期中...")
                        # まずグローバルコマンドとして同期を試す
                        synced = await self.bot.tree.sync()
                        self.logger.info(
                            f"✅ {len(synced)} 個の Slash Commands を同期しました"
                        )

                        # 同期されたコマンドの詳細をログ出力
                        if synced:
                            command_names = [cmd.name for cmd in synced]
                            self.logger.info(f"同期されたコマンド: {command_names}")
                        else:
                            self.logger.warning("同期されたコマンドがありません")

                    except Exception as e:
                        self.logger.error(
                            f"❌ Slash Commands 同期失敗: {e}", exc_info=True
                        )

                    self.logger.info(f"Connected to guild: {guild.name}")
                else:
                    self.logger.error(f"Guild with ID {guild_id} not found")

            except Exception as e:
                self.logger.error(
                    f"on_ready イベントで予期しないエラー: {e}", exc_info=True
                )

        @self.bot.event
        async def on_message(message: discord.Message) -> None:
            """Message event handler"""
            from ..utils.logger import secure_log_message_content

            # Secure debug logging
            channel_name = getattr(message.channel, "name", f"DM-{message.channel.id}")
            log_info = secure_log_message_content(
                content=message.content or "",
                author=str(message.author),
                channel=channel_name,
            )

            self.logger.info("Message received", **log_info)

            # Detailed user identification debug
            self.logger.debug(
                "Message author details",
                author_id=message.author.id,
                bot_user_id=self.bot.user.id if self.bot.user else None,
                is_bot_message=message.author == self.bot.user,
            )

            # Temporarily disabled for testing - allow bot's own messages to be processed
            # if message.author == self.bot.user:
            #     self.logger.debug("Ignoring message from bot itself")
            #     return

            self.last_activity = datetime.now()
            self.system_metrics.increment_message_count()

            try:
                self.logger.debug(
                    "Processing message",
                    message_id=message.id,
                    channel_id=message.channel.id,
                )
                # Process message through the message handler
                await self.message_handler.process_message(message)
                self.system_metrics.increment_ai_success()
                self.logger.debug(
                    "Message processed successfully", message_id=message.id
                )

            except Exception as e:
                self.logger.error(
                    "Error processing message",
                    error=str(e),
                    message_id=message.id,
                    channel=channel_name,
                    exc_info=True,
                )
                self.system_metrics.increment_ai_failure()
                self.system_metrics.add_error(
                    {
                        "type": "message_processing",
                        "error": str(e),
                        "message_id": message.id,
                        "channel": channel_name,
                    }
                )

            # Process bot commands
            await self.bot.process_commands(message)

        @self.bot.event
        async def on_error(event: str, *args: Any, **kwargs: Any) -> None:
            """Global error handler"""
            self.logger.error(f"Discord event error: {event}")
            self.system_metrics.add_error(
                {
                    "type": "discord_event",
                    "event": event,
                    "args": str(args),
                    "kwargs": str(kwargs),
                }
            )

        @self.bot.event
        async def on_command_error(
            ctx: commands.Context, error: commands.CommandError
        ) -> None:
            """Command error handler"""
            self.logger.error(f"Command error: {error}")
            self.system_metrics.add_error(
                {
                    "type": "command_error",
                    "command": ctx.command.name if ctx.command else "unknown",
                    "error": str(error),
                    "user": str(ctx.author),
                }
            )

            if isinstance(error, commands.CommandNotFound):
                await ctx.send(
                    "❌ コマンドが見つかりません。`!help` で利用可能なコマンドを確認してください。"
                )
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"❌ 必要な引数が不足しています: {error.param}")
            elif isinstance(error, commands.BadArgument):
                await ctx.send(f"❌ 引数の形式が正しくありません: {error}")
            else:
                await ctx.send(f"❌ コマンドの実行中にエラーが発生しました: {error}")

    async def run_async(self) -> None:
        """Run the bot asynchronously"""
        try:
            # Debug: Token length and format
            token_str = str(self.settings.discord_bot_token)
            actual_secret_value = self.settings.discord_bot_token.get_secret_value()
            self.logger.info(
                f"🔍 DEBUG: Token length: {len(token_str)}, starts with: {token_str[:20]}..."
            )
            self.logger.info(
                f"🔍 DEBUG: Actual token length: {len(actual_secret_value)}, first 20 chars: {actual_secret_value[:20]}..."
            )
            self.logger.info(
                f"🔍 DEBUG: Environment variable raw value: {os.getenv('DISCORD_BOT_TOKEN', 'NOT_FOUND')[:20]}..."
            )

            # Debug: Discord.py version and settings
            import discord

            self.logger.info(f"🔍 DEBUG: Discord.py version: {discord.__version__}")
            self.logger.info(f"🔍 DEBUG: Bot intents: {self.bot.intents}")

            await self.bot.start(actual_secret_value)
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            self.logger.error(f"🔍 DEBUG: Exception type: {type(e).__name__}")
            raise

    def run(self) -> None:
        """Run the bot synchronously"""
        try:
            self.bot.run(self.settings.discord_bot_token.get_secret_value())
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            raise

    async def shutdown(self) -> None:
        """Gracefully shutdown the bot"""
        self.logger.info("Shutting down bot...")
        if self.bot.is_closed():
            return

        try:
            await self.bot.close()
            self.is_ready = False
            self.logger.info("Bot shutdown completed")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

    def get_uptime(self) -> timedelta | None:
        """Get bot uptime"""
        if not self.start_time:
            return None
        return datetime.now() - self.start_time

    def get_status(self) -> dict[str, Any]:
        """Get bot status information"""
        uptime = self.get_uptime()
        return {
            "is_ready": self.is_ready,
            "uptime": str(uptime) if uptime else None,
            "uptime_seconds": uptime.total_seconds() if uptime else None,
            "last_activity": self.last_activity.isoformat()
            if self.last_activity
            else None,
            "guild_count": len(self.bot.guilds) if self.bot.guilds else 0,
            "user_count": sum(guild.member_count for guild in self.bot.guilds)
            if self.bot.guilds
            else 0,
            "metrics": self.system_metrics.get_metrics_summary(),
            "api_usage": self.api_usage_monitor.get_usage_status(),
        }

    async def get_guild_info(self) -> dict[str, Any] | None:
        """Get guild information"""
        if not self.bot.guilds:
            return None

        guild = self.bot.guilds[0]  # Assuming single guild
        return {
            "id": guild.id,
            "name": guild.name,
            "member_count": guild.member_count,
            "channel_count": len(guild.channels),
            "role_count": len(guild.roles),
            "emoji_count": len(guild.emojis),
            "boost_level": guild.premium_tier,
            "boost_count": guild.premium_subscription_count,
        }

    def is_api_available(self, api_name: str) -> bool:
        """Check if API is available for use"""
        return self.api_usage_monitor.is_api_available(api_name)

    def record_api_usage(self, api_name: str) -> bool:
        """Record API usage and check limits"""
        return self.api_usage_monitor.record_api_usage(api_name)

    def add_performance_metric(self, operation: str, duration: float) -> None:
        """Add performance metric"""
        self.system_metrics.add_performance_data(operation, duration)

    def get_metrics_summary(self) -> dict[str, Any]:
        """Get metrics summary"""
        return self.system_metrics.get_metrics_summary()

    def get_api_usage_status(self) -> dict[str, Any]:
        """Get API usage status"""
        return self.api_usage_monitor.get_usage_status()

    async def send_notification(
        self, message: str, channel_type: str = "notifications"
    ) -> bool:
        """Send notification to specified channel"""
        try:
            channel = self.channel_config.get_channel(channel_type)
            if channel:
                await channel.send(message)
                return True
            else:
                self.logger.warning(f"Channel '{channel_type}' not found")
                return False
        except Exception as e:
            self.logger.error(f"Failed to send notification: {e}")
            return False

    async def update_presence(self, activity_name: str | None = None) -> None:
        """Update bot presence/status"""
        try:
            if activity_name:
                activity = discord.Activity(
                    type=discord.ActivityType.playing, name=activity_name
                )
            else:
                # Default status based on metrics
                metrics = self.system_metrics.get_metrics_summary()
                processed = metrics["total_messages_processed"]
                activity = discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{processed} messages processed",
                )

            await self.bot.change_presence(activity=activity)
        except Exception as e:
            self.logger.error(f"Failed to update presence: {e}")

    def get_bot_user(self) -> discord.ClientUser | None:
        """Get bot user object"""
        return self.bot.user

    def get_guilds(self) -> list[discord.Guild]:
        """Get list of connected guilds"""
        return list(self.bot.guilds)

    async def get_channel_by_name(
        self, channel_name: str
    ) -> discord.TextChannel | None:
        """Get channel by name"""
        for guild in self.bot.guilds:
            for channel in guild.channels:
                if (
                    isinstance(channel, discord.TextChannel)
                    and channel.name == channel_name
                ):
                    return channel
        return None

    async def get_channel_by_id(self, channel_id: int) -> discord.TextChannel | None:
        """Get channel by ID"""
        channel = self.bot.get_channel(channel_id)
        return channel if isinstance(channel, discord.TextChannel) else None

    def is_user_admin(self, user: discord.Member) -> bool:
        """For personal use, all users are admins"""
        return True

    def is_user_moderator(self, user: discord.Member) -> bool:
        """For personal use, all users are moderators"""
        return True

    async def cleanup_old_messages(self, channel_name: str, days: int = 30) -> int:
        """Clean up old messages in a channel"""
        try:
            channel = await self.get_channel_by_name(channel_name)
            if not channel:
                self.logger.warning(f"Channel '{channel_name}' not found for cleanup")
                return 0

            cutoff_date = datetime.now() - timedelta(days=days)
            deleted_count = 0

            async for message in channel.history(limit=None):
                if message.created_at < cutoff_date:
                    try:
                        await message.delete()
                        deleted_count += 1
                    except discord.NotFound:
                        # Message already deleted
                        pass
                    except discord.Forbidden:
                        self.logger.warning(
                            f"No permission to delete message {message.id}"
                        )
                        break

            self.logger.info(
                f"Cleaned up {deleted_count} old messages from #{channel_name}"
            )
            return deleted_count

        except Exception as e:
            self.logger.error(f"Error during message cleanup: {e}")
            return 0

    async def backup_channel_messages(
        self, channel_name: str, limit: int = 1000
    ) -> list[dict[str, Any]]:
        """Backup messages from a channel"""
        try:
            channel = await self.get_channel_by_name(channel_name)
            if not channel:
                self.logger.warning(f"Channel '{channel_name}' not found for backup")
                return []

            messages = []
            async for message in channel.history(limit=limit):
                from ..utils.logger import sanitize_log_content

                messages.append(
                    {
                        "id": message.id,
                        "author": str(message.author),
                        "content": sanitize_log_content(
                            message.content or "", max_length=200
                        ),
                        "content_length": len(message.content or ""),
                        "timestamp": message.created_at.isoformat(),
                        "attachments": [att.url for att in message.attachments],
                        "embeds": len(message.embeds),
                    }
                )

            self.logger.info(f"Backed up {len(messages)} messages from #{channel_name}")
            return messages

        except Exception as e:
            self.logger.error(f"Error during message backup: {e}")
            return []

    def get_connection_status(self) -> dict[str, Any]:
        """Get detailed connection status"""
        return {
            "is_ready": self.is_ready,
            "is_closed": self.bot.is_closed()
            if hasattr(self.bot, "is_closed")
            else False,
            "latency": round(self.bot.latency * 1000, 2) if self.bot.latency else None,
            "shard_count": self.bot.shard_count,
            "user": str(self.bot.user) if self.bot.user else None,
            "guilds": len(self.bot.guilds),
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "last_activity": self.last_activity.isoformat()
            if self.last_activity
            else None,
        }
