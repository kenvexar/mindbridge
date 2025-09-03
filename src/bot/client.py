"""
Discord bot client implementation
"""

from datetime import datetime, timedelta
from typing import Any

import discord
from discord.ext import commands

from src.bot.channel_config import ChannelConfig
from src.bot.commands import setup_commands
from src.bot.handlers import MessageHandler
from src.config.settings import get_settings
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

        # 🔧 FIX: 同一の ChannelConfig インスタンスを MessageHandler に渡す
        # Create MessageHandler with all required dependencies and shared ChannelConfig
        self.message_handler = MessageHandler(
            ai_processor=ai_processor,
            obsidian_manager=vault_manager,
            note_template=note_template,
            daily_integration=daily_integration,
            template_engine=template_engine,
            note_analyzer=note_analyzer,
            speech_processor=speech_processor,
            channel_config=self.channel_config,  # 同一インスタンスを共有
        )

        self.settings = get_settings()

        # Track bot state
        self.is_ready = False
        self.guild: discord.Guild | None = None
        self._start_time = datetime.now()

        # Initialize monitoring systems
        self.system_metrics = SystemMetrics()
        self.api_usage_monitor = APIUsageMonitor()

        # Initialize reminder systems list (actual initialization after client setup)
        self.reminder_systems: list[Any] = []

        # Initialize notification system
        self.notification_system = None  # Will be initialized after client setup
        self.config_manager = None  # Will be initialized after client setup

        # Initialize client based on mock mode
        if self.settings.is_mock_mode:
            self.logger.info("Initializing Discord bot in MOCK mode")
            from src.bot.mock_client import MockDiscordBot

            self.client: commands.Bot | Any = (
                MockDiscordBot()
            )  # Use Any for MockDiscordBot
            self.client._start_time = self._start_time

            # Register mock event handlers
            self.client.on_ready(self._on_ready_mock)
            self.client.on_message(self._on_message_mock)
            self.client.on_error(self._on_error_mock)
        else:
            self.logger.info("Initializing Discord bot in PRODUCTION mode")
            # Configure Discord intents
            intents = discord.Intents.default()
            intents.message_content = True  # Required to read message content
            intents.guilds = True
            intents.guild_messages = True
            intents.voice_states = True  # For voice memo processing

            # Initialize bot client
            self.client = commands.Bot(
                command_prefix="/",
                intents=intents,
                help_command=None,  # We'll implement custom help
            )
            # Add start time to client using type ignore to avoid type checking
            self.client._start_time = self._start_time  # type: ignore[attr-defined]

            # Register event handlers
            self._register_events()

        # Initialize reminder systems after client is ready
        self._initialize_reminder_systems()

        # Initialize notification system after client is ready
        from src.bot.notification_system import NotificationSystem

        self.notification_system = NotificationSystem(self.client, self.channel_config)

        # Initialize configuration management system
        from src.bot.config_manager import DynamicConfigManager

        self.config_manager = DynamicConfigManager(
            self.client,  # type: ignore[arg-type]
            self.notification_system,
        )

        # Initialize backup and review systems
        from src.bot.backup_system import DataBackupSystem
        from src.bot.review_system import AutoReviewSystem

        self.backup_system = DataBackupSystem(self.client, self.notification_system)  # type: ignore[arg-type]
        self.review_system = AutoReviewSystem(self.client, self.notification_system)  # type: ignore[arg-type]

        self.logger.info(
            "Discord bot initialized", mock_mode=self.settings.is_mock_mode
        )

    def _register_events(self) -> None:
        """Register Discord event handlers"""

        @self.client.event
        async def on_ready() -> None:
            """Handle bot ready event"""
            settings = get_settings()
            self.logger.info(
                "Bot connected to Discord",
                bot_user=str(self.client.user),
                guild_count=len(self.client.guilds),
            )

            # Get the configured guild
            if settings.discord_guild_id:
                self.guild = self.client.get_guild(settings.discord_guild_id)
            else:
                self.guild = None

            if not self.guild:
                self.logger.error(
                    "Configured guild not found", guild_id=settings.discord_guild_id
                )
                return

            self.logger.info(
                "Connected to guild",
                guild_name=self.guild.name,
                guild_id=self.guild.id,
                member_count=self.guild.member_count,
            )

            # 🔧 FIX: Initialize channel configuration with bot instance
            await self.channel_config.set_bot(self)

            # Validate channel configuration
            await self._validate_channels()

            # Setup commands
            await setup_commands(self.client, self.channel_config)

            # Setup monitoring integration
            self.message_handler.set_monitoring_systems(
                self.system_metrics, self.api_usage_monitor
            )

            # Initialize MessageHandler async components (including default templates)
            await self.message_handler.initialize()

            # Start reminder systems
            await self._start_reminder_systems()

            # Start backup and review systems
            if self.backup_system:
                await self.backup_system.start()

                # GitHub 同期: アプリ起動時に vault をリストア
                try:
                    if (
                        hasattr(self.backup_system, "github_sync")
                        and self.backup_system.github_sync.is_configured
                    ):
                        await self.backup_system.github_sync.setup_git_repository()
                        restore_success = (
                            await self.backup_system.github_sync.sync_from_github()
                        )
                        if restore_success:
                            self.logger.info("Successfully restored vault from GitHub")
                        else:
                            self.logger.warning("Failed to restore vault from GitHub")
                except Exception as e:
                    self.logger.error(f"GitHub restore error during startup: {e}")

            if self.review_system:
                await self.review_system.start()

            self.is_ready = True
            self.logger.info("Bot is ready and operational")

            # Send system startup notification
            if self.notification_system:
                await self.notification_system.send_system_event_notification(
                    event_type="Bot Startup",
                    description="MindBridge が正常に起動しました。",
                    system_info={
                        "mode": "Production Mode",
                        "guild": self.guild.name,
                        "guild_id": self.guild.id,
                        "member_count": self.guild.member_count,
                        "channels_validated": True,
                        "reminder_systems": len(self.reminder_systems),
                        "startup_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )

        @self.client.event
        async def on_message(message: discord.Message) -> None:
            """Handle incoming messages"""
            # DEBUG: Add temporary logging to verify message reception
            self.logger.info(
                "🔍 DEBUG: Message received in on_message",
                message_id=message.id,
                author=str(message.author),
                channel_name=getattr(message.channel, "name", "unknown"),
                channel_id=message.channel.id,
                content_preview=message.content[:50] + "..."
                if len(message.content) > 50
                else message.content,
                is_bot=message.author.bot,
                bot_ready=self.is_ready,
            )

            if not self.is_ready:
                self.logger.warning("Bot not ready, skipping message processing")
                return

            try:
                # Process message through handler
                self.logger.info("🚀 DEBUG: Calling message_handler.process_message")
                result = await self.message_handler.process_message(message)
                self.logger.info(f"🔄 DEBUG: Message handler returned: {result}")

                if result:
                    self.logger.debug(
                        "Message processed successfully",
                        message_id=message.id,
                        channel_id=message.channel.id,
                    )

                    # Send processing complete notification if significant processing occurred
                    if result.get("ai_processed") or result.get("note_created"):
                        await self._send_processing_notification(message, result)

                # Process commands
                await self.client.process_commands(message)

            except Exception as e:
                self.logger.error(
                    "Error processing message",
                    message_id=message.id,
                    channel_id=message.channel.id,
                    error=str(e),
                    exc_info=True,
                )

                # Send error notification for critical errors
                if self.notification_system:
                    await self.notification_system.send_error_notification(
                        error_type="Message Processing Error",
                        error_message=f"メッセージ処理中にエラーが発生しました: {str(e)[:200]}",
                        context={
                            "message_id": message.id,
                            "channel_id": message.channel.id,
                            "channel_name": getattr(message.channel, "name", "unknown"),
                            "author": str(message.author),
                            "content_length": len(message.content),
                        },
                    )

        @self.client.event
        async def on_error(event: str, *args: Any, **kwargs: Any) -> None:
            """Handle Discord client errors"""
            self.logger.error(
                "Discord client error",
                discord_event=event,
                args=args,
                kwargs=kwargs,
                exc_info=True,
            )

            # Send system error notification
            if self.notification_system:
                await self.notification_system.send_error_notification(
                    error_type="Discord Client Error",
                    error_message=f"Discord クライアントでエラーが発生しました: {event}",
                    context={
                        "event": event,
                        "args": str(args)[:300],
                        "kwargs": str(kwargs)[:300],
                    },
                )

        @self.client.event
        async def on_command_error(
            ctx: commands.Context[commands.Bot], error: commands.CommandError
        ) -> None:
            """Handle command errors"""
            self.logger.error(
                "Command error",
                command=ctx.command.name if ctx.command else "unknown",
                author=str(ctx.author),
                channel_id=ctx.channel.id,
                error=str(error),
                exc_info=True,
            )

            # Send command error notification for serious errors
            if self.notification_system and not isinstance(
                error, commands.CommandNotFound | commands.MissingRequiredArgument
            ):
                await self.notification_system.send_error_notification(
                    error_type="Command Error",
                    error_message=f"コマンド実行中にエラーが発生しました: {str(error)[:200]}",
                    context={
                        "command": ctx.command.name if ctx.command else "unknown",
                        "author": str(ctx.author),
                        "channel": getattr(ctx.channel, "name", "unknown"),
                        "channel_id": ctx.channel.id,
                    },
                    user_mention=ctx.author.mention,
                )

    async def _send_processing_notification(
        self, message: discord.Message, result: dict
    ) -> None:
        """Send message processing complete notification"""
        try:
            if self.notification_system and result.get("note_path"):
                processing_details = {
                    "processing_time": result.get("processing_time", "不明"),
                    "ai_processed": result.get("ai_processed", False),
                    "categories": result.get("ai_categories", []),
                    "confidence": result.get("ai_confidence"),
                    "word_count": (
                        len(message.content.split()) if message.content else 0
                    ),
                }

                await self.notification_system.send_processing_complete_notification(
                    message_id=message.id,
                    channel_name=getattr(message.channel, "name", "unknown"),
                    note_path=result["note_path"],
                    processing_details=processing_details,
                )
        except Exception as e:
            self.logger.warning("Failed to send processing notification", error=str(e))

    async def _on_ready_mock(self) -> None:
        """Handle mock bot ready event"""
        self.logger.info("Mock bot ready event triggered")

        # Set mock guild
        if hasattr(self.client, "guild"):
            self.guild = self.client.guild
        else:
            self.guild = None

        if self.guild:
            self.logger.info(
                "Connected to mock guild",
                guild_name=self.guild.name,
                guild_id=self.guild.id,
                member_count=self.guild.member_count,
            )
        else:
            self.logger.warning("No guild available in mock mode")

        # Validate mock channels
        await self._validate_channels_mock()

        # Setup monitoring integration
        self.message_handler.set_monitoring_systems(
            self.system_metrics, self.api_usage_monitor
        )

        # Initialize MessageHandler async components (including default templates)
        await self.message_handler.initialize()

        # Start reminder systems
        await self._start_reminder_systems()

        # Start backup and review systems
        if self.backup_system:
            await self.backup_system.start()
        if self.review_system:
            await self.review_system.start()

        self.is_ready = True
        self.logger.info("Mock bot is ready and operational")

        # Send system startup notification
        if self.notification_system:
            await self.notification_system.send_system_event_notification(
                event_type="Bot Startup",
                description="MindBridge が正常に起動しました（モックモード）。",
                system_info={
                    "mode": "Mock Mode",
                    "guild": self.guild.name if self.guild else "N/A",
                    "channels_validated": True,
                    "reminder_systems": len(self.reminder_systems),
                    "startup_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
            )

    async def _on_message_mock(self, message: Any) -> None:
        """Handle mock incoming messages"""
        if not self.is_ready:
            return

        try:
            # Process message through handler
            result = await self.message_handler.process_message(message)

            if result:
                self.logger.debug(
                    "Mock message processed successfully",
                    message_id=message.id,
                    channel_id=message.channel_id,
                )

            # Process commands
            await self.client.process_commands(message)

        except Exception as e:
            self.logger.error(
                "Error processing mock message",
                message_id=message.id,
                channel_id=message.channel_id,
                error=str(e),
                exc_info=True,
            )

    async def _on_error_mock(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Handle mock Discord client errors"""
        self.logger.error(
            "Mock Discord client error",
            discord_event=event,
            args=args,
            kwargs=kwargs,
            exc_info=True,
        )

    async def _validate_channels_mock(self) -> None:
        """Validate that all configured channels exist in the mock guild"""
        if not self.guild:
            return

        missing_channels = []

        for channel_id, channel_info in self.channel_config.channels.items():
            channel = self.client.get_channel(channel_id)
            if not channel:
                missing_channels.append(f"{channel_info.name} (ID: {channel_id})")
                self.logger.warning(
                    "Mock configured channel not found",
                    channel_name=channel_info.name,
                    channel_id=channel_id,
                )
            else:
                channel_name = getattr(channel, "name", "Private Channel")
                self.logger.debug(
                    "Mock channel validated",
                    channel_name=channel_name,
                    channel_id=channel_id,
                    category=channel_info.category.value,
                )

        if missing_channels:
            self.logger.warning(
                "Some mock configured channels are missing",
                missing_channels=missing_channels,
            )
        else:
            self.logger.info("All mock configured channels validated successfully")

    def _initialize_reminder_systems(self) -> None:
        """Initialize all reminder systems"""
        from src.finance import BudgetManager, ExpenseManager, SubscriptionManager
        from src.finance.reminder_system import FinanceReminderSystem
        from src.obsidian import ObsidianFileManager
        from src.tasks import ScheduleManager, TaskManager
        from src.tasks.reminder_system import TaskReminderSystem

        try:
            # Create basic obsidian manager for reminder systems
            obsidian_manager = ObsidianFileManager(self.settings.obsidian_vault_path)

            # Initialize financial reminder system
            file_manager = obsidian_manager
            expense_manager = ExpenseManager(file_manager)
            # subscription_manager requires SubscriptionManager
            subscription_manager = SubscriptionManager(file_manager)
            budget_manager = BudgetManager(file_manager, expense_manager)

            self.finance_reminder_system = FinanceReminderSystem(
                bot=self.client,  # Use self.client instead of self
                channel_config=self.channel_config,
                subscription_manager=subscription_manager,
                budget_manager=budget_manager,
            )
            self.reminder_systems.append(self.finance_reminder_system)

            # Initialize task reminder system
            task_manager = TaskManager(file_manager)
            schedule_manager = ScheduleManager(file_manager)

            self.task_reminder_system = TaskReminderSystem(
                bot=self.client,  # Use self.client instead of self
                channel_config=self.channel_config,
                task_manager=task_manager,
                schedule_manager=schedule_manager,
            )
            self.reminder_systems.append(self.task_reminder_system)

            # Initialize health analysis scheduler (if not in mock mode)
            if (
                not self.settings.is_mock_mode
                and self.settings.garmin_username
                and self.settings.garmin_password
            ):
                try:
                    from src.garmin import GarminClient
                    from src.health_analysis import (
                        HealthActivityIntegrator,
                        HealthDataAnalyzer,
                    )
                    from src.health_analysis.scheduler import HealthAnalysisScheduler
                    from src.obsidian import ObsidianFileManager
                    from src.obsidian.daily_integration import DailyNoteIntegration

                    # Initialize health analysis components
                    garmin_client = (
                        GarminClient()
                    )  # Credentials loaded from environment
                    health_analyzer = HealthDataAnalyzer()

                    # Create file manager for health integrator
                    obsidian_manager = ObsidianFileManager(
                        self.settings.obsidian_vault_path
                    )
                    health_integrator = HealthActivityIntegrator(obsidian_manager)
                    daily_integration = DailyNoteIntegration(obsidian_manager)

                    # Initialize HealthAnalysisScheduler with proper dependencies
                    self.health_scheduler = HealthAnalysisScheduler(
                        garmin_client=garmin_client,
                        analyzer=health_analyzer,
                        integrator=health_integrator,
                        daily_integration=daily_integration,
                    )
                    self.reminder_systems.append(self.health_scheduler)

                    self.logger.info(
                        "Health analysis scheduler initialized successfully"
                    )
                except ImportError as e:
                    self.logger.warning(f"Health analysis scheduler not available: {e}")
                except Exception as e:
                    self.logger.error(
                        f"Failed to initialize health analysis scheduler: {e}"
                    )
            else:
                self.logger.info(
                    "Health analysis scheduler skipped (mock mode or missing Garmin credentials)"
                )

            self.logger.info(
                "Reminder systems initialized", count=len(self.reminder_systems)
            )

        except Exception as e:
            self.logger.error(
                "Failed to initialize reminder systems", error=str(e), exc_info=True
            )

    async def _start_reminder_systems(self) -> None:
        """Start all reminder systems"""
        if not self.reminder_systems:
            self.logger.warning("No reminder systems to start")
            return

        started_count = 0
        for system in self.reminder_systems:
            try:
                await system.start()
                started_count += 1
            except Exception as e:
                self.logger.error(
                    "Failed to start reminder system",
                    system=type(system).__name__,
                    error=str(e),
                    exc_info=True,
                )

        self.logger.info(
            "Reminder systems started",
            started=started_count,
            total=len(self.reminder_systems),
        )

    async def _stop_reminder_systems(self) -> None:
        """Stop all reminder systems"""
        if not self.reminder_systems:
            return

        stopped_count = 0
        for system in self.reminder_systems:
            try:
                await system.stop()
                stopped_count += 1
            except Exception as e:
                self.logger.error(
                    "Failed to stop reminder system",
                    system=type(system).__name__,
                    error=str(e),
                    exc_info=True,
                )

        self.logger.info(
            "Reminder systems stopped",
            stopped=stopped_count,
            total=len(self.reminder_systems),
        )

    async def _validate_channels(self) -> None:
        """Validate that all configured channels exist in the guild"""
        if not self.guild:
            return

        missing_channels = []

        for channel_id, channel_info in self.channel_config.channels.items():
            channel = self.guild.get_channel(channel_id)
            if not channel:
                missing_channels.append(f"{channel_info.name} (ID: {channel_id})")
                self.logger.warning(
                    "Configured channel not found",
                    channel_name=channel_info.name,
                    channel_id=channel_id,
                )
            else:
                self.logger.debug(
                    "Channel validated",
                    channel_name=channel.name,
                    channel_id=channel_id,
                    category=channel_info.category.value,
                )

        if missing_channels:
            self.logger.warning(
                "Some configured channels are missing",
                missing_channels=missing_channels,
            )
        else:
            self.logger.info("All configured channels validated successfully")

    async def start(self) -> None:
        """Start the Discord bot"""
        settings = get_settings()
        self.logger.info("Starting Discord bot")

        try:
            await self.client.start(settings.discord_bot_token.get_secret_value())
        except discord.LoginFailure:
            self.logger.error("Invalid Discord bot token")
            raise
        except Exception as e:
            self.logger.error(
                "Failed to start Discord bot", error=str(e), exc_info=True
            )
            raise

    async def stop(self) -> None:
        """Stop the Discord bot"""
        self.logger.info("Stopping Discord bot")

        # Stop reminder systems first
        await self._stop_reminder_systems()

        # Stop backup and review systems
        if hasattr(self, "backup_system") and self.backup_system:
            # GitHub 同期: アプリ終了時に vault をバックアップ
            try:
                if (
                    hasattr(self.backup_system, "github_sync")
                    and self.backup_system.github_sync.is_configured
                ):
                    backup_success = (
                        await self.backup_system.github_sync.sync_to_github(
                            "Bot shutdown backup"
                        )
                    )
                    if backup_success:
                        self.logger.info(
                            "Successfully backed up vault to GitHub during shutdown"
                        )
                    else:
                        self.logger.warning(
                            "Failed to backup vault to GitHub during shutdown"
                        )
            except Exception as e:
                self.logger.error(f"GitHub backup error during shutdown: {e}")

            await self.backup_system.stop()
        if hasattr(self, "review_system") and self.review_system:
            await self.review_system.stop()

        # Close Discord client
        await self.client.close()

    async def send_notification(self, message: str) -> None:
        """Send a notification message to the notifications channel"""
        if not self.is_ready or not self.guild:
            self.logger.warning("Bot not ready, cannot send notification")
            return

        # デフォルトの通知チャンネルのみ使用
        notifications_channel_id = self.channel_config.get_channel_by_name(
            "notifications"
        )
        channel = (
            self.guild.get_channel(notifications_channel_id)
            if notifications_channel_id
            else None
        )

        if not channel:
            self.logger.error("Notification channel not found")
            return

        try:
            if hasattr(channel, "send"):
                await channel.send(message)
            else:
                self.logger.error(
                    "Channel does not support sending messages",
                    channel_type=type(channel).__name__,
                )
                return
            self.logger.info(
                "Notification sent",
                channel_id=channel.id if channel else None,
                message_length=len(message),
            )
        except Exception as e:
            self.logger.error(
                "Failed to send notification",
                channel_id=channel.id if channel else None,
                error=str(e),
                exc_info=True,
            )


class SystemMetrics(LoggerMixin):
    """システムメトリクス収集とパフォーマンス監視"""

    def __init__(self) -> None:
        self.metrics: dict[str, Any] = {
            "total_messages_processed": 0,
            "successful_ai_requests": 0,
            "failed_ai_requests": 0,
            "api_usage_minutes": 0.0,
            "obsidian_files_created": 0,
            "errors_last_hour": 0,
            "warnings_last_hour": 0,
            "system_start_time": datetime.now(),
        }
        self.hourly_stats: dict[str, Any] = {}
        self.error_history: list[Any] = []
        self.performance_history: list[Any] = []

    def record_message_processed(self) -> None:
        """メッセージ処理の記録"""
        self.metrics["total_messages_processed"] += 1

    def record_ai_request(self, success: bool, processing_time_ms: int) -> None:
        """AI リクエストの記録"""
        if success:
            self.metrics["successful_ai_requests"] += 1
        else:
            self.metrics["failed_ai_requests"] += 1

        self.performance_history.append(
            {
                "timestamp": datetime.now(),
                "type": "ai_request",
                "success": success,
                "processing_time_ms": processing_time_ms,
            }
        )

    def record_api_usage(self, minutes: float) -> None:
        """API 使用時間の記録"""
        self.metrics["api_usage_minutes"] += minutes

    def record_file_created(self) -> None:
        """Obsidian ファイル作成の記録"""
        self.metrics["obsidian_files_created"] += 1

    def record_error(self, error_type: str, message: str) -> None:
        """エラーの記録"""
        self.metrics["errors_last_hour"] += 1
        self.error_history.append(
            {"timestamp": datetime.now(), "type": error_type, "message": message}
        )
        # 古いエラー履歴を削除（過去 1 時間のみ保持）
        cutoff = datetime.now() - timedelta(hours=1)
        self.error_history = [e for e in self.error_history if e["timestamp"] > cutoff]

    def record_warning(self, warning_type: str, message: str) -> None:
        """警告の記録"""
        self.metrics["warnings_last_hour"] += 1

    def get_system_health_status(self) -> dict:
        """システム健康状態の取得"""
        uptime = datetime.now() - self.metrics["system_start_time"]

        # 最近のパフォーマンス分析
        recent_performance = [
            p
            for p in self.performance_history
            if p["timestamp"] > datetime.now() - timedelta(hours=1)
        ]

        avg_response_time = 0
        if recent_performance:
            avg_response_time = sum(
                p["processing_time_ms"] for p in recent_performance
            ) / len(recent_performance)

        return {
            "system_uptime": str(uptime),
            "discord_status": "connected",
            "total_messages_processed": self.metrics["total_messages_processed"],
            "recent_errors": len(
                [
                    e
                    for e in self.error_history
                    if e["timestamp"] > datetime.now() - timedelta(hours=1)
                ]
            ),
            "recent_warnings": self.metrics["warnings_last_hour"],
            "avg_response_time_ms": int(avg_response_time),
            "ai_success_rate": (
                self.metrics["successful_ai_requests"]
                / max(
                    1,
                    self.metrics["successful_ai_requests"]
                    + self.metrics["failed_ai_requests"],
                )
            )
            * 100,
            "api_usage_minutes": self.metrics["api_usage_minutes"],
            "files_created": self.metrics["obsidian_files_created"],
            "performance_score": self._calculate_performance_score(),
        }

    def _calculate_performance_score(self) -> int:
        """パフォーマンススコアの計算（ 0-100 ）"""
        score = 100

        # エラー率による減点
        total_requests = (
            self.metrics["successful_ai_requests"] + self.metrics["failed_ai_requests"]
        )
        if total_requests > 0:
            error_rate = self.metrics["failed_ai_requests"] / total_requests
            score -= int(error_rate * 50)  # 最大 50 点減点

        # 最近のエラー数による減点
        recent_errors = len(self.error_history)
        if recent_errors > 10:
            score -= min(30, recent_errors - 10)  # 最大 30 点減点

        # 警告数による減点
        if self.metrics["warnings_last_hour"] > 5:
            score -= min(
                20, (self.metrics["warnings_last_hour"] - 5) * 2
            )  # 最大 20 点減点

        return max(0, score)

    def get_hourly_report(self) -> dict:
        """時間別レポートの生成"""
        current_hour = datetime.now().hour
        if str(current_hour) not in self.hourly_stats:
            self.hourly_stats[str(current_hour)] = {
                "messages": 0,
                "ai_requests": 0,
                "errors": 0,
                "files_created": 0,
                "start_time": datetime.now().replace(minute=0, second=0, microsecond=0),
            }

        return self.hourly_stats

    def reset_hourly_metrics(self) -> None:
        """時間別メトリクスのリセット"""
        self.metrics["errors_last_hour"] = 0
        self.metrics["warnings_last_hour"] = 0
        # 古いパフォーマンス履歴を削除
        cutoff = datetime.now() - timedelta(hours=24)
        self.performance_history = [
            p for p in self.performance_history if p["timestamp"] > cutoff
        ]


class APIUsageMonitor(LoggerMixin):
    """API 使用量の監視とダッシュボード"""

    def __init__(self) -> None:
        self.gemini_usage: dict[str, Any] = {"requests": 0, "tokens": 0, "errors": 0}
        self.speech_usage: dict[str, Any] = {"requests": 0, "minutes": 0.0, "errors": 0}
        self.daily_limits: dict[str, Any] = {
            "gemini_requests": 10000,
            "speech_minutes": 60.0,
        }
        self.monthly_usage: dict[str, Any] = {}
        self.usage_warnings_sent: set[str] = set()

    def track_gemini_usage(self, tokens: int, success: bool) -> None:
        """Gemini API 使用量の記録"""
        self.gemini_usage["requests"] += 1
        if success:
            self.gemini_usage["tokens"] += tokens
        else:
            self.gemini_usage["errors"] += 1

        self._check_usage_limits()

    def track_speech_usage(self, minutes: float, success: bool) -> None:
        """Speech API 使用量の記録"""
        self.speech_usage["requests"] += 1
        if success:
            self.speech_usage["minutes"] += minutes
        else:
            self.speech_usage["errors"] += 1

        self._check_usage_limits()

    def _check_usage_limits(self) -> None:
        """使用量制限のチェックと警告"""
        # Gemini API 制限チェック（ 80% に達した場合）
        gemini_usage_percent = (
            self.gemini_usage["requests"] / self.daily_limits["gemini_requests"]
        ) * 100
        if gemini_usage_percent >= 80 and "gemini_80" not in self.usage_warnings_sent:
            self.logger.warning(
                "Gemini API usage approaching limit",
                usage_percent=gemini_usage_percent,
                requests=self.gemini_usage["requests"],
                limit=self.daily_limits["gemini_requests"],
            )
            self.usage_warnings_sent.add("gemini_80")

        # Speech API 制限チェック（ 80% に達した場合）
        speech_usage_percent = (
            self.speech_usage["minutes"] / self.daily_limits["speech_minutes"]
        ) * 100
        if speech_usage_percent >= 80 and "speech_80" not in self.usage_warnings_sent:
            self.logger.warning(
                "Speech API usage approaching limit",
                usage_percent=speech_usage_percent,
                minutes=self.speech_usage["minutes"],
                limit=self.daily_limits["speech_minutes"],
            )
            self.usage_warnings_sent.add("speech_80")

    def get_usage_dashboard(self) -> dict:
        """API 使用量ダッシュボードデータの取得"""
        return {
            "gemini_api": {
                "requests_used": self.gemini_usage["requests"],
                "requests_limit": self.daily_limits["gemini_requests"],
                "usage_percentage": (
                    self.gemini_usage["requests"] / self.daily_limits["gemini_requests"]
                )
                * 100,
                "tokens_processed": self.gemini_usage["tokens"],
                "error_count": self.gemini_usage["errors"],
                "success_rate": (
                    (self.gemini_usage["requests"] - self.gemini_usage["errors"])
                    / max(1, self.gemini_usage["requests"])
                )
                * 100,
            },
            "speech_api": {
                "minutes_used": self.speech_usage["minutes"],
                "minutes_limit": self.daily_limits["speech_minutes"],
                "usage_percentage": (
                    self.speech_usage["minutes"] / self.daily_limits["speech_minutes"]
                )
                * 100,
                "requests_made": self.speech_usage["requests"],
                "error_count": self.speech_usage["errors"],
                "success_rate": (
                    (self.speech_usage["requests"] - self.speech_usage["errors"])
                    / max(1, self.speech_usage["requests"])
                )
                * 100,
            },
        }

    def reset_daily_usage(self) -> None:
        """日次使用量のリセット"""
        self.gemini_usage = {"requests": 0, "tokens": 0, "errors": 0}
        self.speech_usage = {"requests": 0, "minutes": 0.0, "errors": 0}
        self.usage_warnings_sent.clear()
        self.logger.info("Daily API usage metrics reset")

    def export_usage_report(self) -> dict:
        """使用量レポートのエクスポート"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "period": "daily",
            "apis": self.get_usage_dashboard(),
            "summary": {
                "total_requests": self.gemini_usage["requests"]
                + self.speech_usage["requests"],
                "total_errors": self.gemini_usage["errors"]
                + self.speech_usage["errors"],
                "cost_estimation": self._estimate_costs(),
            },
        }
        return report

    def _estimate_costs(self) -> dict:
        """コスト見積もり（概算）"""
        # Google Cloud Speech-to-Text: $0.006 per 15 seconds
        speech_cost = (self.speech_usage["minutes"] * 60 / 15) * 0.006

        # Gemini API: 大まかな見積もり（トークン数ベース）
        gemini_cost = (
            self.gemini_usage["tokens"] / 1000
        ) * 0.001  # $0.001 per 1K tokens (概算)

        return {
            "speech_api_usd": round(speech_cost, 4),
            "gemini_api_usd": round(gemini_cost, 4),
            "total_estimated_usd": round(speech_cost + gemini_cost, 4),
        }
