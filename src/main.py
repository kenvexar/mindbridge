"""
Main entry point for MindBridge
"""

import asyncio
import sys

from src import __version__
from src.config import get_secure_settings, get_settings
from src.security.access_logger import (
    SecurityEventType,
    get_access_logger,
    log_security_event,
)
from src.utils import get_logger, setup_logging


async def main() -> None:
    """Main application entry point"""
    # Setup logging
    setup_logging()
    logger = get_logger("main")

    logger.info("Starting MindBridge", version=__version__)

    try:
        # Initialize security systems
        logger.info("Initializing security systems...")
        secure_settings = get_secure_settings()
        settings_instance = get_settings()  # Get settings instance

        # Initialize access logger if enabled
        if settings_instance.enable_access_logging:
            get_access_logger()
            await log_security_event(
                SecurityEventType.LOGIN_ATTEMPT,
                action="Bot startup",
                success=True,
                details={"version": __version__, "mode": settings_instance.environment},
            )
            logger.info("Access logging enabled")

        # Validate critical settings using secure manager
        discord_token = secure_settings.get_discord_token()
        if not discord_token:
            await log_security_event(
                SecurityEventType.LOGIN_ATTEMPT,
                action="Missing Discord token",
                success=False,
            )
            raise ValueError("Discord bot token not available")

        gemini_key = secure_settings.get_gemini_api_key()
        if not gemini_key:
            await log_security_event(
                SecurityEventType.LOGIN_ATTEMPT,
                action="Missing Gemini API key",
                success=False,
            )
            raise ValueError("Gemini API key not available")

        if not settings_instance.obsidian_vault_path.exists():
            logger.warning(
                "Obsidian vault path does not exist, creating directory",
                path=str(settings_instance.obsidian_vault_path),
            )
            settings_instance.obsidian_vault_path.mkdir(parents=True, exist_ok=True)

        logger.info("Configuration validated successfully")
        logger.info("Environment", env=settings_instance.environment)
        logger.info(
            "Obsidian vault path", path=str(settings_instance.obsidian_vault_path)
        )

        # Initialize GitHub sync for Cloud Run persistence
        github_sync = None
        try:
            from src.obsidian.github_sync import GitHubObsidianSync

            github_sync = GitHubObsidianSync()
            if github_sync.is_configured:
                logger.info("GitHub sync configured, performing startup sync...")

                # Setup git repository if needed
                setup_success = await github_sync.setup_git_repository()
                if setup_success:
                    logger.info("Git repository setup completed")

                # Sync from GitHub on startup (for Cloud Run persistence)
                if settings_instance.environment == "production":
                    logger.info(
                        "Production environment detected, syncing from GitHub..."
                    )
                    sync_success = await github_sync.sync_from_github()
                    if sync_success:
                        logger.info("Successfully synced vault from GitHub on startup")
                    else:
                        logger.warning(
                            "Failed to sync from GitHub on startup, continuing with local vault"
                        )
                else:
                    logger.info("Development environment, skipping startup sync")
            else:
                logger.info("GitHub sync not configured, using local vault only")
        except Exception as e:
            logger.warning(f"GitHub sync initialization failed: {e}")
            logger.info("Continuing with local vault only")

        # Initialize health analysis components with lazy loading
        logger.info("Initializing health analysis scheduler...")
        from src.utils.lazy_loader import get_component_manager

        component_manager = get_component_manager()

        # Register components for lazy loading
        def create_ai_processor():
            from src.ai.processor import AIProcessor

            return AIProcessor()

        def create_garmin_client():
            from src.garmin import GarminClient

            return GarminClient()

        # Register components
        component_manager.register_component(
            "ai_processor",
            create_ai_processor,
            cache_duration=3600.0,  # 1 時間キャッシュ
        )
        component_manager.register_component(
            "garmin_client",
            create_garmin_client,
            cache_duration=1800.0,  # 30 分キャッシュ
        )
        # Initialize components for health analysis with lazy loading
        garmin_client = component_manager.get_component("garmin_client")
        ai_processor = component_manager.get_component("ai_processor")

        from src.health_analysis.analyzer import HealthDataAnalyzer
        from src.health_analysis.integrator import HealthActivityIntegrator
        from src.health_analysis.scheduler import HealthAnalysisScheduler
        from src.obsidian.daily_integration import DailyNoteIntegration

        analyzer = HealthDataAnalyzer(ai_processor=ai_processor)

        # Initialize file manager for integrator
        from src.obsidian.file_manager import ObsidianFileManager

        file_manager = ObsidianFileManager()
        integrator = HealthActivityIntegrator(file_manager=file_manager)
        daily_integration = DailyNoteIntegration(file_manager=file_manager)

        health_scheduler = HealthAnalysisScheduler(
            garmin_client=garmin_client,
            analyzer=analyzer,
            integrator=integrator,
            daily_integration=daily_integration,
        )

        logger.info("Health analysis scheduler initialized successfully")

        # Initialize additional components needed for MessageHandler
        from src.ai.note_analyzer import AdvancedNoteAnalyzer
        from src.audio import SpeechProcessor
        from src.obsidian.template_system import TemplateEngine

        # Create additional dependencies
        template_engine = TemplateEngine(
            vault_path=settings_instance.obsidian_vault_path
        )
        note_analyzer = AdvancedNoteAnalyzer(
            obsidian_file_manager=file_manager, ai_processor=ai_processor
        )
        speech_processor = (
            SpeechProcessor() if not settings_instance.is_mock_mode else None
        )
        note_template = "# {title}\n\n{content}\n\n---\nCreated: {timestamp}"

        # Initialize and start Discord bot
        from src.bot import DiscordBot

        bot = DiscordBot(
            ai_processor=ai_processor,
            vault_manager=file_manager,  # 🔧 FIX: ObsidianFileManager を使用（ save_note メソッドがある）
            note_template=note_template,
            daily_integration=daily_integration,
            template_engine=template_engine,
            note_analyzer=note_analyzer,
            speech_processor=speech_processor,
        )

        # Start health check server for Cloud Run with port conflict handling
        health_server = None
        from src.monitoring import HealthServer

        try:
            health_server = HealthServer(bot_instance=bot, port=8080)
            health_server.start()
            logger.info(f"Health server started on port {health_server.port}")
        except OSError as e:
            logger.warning(f"Health server startup failed: {e}")
            logger.info("Bot will continue without health server")

        logger.info("Starting Discord bot and health scheduler...")

        # Start health scheduler in background
        health_scheduler_task = asyncio.create_task(health_scheduler.start_scheduler())
        logger.info("Health analysis scheduler started in background")

        try:
            await bot.run_async()  # 🔧 FIX: start() → run_async() に修正
        finally:
            # Cleanup and sync to GitHub on shutdown
            logger.info("Shutting down services...")

            # Perform final GitHub sync before shutdown (for Cloud Run persistence)
            if (
                github_sync
                and github_sync.is_configured
                and settings_instance.environment == "production"
            ):
                logger.info("Performing final sync to GitHub before shutdown...")
                try:
                    sync_success = await github_sync.sync_to_github(
                        "Auto-sync: Bot shutdown"
                    )
                    if sync_success:
                        logger.info("Successfully synced vault to GitHub on shutdown")
                    else:
                        logger.warning("Failed to sync to GitHub on shutdown")
                except Exception as e:
                    logger.error(f"Error during shutdown sync: {e}")

            health_scheduler.stop_scheduler()
            health_scheduler_task.cancel()
            try:
                await health_scheduler_task
            except asyncio.CancelledError:
                pass

            if health_server:
                health_server.stop()
            logger.info("All services stopped")

    except Exception as e:
        logger.error("Failed to start bot", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
        sys.exit(0)
