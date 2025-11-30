"""
Secure settings loader with enhanced validation for personal use.
個人使用向け強化セキュリティ設定管理
"""

from __future__ import annotations

import os
import re
from typing import Any

import structlog
from pydantic import SecretStr

from src.config.settings import get_settings


class SecureSettingsManager:
    """Settings manager with secure credential loading"""

    def __init__(self) -> None:
        self.logger = structlog.get_logger("secure_settings")
        self.base_settings = get_settings()
        self._secrets_cache: dict[str, str] = {}

        # セキュリティ: 個人使用向け設定検証ルール
        self._validation_rules = {
            "discord_bot_token": self._validate_discord_token,
            "gemini_api_key": self._validate_gemini_key,
            "github_token": self._validate_github_token,
            "encryption_key": self._validate_encryption_key,
        }

    def get_secure_setting(self, key: str, default: str | None = None) -> str | None:
        """Get a setting securely from environment or base settings"""
        if key in self._secrets_cache:
            return self._secrets_cache[key]

        # First try environment variable (uppercase)

        env_value = os.getenv(key.upper())
        if env_value:
            self._secrets_cache[key] = env_value
            return env_value

        # Fall back to base settings
        try:
            value = getattr(self.base_settings, key, default)
            normalized = self._normalize_secret_value(value)
            if normalized:
                self._secrets_cache[key] = normalized
                return normalized
        except Exception as e:
            self.logger.warning(
                "Failed to get setting",
                error=str(e),
                key=key,
            )

        return default

    def _normalize_secret_value(self, value: Any) -> str | None:
        """Convert supported secret types to plain string."""
        if value is None:
            return None

        if isinstance(value, SecretStr):
            return value.get_secret_value()

        get_secret = getattr(value, "get_secret_value", None)
        if callable(get_secret):
            try:
                return get_secret()
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger.warning(
                    "Failed to unwrap secret value",
                    error=str(exc),
                    value_type=type(value).__name__,
                )
                return None

        return str(value)

    def get_discord_token(self) -> str:
        """Get Discord bot token securely with validation"""
        token = self.get_secure_setting("discord_bot_token")
        if not token:
            raise ValueError("Discord bot token not found")

        # セキュリティ: トークン形式を検証
        is_valid, message = self._validate_discord_token(token)
        if not is_valid:
            self.logger.warning("Discord token validation failed", reason=message)
            # 個人使用なので警告のみ、処理は継続
        else:
            self.logger.info("Discord token validation passed")

        return token

    def get_gemini_api_key(self) -> str:
        """Get Gemini API key securely with validation"""
        key = self.get_secure_setting("gemini_api_key")
        if not key:
            raise ValueError("Gemini API key not found")

        # セキュリティ: キー形式を検証
        is_valid, message = self._validate_gemini_key(key)
        if not is_valid:
            self.logger.warning("Gemini API key validation failed", reason=message)
            # 個人使用なので警告のみ、処理は継続
        else:
            self.logger.info("Gemini API key validation passed")

        return key

    def _validate_discord_token(self, token: str) -> tuple[bool, str]:
        """Discord トークンの形式を検証"""
        if not token or len(token) < 40:
            return False, "Discord token too short (minimum 40 characters)"

        # Discord bot token は通常 "Bot " または長いランダム文字列
        # 実際のトークンは 59-70 文字程度
        if len(token) >= 40 and re.match(r"^[A-Za-z0-9._-]+$", token):
            return True, "Valid Discord token format"

        return False, "Discord token format appears invalid"

    def _validate_gemini_key(self, key: str) -> tuple[bool, str]:
        """Gemini API キーの形式を検証"""
        if not key or len(key) < 20:
            return False, "Gemini API key too short"

        # Gemini API key は通常英数字とハイフン、アンダースコアの組み合わせ
        # 実際のキーは 39 文字程度
        if re.match(r"^[A-Za-z0-9_-]+$", key):
            return True, "Valid Gemini API key format"

        return False, "Gemini API key contains invalid characters"

    def _validate_github_token(self, token: str) -> tuple[bool, str]:
        """GitHub トークンの形式を検証"""
        if not token:
            return False, "GitHub token is empty"

        # GitHub の新しいトークン形式をチェック
        if token.startswith("ghp_") and len(token) == 40:
            return True, "Valid GitHub personal access token format"
        elif token.startswith("gho_") and len(token) >= 36:
            return True, "Valid GitHub OAuth token format"
        elif token.startswith("github_pat_") and len(token) >= 82:
            return True, "Valid GitHub fine-grained token format"
        elif len(token) >= 30 and re.match(r"^[a-f0-9]+$", token):
            return True, "Valid GitHub classic token format"

        return False, "GitHub token format appears invalid"

    def _validate_encryption_key(self, key: str) -> tuple[bool, str]:
        """暗号化キーの強度を検証"""
        if not key:
            return False, "Encryption key is empty"

        # Base64 エンコードされた 32 バイトキーかチェック
        try:
            import base64

            decoded = base64.urlsafe_b64decode(key)
            if len(decoded) != 32:
                return False, f"Encryption key must be 32 bytes (got {len(decoded)})"
            return True, "Valid encryption key"
        except Exception:
            # 生の 32 バイト文字列の場合
            if len(key) == 32:
                return True, "Valid raw encryption key"
            return False, "Invalid encryption key format"


# Global instance for easy access
_secure_settings_manager: SecureSettingsManager | None = None


def get_secure_settings() -> SecureSettingsManager:
    """Get the global secure settings manager instance"""
    global _secure_settings_manager
    if _secure_settings_manager is None:
        _secure_settings_manager = SecureSettingsManager()
    return _secure_settings_manager
