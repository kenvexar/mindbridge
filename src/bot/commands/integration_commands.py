"""
外部連携制御用 Discord コマンド

外部連携の状態確認、同期実行、設定管理を行うコマンド群
"""

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import discord
import structlog
from discord.ext import commands

from ...config.settings import Settings
from ...lifelog.integrations.base import IntegrationConfig
from ...lifelog.integrations.manager import IntegrationManager
from ...lifelog.integrations.pipelines.scheduler import (
    IntegrationSyncScheduler,
    ScheduleType,
)
from ...lifelog.manager import LifelogManager
from ...monitoring.health_server import OAuthCodeVault
from ...security.simple_admin import admin_required

logger = structlog.get_logger(__name__)


class IntegrationCommands(commands.Cog):
    """外部連携制御コマンド"""

    def __init__(self, bot, settings: Settings):
        self.bot = bot
        self.settings = settings

        # 外部連携システム（遅延初期化）
        self.integration_manager: IntegrationManager | None = None
        self.scheduler: IntegrationSyncScheduler | None = None
        self.lifelog_manager: LifelogManager | None = None

        self._initialized = False
        self._calendar_env_cache: tuple[str, str, str, str] | None = None

    def _hydrate_google_calendar_from_env(self):
        """環境変数の Google Calendar 認証情報を統合へ反映"""
        if not self.integration_manager:
            return None

        integration = self.integration_manager.integrations.get("google_calendar")
        if integration is None:
            return None

        env_access = os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN", "").strip()
        env_refresh = os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN", "").strip()
        env_client_id = os.getenv("GOOGLE_CALENDAR_CLIENT_ID", "").strip()
        env_client_secret = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET", "").strip()

        cache = (env_access, env_refresh, env_client_id, env_client_secret)
        if self._calendar_env_cache == cache:
            return integration

        config = integration.config
        updated = False

        if env_client_id and env_client_id != (config.client_id or ""):
            config.client_id = env_client_id
            updated = True

        if env_client_secret and env_client_secret != (config.client_secret or ""):
            config.client_secret = env_client_secret
            updated = True

        if env_access and env_access != (config.access_token or ""):
            config.access_token = env_access
            updated = True

        if env_refresh and env_refresh != (config.refresh_token or ""):
            config.refresh_token = env_refresh
            updated = True

        if updated:
            config.enabled = bool(config.access_token or config.refresh_token)
            integration._authenticated = False
            self._calendar_env_cache = cache

        return integration

    async def _ensure_initialized(self):
        """外部連携システムの初期化を確認"""
        if self._initialized:
            return

        try:
            # 設定読み込み（エラーハンドリング強化）
            try:
                from ...lifelog.integrations.manager import IntegrationManagerConfig
                from ...lifelog.integrations.pipelines.scheduler import (
                    IntegrationSyncSchedulerConfig,
                )

                manager_config = IntegrationManagerConfig()
                scheduler_config = IntegrationSyncSchedulerConfig()
            except Exception as e:
                logger.warning(f"設定読み込みに失敗、デフォルト設定を使用: {e}")
                # デフォルト設定を使用
                from ...lifelog.integrations.manager import IntegrationManagerConfig
                from ...lifelog.integrations.pipelines.scheduler import (
                    IntegrationSyncSchedulerConfig,
                )

                manager_config = IntegrationManagerConfig()
                scheduler_config = IntegrationSyncSchedulerConfig()

            # マネージャー初期化（エラーハンドリング）
            try:
                self.integration_manager = IntegrationManager(manager_config)
            except Exception as e:
                logger.warning(f"IntegrationManager 初期化失敗: {e}")
                self.integration_manager = None

            # LifelogManager 初期化（オプション）
            try:
                self.lifelog_manager = LifelogManager(self.settings)
                await self.lifelog_manager.initialize()
            except Exception as e:
                logger.warning(f"LifelogManager 初期化失敗: {e}")
                self.lifelog_manager = None

            # スケジューラー初期化（ IntegrationManager が必要）
            if self.integration_manager:
                try:
                    self.scheduler = IntegrationSyncScheduler(
                        self.integration_manager, scheduler_config
                    )
                except Exception as e:
                    logger.warning(f"IntegrationSyncScheduler 初期化失敗: {e}")
                    self.scheduler = None

                # デフォルト連携を登録
                try:
                    await self._setup_default_integrations()
                except Exception as e:
                    logger.warning(f"デフォルト連携登録失敗: {e}")

            self._initialized = True
            logger.info(
                "外部連携システムを初期化しました（一部機能は制限される可能性があります）"
            )

        except Exception as e:
            logger.error(f"外部連携システムの初期化に失敗: {e}")
            # 最低限の状態で動作を継続
            self._initialized = True

    async def _store_google_calendar_tokens_in_secret_manager(
        self, access_token: str, refresh_token: str
    ) -> bool:
        """Save Google Calendar tokens to Google Secret Manager when available."""

        strategy = (self.settings.secret_manager_strategy or "env").lower()
        if strategy not in {"google", "gcp", "google-secret-manager"}:
            logger.info(
                "Secret Manager strategy is not Google; skipping token persistence",
                strategy=strategy,
            )
            return False

        project_id = (
            self.settings.secret_manager_project_id
            or os.getenv("SECRET_MANAGER_PROJECT_ID", "").strip()
        )
        if not project_id:
            logger.warning(
                "SECRET_MANAGER_PROJECT_ID が設定されていないためトークン保存をスキップ"
            )
            return False

        try:  # pragma: no cover - optional dependency
            from google.api_core import exceptions as google_exceptions
            from google.cloud import secretmanager
        except ImportError as exc:  # pragma: no cover - optional dependency
            logger.warning(
                "google-cloud-secret-manager が利用できないためトークン保存をスキップ",
                error=str(exc),
            )
            return False

        client: Any | None = None
        stored_all = True
        secrets_payload = {
            "google-calendar-access-token": access_token,
            "google-calendar-refresh-token": refresh_token,
        }

        try:
            client = secretmanager.SecretManagerServiceAsyncClient()

            for secret_name, value in secrets_payload.items():
                parent = f"projects/{project_id}/secrets/{secret_name}"
                try:
                    await client.add_secret_version(
                        request={
                            "parent": parent,
                            "payload": {"data": value.encode("utf-8")},
                        }
                    )
                except google_exceptions.NotFound:
                    await client.create_secret(
                        request={
                            "parent": f"projects/{project_id}",
                            "secret_id": secret_name,
                            "secret": {"replication": {"automatic": {}}},
                        }
                    )
                    await client.add_secret_version(
                        request={
                            "parent": parent,
                            "payload": {"data": value.encode("utf-8")},
                        }
                    )
                except google_exceptions.PermissionDenied as exc:
                    stored_all = False
                    logger.warning(
                        "Permission denied while accessing Secret Manager",
                        secret=secret_name,
                        project_id=project_id,
                        error=str(exc),
                    )
                    continue

                logger.info(
                    "Stored Google Calendar token in Secret Manager",
                    secret=secret_name,
                    project_id=project_id,
                )

        except Exception as exc:  # pragma: no cover - defensive
            stored_all = False
            logger.warning(
                "Failed to persist Google Calendar tokens to Secret Manager",
                error=str(exc),
            )
        finally:
            if client is not None:
                close_method = getattr(client, "close", None)
                if callable(close_method):
                    maybe_coroutine = close_method()
                    if asyncio.iscoroutine(maybe_coroutine):
                        await maybe_coroutine
                else:  # pragmatic fallback for older client versions
                    transport = getattr(client, "transport", None)
                    if transport is not None:
                        transport_close = getattr(transport, "close", None)
                        if callable(transport_close):
                            maybe_coroutine = transport_close()
                            if asyncio.iscoroutine(maybe_coroutine):
                                await maybe_coroutine

        return stored_all

    async def _setup_default_integrations(self):
        """デフォルト外部連携を設定"""
        # mypy: integration_manager は _ensure_initialized 内で初期化済みだが、
        # 本メソッド単体では Optional なので明示的にガード
        if self.integration_manager is None:
            logger.warning(
                "IntegrationManager 未初期化のためデフォルト連携登録をスキップ"
            )
            return

        # 設定から外部連携情報を読み込み（将来的に設定ファイル化）
        # 設定ファイルから外部連携設定を読み込み
        import json

        settings_path = "/app/.mindbridge/integrations/settings.json"
        file_settings = {}
        if os.path.exists(settings_path):
            try:
                with open(settings_path) as f:
                    file_settings = json.load(f)
                logger.info(
                    f"設定ファイルから {len(file_settings)} の連携設定を読み込み"
                )
                logger.info(f"ファイル設定内容: {file_settings}")
            except Exception as e:
                logger.warning(f"設定ファイル読み込みエラー: {e}")
        env_calendar_access = os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN", "").strip()
        env_calendar_refresh = os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN", "").strip()
        env_calendar_client_id = os.getenv("GOOGLE_CALENDAR_CLIENT_ID", "").strip()
        env_calendar_client_secret = os.getenv(
            "GOOGLE_CALENDAR_CLIENT_SECRET", ""
        ).strip()

        default_integrations = {
            "garmin": {
                "enabled": True,  # Garmin 統合を有効化
                "sync_interval": 3600,
                "custom_settings": {
                    "garmin": {
                        "sync_activities": True,
                        "sync_health_data": True,
                        "activity_types": [
                            "running",
                            "cycling",
                            "walking",
                            "strength_training",
                        ],
                    }
                },
            },
            "google_calendar": {
                # OAuth トークンが未設定の場合は無効化状態で登録しておく
                "enabled": bool(env_calendar_access),
                "sync_interval": 1800,  # 30 分間隔
                "custom_settings": {
                    "google_calendar": {
                        "calendars": ["primary"],  # デフォルトはプライマリのみ
                        "auto_discover_calendars": True,  # 自動検出を有効
                        "sync_selected_only": True,  # 選択されたカレンダーのみ同期
                        "sync_past_events": True,
                        "sync_all_day_events": True,
                        "min_duration_minutes": 5,
                        "exclude_keywords": [],
                    }
                },
            },
            "financial": {
                "enabled": False,
                "sync_interval": 7200,  # 2 時間間隔
                "custom_settings": {
                    "financial": {
                        "sources": ["generic_api"],
                        "min_amount": 500,
                        "exclude_categories": ["Transfer", "Internal"],
                    }
                },
            },
        }

        # ファイル設定でデフォルト設定を上書き
        for name, config in file_settings.items():
            if name in default_integrations:
                default_integrations[name].update(config)
                logger.info(
                    f"連携 {name} を更新: enabled={config.get('enabled', False)}"
                )
            else:
                default_integrations[name] = config
                logger.info(
                    f"連携 {name} を追加: enabled={config.get('enabled', False)}"
                )

        for integration_name, config_data in default_integrations.items():
            integration_config = IntegrationConfig(
                integration_name=integration_name,
                enabled=config_data.get("enabled", False),
                sync_interval=config_data.get("sync_interval", 3600),
                custom_settings=config_data.get("custom_settings", {}),
            )

            if integration_name == "google_calendar":
                # `.env` の資格情報を設定に反映
                if env_calendar_client_id:
                    integration_config.client_id = env_calendar_client_id
                if env_calendar_client_secret:
                    integration_config.client_secret = env_calendar_client_secret
                if env_calendar_access:
                    integration_config.access_token = env_calendar_access
                if env_calendar_refresh:
                    integration_config.refresh_token = env_calendar_refresh

                # 認証情報が不足している場合は有効化をオフにする
                if integration_config.enabled and not integration_config.access_token:
                    integration_config.enabled = False

            await self.integration_manager.register_integration(
                integration_name, integration_config
            )

    def _google_token_vault_path(self) -> Path:
        """Google Calendar トークンの暗号化保存先"""
        return Path("logs") / "google_calendar_tokens.enc"

    def _persist_google_calendar_tokens(
        self, access_token: str, refresh_token: str
    ) -> tuple[bool, str]:
        """Google Calendar トークンを暗号化して保存する"""
        vault = OAuthCodeVault(storage_path=self._google_token_vault_path())
        stored_path = vault.store_secret_blob(
            "google_calendar_tokens",
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "stored_at": datetime.now().isoformat(),
            },
        )

        if stored_path:
            return True, str(stored_path)
        return False, str(self._google_token_vault_path())

    async def _save_integration_settings(self):
        """統合設定をファイルに保存"""
        if self.integration_manager is None:
            logger.warning("IntegrationManager未初期化のため設定保存をスキップ")
            return False

        try:
            import json
            from pathlib import Path

            import aiofiles

            # 設定ディレクトリの確保
            settings_dir = Path("/app/.mindbridge/integrations")
            settings_dir.mkdir(parents=True, exist_ok=True)
            settings_path = settings_dir / "settings.json"

            # 現在の設定を辞書形式で取得
            current_settings = {}
            for (
                integration_name,
                integration_obj,
            ) in self.integration_manager.integrations.items():
                config = integration_obj.config
                current_settings[integration_name] = {
                    "enabled": config.enabled,
                    "sync_interval": config.sync_interval,
                    "custom_settings": config.custom_settings,
                    "last_sync": config.last_sync.isoformat()
                    if config.last_sync
                    else None,
                    "auth_type": config.auth_type,
                }

            # 非同期でファイルに保存
            async with aiofiles.open(settings_path, "w") as f:
                await f.write(
                    json.dumps(current_settings, indent=2, ensure_ascii=False)
                )

            logger.info(
                f"統合設定を保存しました: {len(current_settings)}件の設定をファイルに保存"
            )
            return True

        except Exception as e:
            logger.error("統合設定の保存でエラー", error=str(e))
            return False

    @discord.app_commands.command(
        name="integration_status", description="外部連携の状態を確認"
    )
    @admin_required
    async def integration_status(self, interaction: discord.Interaction):
        """外部連携の状態を表示"""
        await interaction.response.defer()

        try:
            await self._ensure_initialized()

            # 全連携の状態取得
            if self.integration_manager is None:
                await interaction.followup.send(
                    "❌ Integration Manager が初期化されていません"
                )
                return

            status_data = await self.integration_manager.get_all_integration_status()

            # 埋め込みメッセージ作成
            embed = discord.Embed(
                title="🔗 外部連携状態",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            summary = status_data.get("_summary", {})
            embed.add_field(
                name="📊 概要",
                value=(
                    f"**総連携数**: {summary.get('total_integrations', 0)}\n"
                    f"**有効連携数**: {summary.get('enabled_integrations', 0)}\n"
                    f"**総同期回数**: {summary.get('total_syncs', 0)}\n"
                    f"**総取得レコード数**: {summary.get('total_records', 0)}\n"
                    f"**エラー回数**: {summary.get('total_errors', 0)}"
                ),
                inline=False,
            )

            # 各連携の詳細
            for integration_name, integration_data in status_data.items():
                if integration_name == "_summary":
                    continue

                config = integration_data.get("config", {})
                enabled_icon = "✅" if config.get("enabled") else "❌"
                status_icon = self._get_status_icon(integration_data.get("status"))

                last_sync = config.get("last_sync")
                if last_sync:
                    last_sync_str = (
                        f"<t:{int(datetime.fromisoformat(last_sync).timestamp())}:R>"
                    )
                else:
                    last_sync_str = "未同期"

                recent_syncs = integration_data.get("recent_syncs", [])
                success_count = sum(1 for sync in recent_syncs if sync.get("success"))

                embed.add_field(
                    name=f"{enabled_icon} {status_icon} {integration_name.title()}",
                    value=(
                        f"**ステータス**: {integration_data.get('status', 'unknown')}\n"
                        f"**最終同期**: {last_sync_str}\n"
                        f"**同期間隔**: {config.get('sync_interval', 0)}秒\n"
                        f"**最近の成功率**: {success_count}/{len(recent_syncs)}"
                    ),
                    inline=True,
                )

            # ヘルスチェック実行
            if self.integration_manager is None:
                await interaction.followup.send(
                    "❌ Integration Manager が初期化されていません"
                )
                return

            health = await self.integration_manager.health_check()
            health_icon = "🟢" if health.get("healthy") else "🔴"

            embed.add_field(
                name=f"{health_icon} システムヘルス",
                value=(
                    f"**健全な連携**: {health.get('healthy_integrations', 0)}"
                    f"/{health.get('total_enabled', 0)}\n"
                    f"**同期履歴サイズ**: {health.get('manager_stats', {}).get('sync_history_size', 0)}"
                ),
                inline=False,
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("外部連携状態確認でエラー", error=str(e))
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")

    @discord.app_commands.command(
        name="system_status", description="システム全体の状態を確認"
    )
    @admin_required
    async def system_status(self, interaction: discord.Interaction):
        """システム全体の状態を表示"""
        await interaction.response.defer()

        try:
            await self._ensure_initialized()

            # 基本的な状態確認
            embed = discord.Embed(
                title="🔧 システム状態",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )

            # Bot の状態
            embed.add_field(
                name="🤖 Bot",
                value=f"**ステータス**: ✅ オンライン\n**ユーザー**: {self.bot.user.name}\n**サーバー数**: {len(self.bot.guilds)}",
                inline=True,
            )

            # Integration Manager の状態
            if self.integration_manager:
                status_data = (
                    await self.integration_manager.get_all_integration_status()
                )
                summary = status_data.get("_summary", {})

                embed.add_field(
                    name="🔗 連携",
                    value=f"**有効連携**: {summary.get('enabled_integrations', 0)}\n**総同期回数**: {summary.get('total_syncs', 0)}\n**エラー回数**: {summary.get('total_errors', 0)}",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="🔗 連携",
                    value="❌ 未初期化",
                    inline=True,
                )

            # Scheduler の状態
            if self.scheduler:
                embed.add_field(
                    name="⏰ スケジューラー",
                    value="✅ 稼働中",
                    inline=True,
                )
            else:
                embed.add_field(
                    name="⏰ スケジューラー",
                    value="❌ 未初期化",
                    inline=True,
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("システム状態確認でエラー", error=str(e))
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")

    @discord.app_commands.command(
        name="manual_sync", description="外部連携の手動同期を実行"
    )
    @discord.app_commands.describe(
        integration="同期する外部連携名（省略時は全て）",
        force="強制実行（実行中でも再実行）",
    )
    @admin_required
    async def manual_sync(
        self,
        interaction: discord.Interaction,
        integration: str | None = None,
        force: bool = False,
    ) -> None:
        """外部連携の手動同期"""
        await interaction.response.defer()

        try:
            await self._ensure_initialized()

            if integration:
                # 特定の連携を同期
                if self.integration_manager is None:
                    await interaction.followup.send(
                        "❌ Integration Manager が初期化されていません"
                    )
                    return

                if integration not in self.integration_manager.integrations:
                    available = ", ".join(self.integration_manager.integrations.keys())
                    await interaction.followup.send(
                        f"❌ 連携 '{integration}' が見つかりません。\n"
                        f"利用可能: {available}"
                    )
                    return

                embed = discord.Embed(
                    title=f"🔄 {integration.title()} 同期実行中...",
                    color=discord.Color.orange(),
                )
                message = await interaction.followup.send(embed=embed)  # type: ignore[func-returns-value]  # type: ignore[assignment,func-returns-value]

                if self.integration_manager is None:
                    await interaction.followup.send(
                        "❌ Integration Manager が初期化されていません"
                    )
                    return

                result = await self.integration_manager.sync_integration(
                    integration, force_sync=force
                )

                # 結果表示
                if result.success:
                    embed.colour = discord.Color.green()
                    embed.title = f"✅ {integration.title()} 同期完了"
                    embed.add_field(
                        name="結果",
                        value=(
                            f"**取得レコード数**: {result.records_synced}\n"
                            f"**実行時間**: {result.duration:.1f}秒"
                        ),
                    )

                    # ライフログに統合
                    if result.records_synced > 0 and self.lifelog_manager:
                        try:
                            # IntegrationManagerから統合データを取得
                            integration_obj = self.integration_manager.integrations.get(
                                integration
                            )
                            if integration_obj:
                                # 最新のデータを取得してライフログに統合
                                from datetime import datetime, timedelta

                                end_date = datetime.now()
                                start_date = end_date - timedelta(days=1)  # 過去1日分

                                base_integration_data = await integration_obj.sync_data(
                                    start_date, end_date
                                )

                                if base_integration_data:
                                    # base.IntegrationData を models.IntegrationData に変換
                                    from ...lifelog.integrations.models import (
                                        IntegrationData as ModelsIntegrationData,
                                    )

                                    models_integration_data = []
                                    for base_data in base_integration_data:
                                        models_data = ModelsIntegrationData(
                                            integration_type=base_data.integration_name,
                                            source_id=base_data.external_id,
                                            timestamp=base_data.timestamp,
                                            data=base_data.raw_data,
                                            metadata=base_data.processed_data,
                                        )
                                        models_integration_data.append(models_data)

                                    integrated_count = await self.lifelog_manager.integrate_external_data(
                                        models_integration_data
                                    )
                                    if integrated_count > 0:
                                        embed.add_field(
                                            name="ライフログ統合",
                                            value=f"✅ {integrated_count}件のデータをライフログに統合しました",
                                            inline=False,
                                        )
                        except Exception as e:
                            logger.error("ライフログ統合でエラー", error=str(e))
                            embed.add_field(
                                name="ライフログ統合",
                                value="⚠️ ライフログ統合でエラーが発生しました",
                                inline=False,
                            )

                else:
                    embed.colour = discord.Color.red()
                    embed.title = f"❌ {integration.title()} 同期失敗"
                    embed.add_field(
                        name="エラー", value=result.error_message or "不明なエラー"
                    )

                if message:
                    await message.edit(embed=embed)
                else:
                    await interaction.followup.send(embed=embed)

            else:
                # 全連携を同期
                embed = discord.Embed(
                    title="🔄 全外部連携同期実行中...", color=discord.Color.orange()
                )
                message = await interaction.followup.send(embed=embed)  # type: ignore[func-returns-value]  # type: ignore[assignment,func-returns-value]

                if self.integration_manager is None:
                    await interaction.followup.send(
                        "❌ Integration Manager が初期化されていません"
                    )
                    return

                results = await self.integration_manager.sync_all_integrations(
                    force_sync=force
                )

                # 結果集計
                successful = sum(1 for r in results if r.success)
                total_records = sum(r.records_synced for r in results)
                total_duration = sum(r.duration for r in results)

                if successful == len(results):
                    embed.colour = discord.Color.green()
                    embed.title = "✅ 全外部連携同期完了"
                else:
                    embed.colour = discord.Color.yellow()
                    embed.title = (
                        f"⚠️ 外部連携同期完了 ({successful}/{len(results)} 成功)"
                    )

                embed.add_field(
                    name="📊 結果サマリー",
                    value=(
                        f"**成功**: {successful}/{len(results)}\n"
                        f"**総取得レコード数**: {total_records}\n"
                        f"**総実行時間**: {total_duration:.1f}秒"
                    ),
                    inline=False,
                )

                # 個別結果
                for result in results:
                    status_icon = "✅" if result.success else "❌"
                    embed.add_field(
                        name=f"{status_icon} {result.integration_name.title()}",
                        value=(
                            f"レコード数: {result.records_synced}\n"
                            f"時間: {result.duration:.1f}秒"
                        ),
                        inline=True,
                    )

                if message:
                    await message.edit(embed=embed)
                else:
                    await interaction.followup.send(embed=embed)

                # ライフログ統合（成功した分のみ）
                if self.lifelog_manager:
                    total_integrated = 0
                    for result in results:
                        if result.success and result.records_synced > 0:
                            try:
                                # IntegrationManagerから統合データを取得
                                integration_obj = (
                                    self.integration_manager.integrations.get(
                                        result.integration_name
                                    )
                                )
                                if integration_obj:
                                    # 最新のデータを取得してライフログに統合
                                    from datetime import datetime, timedelta

                                    end_date = datetime.now()
                                    start_date = end_date - timedelta(
                                        days=1
                                    )  # 過去1日分

                                    base_integration_data = (
                                        await integration_obj.sync_data(
                                            start_date, end_date
                                        )
                                    )

                                    if base_integration_data:
                                        # base.IntegrationData を models.IntegrationData に変換
                                        from ...lifelog.integrations.models import (
                                            IntegrationData as ModelsIntegrationData,
                                        )

                                        models_integration_data = []
                                        for base_data in base_integration_data:
                                            models_data = ModelsIntegrationData(
                                                integration_type=base_data.integration_name,
                                                source_id=base_data.external_id,
                                                timestamp=base_data.timestamp,
                                                data=base_data.raw_data,
                                                metadata=base_data.processed_data,
                                            )
                                            models_integration_data.append(models_data)

                                        integrated_count = await self.lifelog_manager.integrate_external_data(
                                            models_integration_data
                                        )
                                        total_integrated += integrated_count
                            except Exception as e:
                                logger.error(
                                    f"{result.integration_name}のライフログ統合でエラー",
                                    error=str(e),
                                )

                    if total_integrated > 0:
                        integration_embed = discord.Embed(
                            title="📝 ライフログ統合完了",
                            description=f"{total_integrated}件のデータをライフログに統合しました",
                            color=discord.Color.green(),
                        )
                        await interaction.followup.send(embed=integration_embed)

        except Exception as e:
            logger.error("手動同期でエラー", error=str(e))
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")

    @discord.app_commands.command(
        name="integration_config", description="外部連携の設定を表示・変更"
    )
    @discord.app_commands.describe(
        integration="設定する外部連携名",
        enabled="有効/無効の切り替え",
        interval="同期間隔（秒）",
    )
    @admin_required
    async def integration_config(
        self,
        interaction: discord.Interaction,
        integration: str,
        enabled: bool | None = None,
        interval: int | None = None,
    ) -> None:
        """外部連携設定の表示・変更"""
        await interaction.response.defer()

        try:
            await self._ensure_initialized()

            if self.integration_manager is None:
                await interaction.followup.send(
                    "❌ Integration Manager が初期化されていません"
                )
                return

            if integration not in self.integration_manager.integrations:
                available = ", ".join(self.integration_manager.integrations.keys())
                await interaction.followup.send(
                    f"❌ 連携 '{integration}' が見つかりません。\n 利用可能: {available}"
                )
                return

            integration_obj = self.integration_manager.integrations[integration]
            config = integration_obj.config

            # 設定変更
            changed = False
            if enabled is not None:
                config.enabled = enabled
                changed = True

            if interval is not None:
                if interval < 60:
                    await interaction.followup.send(
                        "❌ 同期間隔は 60 秒以上である必要があります。"
                    )
                    return
                config.sync_interval = interval
                changed = True

            # 変更を保存
            if changed:
                # 設定ファイルに保存
                save_success = await self._save_integration_settings()

                # スケジューラー更新
                if self.scheduler:
                    if config.enabled:
                        await self.scheduler.add_schedule(
                            integration,
                            schedule_type=ScheduleType.INTERVAL,
                            interval=config.sync_interval,
                        )
                    else:
                        await self.scheduler.disable_schedule(integration)

            # 現在設定表示
            embed = discord.Embed(
                title=f"⚙️ {integration.title()} 設定", color=discord.Color.blue()
            )

            status_icon = "✅" if config.enabled else "❌"
            embed.add_field(
                name="基本設定",
                value=(
                    f"**状態**: {status_icon} {'有効' if config.enabled else '無効'}\n"
                    f"**同期間隔**: {config.sync_interval}秒 ({config.sync_interval // 60}分)\n"
                    f"**認証タイプ**: {config.auth_type}\n"
                    f"**最終同期**: {config.last_sync.strftime('%Y-%m-%d %H:%M') if config.last_sync else '未同期'}"
                ),
                inline=False,
            )

            # カスタム設定表示
            if config.custom_settings:
                custom_text = ""
                for key, value in config.custom_settings.items():
                    if isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            custom_text += f"**{sub_key}**: {sub_value}\n"
                    else:
                        custom_text += f"**{key}**: {value}\n"

                if custom_text:
                    embed.add_field(
                        name="詳細設定",
                        value=custom_text[:1024],  # Discord 制限
                        inline=False,
                    )

            if changed:
                if save_success:
                    embed.add_field(
                        name="✅ 変更完了",
                        value="設定が正常に更新され、ファイルに保存されました。",
                        inline=False,
                    )
                else:
                    embed.add_field(
                        name="⚠️ 部分的完了",
                        value="設定は更新されましたが、ファイル保存でエラーが発生しました。\n再起動時に設定が失われる可能性があります。",
                        inline=False,
                    )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("外部連携設定でエラー", error=str(e))
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")

    @discord.app_commands.command(
        name="scheduler_status", description="自動同期スケジューラーの状態を確認"
    )
    @admin_required
    async def scheduler_status(self, interaction: discord.Interaction):
        """スケジューラー状態表示"""
        await interaction.response.defer()

        try:
            await self._ensure_initialized()

            if not self.scheduler:
                await interaction.followup.send(
                    "❌ スケジューラーが初期化されていません。"
                )
                return

            status = self.scheduler.get_schedule_status()

            embed = discord.Embed(
                title="📅 自動同期スケジューラー状態",
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            running_icon = "🟢" if status.get("scheduler_running") else "🔴"
            stats = status.get("statistics", {})

            embed.add_field(
                name=f"{running_icon} スケジューラー状態",
                value=(
                    f"**実行状態**: {'実行中' if status.get('scheduler_running') else '停止中'}\n"
                    f"**総スケジュール数**: {status.get('total_schedules', 0)}\n"
                    f"**有効スケジュール数**: {status.get('enabled_schedules', 0)}\n"
                    f"**実行中タスク数**: {status.get('running_tasks', 0)}"
                ),
                inline=False,
            )

            embed.add_field(
                name="📊 実行統計",
                value=(
                    f"**総実行回数**: {stats.get('total_scheduled_runs', 0)}\n"
                    f"**成功回数**: {stats.get('successful_runs', 0)}\n"
                    f"**失敗回数**: {stats.get('failed_runs', 0)}\n"
                    f"**成功率**: {stats.get('success_rate', 0):.1f}%"
                ),
                inline=False,
            )

            # 各スケジュール詳細
            schedules = status.get("schedules", {})
            for schedule_name, schedule_data in schedules.items():
                enabled_icon = "✅" if schedule_data.get("enabled") else "❌"
                running_icon = "🔄" if schedule_data.get("currently_running") else "⏸️"

                next_run = schedule_data.get("next_run")
                if next_run:
                    next_run_str = (
                        f"<t:{int(datetime.fromisoformat(next_run).timestamp())}:R>"
                    )
                else:
                    next_run_str = "未設定"

                last_run = schedule_data.get("last_run")
                if last_run:
                    last_run_str = (
                        f"<t:{int(datetime.fromisoformat(last_run).timestamp())}:R>"
                    )
                else:
                    last_run_str = "未実行"

                embed.add_field(
                    name=f"{enabled_icon}{running_icon} {schedule_name.title()}",
                    value=(
                        f"**タイプ**: {schedule_data.get('schedule_type', 'unknown')}\n"
                        f"**次回実行**: {next_run_str}\n"
                        f"**前回実行**: {last_run_str}\n"
                        f"**リトライ回数**: {schedule_data.get('retry_count', 0)}"
                    ),
                    inline=True,
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("スケジューラー状態確認でエラー", error=str(e))
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")

    @discord.app_commands.command(
        name="lifelog_stats", description="外部連携から取得したライフログ統計を表示"
    )
    @discord.app_commands.describe(days="表示期間（日数、デフォルト 30 日）")
    @admin_required
    async def lifelog_integration_stats(
        self, interaction: discord.Interaction, days: int = 30
    ):
        """外部連携ライフログ統計"""
        await interaction.response.defer()

        try:
            await self._ensure_initialized()

            if not self.lifelog_manager:
                await interaction.followup.send(
                    "❌ ライフログマネージャーが初期化されていません。"
                )
                return

            if days < 1 or days > 365:
                await interaction.followup.send(
                    "❌ 表示期間は 1 〜 365 日の範囲で指定してください。"
                )
                return

            # 統計取得
            stats = await self.lifelog_manager.get_integration_statistics(days)

            embed = discord.Embed(
                title=f"📊 外部連携ライフログ統計（過去{days}日）",
                color=discord.Color.green(),
                timestamp=datetime.now(),
            )

            total_entries = stats.get("total_integration_entries", 0)
            if total_entries == 0:
                embed.description = (
                    "外部連携から取得されたライフログエントリーがありません。"
                )
                await interaction.followup.send(embed=embed)
                return

            embed.add_field(
                name="📈 概要",
                value=f"**総エントリー数**: {total_entries:,}件",
                inline=False,
            )

            # 連携別統計
            integration_breakdown = stats.get("integration_breakdown", {})
            if integration_breakdown:
                breakdown_text = ""
                for (
                    integration_name,
                    integration_stats,
                ) in integration_breakdown.items():
                    count = integration_stats.get("count", 0)
                    latest = integration_stats.get("latest_entry")
                    if latest:
                        latest_str = (
                            f"<t:{int(datetime.fromisoformat(latest).timestamp())}:R>"
                        )
                    else:
                        latest_str = "なし"

                    breakdown_text += f"**{integration_name.title()}**: {count:,}件 (最新: {latest_str})\n"

                embed.add_field(
                    name="🔗 連携別統計", value=breakdown_text, inline=False
                )

            # カテゴリ分布
            category_distribution = stats.get("category_distribution", {})
            if category_distribution:
                category_text = ""
                for category, count in sorted(
                    category_distribution.items(), key=lambda x: x[1], reverse=True
                ):
                    percentage = (count / total_entries) * 100
                    category_text += (
                        f"**{category}**: {count:,}件 ({percentage:.1f}%)\n"
                    )

                embed.add_field(
                    name="📂 カテゴリ分布", value=category_text, inline=False
                )

            # 最新エントリー
            recent_entries = stats.get("recent_entries", [])
            if recent_entries:
                recent_text = ""
                for entry in recent_entries[:5]:  # 最大 5 件
                    integration = entry.get("integration", "unknown")
                    title = entry.get("title", "無題")[:30]
                    timestamp_str = f"<t:{int(datetime.fromisoformat(entry.get('timestamp')).timestamp())}:R>"

                    recent_text += f"**{integration}**: {title} ({timestamp_str})\n"

                embed.add_field(
                    name="📝 最新エントリー（ 5 件）", value=recent_text, inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("ライフログ統計確認でエラー", error=str(e))
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")

    @discord.app_commands.command(
        name="calendar_auth", description="Google Calendar の OAuth 認証を開始"
    )
    @admin_required
    async def calendar_auth(self, interaction: discord.Interaction):
        """Google Calendar OAuth 認証"""
        await interaction.response.defer()

        try:
            # 認証 URL 生成
            client_id = os.getenv("GOOGLE_CALENDAR_CLIENT_ID")
            redirect_uri = "http://localhost:8080/callback"

            if not client_id:
                await interaction.followup.send(
                    "❌ Google Calendar の Client ID が設定されていません。\n"
                    "`.env` ファイルで `GOOGLE_CALENDAR_CLIENT_ID` を設定してください。"
                )
                return

            # OAuth2 認証 URL 構築
            import urllib.parse

            scope = "https://www.googleapis.com/auth/calendar.readonly"
            auth_url = (
                "https://accounts.google.com/o/oauth2/auth"
                f"?client_id={client_id}"
                f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
                "&response_type=code"
                f"&scope={urllib.parse.quote(scope)}"
                "&access_type=offline"
                "&prompt=consent"
            )

            embed = discord.Embed(
                title="🔐 Google Calendar 認証",
                description="Google Calendar との連携を開始するには、以下の手順に従ってください：",
                color=discord.Color.blue(),
            )

            embed.add_field(
                name="📋 手順",
                value=(
                    "1. 以下のリンクをクリック\n"
                    "2. Google アカウントでログイン\n"
                    "3. カレンダーへのアクセスを許可\n"
                    "4. 認証コードを取得\n"
                    "5. `/calendar_token` コマンドでコードを入力"
                ),
                inline=False,
            )

            embed.add_field(
                name="🔗 認証 URL",
                value=f"[こちらをクリックして認証]({auth_url})",
                inline=False,
            )

            embed.add_field(
                name="⚠️ 注意",
                value=(
                    "• 認証後に取得したコードは機密情報です\n"
                    "• コードは一度のみ有効です\n"
                    "• 認証は安全な環境で実行してください"
                ),
                inline=False,
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("Google Calendar 認証でエラー", error=str(e))
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")

    @discord.app_commands.command(
        name="calendar_token", description="Google Calendar 認証コードを設定"
    )
    @discord.app_commands.describe(code="Google から取得した認証コード")
    @admin_required
    async def calendar_token(self, interaction: discord.Interaction, code: str):
        """Google Calendar 認証コード処理"""
        await interaction.response.defer(ephemeral=True)  # プライベート応答

        try:
            import aiohttp

            # 設定確認
            client_id = os.getenv("GOOGLE_CALENDAR_CLIENT_ID")
            client_secret = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET")
            redirect_uri = "http://localhost:8080/callback"

            if not all([client_id, client_secret]):
                await interaction.followup.send(
                    "❌ Google Calendar の認証設定が不完全です。\n"
                    "`.env` ファイルで `GOOGLE_CALENDAR_CLIENT_ID` と "
                    "`GOOGLE_CALENDAR_CLIENT_SECRET` を設定してください。",
                    ephemeral=True,
                )
                return

            # 認証コードをアクセストークンに交換
            token_url = "https://oauth2.googleapis.com/token"  # nosec: B105
            token_data = {
                "client_id": client_id if client_id else "",
                "client_secret": client_secret if client_secret else "",
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(token_url, data=token_data) as response:
                    if response.status == 200:
                        token_response = await response.json()
                        access_token = token_response.get("access_token")
                        refresh_token = token_response.get("refresh_token")

                        if access_token and refresh_token:
                            stored, storage_path = self._persist_google_calendar_tokens(
                                access_token, refresh_token
                            )

                            if not stored:
                                await interaction.followup.send(
                                    "⚠️ ENCRYPTION_KEY が未設定のため取得したトークンを保存できませんでした。\n"
                                    "`ENCRYPTION_KEY` を安全な 32 バイトキーで設定し、再度コマンドを実行してください。",
                                    ephemeral=True,
                                )
                                return

                            secret_manager_synced = await self._store_google_calendar_tokens_in_secret_manager(
                                access_token, refresh_token
                            )
                            self._calendar_env_cache = None

                            embed = discord.Embed(
                                title="✅ Google Calendar 認証成功",
                                description="トークンを暗号化して保存しました。",
                                color=discord.Color.green(),
                            )

                            embed.add_field(
                                name="🔐 保存先",
                                value=(
                                    f"暗号化ファイル: `{storage_path}`\n"
                                    "復号には設定済みの `ENCRYPTION_KEY` (32 バイトのFernetキー) が必要です。"
                                ),
                                inline=False,
                            )

                            if secret_manager_synced:
                                embed.add_field(
                                    name="☁️ Secret Manager",
                                    value=(
                                        "Google Cloud Secret Manager に `google-calendar-access-token` と `google-calendar-refresh-token` の最新バージョンを保存しました。"
                                        "Cloud Run 側では次回デプロイ時に自動的に参照されます。"
                                    ),
                                    inline=False,
                                )
                                embed.add_field(
                                    name="🚀 次の手順",
                                    value=(
                                        "1. `./scripts/manage.sh deploy <PROJECT_ID>` を実行して Cloud Run を更新\n"
                                        "2. Discord で `/integration_config integration:google_calendar enabled:true`\n"
                                        "3. `/calendar_test` で連携確認"
                                    ),
                                    inline=False,
                                )
                            else:
                                embed.add_field(
                                    name="📝 復号後の手順",
                                    value=(
                                        "1. `ENCRYPTION_KEY` で暗号化レコードを復号\n"
                                        "2. `.env` 等に `GOOGLE_CALENDAR_ACCESS_TOKEN` と `GOOGLE_CALENDAR_REFRESH_TOKEN` を設定\n"
                                        "3. `/integration_config integration:google_calendar enabled:true` を実行"
                                    ),
                                    inline=False,
                                )

                            await interaction.followup.send(embed=embed, ephemeral=True)
                        else:
                            await interaction.followup.send(
                                "❌ トークンの取得に失敗しました。認証コードが正しいか確認してください。",
                                ephemeral=True,
                            )
                    else:
                        error_data = await response.json()
                        error_msg = error_data.get("error_description", "不明なエラー")
                        await interaction.followup.send(
                            f"❌ 認証に失敗しました: {error_msg}",
                            ephemeral=True,
                        )

        except Exception as e:
            logger.error("Google Calendar トークン処理でエラー", error=str(e))
            await interaction.followup.send(
                f"❌ エラーが発生しました: {str(e)}", ephemeral=True
            )

    @discord.app_commands.command(
        name="calendar_test", description="Google Calendar 接続をテスト"
    )
    @admin_required
    async def calendar_test(self, interaction: discord.Interaction):
        """Google Calendar 接続テスト"""
        await interaction.response.defer()

        try:
            await self._ensure_initialized()

            if not self.integration_manager:
                await interaction.followup.send(
                    "❌ Integration Manager が初期化されていません"
                )
                return

            # Google Calendar 統合があるかチェック
            if "google_calendar" not in self.integration_manager.integrations:
                await interaction.followup.send(
                    "❌ Google Calendar 統合が見つかりません。認証を先に実行してください。"
                )
                return
            calendar_integration = self._hydrate_google_calendar_from_env()
            if calendar_integration is None:
                await interaction.followup.send(
                    "❌ Google Calendar 統合が初期化されていません。"
                )
                return

            if not await calendar_integration.authenticate():
                recent_errors = getattr(
                    calendar_integration.metrics, "recent_errors", []
                )
                error_text = (
                    "\n".join(recent_errors[-3:])
                    if recent_errors
                    else "Google Calendar 認証に失敗しました。`/calendar_auth` で再認証してください。"
                )
                embed = discord.Embed(
                    title="❌ Google Calendar 認証失敗",
                    description="Google Calendar への認証に失敗しました。",
                    color=discord.Color.red(),
                )
                embed.add_field(
                    name="エラー詳細", value=error_text[:1024], inline=False
                )
                await interaction.followup.send(embed=embed)
                return

            # 接続テスト実行
            test_result = await calendar_integration.test_connection()

            if test_result:
                # カレンダーリストを取得してテスト
                embed = discord.Embed(
                    title="✅ Google Calendar 接続テスト成功",
                    description="Google Calendar への接続が正常に確認されました。",
                    color=discord.Color.green(),
                )

                # 簡単な統計情報
                try:
                    from datetime import datetime, timedelta

                    sync_data = await calendar_integration.sync_data(
                        start_date=datetime.now() - timedelta(days=1),
                        end_date=datetime.now() + timedelta(days=7),
                    )

                    embed.add_field(
                        name="📊 テスト結果",
                        value=f"過去 1 日〜今後 7 日間で {len(sync_data)} 件のイベントが見つかりました。",
                        inline=False,
                    )

                    if sync_data:
                        recent_events = sync_data[:3]  # 最新 3 件表示
                        events_text = ""
                        for event_data in recent_events:
                            processed = event_data.processed_data
                            title = processed.get("summary", "無題")[:30]
                            start_time = processed.get("start_time")
                            if start_time:
                                events_text += f"• {title} ({start_time})\n"

                        if events_text:
                            embed.add_field(
                                name="📅 最近のイベント（ 3 件）",
                                value=events_text,
                                inline=False,
                            )

                except Exception as e:
                    logger.warning("カレンダーイベント取得でエラー", error=str(e))

                await interaction.followup.send(embed=embed)
            else:
                recent_errors = getattr(
                    calendar_integration.metrics, "recent_errors", []
                )
                error_text = (
                    "\n".join(recent_errors[-3:])
                    if recent_errors
                    else "Google Calendar 接続テストでエラーが発生しました。"
                )

                embed = discord.Embed(
                    title="❌ Google Calendar 接続テスト失敗",
                    description="Google Calendar への接続に失敗しました。",
                    color=discord.Color.red(),
                )

                embed.add_field(
                    name="エラー詳細",
                    value=error_text[:1024],
                    inline=False,
                )

                embed.add_field(
                    name="対処法",
                    value="1. 認証トークンが正しいか確認\n2. `/calendar_auth` で再認証\n3. API 制限に達していないか確認",
                    inline=False,
                )

                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("Google Calendar テストでエラー", error=str(e))
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")

    @discord.app_commands.command(
        name="garmin_sleep", description="Garmin 睡眠データを取得・表示"
    )
    @admin_required
    async def garmin_sleep(self, interaction: discord.Interaction) -> None:
        """Garmin 睡眠データ表示"""
        await interaction.response.defer()

        try:
            await self._ensure_initialized()

            if self.integration_manager is None:
                await interaction.followup.send(
                    "❌ Integration Manager が初期化されていません"
                )
                return

            # Garmin 連携の確認
            if "garmin" not in self.integration_manager.integrations:
                await interaction.followup.send(
                    "❌ Garmin 連携が設定されていません。\n"
                    "`/integration_config garmin enabled:True` で有効化してください。"
                )
                return

            # Garmin 同期を実行
            embed = discord.Embed(
                title="🛏️ Garmin 睡眠データ取得中...",
                color=discord.Color.orange(),
            )
            message = await interaction.followup.send(embed=embed)  # type: ignore[func-returns-value]

            result = await self.integration_manager.sync_integration(
                "garmin", force_sync=True
            )

            if result.success:
                # 睡眠データを取得
                import os
                from datetime import date, timedelta

                from garminconnect import Garmin

                email = os.getenv("GARMIN_EMAIL")
                password = os.getenv("GARMIN_PASSWORD")

                if email and password:
                    client = Garmin(email, password)
                    await asyncio.get_event_loop().run_in_executor(None, client.login)

                    # 今日と昨日の睡眠データ
                    today = date.today()
                    yesterday = today - timedelta(days=1)

                    embed.colour = discord.Color.blue()
                    embed.title = "🛏️ Garmin 睡眠データ"
                    embed.description = ""

                    for test_date in [today, yesterday]:
                        date_str = test_date.strftime("%Y-%m-%d")

                        # Wellness summary から睡眠データ取得
                        wellness = await asyncio.get_event_loop().run_in_executor(
                            None, client.get_user_summary, date_str
                        )

                        if wellness:
                            sleeping_seconds = wellness.get("sleepingSeconds", 0)
                            measurable_sleep = wellness.get(
                                "measurableAsleepDuration", 0
                            )
                            body_battery = wellness.get("bodyBatteryDuringSleep", 0)

                            if sleeping_seconds > 0:
                                hours = sleeping_seconds // 3600
                                minutes = (sleeping_seconds % 3600) // 60

                                # 詳細睡眠データも取得
                                try:
                                    sleep_data = (
                                        await asyncio.get_event_loop().run_in_executor(
                                            None, client.get_sleep_data, date_str
                                        )
                                    )

                                    sleep_score = "N/A"
                                    deep_sleep_mins = 0
                                    light_sleep_mins = 0
                                    rem_sleep_mins = 0

                                    if sleep_data and "dailySleepDTO" in sleep_data:
                                        sleep_dto = sleep_data["dailySleepDTO"]
                                        sleep_scores = sleep_dto.get("sleepScores", {})
                                        overall_score = sleep_scores.get("overall", {})
                                        sleep_score = overall_score.get("value", "N/A")

                                        deep_sleep_mins = (
                                            sleep_dto.get("deepSleepSeconds", 0) // 60
                                        )
                                        light_sleep_mins = (
                                            sleep_dto.get("lightSleepSeconds", 0) // 60
                                        )
                                        rem_sleep_mins = (
                                            sleep_dto.get("remSleepSeconds", 0) // 60
                                        )

                                except Exception as sleep_error:
                                    logger.debug(
                                        f"詳細睡眠データ取得エラー: {sleep_error}"
                                    )

                                date_display = "今日" if test_date == today else "昨日"
                                embed.add_field(
                                    name=f"📅 {date_display} ({test_date.strftime('%m/%d')})",
                                    value=(
                                        f"**総睡眠時間**: {hours}時間{minutes}分\n"
                                        f"**測定可能睡眠**: {measurable_sleep // 3600}時間{(measurable_sleep % 3600) // 60}分\n"
                                        f"**睡眠スコア**: {sleep_score}点\n"
                                        f"**Body Battery**: {body_battery}\n"
                                        f"**深眠**: {deep_sleep_mins}分\n"
                                        f"**浅眠**: {light_sleep_mins}分\n"
                                        f"**REM**: {rem_sleep_mins}分"
                                    ),
                                    inline=True,
                                )
                            else:
                                date_display = "今日" if test_date == today else "昨日"
                                embed.add_field(
                                    name=f"📅 {date_display} ({test_date.strftime('%m/%d')})",
                                    value="睡眠データなし",
                                    inline=True,
                                )

                    if not embed.fields:
                        embed.description = "睡眠データが見つかりませんでした。"

                else:
                    embed.colour = discord.Color.red()
                    embed.title = "❌ Garmin 認証エラー"
                    embed.description = "Garmin 認証情報が設定されていません。"

            else:
                embed.colour = discord.Color.red()
                embed.title = "❌ Garmin 同期失敗"
                embed.description = result.error_message or "不明なエラー"

            if message is not None:
                await message.edit(embed=embed)
            else:
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("Garmin 睡眠データ取得でエラー", error=str(e))
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")
            return

    @discord.app_commands.command(
        name="garmin_today", description="Garmin 今日のアクティビティデータを表示"
    )
    @admin_required
    async def garmin_today(self, interaction: discord.Interaction) -> None:
        """Garmin 今日のデータ表示"""
        await interaction.response.defer()

        try:
            await self._ensure_initialized()

            if self.integration_manager is None:
                await interaction.followup.send(
                    "❌ Integration Manager が初期化されていません"
                )
                return

            # Garmin 連携の確認
            if "garmin" not in self.integration_manager.integrations:
                await interaction.followup.send(
                    "❌ Garmin 連携が設定されていません。\n"
                    "`/integration_config garmin enabled:True` で有効化してください。"
                )
                return

            # 直接 Garmin API にアクセス
            import os
            from datetime import date

            from garminconnect import Garmin

            email = os.getenv("GARMIN_EMAIL")
            password = os.getenv("GARMIN_PASSWORD")

            if not email or not password:
                await interaction.followup.send(
                    "❌ Garmin 認証情報が設定されていません。\n"
                    "環境変数 `GARMIN_EMAIL` と `GARMIN_PASSWORD` を設定してください。"
                )
                return

            embed = discord.Embed(
                title="🏃‍♂️ Garmin 今日のデータ取得中...",
                color=discord.Color.orange(),
            )
            message = await interaction.followup.send(embed=embed)  # type: ignore[func-returns-value]

            client = Garmin(email, password)
            await asyncio.get_event_loop().run_in_executor(None, client.login)

            today = date.today()
            date_str = today.strftime("%Y-%m-%d")

            # Wellness summary から健康データ取得
            wellness = await asyncio.get_event_loop().run_in_executor(
                None, client.get_user_summary, date_str
            )

            embed.colour = discord.Color.blue()
            embed.title = f"🏃‍♂️ Garmin 今日のデータ ({today.strftime('%Y-%m-%d')})"

            if wellness:
                steps = wellness.get("totalSteps", 0)
                distance = wellness.get("totalDistanceMeters", 0) / 1000  # km
                calories = wellness.get("totalKilocalories", 0)
                active_calories = wellness.get("activeKilocalories", 0)

                embed.add_field(
                    name="📊 基本データ",
                    value=(
                        f"**歩数**: {steps:,}歩\n"
                        f"**距離**: {distance:.2f}km\n"
                        f"**総消費カロリー**: {calories}kcal\n"
                        f"**アクティブカロリー**: {active_calories}kcal"
                    ),
                    inline=False,
                )

                # 睡眠データも含める
                sleeping_seconds = wellness.get("sleepingSeconds", 0)
                body_battery = wellness.get("bodyBatteryDuringSleep", 0)

                if sleeping_seconds > 0:
                    hours = sleeping_seconds // 3600
                    minutes = (sleeping_seconds % 3600) // 60
                    embed.add_field(
                        name="🛏️ 睡眠データ",
                        value=(
                            f"**睡眠時間**: {hours}時間{minutes}分\n"
                            f"**Body Battery**: {body_battery}"
                        ),
                        inline=True,
                    )

                # 今日のアクティビティ
                try:
                    activities = await asyncio.get_event_loop().run_in_executor(
                        None, client.get_activities_by_date, date_str
                    )

                    if activities:
                        activity_text = ""
                        for activity in activities[:3]:  # 最大 3 件
                            name = activity.get("activityName", "不明")
                            activity_type = activity.get("activityType", {}).get(
                                "typeKey", "不明"
                            )
                            duration = activity.get("duration", 0)
                            duration_mins = duration // 60 if duration else 0

                            activity_text += f"• **{name}** ({activity_type})"
                            if duration_mins > 0:
                                activity_text += f" - {duration_mins}分"
                            activity_text += "\n"

                        if activity_text:
                            embed.add_field(
                                name="🏃‍♂️ 今日のアクティビティ",
                                value=activity_text,
                                inline=False,
                            )
                    else:
                        embed.add_field(
                            name="🏃‍♂️ 今日のアクティビティ",
                            value="アクティビティなし",
                            inline=False,
                        )
                except Exception as activity_error:
                    logger.debug(f"アクティビティデータ取得エラー: {activity_error}")

            else:
                embed.description = "今日のデータが見つかりませんでした。"

            if message is not None:
                await message.edit(embed=embed)
            else:
                await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("Garmin 今日のデータ取得でエラー", error=str(e))
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")
            return

    def _get_status_icon(self, status: str) -> str:
        """ステータスアイコンを取得"""
        status_icons = {
            "disabled": "❌",
            "enabled": "🟡",
            "authenticated": "🟢",
            "error": "🔴",
            "syncing": "🔄",
            "rate_limited": "⏳",
        }
        return status_icons.get(status, "❓")

    async def cog_unload(self):
        """Cog アンロード時のクリーンアップ"""
        if self.scheduler:
            await self.scheduler.stop()

        if self.integration_manager:
            await self.integration_manager.__aexit__(None, None, None)


async def setup(bot, settings: Settings):
    """Cog を bot に追加"""
    await bot.add_cog(IntegrationCommands(bot, settings))
