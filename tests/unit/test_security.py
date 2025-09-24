"""Tests for security components"""

import json
import os
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.config.secure_settings import SecureSettingsManager
from src.monitoring.health_server import OAuthCodeVault
from src.security.access_logger import AccessLogger, SecurityEvent, SecurityEventType
from src.security.secret_manager import PersonalConfigManager, PersonalSecretManager


class DummySecureSettingsManager:
    def __init__(self, encryption_key: str | None):
        self._encryption_key = encryption_key

    def get_secure_setting(self, key: str, default: str | None = None) -> str | None:
        if key == "encryption_key":
            return self._encryption_key
        return default


class DummySettings:
    def __init__(self, value):
        self.discord_bot_token = value


class TestSecureSettingsManager:
    """Tests for SecureSettingsManager secret handling"""

    def test_secretstr_is_unwrapped(self):
        secret = SecretStr("plain-token")

        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": ""}, clear=False):
            with patch("src.config.secure_settings.get_settings") as mock_settings:
                mock_settings.return_value = DummySettings(secret)
                manager = SecureSettingsManager()

            assert manager.get_secure_setting("discord_bot_token") == "plain-token"
            # Cache should return raw value even after SecretStr is gone
            assert manager.get_secure_setting("discord_bot_token") == "plain-token"


class TestOAuthCodeVault:
    """Test secure storage of OAuth codes"""

    def test_store_code_encrypted(self, tmp_path):
        key = Fernet.generate_key().decode()
        storage_path = tmp_path / "oauth.enc"
        vault = OAuthCodeVault(
            storage_path=storage_path, secure_settings=DummySecureSettingsManager(key)
        )

        stored_path = vault.store_code("sensitive-code")
        assert stored_path == storage_path

        contents = stored_path.read_text().strip()
        assert "sensitive-code" not in contents
        record = json.loads(contents)

        decrypted = Fernet(key).decrypt(record["payload"].encode()).decode()
        assert decrypted == "sensitive-code"

    def test_store_code_without_key(self, tmp_path):
        storage_path = tmp_path / "oauth.enc"
        vault = OAuthCodeVault(
            storage_path=storage_path, secure_settings=DummySecureSettingsManager(None)
        )

        result = vault.store_code("code")
        assert result is None
        assert not storage_path.exists()


class TestPersonalSecretManager:
    """Test PersonalSecretManager functionality"""

    def test_init(self):
        """Test initialization"""
        manager = PersonalSecretManager("test-project")
        assert manager.project_id == "test-project"
        assert isinstance(manager._cache, dict)

    @pytest.mark.asyncio
    async def test_get_secret_from_env(self):
        """Test getting secret from environment variable"""
        manager = PersonalSecretManager()

        with patch.dict(os.environ, {"TEST_SECRET": "test_value"}):
            result = await manager.get_secret("test-secret")
            assert result == "test_value"

    @pytest.mark.asyncio
    async def test_get_secret_not_found(self):
        """Test getting non-existent secret"""
        manager = PersonalSecretManager()

        with patch.dict(os.environ, {}, clear=True):
            result = await manager.get_secret("nonexistent-secret")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_secret_caching(self):
        """Test secret caching functionality"""
        manager = PersonalSecretManager()

        with patch.dict(os.environ, {"CACHED_SECRET": "cached_value"}):
            # First call should access environment
            result1 = await manager.get_secret("cached-secret")
            assert result1 == "cached_value"

            # Second call should use cache
            with patch.dict(os.environ, {}, clear=True):
                result2 = await manager.get_secret("cached-secret")
                assert result2 == "cached_value"

    def test_clear_cache(self):
        """Test cache clearing"""
        manager = PersonalSecretManager()
        manager._cache["test"] = "value"

        manager.clear_cache()
        assert len(manager._cache) == 0


class TestPersonalConfigManager:
    """Test PersonalConfigManager functionality"""

    def test_init(self):
        """Test initialization"""
        manager = PersonalConfigManager()
        assert manager.secret_manager is not None

    @pytest.mark.asyncio
    async def test_get_config_value_discord_token(self):
        """Test getting Discord token via config value"""
        manager = PersonalConfigManager()

        with patch.object(
            manager.secret_manager, "get_secret", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = "discord_token_123"
            result = await manager.get_config_value("discord_bot_token")
            assert result == "discord_token_123"
            mock_get.assert_called_once_with("discord-bot-token")

    @pytest.mark.asyncio
    async def test_get_config_value_gemini_key(self):
        """Test getting Gemini API key via config value"""
        manager = PersonalConfigManager()

        with patch.object(
            manager.secret_manager, "get_secret", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = "gemini_key_123"
            result = await manager.get_config_value("gemini_api_key")
            assert result == "gemini_key_123"
            mock_get.assert_called_once_with("gemini-api-key")


class TestAccessLogger:
    """Test AccessLogger functionality"""

    def test_init(self):
        """Test initialization"""
        logger = AccessLogger()
        assert logger.logger is not None
        assert isinstance(logger.recent_events, list)

    @pytest.mark.asyncio
    async def test_log_event_success(self):
        """Test logging successful event"""
        logger = AccessLogger()

        event = SecurityEvent(
            event_type=SecurityEventType.LOGIN_ATTEMPT,
            user_id="test_user",
            action="test_login",
            success=True,
            details={"source": "test"},
        )

        # Test that event logging works without errors
        await logger.log_event(event)

        # Check that event was added to recent events
        assert len(logger.recent_events) == 1
        assert logger.recent_events[0].action == "test_login"

    @pytest.mark.asyncio
    async def test_log_event_failure(self):
        """Test logging failed event"""
        logger = AccessLogger()

        event = SecurityEvent(
            event_type=SecurityEventType.LOGIN_ATTEMPT,
            user_id="test_user",
            action="test_login",
            success=False,
            details={"source": "test"},
        )

        await logger.log_event(event)

        # Failed attempts should be tracked
        assert len(logger.failed_attempts["test_user"]) == 1
        # Event should be added to recent events
        assert len(logger.recent_events) == 1


class TestSecurityIntegration:
    """Integration tests for security components"""

    @pytest.mark.asyncio
    async def test_access_logging_integration(self):
        """Test access logging integration"""
        from src.security.access_logger import get_access_logger, log_security_event

        logger = get_access_logger()
        assert logger is not None

        # Test logging without errors
        await log_security_event(
            SecurityEventType.LOGIN_ATTEMPT, action="test_integration", success=True
        )

    @pytest.mark.asyncio
    async def test_security_report_generation(self):
        """Test security report generation"""
        logger = AccessLogger()

        # Create some test events
        event1 = SecurityEvent(
            event_type=SecurityEventType.LOGIN_ATTEMPT,
            user_id="user1",
            action="login",
            success=True,
        )
        event2 = SecurityEvent(
            event_type=SecurityEventType.LOGIN_ATTEMPT,
            user_id="user1",
            action="login",
            success=False,
        )

        await logger.log_event(event1)
        await logger.log_event(event2)

        # Generate report
        report = await logger.get_security_report(hours=1)

        assert report["total_events"] == 2
        assert report["failed_events"] == 1
        assert "user1" in report["most_active_users"]


class TestSecurityHelpers:
    """Test security helper functions"""

    def test_security_event_type_enum(self):
        """Test SecurityEventType enum values"""
        assert SecurityEventType.LOGIN_ATTEMPT.value == "login_attempt"
        assert SecurityEventType.COMMAND_EXECUTION.value == "command_execution"
        assert SecurityEventType.SUSPICIOUS_ACTIVITY.value == "suspicious_activity"

    @pytest.mark.asyncio
    async def test_error_handling_in_secret_manager(self):
        """Test error handling in secret manager"""
        manager = PersonalSecretManager()

        # Test with empty string
        result = await manager.get_secret("")
        assert result is None

    def test_security_event_creation(self):
        """Test SecurityEvent creation"""
        event = SecurityEvent(
            event_type=SecurityEventType.LOGIN_ATTEMPT,
            user_id="test_user",
            action="test_action",
            success=True,
            details={"key": "value"},
        )

        assert event.event_type == SecurityEventType.LOGIN_ATTEMPT
        assert event.user_id == "test_user"
        assert event.action == "test_action"
        assert event.success is True
        assert event.details["key"] == "value"
