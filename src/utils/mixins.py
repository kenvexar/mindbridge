import structlog


class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger instance for this class"""
        from typing import cast

        return cast(
            "structlog.stdlib.BoundLogger",
            structlog.get_logger(self.__class__.__name__),
        )
