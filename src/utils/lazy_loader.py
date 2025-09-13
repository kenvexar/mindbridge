"""Lazy loading utilities for performance optimization."""

import asyncio
import threading
import time
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Any, TypeVar

from src.utils.logger import get_logger

logger = get_logger("lazy_loader")

T = TypeVar("T")


class LazyLoader[T]:
    """遅延読み込み（ Lazy Loading ）を実現するクラス."""

    def __init__(
        self,
        loader_func: Callable[[], T],
        cache_duration: float | None = None,
        thread_safe: bool = True,
    ):
        """
        Initialize lazy loader.

        Args:
            loader_func: オブジェクト作成関数
            cache_duration: キャッシュ持続時間（秒）
            thread_safe: スレッドセーフティ
        """
        self._loader_func = loader_func
        self._cache_duration = cache_duration
        self._thread_safe = thread_safe

        self._instance: T | None = None
        self._load_time: float | None = None
        self._lock = threading.Lock() if thread_safe else None

        self._access_count = 0
        self._load_count = 0

    @property
    def instance(self) -> T:
        """インスタンスを取得（必要時に作成）."""
        if self._thread_safe and self._lock:
            with self._lock:
                return self._get_instance()
        else:
            return self._get_instance()

    def _get_instance(self) -> T:
        """インスタンス取得の内部実装."""
        self._access_count += 1
        current_time = time.time()

        # キャッシュ期限チェック
        if (
            self._instance is not None
            and self._cache_duration is not None
            and self._load_time is not None
            and current_time - self._load_time > self._cache_duration
        ):
            logger.debug(
                "Lazy loader cache expired",
                loader=self._loader_func.__name__,
                age=current_time - self._load_time,
                duration=self._cache_duration,
            )
            self._instance = None

        # インスタンス作成
        if self._instance is None:
            logger.debug(
                "Lazy loading instance",
                loader=self._loader_func.__name__,
                access_count=self._access_count,
            )

            start_time = time.time()
            self._instance = self._loader_func()
            load_time = time.time() - start_time

            self._load_time = current_time
            self._load_count += 1

            logger.info(
                "Lazy loaded instance",
                loader=self._loader_func.__name__,
                load_time_ms=load_time * 1000,
                load_count=self._load_count,
            )

        return self._instance

    def reload(self) -> T:
        """インスタンスを強制再読み込み."""
        if self._thread_safe and self._lock:
            with self._lock:
                self._instance = None
                return self._get_instance()
        else:
            self._instance = None
            return self._get_instance()

    def is_loaded(self) -> bool:
        """インスタンスが読み込み済みかチェック."""
        return self._instance is not None

    def get_stats(self) -> dict[str, Any]:
        """統計情報を取得."""
        return {
            "is_loaded": self.is_loaded(),
            "access_count": self._access_count,
            "load_count": self._load_count,
            "load_time": self._load_time,
            "cache_duration": self._cache_duration,
        }


class AsyncLazyLoader[T]:
    """非同期遅延読み込み（ Async Lazy Loading ）を実現するクラス."""

    def __init__(
        self,
        loader_func: Callable[[], Awaitable[T]],
        cache_duration: float | None = None,
    ):
        """
        Initialize async lazy loader.

        Args:
            loader_func: 非同期オブジェクト作成関数
            cache_duration: キャッシュ持続時間（秒）
        """
        self._loader_func = loader_func
        self._cache_duration = cache_duration

        self._instance: T | None = None
        self._load_time: float | None = None
        self._loading_lock = asyncio.Lock()
        self._loading_task: asyncio.Task | None = None

        self._access_count = 0
        self._load_count = 0

    async def get_instance(self) -> T:
        """インスタンスを取得（必要時に非同期作成）."""
        async with self._loading_lock:
            self._access_count += 1
            current_time = time.time()

            # キャッシュ期限チェック
            if (
                self._instance is not None
                and self._cache_duration is not None
                and self._load_time is not None
                and current_time - self._load_time > self._cache_duration
            ):
                logger.debug(
                    "Async lazy loader cache expired",
                    loader=self._loader_func.__name__,
                    age=current_time - self._load_time,
                )
                self._instance = None

            # インスタンス作成
            if self._instance is None:
                # 既に読み込み中の場合は待機
                if self._loading_task and not self._loading_task.done():
                    logger.debug("Waiting for ongoing load operation")
                    await self._loading_task
                    if self._instance is None:
                        raise RuntimeError(
                            "Loading task completed but instance is None"
                        )
                    return self._instance

                logger.debug(
                    "Async lazy loading instance",
                    loader=self._loader_func.__name__,
                    access_count=self._access_count,
                )

                # 非同期読み込み開始
                start_time = time.time()
                # 型チェックのために Coroutine にキャスト
                coro = self._loader_func()
                if not asyncio.iscoroutine(coro):
                    raise TypeError(
                        f"loader_func must return a coroutine, got {type(coro)}"
                    )
                self._loading_task = asyncio.create_task(coro)
                self._instance = await self._loading_task
                load_time = time.time() - start_time

                self._load_time = current_time
                self._load_count += 1

                logger.info(
                    "Async lazy loaded instance",
                    loader=self._loader_func.__name__,
                    load_time_ms=load_time * 1000,
                    load_count=self._load_count,
                )

            return self._instance

    async def reload(self) -> T:
        """インスタンスを強制再読み込み."""
        async with self._loading_lock:
            self._instance = None
            return await self.get_instance()

    def is_loaded(self) -> bool:
        """インスタンスが読み込み済みかチェック."""
        return self._instance is not None

    def get_stats(self) -> dict[str, Any]:
        """統計情報を取得."""
        return {
            "is_loaded": self.is_loaded(),
            "access_count": self._access_count,
            "load_count": self._load_count,
            "load_time": self._load_time,
            "cache_duration": self._cache_duration,
        }


class LazyComponentManager:
    """遅延読み込みコンポーネントマネージャー."""

    def __init__(self):
        """Initialize component manager."""
        self._components: dict[str, LazyLoader[Any]] = {}
        self._async_components: dict[str, AsyncLazyLoader[Any]] = {}
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="lazy-")

    def register_component(
        self,
        name: str,
        loader_func: Callable[[], T],
        cache_duration: float | None = None,
        thread_safe: bool = True,
    ) -> LazyLoader[T]:
        """
        コンポーネントを登録.

        Args:
            name: コンポーネント名
            loader_func: 読み込み関数
            cache_duration: キャッシュ期間
            thread_safe: スレッドセーフ

        Returns:
            LazyLoader インスタンス
        """
        lazy_loader = LazyLoader(
            loader_func=loader_func,
            cache_duration=cache_duration,
            thread_safe=thread_safe,
        )
        self._components[name] = lazy_loader

        logger.debug(
            "Registered lazy component",
            name=name,
            cache_duration=cache_duration,
            thread_safe=thread_safe,
        )

        return lazy_loader

    def register_async_component(
        self,
        name: str,
        loader_func: Callable[[], Awaitable[T]],
        cache_duration: float | None = None,
    ) -> AsyncLazyLoader[T]:
        """
        非同期コンポーネントを登録.

        Args:
            name: コンポーネント名
            loader_func: 非同期読み込み関数
            cache_duration: キャッシュ期間

        Returns:
            AsyncLazyLoader インスタンス
        """
        async_lazy_loader = AsyncLazyLoader(
            loader_func=loader_func,
            cache_duration=cache_duration,
        )
        self._async_components[name] = async_lazy_loader

        logger.debug(
            "Registered async lazy component",
            name=name,
            cache_duration=cache_duration,
        )

        return async_lazy_loader

    def get_component(self, name: str) -> Any:
        """コンポーネントを取得."""
        if name not in self._components:
            raise KeyError(f"Component '{name}' not found")
        return self._components[name].instance

    async def get_async_component(self, name: str) -> Any:
        """非同期コンポーネントを取得."""
        if name not in self._async_components:
            raise KeyError(f"Async component '{name}' not found")
        return await self._async_components[name].get_instance()

    def reload_component(self, name: str) -> Any:
        """コンポーネントを再読み込み."""
        if name not in self._components:
            raise KeyError(f"Component '{name}' not found")
        return self._components[name].reload()

    async def reload_async_component(self, name: str) -> T:
        """非同期コンポーネントを再読み込み."""
        if name not in self._async_components:
            raise KeyError(f"Async component '{name}' not found")
        return await self._async_components[name].reload()

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """全コンポーネントの統計を取得."""
        stats = {}

        for name, component in self._components.items():
            stats[name] = {
                "type": "sync",
                **component.get_stats(),
            }

        for name, async_component in self._async_components.items():
            stats[name] = {
                "type": "async",
                **async_component.get_stats(),
            }

        return stats

    def cleanup(self) -> None:
        """リソースをクリーンアップ."""
        self._executor.shutdown(wait=True)
        logger.info("Lazy component manager cleaned up")


def lazy_property(cache_duration: float | None = None, thread_safe: bool = True):
    """
    遅延読み込みプロパティデコレータ.

    Args:
        cache_duration: キャッシュ期間（秒）
        thread_safe: スレッドセーフ
    """

    def decorator(func):
        attr_name = f"_lazy_{func.__name__}"

        @wraps(func)
        def wrapper(self):
            if not hasattr(self, attr_name):
                setattr(
                    self,
                    attr_name,
                    LazyLoader(
                        loader_func=lambda: func(self),
                        cache_duration=cache_duration,
                        thread_safe=thread_safe,
                    ),
                )
            return getattr(self, attr_name).instance

        return property(wrapper)

    return decorator


# グローバルコンポーネントマネージャー
_global_component_manager: LazyComponentManager | None = None


def get_component_manager() -> LazyComponentManager:
    """グローバルコンポーネントマネージャーを取得."""
    global _global_component_manager
    if _global_component_manager is None:
        _global_component_manager = LazyComponentManager()
    return _global_component_manager
