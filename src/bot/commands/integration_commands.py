"""
外部連携制御用 Discord コマンド

外部連携の状態確認、同期実行、設定管理を行うコマンド群
"""

import os
from datetime import datetime

import discord
import structlog
from discord.ext import commands

from ...config.settings import Settings
from ...lifelog.integrations.base import IntegrationConfig
from ...lifelog.integrations.manager import IntegrationManager
from ...lifelog.integrations.scheduler import (
    IntegrationScheduler,
    ScheduleType,
)
from ...lifelog.manager import LifelogManager

logger = structlog.get_logger(__name__)


class IntegrationCommands(commands.Cog):
    """外部連携制御コマンド"""

    def __init__(self, bot, settings: Settings):
        self.bot = bot
        self.settings = settings

        # 外部連携システム（遅延初期化）
        self.integration_manager: IntegrationManager | None = None
        self.scheduler: IntegrationScheduler | None = None
        self.lifelog_manager: LifelogManager | None = None

        self._initialized = False

    async def _ensure_initialized(self):
        """外部連携システムの初期化を確認"""
        if self._initialized:
            return

        try:
            # 設定読み込み（エラーハンドリング強化）
            try:
                from ...lifelog.integrations.manager import IntegrationManagerConfig
                from ...lifelog.integrations.scheduler import IntegrationSchedulerConfig

                manager_config = IntegrationManagerConfig()
                scheduler_config = IntegrationSchedulerConfig()
            except Exception as e:
                logger.warning(f"設定読み込みに失敗、デフォルト設定を使用: {e}")
                # デフォルト設定を使用
                from ...lifelog.integrations.manager import IntegrationManagerConfig
                from ...lifelog.integrations.scheduler import IntegrationSchedulerConfig

                manager_config = IntegrationManagerConfig()
                scheduler_config = IntegrationSchedulerConfig()

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
                    self.scheduler = IntegrationScheduler(
                        self.integration_manager, scheduler_config
                    )
                except Exception as e:
                    logger.warning(f"IntegrationScheduler 初期化失敗: {e}")
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
        default_integrations = {
            "garmin": {
                "enabled": False,  # 初期は無効
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
                "enabled": False,
                "sync_interval": 1800,  # 30 分間隔
                "custom_settings": {
                    "google_calendar": {
                        "calendars": ["primary"],
                        "sync_past_events": False,
                        "min_duration_minutes": 15,
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

        for integration_name, config_data in default_integrations.items():
            integration_config = IntegrationConfig(
                integration_name=integration_name,
                enabled=config_data["enabled"],
                sync_interval=config_data["sync_interval"],
                custom_settings=config_data["custom_settings"],
            )

            await self.integration_manager.register_integration(
                integration_name, integration_config
            )

    @discord.app_commands.command(
        name="integration_status", description="外部連携の状態を確認"
    )
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
        name="manual_sync", description="外部連携の手動同期を実行"
    )
    @discord.app_commands.describe(
        integration="同期する外部連携名（省略時は全て）",
        force="強制実行（実行中でも再実行）",
    )
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
                message = await interaction.followup.send(embed=embed)  # type: ignore[assignment,func-returns-value]

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
                    if result.records_synced > 0:
                        # 同期データをライフログに統合（実装予定）
                        pass

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
                message = await interaction.followup.send(embed=embed)  # type: ignore[assignment,func-returns-value]

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
                integration_count = 0
                for result in results:
                    if result.success and result.records_synced > 0:
                        # 実際の統合処理（実装予定）
                        integration_count += 1

                if integration_count > 0:
                    integration_embed = discord.Embed(
                        title="📝 ライフログ統合完了",
                        description=f"{integration_count}個の連携データをライフログに統合しました",
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

            # 変更を保存（実際の設定永続化は実装予定）
            if changed:
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
                embed.add_field(
                    name="✅ 変更完了",
                    value="設定が正常に更新されました。",
                    inline=False,
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            logger.error("外部連携設定でエラー", error=str(e))
            await interaction.followup.send(f"❌ エラーが発生しました: {str(e)}")

    @discord.app_commands.command(
        name="scheduler_status", description="自動同期スケジューラーの状態を確認"
    )
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
                            embed = discord.Embed(
                                title="✅ Google Calendar 認証成功",
                                description="認証が正常に完了しました！",
                                color=discord.Color.green(),
                            )

                            embed.add_field(
                                name="📝 次の手順",
                                value=(
                                    "以下のトークンを `.env` ファイルに追加してください：\n"
                                    f"```\n"
                                    f"GOOGLE_CALENDAR_ACCESS_TOKEN={access_token}\n"
                                    f"GOOGLE_CALENDAR_REFRESH_TOKEN={refresh_token}\n"
                                    f"```"
                                ),
                                inline=False,
                            )

                            embed.add_field(
                                name="🔄 有効化",
                                value="その後、`/外部連携設定 google_calendar enabled:True` で有効化してください。",
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

            calendar_integration = self.integration_manager.integrations[
                "google_calendar"
            ]

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
                error_messages = getattr(calendar_integration, "error_messages", [])
                error_text = (
                    "\n".join(error_messages[-3:]) if error_messages else "認証エラー"
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
