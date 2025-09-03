"""
Dynamic configuration management system for MindBridge
"""

import json
import os
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from discord.ext import commands

from src.utils.mixins import LoggerMixin


class ConfigLevel(str, Enum):
    """設定レベル"""

    SYSTEM = "system"
    USER = "user"
    CHANNEL = "channel"
    GUILD = "guild"


class ConfigCategory(str, Enum):
    """設定カテゴリ"""

    CHANNELS = "channels"
    AI_PROCESSING = "ai_processing"
    NOTIFICATIONS = "notifications"
    REMINDERS = "reminders"
    FILE_MANAGEMENT = "file_management"
    SECURITY = "security"


class DynamicConfigManager(LoggerMixin):
    """動的設定管理システム"""

    def __init__(self, bot: commands.Bot, notification_system: Any = None) -> None:
        self.bot = bot
        self.notification_system = notification_system

        # 設定ファイルパス
        self.config_dir = Path.cwd() / ".config" / "discord-obsidian-bot"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.user_config_file = self.config_dir / "user_settings.json"
        self.runtime_config_file = self.config_dir / "runtime_settings.json"

        # 設定キャッシュ
        self.user_configs: dict[str, dict[str, Any]] = {}
        self.runtime_configs: dict[str, Any] = {}

        # 設定変更履歴
        self.config_history: list[dict[str, Any]] = []

        # デフォルト設定
        self.default_configs = {
            ConfigCategory.CHANNELS.value: {
                "enable_all_channels": False,
                "auto_process_attachments": True,
                "voice_processing_enabled": True,
            },
            ConfigCategory.AI_PROCESSING.value: {
                "ai_processing_enabled": True,
                "confidence_threshold": 0.7,
                "max_daily_requests": 1000,
                "auto_categorization": True,
            },
            ConfigCategory.NOTIFICATIONS.value: {
                "processing_notifications": False,
                "error_notifications": True,
                "reminder_notifications": True,
                "system_notifications": True,
            },
            ConfigCategory.REMINDERS.value: {
                "finance_reminders": True,
                "task_reminders": True,
                "daily_summary": False,
                "weekly_review": False,
            },
            ConfigCategory.FILE_MANAGEMENT.value: {
                "auto_backup": False,
                "backup_frequency_hours": 24,
                "cleanup_old_files": False,
                "max_file_size_mb": 50,
            },
            ConfigCategory.SECURITY.value: {
                "require_permission_for_commands": False,
                "log_all_interactions": True,
                "allowed_users": [],
                "restricted_commands": [],
            },
        }

        # 起動時に設定をロード
        self._load_configs()

    async def get_config(
        self,
        category: ConfigCategory,
        key: str,
        user_id: str | None = None,
        default: Any = None,
    ) -> Any:
        """設定値を取得"""
        try:
            # ユーザー固有設定を優先
            if user_id and user_id in self.user_configs:
                user_config = self.user_configs[user_id].get(category.value, {})
                if key in user_config:
                    return user_config[key]

            # ランタイム設定を確認
            runtime_config = self.runtime_configs.get(category.value, {})
            if key in runtime_config:
                return runtime_config[key]

            # デフォルト設定を確認
            default_config: dict[str, Any] = {}
            if category.value in self.default_configs:
                config_value = self.default_configs[category.value]
            else:
                config_value = None
            if isinstance(config_value, dict):
                default_config = config_value
            if key in default_config:
                return default_config[key]

            return default

        except Exception as e:
            self.logger.error(
                "Failed to get config",
                category=category.value,
                key=key,
                user_id=user_id,
                error=str(e),
            )
            return default

    async def set_config(
        self,
        category: ConfigCategory,
        key: str,
        value: Any,
        user_id: str | None = None,
        level: ConfigLevel = ConfigLevel.SYSTEM,
        requester: str | None = None,
    ) -> bool:
        """設定値を更新"""
        try:
            old_value = await self.get_config(category, key, user_id)

            if level == ConfigLevel.USER and user_id:
                # ユーザー固有設定
                if user_id not in self.user_configs:
                    self.user_configs[user_id] = {}
                if category.value not in self.user_configs[user_id]:
                    self.user_configs[user_id][category.value] = {}

                self.user_configs[user_id][category.value][key] = value
                await self._save_user_configs()

            else:
                # システム全体設定
                if category.value not in self.runtime_configs:
                    self.runtime_configs[category.value] = {}

                self.runtime_configs[category.value][key] = value
                await self._save_runtime_configs()

            # 変更履歴を記録
            self._record_config_change(
                category, key, old_value, value, user_id, requester
            )

            # 通知送信
            if self.notification_system:
                await self.notification_system.send_system_event_notification(
                    event_type="Configuration Changed",
                    description=f"設定 {category.value}.{key} が変更されました。",
                    system_info={
                        "category": category.value,
                        "key": key,
                        "old_value": str(old_value),
                        "new_value": str(value),
                        "level": level.value,
                        "user_id": user_id,
                        "requester": requester,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

            self.logger.info(
                "Configuration updated",
                category=category.value,
                key=key,
                old_value=old_value,
                new_value=value,
                level=level.value,
                requester=requester,
            )

            return True

        except Exception as e:
            self.logger.error(
                "Failed to set config",
                category=category.value,
                key=key,
                value=value,
                user_id=user_id,
                level=level.value,
                error=str(e),
                exc_info=True,
            )
            return False

    async def validate_api_key(self, api_name: str, api_key: str) -> dict[str, Any]:
        """APIキーの検証"""
        validation_result: dict[str, Any] = {
            "valid": False,
            "error": None,
            "details": {},
        }

        try:
            if api_name == "gemini":
                # Gemini API キーの検証（新しいgoogle-genai SDK使用）
                from google import genai
                from google.genai import types

                client = genai.Client(api_key=api_key)

                # 簡単なテストリクエスト
                response = client.models.generate_content(
                    model="gemini-2.0-flash-001",
                    contents="Hello",
                    config=types.GenerateContentConfig(
                        max_output_tokens=10,
                        temperature=0.1,
                    ),
                )

                if response.text:
                    validation_result["valid"] = True
                    validation_result["details"]["model"] = "gemini-2.0-flash-001"
                    validation_result["details"]["response_received"] = True

            elif api_name == "google_speech":
                # Google Cloud Speech-to-Text API キーの検証
                import json
                import tempfile

                from google.cloud import speech

                # 一時的にサービスアカウントキーを作成
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as f:
                    json.dump(json.loads(api_key), f)
                    temp_key_path = f.name

                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_key_path

                try:
                    speech.SpeechClient()
                    # 簡単な設定テスト
                    speech.RecognitionConfig(
                        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                        sample_rate_hertz=16000,
                        language_code="ja-JP",
                    )

                    validation_result["valid"] = True
                    validation_result["details"]["client_initialized"] = True

                finally:
                    # 一時ファイルを削除
                    os.unlink(temp_key_path)
                    if "GOOGLE_APPLICATION_CREDENTIALS" in os.environ:
                        del os.environ["GOOGLE_APPLICATION_CREDENTIALS"]

            else:
                validation_result["error"] = f"Unknown API: {api_name}"

        except Exception as e:
            validation_result["error"] = str(e)
            validation_result["details"]["exception"] = type(e).__name__

        return validation_result

    async def update_channel_config(
        self,
        channel_id: int,
        config_updates: dict[str, Any],
        requester: str | None = None,
    ) -> bool:
        """チャンネル設定の動的更新"""
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return False

            # 現在の設定を取得
            current_config = self.runtime_configs.get("channels", {}).get(
                str(channel_id), {}
            )

            # 設定を更新
            updated_config = {**current_config, **config_updates}

            if "channels" not in self.runtime_configs:
                self.runtime_configs["channels"] = {}

            self.runtime_configs["channels"][str(channel_id)] = updated_config

            await self._save_runtime_configs()

            # 変更通知
            if self.notification_system:
                channel_name = getattr(channel, "name", f"Private Channel {channel.id}")
                await self.notification_system.send_system_event_notification(
                    event_type="Channel Configuration Updated",
                    description=f"チャンネル #{channel_name} の設定が更新されました。",
                    system_info={
                        "channel_id": channel_id,
                        "channel_name": channel_name,
                        "updates": config_updates,
                        "requester": requester,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

            self.logger.info(
                "Channel configuration updated",
                channel_id=channel_id,
                channel_name=channel_name,
                updates=config_updates,
                requester=requester,
            )

            return True

        except Exception as e:
            self.logger.error(
                "Failed to update channel config",
                channel_id=channel_id,
                updates=config_updates,
                error=str(e),
                exc_info=True,
            )
            return False

    def get_config_summary(self) -> dict[str, Any]:
        """設定概要を取得"""
        try:
            summary: dict[str, Any] = {
                "system_configs": {},
                "user_config_count": len(self.user_configs),
                "total_categories": len(self.default_configs),
                "last_updated": None,
                "config_changes_today": 0,
            }

            # システム設定の概要
            for category, configs in self.runtime_configs.items():
                summary["system_configs"][category] = len(configs)

            # 今日の変更数
            today = datetime.now().date()
            summary["config_changes_today"] = len(
                [
                    change
                    for change in self.config_history
                    if change["timestamp"].date() == today
                ]
            )

            # 最終更新時刻
            if self.config_history:
                summary["last_updated"] = self.config_history[-1][
                    "timestamp"
                ].isoformat()

            return summary

        except Exception as e:
            self.logger.error("Failed to get config summary", error=str(e))
            return {"error": "設定概要の取得に失敗しました"}

    def _load_configs(self) -> None:
        """設定ファイルからロード"""
        try:
            # ユーザー設定をロード
            if self.user_config_file.exists():
                with open(self.user_config_file, encoding="utf-8") as f:
                    self.user_configs = json.load(f)

            # ランタイム設定をロード
            if self.runtime_config_file.exists():
                with open(self.runtime_config_file, encoding="utf-8") as f:
                    self.runtime_configs = json.load(f)

            self.logger.info(
                "Configurations loaded",
                user_configs=len(self.user_configs),
                runtime_configs=len(self.runtime_configs),
            )

        except Exception as e:
            self.logger.error("Failed to load configs", error=str(e), exc_info=True)

    async def _save_user_configs(self) -> None:
        """ユーザー設定を保存"""
        try:
            with open(self.user_config_file, "w", encoding="utf-8") as f:
                json.dump(self.user_configs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error("Failed to save user configs", error=str(e))

    async def _save_runtime_configs(self) -> None:
        """ランタイム設定を保存"""
        try:
            with open(self.runtime_config_file, "w", encoding="utf-8") as f:
                json.dump(self.runtime_configs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error("Failed to save runtime configs", error=str(e))

    def _record_config_change(
        self,
        category: ConfigCategory,
        key: str,
        old_value: Any,
        new_value: Any,
        user_id: str | None,
        requester: str | None,
    ) -> None:
        """設定変更履歴を記録"""
        change_record = {
            "timestamp": datetime.now(),
            "category": category.value,
            "key": key,
            "old_value": old_value,
            "new_value": new_value,
            "user_id": user_id,
            "requester": requester,
        }

        self.config_history.append(change_record)

        # 履歴サイズ制限 (最大1000件)
        if len(self.config_history) > 1000:
            self.config_history = self.config_history[-1000:]

    def get_config_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """設定変更履歴を取得"""
        # 最新順でソート
        sorted_history = sorted(
            self.config_history, key=lambda x: x["timestamp"], reverse=True
        )

        # 日時を文字列に変換してシリアライズ可能にする
        serializable_history = []
        for record in sorted_history[:limit]:
            serializable_record = record.copy()
            serializable_record["timestamp"] = record["timestamp"].isoformat()
            serializable_history.append(serializable_record)

        return serializable_history
