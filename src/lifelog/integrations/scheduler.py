"""
外部連携スケジューラー

外部連携の自動同期をスケジューリングするためのシステム
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from .manager import IntegrationManager, SyncResult

logger = structlog.get_logger(__name__)


class ScheduleType(str, Enum):
    """スケジュールタイプ"""

    INTERVAL = "interval"  # 間隔指定
    DAILY = "daily"  # 毎日
    HOURLY = "hourly"  # 毎時
    WEEKLY = "weekly"  # 毎週
    MANUAL = "manual"  # 手動のみ


@dataclass
class ScheduleTask:
    """スケジュールタスク"""

    integration_name: str
    schedule_type: ScheduleType
    interval_seconds: int | None = None
    next_run: datetime | None = None
    last_run: datetime | None = None
    enabled: bool = True
    retry_count: int = 0
    max_retries: int = 3


class IntegrationSchedulerConfig(BaseModel):
    """スケジューラー設定"""

    # 基本設定
    check_interval: int = Field(default=60, description="チェック間隔（秒）")
    max_concurrent_tasks: int = Field(default=2, description="最大同時実行タスク数")

    # リトライ設定
    retry_delays: list[int] = Field(
        default=[60, 300, 900], description="リトライ遅延（秒）"
    )
    max_retry_attempts: int = Field(default=3, description="最大リトライ回数")

    # 同期ウィンドウ設定
    sync_window_start: int = Field(default=6, description="同期開始時間（時）")
    sync_window_end: int = Field(default=23, description="同期終了時間（時）")

    # デフォルトスケジュール
    default_schedules: dict[str, dict[str, Any]] = Field(
        default={
            "garmin": {"type": "daily", "hour": 7},
            "google_calendar": {"type": "hourly"},
        },
        description="デフォルトスケジュール設定",
    )


class IntegrationScheduler:
    """外部連携スケジューラー"""

    def __init__(self, manager: IntegrationManager, config: IntegrationSchedulerConfig):
        self.manager = manager
        self.config = config
        self.logger = structlog.get_logger(__name__)

        # スケジュール管理
        self.scheduled_tasks: dict[str, ScheduleTask] = {}
        self.running_tasks: dict[str, asyncio.Task] = {}

        # スケジューラー制御
        self._scheduler_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._semaphore = asyncio.Semaphore(config.max_concurrent_tasks)

        # 統計情報
        self.total_scheduled_runs = 0
        self.successful_runs = 0
        self.failed_runs = 0

        # コールバック
        self.on_sync_complete: Callable[[SyncResult], None] | None = None
        self.on_sync_error: Callable[[str, str], None] | None = None

    async def start(self) -> None:
        """スケジューラー開始"""
        if self._scheduler_task and not self._scheduler_task.done():
            self.logger.warning("スケジューラーは既に実行中です")
            return

        self.logger.info("外部連携スケジューラー開始")
        self._stop_event.clear()

        # デフォルトスケジュール設定
        await self._setup_default_schedules()

        # スケジューラータスク開始
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """スケジューラー停止"""
        self.logger.info("外部連携スケジューラー停止中...")

        # 停止イベント設定
        self._stop_event.set()

        # スケジューラータスク停止
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass

        # 実行中のタスクを停止
        for task in list(self.running_tasks.values()):
            if not task.done():
                task.cancel()

        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)

        self.running_tasks.clear()
        self.logger.info("外部連携スケジューラー停止完了")

    async def _setup_default_schedules(self) -> None:
        """デフォルトスケジュール設定"""
        for integration_name, schedule_config in self.config.default_schedules.items():
            if integration_name in self.manager.integrations:
                await self.add_schedule(
                    integration_name=integration_name,
                    schedule_type=ScheduleType(schedule_config["type"]),
                    **{k: v for k, v in schedule_config.items() if k != "type"},
                )

    async def add_schedule(
        self, integration_name: str, schedule_type: ScheduleType, **kwargs
    ) -> bool:
        """スケジュール追加"""
        try:
            if integration_name not in self.manager.integrations:
                self.logger.error(f"未登録の連携: {integration_name}")
                return False

            # 次回実行時刻計算
            next_run = self._calculate_next_run(schedule_type, **kwargs)

            # 間隔設定
            interval_seconds = None
            if schedule_type == ScheduleType.INTERVAL:
                interval_seconds = kwargs.get("interval", 3600)
            elif schedule_type == ScheduleType.HOURLY:
                interval_seconds = 3600
            elif schedule_type == ScheduleType.DAILY:
                interval_seconds = 86400
            elif schedule_type == ScheduleType.WEEKLY:
                interval_seconds = 604800

            task = ScheduleTask(
                integration_name=integration_name,
                schedule_type=schedule_type,
                interval_seconds=interval_seconds,
                next_run=next_run,
                enabled=kwargs.get("enabled", True),
            )

            self.scheduled_tasks[integration_name] = task

            self.logger.info(
                "スケジュール追加",
                integration_name=integration_name,
                schedule_type=schedule_type.value,
                next_run=next_run.isoformat() if next_run else None,
            )

            return True

        except Exception as e:
            self.logger.error(
                "スケジュール追加でエラー",
                integration_name=integration_name,
                error=str(e),
            )
            return False

    async def remove_schedule(self, integration_name: str) -> bool:
        """スケジュール削除"""
        try:
            if integration_name not in self.scheduled_tasks:
                self.logger.warning(f"未登録のスケジュール: {integration_name}")
                return False

            # 実行中のタスクがあればキャンセル
            if integration_name in self.running_tasks:
                task = self.running_tasks[integration_name]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self.running_tasks[integration_name]

            del self.scheduled_tasks[integration_name]

            self.logger.info("スケジュール削除", integration_name=integration_name)
            return True

        except Exception as e:
            self.logger.error(
                "スケジュール削除でエラー",
                integration_name=integration_name,
                error=str(e),
            )
            return False

    async def enable_schedule(self, integration_name: str) -> bool:
        """スケジュール有効化"""
        if integration_name not in self.scheduled_tasks:
            return False

        self.scheduled_tasks[integration_name].enabled = True
        self.logger.info("スケジュール有効化", integration_name=integration_name)
        return True

    async def disable_schedule(self, integration_name: str) -> bool:
        """スケジュール無効化"""
        if integration_name not in self.scheduled_tasks:
            return False

        self.scheduled_tasks[integration_name].enabled = False

        # 実行中のタスクをキャンセル
        if integration_name in self.running_tasks:
            task = self.running_tasks[integration_name]
            if not task.done():
                task.cancel()

        self.logger.info("スケジュール無効化", integration_name=integration_name)
        return True

    async def trigger_sync(
        self, integration_name: str, force: bool = False
    ) -> SyncResult | None:
        """手動同期トリガー"""
        if integration_name not in self.manager.integrations:
            self.logger.error(f"未登録の連携: {integration_name}")
            return None

        if integration_name in self.running_tasks and not force:
            self.logger.warning(f"連携は既に実行中: {integration_name}")
            return None

        self.logger.info("手動同期実行", integration_name=integration_name)

        async with self._semaphore:
            result = await self.manager.sync_integration(integration_name)

            # コールバック実行
            if result.success and self.on_sync_complete:
                self.on_sync_complete(result)
            elif not result.success and self.on_sync_error:
                self.on_sync_error(
                    integration_name, result.error_message or "不明なエラー"
                )

            return result

    async def _scheduler_loop(self) -> None:
        """メインスケジューラーループ"""
        self.logger.info("スケジューラーループ開始")

        while not self._stop_event.is_set():
            try:
                current_time = datetime.now()

                # 同期ウィンドウチェック
                if not self._is_in_sync_window(current_time):
                    await asyncio.sleep(self.config.check_interval)
                    continue

                # 実行対象タスク特定
                ready_tasks = [
                    task
                    for task in self.scheduled_tasks.values()
                    if (
                        task.enabled
                        and task.next_run
                        and task.next_run <= current_time
                        and task.integration_name not in self.running_tasks
                    )
                ]

                # 並列実行
                for task in ready_tasks:
                    if len(self.running_tasks) >= self.config.max_concurrent_tasks:
                        break

                    self.running_tasks[task.integration_name] = asyncio.create_task(
                        self._execute_scheduled_sync(task)
                    )

                # 完了したタスクをクリーンアップ
                completed_tasks = [
                    name for name, task in self.running_tasks.items() if task.done()
                ]

                for name in completed_tasks:
                    del self.running_tasks[name]

                await asyncio.sleep(self.config.check_interval)

            except Exception as e:
                self.logger.error(f"スケジューラーループでエラー: {str(e)}")
                await asyncio.sleep(self.config.check_interval)

    async def _execute_scheduled_sync(self, task: ScheduleTask) -> None:
        """スケジュール同期実行"""
        self.total_scheduled_runs += 1

        try:
            self.logger.info(
                "スケジュール同期開始",
                integration_name=task.integration_name,
                scheduled_time=task.next_run.isoformat() if task.next_run else None,
            )

            # セマフォで同時実行数制限
            async with self._semaphore:
                result = await self.manager.sync_integration(task.integration_name)

            # 結果処理
            if result.success:
                self.successful_runs += 1
                task.retry_count = 0  # リトライカウントリセット

                # コールバック実行
                if self.on_sync_complete:
                    self.on_sync_complete(result)

                self.logger.info(
                    "スケジュール同期成功",
                    integration_name=task.integration_name,
                    records=result.records_synced,
                    duration=f"{result.duration:.1f}s",
                )

            else:
                self.failed_runs += 1
                task.retry_count += 1

                # リトライ判定
                if task.retry_count < self.config.max_retry_attempts:
                    retry_delay = self.config.retry_delays[
                        min(task.retry_count - 1, len(self.config.retry_delays) - 1)
                    ]
                    task.next_run = datetime.now() + timedelta(seconds=retry_delay)

                    self.logger.warning(
                        "スケジュール同期失敗 - リトライ予定",
                        integration_name=task.integration_name,
                        retry_count=task.retry_count,
                        retry_at=task.next_run.isoformat(),
                        error=result.error_message,
                    )

                else:
                    self.logger.error(
                        "スケジュール同期失敗 - 最大リトライ回数に達しました",
                        integration_name=task.integration_name,
                        error=result.error_message,
                    )
                    task.retry_count = 0  # リトライカウントリセット

                # エラーコールバック実行
                if self.on_sync_error:
                    self.on_sync_error(
                        task.integration_name, result.error_message or "不明なエラー"
                    )

            # 成功時またはリトライ上限時に次回実行時刻更新
            if result.success or task.retry_count == 0:
                task.next_run = self._calculate_next_run_from_task(task)

            task.last_run = datetime.now()

        except Exception as e:
            self.failed_runs += 1
            self.logger.error(
                "スケジュール同期実行でエラー",
                integration_name=task.integration_name,
                error=str(e),
            )

            # エラー時も次回実行時刻更新
            task.next_run = self._calculate_next_run_from_task(task)
            task.last_run = datetime.now()

    def _calculate_next_run(
        self, schedule_type: ScheduleType, **kwargs
    ) -> datetime | None:
        """次回実行時刻計算"""
        now = datetime.now()

        if schedule_type == ScheduleType.MANUAL:
            return None

        elif schedule_type == ScheduleType.INTERVAL:
            interval = kwargs.get("interval", 3600)
            return now + timedelta(seconds=interval)

        elif schedule_type == ScheduleType.HOURLY:
            # 次の時間の 0 分に実行
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(
                hours=1
            )
            return next_hour

        elif schedule_type == ScheduleType.DAILY:
            # 指定時刻に実行（デフォルト 8 時）
            hour = kwargs.get("hour", 8)
            target_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)

            if target_time <= now:
                target_time += timedelta(days=1)

            return target_time

        elif schedule_type == ScheduleType.WEEKLY:
            # 週 1 回指定曜日・時刻に実行（デフォルト月曜 8 時）
            weekday = kwargs.get("weekday", 0)  # 0=月曜
            hour = kwargs.get("hour", 8)

            days_ahead = weekday - now.weekday()
            if days_ahead <= 0:  # 今日が対象曜日またはそれより後
                days_ahead += 7

            target_time = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            target_time += timedelta(days=days_ahead)

            return target_time

        return None

    def _calculate_next_run_from_task(self, task: ScheduleTask) -> datetime | None:
        """タスクから次回実行時刻を計算"""
        if task.schedule_type == ScheduleType.MANUAL:
            return None

        elif task.schedule_type == ScheduleType.INTERVAL and task.interval_seconds:
            return datetime.now() + timedelta(seconds=task.interval_seconds)

        elif task.schedule_type == ScheduleType.HOURLY:
            now = datetime.now()
            return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        elif task.schedule_type == ScheduleType.DAILY:
            return datetime.now() + timedelta(days=1)

        elif task.schedule_type == ScheduleType.WEEKLY:
            return datetime.now() + timedelta(weeks=1)

        return None

    def _is_in_sync_window(self, current_time: datetime) -> bool:
        """同期ウィンドウ内かチェック"""
        current_hour = current_time.hour

        if self.config.sync_window_start <= self.config.sync_window_end:
            # 同日内ウィンドウ（例： 6 時〜 23 時）
            return (
                self.config.sync_window_start
                <= current_hour
                <= self.config.sync_window_end
            )
        else:
            # 日跨ぎウィンドウ（例： 23 時〜 6 時）
            return (
                current_hour >= self.config.sync_window_start
                or current_hour <= self.config.sync_window_end
            )

    def get_schedule_status(self) -> dict[str, Any]:
        """スケジュール状況取得"""
        return {
            "scheduler_running": bool(
                self._scheduler_task and not self._scheduler_task.done()
            ),
            "total_schedules": len(self.scheduled_tasks),
            "enabled_schedules": sum(
                1 for task in self.scheduled_tasks.values() if task.enabled
            ),
            "running_tasks": len(self.running_tasks),
            "statistics": {
                "total_scheduled_runs": self.total_scheduled_runs,
                "successful_runs": self.successful_runs,
                "failed_runs": self.failed_runs,
                "success_rate": (
                    self.successful_runs / self.total_scheduled_runs * 100
                    if self.total_scheduled_runs > 0
                    else 0
                ),
            },
            "schedules": {
                name: {
                    "schedule_type": task.schedule_type.value,
                    "enabled": task.enabled,
                    "next_run": task.next_run.isoformat() if task.next_run else None,
                    "last_run": task.last_run.isoformat() if task.last_run else None,
                    "retry_count": task.retry_count,
                    "currently_running": name in self.running_tasks,
                }
                for name, task in self.scheduled_tasks.items()
            },
        }

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
