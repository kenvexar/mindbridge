"""
Secure settings loader with Google Cloud Secret Manager integration
"""

import structlog

from src.config.settings import get_settings


class SecureSettingsManager:
    """Settings manager with secure credential loading"""

    def __init__(self) -> None:
        self.logger = structlog.get_logger("secure_settings")
        self.base_settings = get_settings()
        self._secrets_cache: dict[str, str] = {}

    def get_secure_setting(self, key: str, default: str | None = None) -> str | None:
        """Get a setting securely from environment or base settings"""
        if key in self._secrets_cache:
            return self._secrets_cache[key]

        # First try environment variable (uppercase)
        import os

        env_value = os.getenv(key.upper())
        if env_value:
            self._secrets_cache[key] = env_value
            return env_value

        # Fall back to base settings
        try:
            value = getattr(self.base_settings, key, default)
            if value:
                self._secrets_cache[key] = str(value)
                return str(value)
        except Exception as e:
            self.logger.warning(
                "Failed to get setting",
                error=str(e),
                key=key,
            )

        return default

    def get_discord_token(self) -> str:
        """Get Discord bot token securely"""
        token = self.get_secure_setting("discord_bot_token")
        if not token:
            raise ValueError("Discord bot token not found")
        return token

    def get_gemini_api_key(self) -> str:
        """Get Gemini API key securely"""
        key = self.get_secure_setting("gemini_api_key")
        if not key:
            raise ValueError("Gemini API key not found")
        return key


# Global instance for easy access
_secure_settings_manager: SecureSettingsManager | None = None


def get_secure_settings() -> SecureSettingsManager:
    """Get the global secure settings manager instance"""
    global _secure_settings_manager
    if _secure_settings_manager is None:
        _secure_settings_manager = SecureSettingsManager()
    return _secure_settings_manager
