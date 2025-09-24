"""
Main entry point for MindBridge
"""

import asyncio
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from src import __version__
from src.config import get_secure_settings, get_settings
from src.security.access_logger import (
    SecurityEventType,
    get_access_logger,
    log_security_event,
)
from src.utils import get_logger, setup_logging

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger

    from src.bot import DiscordBot
    from src.config.secure_settings import SecureSettingsManager
    from src.config.settings import Settings
    from src.health_analysis.scheduler import HealthAnalysisScheduler
    from src.monitoring.health_server import HealthServer
    from src.obsidian.github_sync import GitHubObsidianSync


@dataclass
class RuntimeContext:
    """Container for runtime components."""

    settings: "Settings"
    secure_settings: "SecureSettingsManager"
    github_sync: "GitHubObsidianSync | None"
    bot: "DiscordBot"
    health_scheduler: "HealthAnalysisScheduler"
    health_server: "HealthServer | None" = None


async def initialize_security(
    logger: "BoundLogger",
) -> tuple["SecureSettingsManager", "Settings"]:
    """Initialize secure settings and access logging."""
    secure_settings = get_secure_settings()
    settings = get_settings()

    if settings.enable_access_logging:
        get_access_logger()
        await log_security_event(
            SecurityEventType.LOGIN_ATTEMPT,
            action="Bot startup",
            success=True,
            details={"version": __version__, "mode": settings.environment},
        )
        logger.info("Access logging enabled")

    return secure_settings, settings


async def validate_required_credentials(
    settings: "Settings",
    secure_settings: "SecureSettingsManager",
    logger: "BoundLogger",
) -> None:
    """Ensure required secrets and directories exist."""
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

    if not settings.obsidian_vault_path.exists():
        logger.warning(
            "Obsidian vault path does not exist, creating directory",
            path=str(settings.obsidian_vault_path),
        )
        settings.obsidian_vault_path.mkdir(parents=True, exist_ok=True)

    logger.info("Configuration validated successfully")
    logger.info("Environment", env=settings.environment)
    logger.info("Obsidian vault path", path=str(settings.obsidian_vault_path))


async def setup_github_sync(
    settings: "Settings", logger: "BoundLogger"
) -> "GitHubObsidianSync | None":
    """Initialize GitHub synchronization if configured."""
    github_sync = None
    try:
        from src.obsidian.github_sync import GitHubObsidianSync

        github_sync = GitHubObsidianSync()
        if not github_sync.is_configured:
            logger.info("GitHub sync not configured, using local vault only")
            return github_sync

        logger.info("GitHub sync configured, performing startup sync...")
        setup_success = await github_sync.setup_git_repository()
        if setup_success:
            logger.info("Git repository setup completed")

        if settings.environment == "production":
            logger.info("Production environment detected, syncing from GitHub...")
            sync_success = await github_sync.sync_from_github()
            if sync_success:
                logger.info("Successfully synced vault from GitHub on startup")
            else:
                logger.warning(
                    "Failed to sync from GitHub on startup, continuing with local vault"
                )
        else:
            logger.info("Development environment, skipping startup sync")
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(f"GitHub sync initialization failed: {exc}")
        logger.info("Continuing with local vault only")

    return github_sync


async def build_runtime_context(
    settings: "Settings",
    secure_settings: "SecureSettingsManager",
    github_sync: "GitHubObsidianSync | None",
    logger: "BoundLogger",
) -> RuntimeContext:
    """Construct the runtime components for the application."""
    logger.info("Initializing health analysis scheduler...")

    from src.utils.lazy_loader import get_component_manager

    component_manager = get_component_manager()

    def create_ai_processor():
        from src.ai.processor import AIProcessor

        return AIProcessor()

    def create_garmin_client():
        from src.garmin import GarminClient

        return GarminClient()

    component_manager.register_component(
        "ai_processor", create_ai_processor, cache_duration=3600.0
    )
    component_manager.register_component(
        "garmin_client", create_garmin_client, cache_duration=1800.0
    )

    garmin_client = component_manager.get_component("garmin_client")
    ai_processor = component_manager.get_component("ai_processor")

    from src.health_analysis.analyzer import HealthDataAnalyzer
    from src.health_analysis.integrator import HealthActivityIntegrator
    from src.health_analysis.scheduler import HealthAnalysisScheduler
    from src.obsidian.daily_integration import DailyNoteIntegration
    from src.obsidian.file_manager import ObsidianFileManager

    analyzer = HealthDataAnalyzer(ai_processor=ai_processor)
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

    from src.ai.note_analyzer import AdvancedNoteAnalyzer
    from src.audio import SpeechProcessor
    from src.bot import DiscordBot
    from src.obsidian.template_system import TemplateEngine

    template_engine = TemplateEngine(vault_path=settings.obsidian_vault_path)
    note_analyzer = AdvancedNoteAnalyzer(
        obsidian_file_manager=file_manager, ai_processor=ai_processor
    )
    speech_processor = SpeechProcessor() if not settings.is_mock_mode else None
    note_template = "# {title}\n\n{content}\n\n---\nCreated: {timestamp}"

    bot = DiscordBot(
        ai_processor=ai_processor,
        vault_manager=file_manager,
        note_template=note_template,
        daily_integration=daily_integration,
        template_engine=template_engine,
        note_analyzer=note_analyzer,
        speech_processor=speech_processor,
    )

    return RuntimeContext(
        settings=settings,
        secure_settings=secure_settings,
        github_sync=github_sync,
        bot=bot,
        health_scheduler=health_scheduler,
    )


def start_health_server(
    bot: "DiscordBot", logger: "BoundLogger"
) -> "HealthServer | None":
    """Start the health check server, handling port conflicts."""
    from src.monitoring import HealthServer

    try:
        health_server = HealthServer(bot_instance=bot, port=8080)
        health_server.start()
        logger.info(f"Health server started on port {health_server.port}")
        return health_server
    except OSError as exc:
        logger.warning(f"Health server startup failed: {exc}")
        logger.info("Bot will continue without health server")
        return None


async def shutdown_runtime(
    context: RuntimeContext,
    scheduler_task: asyncio.Task[None],
    logger: "BoundLogger",
) -> None:
    """Shutdown services and perform any final synchronization."""
    logger.info("Shutting down services...")

    if (
        context.github_sync
        and context.github_sync.is_configured
        and context.settings.environment == "production"
    ):
        logger.info("Performing final sync to GitHub before shutdown...")
        try:
            sync_success = await context.github_sync.sync_to_github(
                "Auto-sync: Bot shutdown"
            )
            if sync_success:
                logger.info("Successfully synced vault to GitHub on shutdown")
            else:
                logger.warning("Failed to sync to GitHub on shutdown")
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(f"Error during shutdown sync: {exc}")

    context.health_scheduler.stop_scheduler()
    scheduler_task.cancel()
    try:
        await scheduler_task
    except asyncio.CancelledError:
        pass

    if context.health_server:
        context.health_server.stop()
    logger.info("All services stopped")


async def run_application(context: RuntimeContext, logger: "BoundLogger") -> None:
    """Run the Discord bot and supporting services."""
    context.health_server = start_health_server(context.bot, logger)

    logger.info("Starting Discord bot and health scheduler...")
    health_scheduler_task = asyncio.create_task(
        context.health_scheduler.start_scheduler()
    )
    logger.info("Health analysis scheduler started in background")

    try:
        await context.bot.run_async()
    finally:
        await shutdown_runtime(context, health_scheduler_task, logger)


async def main() -> None:
    """Main application entry point."""
    setup_logging()
    logger = get_logger("main")

    logger.info("Starting MindBridge", version=__version__)

    try:
        secure_settings, settings = await initialize_security(logger)
        await validate_required_credentials(settings, secure_settings, logger)
        github_sync = await setup_github_sync(settings, logger)
        context = await build_runtime_context(
            settings, secure_settings, github_sync, logger
        )
        await run_application(context, logger)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Failed to start bot", error=str(exc), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
        sys.exit(0)
