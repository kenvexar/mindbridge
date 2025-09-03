"""共通エラーハンドリングユーティリティ

このモジュールは、アプリケーション全体で使用される共通のエラーハンドリング機能を提供します。
重複したエラーハンドリングコードを排除し、一貫したログ記録を実現します。
"""

import functools
from collections.abc import Callable
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


class ErrorHandler:
    """共通エラーハンドリング機能を提供するクラス"""

    @staticmethod
    def log_and_return_none(
        operation_name: str, exception: Exception, **kwargs: Any
    ) -> None:
        """エラーをログ記録し、None を返す標準パターン"""
        logger.error(f"Failed to {operation_name}", error=str(exception), **kwargs)
        return None

    @staticmethod
    def log_and_return_default(
        operation_name: str, exception: Exception, default_value: T, **kwargs: Any
    ) -> T:
        """エラーをログ記録し、デフォルト値を返す標準パターン"""
        logger.error(f"Failed to {operation_name}", error=str(exception), **kwargs)
        return default_value

    @staticmethod
    def log_and_reraise(
        operation_name: str, exception: Exception, **kwargs: Any
    ) -> None:
        """エラーをログ記録してから例外を再発生させる"""
        logger.error(f"Failed to {operation_name}", error=str(exception), **kwargs)
        raise exception


def handle_errors(
    operation_name: str,
    default_return: Any = None,
    reraise: bool = False,
    **log_kwargs: Any,
):
    """
    メソッドのエラーハンドリングを自動化するデコレータ

    Args:
        operation_name: 操作の名前（ログ記録用）
        default_return: エラー時の戻り値（デフォルト: None）
        reraise: True の場合、例外を再発生させる
        **log_kwargs: ログに追加する情報
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if reraise:
                    ErrorHandler.log_and_reraise(operation_name, e, **log_kwargs)
                else:
                    ErrorHandler.log_and_return_default(
                        operation_name, e, default_return, **log_kwargs
                    )

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if reraise:
                    ErrorHandler.log_and_reraise(operation_name, e, **log_kwargs)
                else:
                    ErrorHandler.log_and_return_default(
                        operation_name, e, default_return, **log_kwargs
                    )

        # 関数が async かどうかを判定
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return wrapper

    return decorator


# よく使用されるエラーハンドリングパターンの短縮形
def safe_operation(operation_name: str, **log_kwargs: Any):
    """セーフな操作（エラー時に None を返す）"""
    return handle_errors(operation_name, default_return=None, **log_kwargs)


def safe_with_default(operation_name: str, default_value: Any, **log_kwargs: Any):
    """デフォルト値付きセーフ操作"""
    return handle_errors(operation_name, default_return=default_value, **log_kwargs)


def critical_operation(operation_name: str, **log_kwargs: Any):
    """重要な操作（エラー時に例外を再発生）"""
    return handle_errors(operation_name, reraise=True, **log_kwargs)
