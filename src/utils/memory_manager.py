"""Memory optimization and garbage collection utilities."""

import asyncio
import gc
import time
import weakref
from datetime import datetime
from typing import Any

from .logger import get_logger

logger = get_logger("memory_manager")


class MemoryManager:
    """メモリ使用量最適化とガベージコレクション管理."""

    def __init__(
        self,
        cleanup_interval: int = 300,  # 5 分間隔
        max_memory_mb: int = 512,  # 最大メモリ使用量 (MB)
        gc_threshold_ratio: float = 0.8,  # GC 実行閾値 (80%)
    ):
        """
        Initialize memory manager.

        Args:
            cleanup_interval: 自動クリーンアップ間隔 (秒)
            max_memory_mb: 最大メモリ使用量 (MB)
            gc_threshold_ratio: GC 実行閾値 (最大値に対する比率)
        """
        self.cleanup_interval = cleanup_interval
        self.max_memory_mb = max_memory_mb
        self.gc_threshold_mb = max_memory_mb * gc_threshold_ratio

        self._cleanup_task: asyncio.Task | None = None
        self._tracked_objects: dict[str, weakref.WeakSet] = {}
        self._last_cleanup = datetime.now()
        self._memory_stats = {
            "peak_memory_mb": 0.0,
            "gc_runs": 0,
            "objects_collected": 0,
            "cleanup_runs": 0,
        }

        # ガベージコレクション設定最適化
        self._optimize_gc_settings()

    def _optimize_gc_settings(self) -> None:
        """ガベージコレクション設定を最適化."""
        # Python GC 閾値をメモリ効率的に調整
        # デフォルト: (700, 10, 10) → より積極的に: (500, 8, 8)
        gc.set_threshold(500, 8, 8)
        logger.info("Optimized GC thresholds", thresholds=gc.get_threshold())

    async def start_auto_cleanup(self) -> None:
        """自動メモリクリーンアップを開始."""
        if self._cleanup_task and not self._cleanup_task.done():
            return

        self._cleanup_task = asyncio.create_task(self._auto_cleanup_loop())
        logger.info("Auto memory cleanup started", interval=self.cleanup_interval)

    async def stop_auto_cleanup(self) -> None:
        """自動メモリクリーンアップを停止."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        logger.info("Auto memory cleanup stopped")

    async def _auto_cleanup_loop(self) -> None:
        """自動クリーンアップループ."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self.cleanup_memory()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Auto cleanup failed", error=str(e), exc_info=True)

    async def cleanup_memory(self, force: bool = False) -> dict[str, Any]:
        """
        メモリクリーンアップを実行.

        Args:
            force: 強制実行フラグ

        Returns:
            クリーンアップ結果の統計
        """
        current_memory = self.get_memory_usage_mb()

        # 閾値チェック（強制実行でない場合）
        if not force and current_memory < self.gc_threshold_mb:
            return {
                "cleanup_executed": False,
                "reason": "below_threshold",
                "current_memory_mb": current_memory,
                "threshold_mb": self.gc_threshold_mb,
            }

        logger.info(
            "Starting memory cleanup",
            current_memory_mb=current_memory,
            threshold_mb=self.gc_threshold_mb,
            force=force,
        )

        start_time = time.time()
        initial_memory = current_memory

        # 1. 期限切れオブジェクトのクリーンアップ
        expired_cleaned = await self._cleanup_expired_objects()

        # 2. 弱参照追跡オブジェクトのクリーンアップ
        tracked_cleaned = self._cleanup_tracked_objects()

        # 3. 明示的ガベージコレクション実行
        collected = self._run_garbage_collection()

        # 4. 統計更新
        end_time = time.time()
        final_memory = self.get_memory_usage_mb()
        memory_freed = initial_memory - final_memory

        self._memory_stats["cleanup_runs"] += 1
        self._memory_stats["objects_collected"] += collected
        self._memory_stats["peak_memory_mb"] = max(
            self._memory_stats["peak_memory_mb"], initial_memory
        )
        self._last_cleanup = datetime.now()

        result = {
            "cleanup_executed": True,
            "duration_seconds": end_time - start_time,
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_freed_mb": memory_freed,
            "expired_cleaned": expired_cleaned,
            "tracked_cleaned": tracked_cleaned,
            "gc_collected": collected,
        }

        logger.info(
            "Memory cleanup completed",
            **result,
        )

        return result

    async def _cleanup_expired_objects(self) -> int:
        """期限切れオブジェクトのクリーンアップ（サブクラスでオーバーライド用）."""
        # 基本実装では何もしない（具象クラスで実装）
        return 0

    def _cleanup_tracked_objects(self) -> int:
        """追跡オブジェクトのクリーンアップ."""
        cleaned = 0
        for name, weak_set in list(self._tracked_objects.items()):
            # 弱参照が無効になったオブジェクトをカウント
            before_size = len(weak_set)
            # WeakSet は自動的に無効な参照を削除するので、単純にサイズをチェック
            after_size = len(weak_set)
            cleaned += before_size - after_size

            # 空になった WeakSet を削除
            if not weak_set:
                del self._tracked_objects[name]

        return cleaned

    def _run_garbage_collection(self) -> int:
        """明示的なガベージコレクションを実行."""
        collected = gc.collect()
        self._memory_stats["gc_runs"] += 1

        logger.debug(
            "Garbage collection completed",
            objects_collected=collected,
            gc_stats=gc.get_stats(),
        )

        return collected

    def track_objects(self, name: str, objects: list[Any]) -> None:
        """オブジェクトを弱参照で追跡."""
        if name not in self._tracked_objects:
            self._tracked_objects[name] = weakref.WeakSet()

        for obj in objects:
            try:
                self._tracked_objects[name].add(obj)
            except TypeError:
                # 弱参照できないオブジェクトはスキップ
                pass

    def get_memory_usage_mb(self) -> float:
        """現在のメモリ使用量を取得 (MB)."""
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            # psutil が利用できない場合は近似値
            return len(gc.get_objects()) * 0.001  # 大まかな近似

    def get_memory_stats(self) -> dict[str, Any]:
        """メモリ使用統計を取得."""
        current_memory = self.get_memory_usage_mb()

        return {
            "current_memory_mb": current_memory,
            "max_memory_mb": self.max_memory_mb,
            "usage_ratio": current_memory / self.max_memory_mb,
            "gc_threshold_mb": self.gc_threshold_mb,
            "last_cleanup": self._last_cleanup.isoformat(),
            "tracked_object_types": len(self._tracked_objects),
            "gc_objects_count": len(gc.get_objects()),
            **self._memory_stats,
        }

    def is_memory_pressure(self) -> bool:
        """メモリプレッシャーの有無を判定."""
        return self.get_memory_usage_mb() > self.gc_threshold_mb


class ComponentMemoryManager(MemoryManager):
    """コンポーネント固有のメモリ管理."""

    def __init__(self, components: list[Any] | None = None, **kwargs):
        """
        Initialize with component-specific cleanup.

        Args:
            components: クリーンアップ対象コンポーネント
        """
        super().__init__(**kwargs)
        self.components = components or []

    async def _cleanup_expired_objects(self) -> int:
        """コンポーネントの期限切れオブジェクトをクリーンアップ."""
        cleaned = 0

        for component in self.components:
            if hasattr(component, "cleanup_expired"):
                try:
                    result = await component.cleanup_expired()
                    cleaned += result if isinstance(result, int) else 0
                except Exception as e:
                    logger.warning(
                        "Component cleanup failed",
                        component=type(component).__name__,
                        error=str(e),
                    )

        return cleaned

    def register_component(self, component: Any) -> None:
        """コンポーネントを登録."""
        if component not in self.components:
            self.components.append(component)
            logger.debug(
                "Component registered",
                component=type(component).__name__,
                total_components=len(self.components),
            )


# グローバルメモリマネージャーインスタンス
_global_memory_manager: ComponentMemoryManager | None = None


def get_memory_manager() -> ComponentMemoryManager:
    """グローバルメモリマネージャーを取得."""
    global _global_memory_manager
    if _global_memory_manager is None:
        _global_memory_manager = ComponentMemoryManager()
    return _global_memory_manager


async def cleanup_global_memory(force: bool = False) -> dict[str, Any]:
    """グローバルメモリクリーンアップを実行."""
    manager = get_memory_manager()
    return await manager.cleanup_memory(force=force)


def get_global_memory_stats() -> dict[str, Any]:
    """グローバルメモリ統計を取得."""
    manager = get_memory_manager()
    return manager.get_memory_stats()
