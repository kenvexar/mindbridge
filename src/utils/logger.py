"""
Logging configuration for Discord-Obsidian Memo Bot
"""

import logging
from pathlib import Path
from typing import Any

import structlog
from rich.console import Console
from rich.logging import RichHandler

from src.config.settings import get_settings


def setup_logging() -> None:
    """Set up structured logging with rich formatting"""

    settings = get_settings()

    # Configure log level
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)

    # Configure standard library logging
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[
            RichHandler(
                console=Console(stderr=True),
                show_time=True,
                show_path=True,
                markup=True,
                rich_tracebacks=True,
            ),
            logging.FileHandler(logs_dir / "bot.log", encoding="utf-8"),
        ],
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            (
                structlog.processors.JSONRenderer()
                if settings.log_format == "json"
                else structlog.dev.ConsoleRenderer()
            ),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance"""
    from typing import cast

    logger = structlog.get_logger(name)
    return cast("structlog.stdlib.BoundLogger", logger)


def log_function_call(func_name: str, **kwargs: Any) -> None:
    """Log function call with parameters"""
    logger = get_logger("function_call")
    logger.info(f"Calling {func_name}", **kwargs)


def log_api_usage(api_name: str, usage_data: dict[str, Any]) -> None:
    """Log API usage for monitoring"""
    logger = get_logger("api_usage")
    logger.info(f"{api_name} API usage", **usage_data)
