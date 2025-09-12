"""Refactored Discord command modules."""

from typing import Any

import structlog

from src.bot.channel_config import ChannelConfig
from src.bot.commands.basic_commands import BasicCommands
from src.bot.commands.config_commands import ConfigCommands
from src.bot.commands.finance_commands import FinanceCommands
from src.bot.commands.integration_commands import IntegrationCommands
from src.bot.commands.stats_commands import StatsCommands
from src.bot.commands.task_commands import TaskCommands

__all__ = [
    "BasicCommands",
    "ConfigCommands",
    "StatsCommands",
    "TaskCommands",
    "FinanceCommands",
    "IntegrationCommands",
    "setup_commands",
    "setup_task_commands",
    "setup_finance_commands",
    "setup_integration_commands",
]


async def setup_commands(bot: Any, channel_config: ChannelConfig) -> None:
    """Setup refactored bot commands."""
    logger = structlog.get_logger(__name__)
    try:
        await bot.add_cog(BasicCommands(bot))
        logger.info("BasicCommands loaded successfully")

        await bot.add_cog(ConfigCommands(bot, channel_config))
        logger.info("ConfigCommands loaded successfully")

        await bot.add_cog(StatsCommands(bot))
        logger.info("StatsCommands loaded successfully")

        logger.info("All command cogs loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load command cogs: {e}", exc_info=True)


async def setup_task_commands(bot: Any) -> None:
    """Setup task management commands."""
    logger = structlog.get_logger(__name__)
    try:
        await bot.add_cog(TaskCommands(bot))
        logger.info("TaskCommands loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load TaskCommands: {e}", exc_info=True)


async def setup_finance_commands(bot: Any) -> None:
    """Setup finance management commands."""
    logger = structlog.get_logger(__name__)
    try:
        await bot.add_cog(FinanceCommands(bot))
        logger.info("FinanceCommands loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load FinanceCommands: {e}", exc_info=True)


async def setup_integration_commands(bot: Any, settings: Any) -> None:
    """Setup integration management commands."""
    logger = structlog.get_logger(__name__)
    try:
        await bot.add_cog(IntegrationCommands(bot, settings))
        logger.info("IntegrationCommands loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load IntegrationCommands: {e}", exc_info=True)
