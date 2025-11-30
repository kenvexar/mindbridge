"""Configuration settings for MindBridge with caching utilities."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import RLock
from typing import Any

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Personal MindBridge application settings"""

    model_config = SettingsConfigDict(
        env_file=[".env.test", ".env.docker", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Discord Configuration (Personal Bot)
    discord_bot_token: SecretStr
    discord_guild_id: int | None = None  # Personal server ID

    # Google API Configuration
    gemini_api_key: SecretStr
    google_application_credentials: str | None = None
    google_cloud_speech_api_key: SecretStr | None = None

    # Personal Garmin Connect Integration
    garmin_email: SecretStr | None = None
    garmin_password: SecretStr | None = None

    # Personal Google Calendar Integration
    google_calendar_id: str = "primary"
    google_calendar_service_account: str | None = None

    # Obsidian Personal Vault
    obsidian_vault_path: Path = Path("./vault")  # Docker と互換性のため相対パス

    # Personal Cache Directory
    garmin_cache_dir: Path | None = None
    garmin_cache_hours: float = 24.0

    # Personal API Limits (Google Cloud 無料枠最適化)
    gemini_api_daily_limit: int = 1500  # Gemini 無料枠: 1,500 回/日
    gemini_api_minute_limit: int = 15  # Gemini 無料枠: 15 回/分
    speech_api_monthly_limit_minutes: int = 60  # Speech-to-Text 無料枠: 60 分/月

    # コスト管理設定
    enable_usage_alerts: bool = True  # 使用量アラートを有効化
    usage_alert_threshold: float = 0.8  # 80% 到達時にアラート
    enable_quota_protection: bool = True  # クォータ保護機能

    # Security and Logging
    enable_access_logging: bool = True  # セキュリティアクセスログを有効化
    log_level: str = "INFO"
    log_format: str = "json"
    access_log_rotation_size_mb: float = 5.0
    access_log_rotation_backups: int = 5
    health_endpoint_token: SecretStr | None = None
    health_callback_state: SecretStr | None = None

    # Environment
    environment: str = "personal"

    # Personal GitHub Backup
    github_token: SecretStr | None = None
    obsidian_backup_repo: str | None = None
    obsidian_backup_branch: str = "main"
    git_user_name: str = "Personal MindBridge"
    git_user_email: str = "mindbridge@personal.local"

    # AI Model Configuration
    model_name: str = "models/gemini-2.5-flash"
    ai_temperature: float = 0.3
    ai_max_tokens: int = 1024

    # Development Configuration
    enable_mock_mode: bool = False
    mock_discord_enabled: bool = False
    mock_gemini_enabled: bool = False
    mock_garmin_enabled: bool = False
    mock_speech_enabled: bool = False

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() in ["development", "dev"]

    @property
    def is_personal(self) -> bool:
        """Check if running in personal mode (default)"""
        return self.environment.lower() in ["personal", "production"]

    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.environment.lower() in ["testing", "test"]

    @property
    def is_mock_mode(self) -> bool:
        """Check if mock mode is enabled"""
        return self.enable_mock_mode or self.is_development

    def get_personal_channels(self) -> dict[str, str]:
        """Get personal Discord channel mapping"""
        return {
            "memo": "memo",  # メイン入力チャンネル
            "notifications": "notifications",  # 通知
            "commands": "commands",  # コマンド実行
        }

    def get_required_channels(self) -> list[str]:
        """Get required Discord channels for personal use"""
        return ["memo", "notifications", "commands"]


_SETTINGS_LOCK = RLock()
_SETTINGS_CACHE: Settings | None = None


def get_settings(*, refresh: bool = False) -> Settings:
    """Return a cached ``Settings`` instance.

    Parameters
    ----------
    refresh:
        When ``True`` the cached instance is discarded and a new one is created.
    """

    global _SETTINGS_CACHE

    with _SETTINGS_LOCK:
        if refresh or _SETTINGS_CACHE is None:
            _SETTINGS_CACHE = Settings()
        return _SETTINGS_CACHE


def clear_settings_cache() -> None:
    """Clear the cached settings instance."""

    global _SETTINGS_CACHE

    with _SETTINGS_LOCK:
        _SETTINGS_CACHE = None


get_settings.cache_clear = clear_settings_cache  # type: ignore[attr-defined]


@contextmanager
def override_settings(**overrides: Any) -> Iterator[Settings]:
    """Temporarily override the cached settings within a context."""

    global _SETTINGS_CACHE

    with _SETTINGS_LOCK:
        previous_settings = _SETTINGS_CACHE

    base_settings = previous_settings or Settings()
    patched_settings = base_settings.model_copy(update=overrides)

    with _SETTINGS_LOCK:
        _SETTINGS_CACHE = patched_settings

    try:
        yield patched_settings
    finally:
        with _SETTINGS_LOCK:
            _SETTINGS_CACHE = previous_settings
