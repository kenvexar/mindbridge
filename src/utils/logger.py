"""
Logging configuration for MindBridge
"""

import logging
from pathlib import Path
from typing import Any

import structlog
from rich.console import Console
from rich.logging import RichHandler

from src.config import get_settings


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
        format="%(message) s",
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


def sanitize_log_content(content: str, max_length: int = 50) -> str:
    """機密情報を含む可能性のあるコンテンツをサニタイズ"""
    import re

    # 機密情報のパターン
    sensitive_patterns = [
        r'token[=:\s]*["\']?[\w\-\.]{20,}["\']?',  # トークン
        r'password[=:\s]*["\']?[\w\-\.]{8,}["\']?',  # パスワード
        r'secret[=:\s]*["\']?[\w\-\.]{20,}["\']?',  # シークレット
        r'key[=:\s]*["\']?[\w\-\.]{20,}["\']?',  # API キー
        r"(?:https?://)?(?:\w+:)?[\w\-\.]+@[\w\-\.]+",  # 認証情報を含む URL
        r"\b[A-Za-z0-9]{20,}\b",  # 長い英数字文字列（トークンの可能性）
    ]

    sanitized = content

    # 機密情報をマスク
    for pattern in sensitive_patterns:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

    # 長さ制限
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."

    return sanitized


def secure_log_message_content(
    content: str, author: str = "", channel: str = ""
) -> dict:
    """Discord メッセージ内容を安全にログに記録するための情報を作成"""
    return {
        "content_preview": sanitize_log_content(content, max_length=50),
        "content_length": len(content),
        "author": author,
        "channel": channel,
        "has_potential_secrets": any(
            pattern in content.lower()
            for pattern in ["token", "password", "secret", "key", "auth"]
        ),
    }


def validate_safe_path(path: str | Path, base_path: str | Path) -> Path:
    """パスが安全であることを検証（ Path Traversal 攻撃を防止）"""
    from pathlib import Path

    try:
        # 文字列を Path オブジェクトに変換
        if isinstance(path, str):
            path = Path(path)
        if isinstance(base_path, str):
            base_path = Path(base_path)

        # パスを正規化
        normalized_path = path.resolve()
        normalized_base = base_path.resolve()

        # ベースパスの下位にあることを確認
        try:
            normalized_path.relative_to(normalized_base)
        except ValueError as e:
            raise ValueError(
                f"Path '{path}' is outside base directory '{base_path}'"
            ) from e

        # 危険な文字列をチェック
        dangerous_patterns = ["..", "~", "$", "`", "|", ";", "&", ">", "<"]
        path_str = str(path)
        for pattern in dangerous_patterns:
            if pattern in path_str:
                raise ValueError(f"Path contains dangerous pattern: {pattern}")

        return normalized_path

    except Exception as e:
        raise ValueError(f"Invalid path: {e}") from e


def secure_file_operation(
    operation: str, target_path: str | Path, base_path: str | Path
) -> bool:
    """安全なファイル操作のための事前チェック"""
    try:
        validated_path = validate_safe_path(target_path, base_path)

        # 操作の種類に応じた追加チェック
        if operation == "delete":
            # 重要なファイル/ディレクトリの削除を防止
            critical_patterns = [
                ".git",
                ".obsidian/app.json",
                ".obsidian/appearance.json",
            ]
            path_str = str(validated_path)
            for pattern in critical_patterns:
                if pattern in path_str:
                    raise ValueError(f"Cannot delete critical path: {pattern}")

        return True

    except Exception as e:
        import structlog

        logger = structlog.get_logger("file_security")
        logger.warning(
            "Unsafe file operation blocked",
            operation=operation,
            target=str(target_path),
            base=str(base_path),
            error=str(e),
        )
        return False


# Default logger instance for convenient access
logger = get_logger("mindbridge")
