"""
Configuration settings for MindBridge
"""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    model_config = SettingsConfigDict(
        env_file=[".env.test", ".env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 追加フィールドを無視
    )

    # Discord Configuration
    discord_bot_token: SecretStr
    discord_guild_id: int | None = None  # Optional for Cloud Run deployment

    # Google API Configuration
    gemini_api_key: SecretStr
    google_application_credentials: str | None = None
    google_cloud_speech_api_key: SecretStr | None = None

    # Garmin Configuration
    garmin_username: str | None = None
    garmin_password: SecretStr | None = None

    # Obsidian Configuration
    obsidian_vault_path: Path

    # NOTE: Channel IDs are no longer required - channels are discovered by name
    # The bot automatically finds channels with standard names: inbox, voice, money, etc.
    # Garmin Connect Integration (Optional)
    garmin_email: SecretStr | None = None
    garmin_cache_dir: Path | None = None
    garmin_cache_hours: float = 24.0

    # API Rate Limiting
    gemini_api_daily_limit: int = 1500
    gemini_api_minute_limit: int = 15
    speech_api_monthly_limit_minutes: int = 60

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"

    # Environment
    environment: str = "development"

    # Security Configuration
    google_cloud_project: str | None = None
    use_secret_manager: bool = False
    enable_access_logging: bool = True
    security_log_path: Path | None = None

    # GitHub Integration Configuration
    github_token: SecretStr | None = None
    obsidian_backup_repo: str | None = None
    obsidian_backup_branch: str = "main"
    git_user_name: str = "ObsidianBot"
    git_user_email: str = "bot@example.com"

    # Mock Mode Configuration (for development/testing)
    enable_mock_mode: bool = False
    mock_discord_enabled: bool = False
    mock_gemini_enabled: bool = False
    mock_garmin_enabled: bool = False
    mock_speech_enabled: bool = False

    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() == "production"

    @property
    def is_testing(self) -> bool:
        """Check if running in testing/staging/integration mode"""
        return self.environment.lower() in ["testing", "staging", "integration"]

    @property
    def is_mock_mode(self) -> bool:
        """Check if mock mode is enabled"""
        return self.enable_mock_mode or self.is_development

    @property
    def should_use_secret_manager(self) -> bool:
        """Check if Secret Manager should be used"""
        return self.use_secret_manager and self.google_cloud_project is not None

    def get_channel_name_mapping(self) -> dict[str, str]:
        """Get mapping of configuration names to Discord channel names"""
        return {
            "memo": "memo",
            "notifications": "notifications",
            "commands": "commands",
        }

    def get_default_channel_names(self) -> list[str]:
        """Get list of default channel names to look for"""
        return [
            "memo",  # Main unified channel for all content
            "notifications",  # System notifications
            "commands",  # Bot commands
        ]

    def get_required_channel_names(self) -> list[str]:
        """Get list of required channel names for basic functionality"""
        return [
            "memo",  # Essential unified channel for all content
            "notifications",  # Essential for system feedback
            "commands",  # Essential for bot interaction
        ]

    def get_optional_channel_names(self) -> list[str]:
        """Get list of optional channel names for enhanced functionality"""
        return []  # All functionality is now unified in the memo channel

    def get_all_supported_channel_names(self) -> list[str]:
        """Get all supported channel names"""
        return self.get_required_channel_names() + self.get_optional_channel_names()


def get_settings() -> Settings:
    """Get application settings instance"""
    return Settings()
