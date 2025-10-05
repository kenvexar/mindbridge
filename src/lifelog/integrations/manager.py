"""
外部連携管理システム

全ての外部連携を統合管理するためのマネージャークラス
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import structlog
from pydantic import BaseModel, Field

from src.integrations.base import integration_registry, register_integration

from .base import BaseIntegration, IntegrationConfig
from .garmin import GarminIntegration
from .google_calendar import GoogleCalendarIntegration

logger = structlog.get_logger(__name__)


@dataclass
class SyncResult:
    """同期結果"""

    integration_name: str
    success: bool
    records_synced: int
    duration: float
    error_message: str | None = None


class IntegrationManagerConfig(BaseModel):
    """統合管理設定"""

    # グローバル設定
    max_concurrent_syncs: int = Field(default=3, description="最大同時同期数")
    default_sync_interval: int = Field(
        default=3600, description="デフォルト同期間隔（秒）"
    )
    global_timeout: int = Field(default=300, description="グローバルタイムアウト（秒）")

    # エラーハンドリング
    max_retry_attempts: int = Field(default=3, description="最大リトライ回数")
    retry_delay: int = Field(default=60, description="リトライ遅延（秒）")

    # データ管理
    max_historical_days: int = Field(default=90, description="最大履歴保持日数")
    cleanup_interval: int = Field(default=86400, description="クリーンアップ間隔（秒）")

    # 通知設定
    notify_on_errors: bool = Field(default=True, description="エラー通知")
    notify_on_success: bool = Field(default=False, description="成功通知")


class IntegrationManager:
    """外部連携統合管理システム"""

    def __init__(self, config: IntegrationManagerConfig):
        self.config = config
        self.logger = structlog.get_logger(__name__)
        self.integrations: dict[str, BaseIntegration] = {}
        self._sync_lock = asyncio.Lock()
        self._sync_tasks: dict[str, asyncio.Task] = {}
        self._last_cleanup = datetime.now()

        # 統計情報
        self.sync_history: list[SyncResult] = []
        self.total_syncs = 0
        self.total_records = 0
        self.total_errors = 0

    async def register_integration(
        self, integration_name: str, integration_config: IntegrationConfig
    ) -> bool:
        """外部連携を登録"""
        try:
            factory = integration_registry.get(integration_name)
            if factory is None:
                self.logger.error(
                    "未対応の連携タイプ",
                    integration_name=integration_name,
                    available=list(integration_registry.available().keys()),
                )
                return False

            # 連携インスタンス作成
            integration = factory(integration_config)

            # 設定検証
            validation_errors = await integration.validate_config()
            if validation_errors:
                self.logger.error(
                    "連携設定検証エラー",
                    integration_name=integration_name,
                    errors=validation_errors,
                )
                return False

            # 認証テスト
            if integration_config.enabled:
                auth_success = await integration.authenticate()
                if not auth_success:
                    self.logger.warning(
                        "連携認証に失敗しましたが、登録は継続します",
                        integration_name=integration_name,
                    )

            self.integrations[integration_name] = integration
            self.logger.info("連携を正常に登録", integration_name=integration_name)
            return True

        except Exception as e:
            self.logger.error(
                "連携登録でエラー", integration_name=integration_name, error=str(e)
            )
            return False

    async def unregister_integration(self, integration_name: str) -> bool:
        """外部連携を登録解除"""
        try:
            if integration_name not in self.integrations:
                self.logger.warning("未登録の連携", integration_name=integration_name)
                return False

            # 実行中の同期タスクを停止
            if integration_name in self._sync_tasks:
                task = self._sync_tasks[integration_name]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self._sync_tasks[integration_name]

            # 連携インスタンス削除
            integration = self.integrations[integration_name]
            if hasattr(integration, "__aexit__"):
                await integration.__aexit__(None, None, None)

            del self.integrations[integration_name]
            self.logger.info("連携を正常に登録解除", integration_name=integration_name)
            return True

        except Exception as e:
            self.logger.error(
                "連携登録解除でエラー", integration_name=integration_name, error=str(e)
            )
            return False

    async def sync_integration(
        self,
        integration_name: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        force_sync: bool = False,
    ) -> SyncResult:
        """特定の連携を同期"""
        sync_start = datetime.now()

        if integration_name not in self.integrations:
            error_msg = f"未登録の連携: {integration_name}"
            self.logger.error(error_msg)
            return SyncResult(
                integration_name=integration_name,
                success=False,
                records_synced=0,
                duration=0,
                error_message=error_msg,
            )

        integration = self.integrations[integration_name]

        try:
            # 同期ロック取得
            async with self._sync_lock:
                # 認証確認
                if not await integration.is_authenticated():
                    if not await integration.authenticate():
                        error_msg = f"認証に失敗: {integration_name}"
                        return SyncResult(
                            integration_name=integration_name,
                            success=False,
                            records_synced=0,
                            duration=(datetime.now() - sync_start).total_seconds(),
                            error_message=error_msg,
                        )

                # 同期実行
                synced_data = await integration.sync_data(start_date, end_date)
                records_count = len(synced_data)

                # 統計更新
                self.total_syncs += 1
                self.total_records += records_count

                sync_duration = (datetime.now() - sync_start).total_seconds()
                result = SyncResult(
                    integration_name=integration_name,
                    success=True,
                    records_synced=records_count,
                    duration=sync_duration,
                )

                self.sync_history.append(result)

                self.logger.info(
                    "連携同期完了",
                    integration_name=integration_name,
                    records=records_count,
                    duration=f"{sync_duration:.1f}s",
                )

                return result

        except Exception as e:
            self.total_errors += 1
            sync_duration = (datetime.now() - sync_start).total_seconds()

            error_msg = f"同期エラー: {str(e)}"
            integration.add_error(error_msg)

            result = SyncResult(
                integration_name=integration_name,
                success=False,
                records_synced=0,
                duration=sync_duration,
                error_message=error_msg,
            )

            self.sync_history.append(result)

            self.logger.error(
                "連携同期でエラー",
                integration_name=integration_name,
                error=str(e),
                duration=f"{sync_duration:.1f}s",
            )

            return result

    async def sync_all_integrations(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        force_sync: bool = False,
    ) -> list[SyncResult]:
        """全ての連携を並行同期"""
        enabled_integrations = [
            name
            for name, integration in self.integrations.items()
            if integration.config.enabled
        ]

        if not enabled_integrations:
            self.logger.warning("有効な連携がありません")
            return []

        self.logger.info(f"全連携同期開始: {len(enabled_integrations)}件")

        # セマフォで同時実行数を制限
        semaphore = asyncio.Semaphore(self.config.max_concurrent_syncs)

        async def sync_with_semaphore(integration_name: str) -> SyncResult:
            async with semaphore:
                return await self.sync_integration(
                    integration_name, start_date, end_date, force_sync
                )

        # 並行実行
        tasks = [sync_with_semaphore(name) for name in enabled_integrations]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 例外を結果に変換
        sync_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                integration_name = enabled_integrations[i]
                sync_results.append(
                    SyncResult(
                        integration_name=integration_name,
                        success=False,
                        records_synced=0,
                        duration=0,
                        error_message=str(result),
                    )
                )
            elif isinstance(result, SyncResult):
                sync_results.append(result)

        successful = sum(1 for r in sync_results if r.success)
        total_records = sum(r.records_synced for r in sync_results)

        self.logger.info(
            "全連携同期完了",
            successful=successful,
            total=len(sync_results),
            records=total_records,
        )

        return sync_results

    async def get_integration_status(
        self, integration_name: str
    ) -> dict[str, Any] | None:
        """連携ステータス取得"""
        if integration_name not in self.integrations:
            return None

        integration = self.integrations[integration_name]
        health_info = await integration.get_health_info()

        # 最近の同期結果
        recent_syncs = [
            result
            for result in self.sync_history[-10:]
            if result.integration_name == integration_name
        ]

        return {
            **health_info,
            "config": {
                "enabled": integration.config.enabled,
                "sync_interval": integration.config.sync_interval,
                "last_sync": integration.config.last_sync.isoformat()
                if integration.config.last_sync
                else None,
            },
            "recent_syncs": [
                {
                    "success": sync.success,
                    "records": sync.records_synced,
                    "duration": sync.duration,
                    "error": sync.error_message,
                }
                for sync in recent_syncs
            ],
        }

    async def get_all_integration_status(self) -> dict[str, Any]:
        """全連携ステータス取得"""
        status = {}

        for name in self.integrations.keys():
            integration_status = await self.get_integration_status(name)
            if integration_status:
                status[name] = integration_status

        # 統計情報追加
        status["_summary"] = {
            "total_integrations": len(self.integrations),
            "enabled_integrations": sum(
                1 for i in self.integrations.values() if i.config.enabled
            ),
            "total_syncs": self.total_syncs,
            "total_records": self.total_records,
            "total_errors": self.total_errors,
            "recent_sync_history": [
                {
                    "integration": sync.integration_name,
                    "success": sync.success,
                    "records": sync.records_synced,
                    "duration": sync.duration,
                }
                for sync in self.sync_history[-5:]
            ],
        }

        return status

    async def cleanup_old_data(self) -> int:
        """古いデータのクリーンアップ"""
        if (datetime.now() - self._last_cleanup).seconds < self.config.cleanup_interval:
            return 0

        cleaned_records = 0

        try:
            # 同期履歴クリーンアップ
            cutoff_date = datetime.now() - timedelta(
                days=self.config.max_historical_days
            )
            original_count = len(self.sync_history)
            self.sync_history = [
                sync
                for sync in self.sync_history
                if datetime.now() - timedelta(seconds=sync.duration) > cutoff_date
            ]
            cleaned_records += original_count - len(self.sync_history)

            # 各連携のクリーンアップ
            for integration in self.integrations.values():
                await integration.cleanup_old_data()

            self._last_cleanup = datetime.now()

            self.logger.info(f"クリーンアップ完了: {cleaned_records}件削除")

        except Exception as e:
            self.logger.error(f"クリーンアップでエラー: {str(e)}")

        return cleaned_records

    async def health_check(self) -> dict[str, Any]:
        """ヘルスチェック"""
        healthy_count = 0
        unhealthy_integrations = []

        for name, integration in self.integrations.items():
            if not integration.config.enabled:
                continue

            try:
                if await integration.test_connection():
                    healthy_count += 1
                else:
                    unhealthy_integrations.append(name)
            except Exception as e:
                unhealthy_integrations.append(f"{name} ({str(e)})")

        total_enabled = sum(1 for i in self.integrations.values() if i.config.enabled)

        return {
            "healthy": healthy_count == total_enabled,
            "healthy_integrations": healthy_count,
            "total_enabled": total_enabled,
            "unhealthy_integrations": unhealthy_integrations,
            "manager_stats": {
                "total_syncs": self.total_syncs,
                "total_records": self.total_records,
                "total_errors": self.total_errors,
                "sync_history_size": len(self.sync_history),
            },
        }

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # 全ての連携を適切に終了
        for integration_name in list(self.integrations.keys()):
            await self.unregister_integration(integration_name)

        # 実行中のタスクをキャンセル
        for task in self._sync_tasks.values():
            if not task.done():
                task.cancel()

        if self._sync_tasks:
            await asyncio.gather(*self._sync_tasks.values(), return_exceptions=True)


register_integration("garmin", GarminIntegration)
register_integration("google_calendar", GoogleCalendarIntegration)
