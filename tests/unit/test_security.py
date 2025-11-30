"""Tests for security components"""

import json
import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from pydantic import SecretStr

from src.config.secure_settings import SecureSettingsManager
from src.monitoring.health_server import OAuthCodeVault
from src.security.access_logger import AccessLogger, SecurityEvent, SecurityEventType


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

    def test_env_used_when_no_secret_manager(self):
        with patch.dict(os.environ, {"DISCORD_BOT_TOKEN": "env-token"}, clear=False):
            with patch("src.config.secure_settings.get_settings") as mock_settings:
                mock_settings.return_value = DummySettings(None)
                manager = SecureSettingsManager()
                result = manager.get_secure_setting("discord_bot_token")

        assert result == "env-token"


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

    @pytest.mark.asyncio
    async def test_access_logger_rotates_logs(self, tmp_path):
        """Ensure access logs rotate when exceeding configured size."""
        log_path = tmp_path / "security_access.jsonl"
        logger = AccessLogger(log_file=log_path)
        logger.max_log_file_size = 100
        logger.max_backup_files = 2

        for index in range(20):
            await logger.log_event(
                SecurityEvent(
                    event_type=SecurityEventType.LOGIN_ATTEMPT,
                    user_id="tester",
                    action=f"attempt-{index}",
                    details={"payload": "x" * 64},
                )
            )

        first_backup = tmp_path / "security_access.jsonl.1"
        second_backup = tmp_path / "security_access.jsonl.2"
        third_backup = tmp_path / "security_access.jsonl.3"

        assert first_backup.exists()
        assert log_path.exists()
        assert log_path.stat().st_size < logger.max_log_file_size
        assert second_backup.exists()
        assert not third_backup.exists()
        assert first_backup.stat().st_size > 0

    def test_get_access_logger_respects_settings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Verify singleton uses configured rotation values."""
        from src.security import access_logger as access_logger_module

        class DummySettings:
            access_log_rotation_size_mb = 1.5
            access_log_rotation_backups = 4

        captured: dict[str, int | None] = {"size": None, "backups": None}

        class DummyLogger:
            def __init__(
                self,
                *,
                log_file=None,
                max_log_file_size=None,
                max_backup_files=None,
            ):
                captured["size"] = max_log_file_size
                captured["backups"] = max_backup_files

        monkeypatch.setattr(access_logger_module, "_access_logger", None)
        monkeypatch.setattr(
            access_logger_module, "get_settings", lambda: DummySettings()
        )
        monkeypatch.setattr(access_logger_module, "AccessLogger", DummyLogger)

        logger_instance = access_logger_module.get_access_logger()

        expected_size = int(DummySettings.access_log_rotation_size_mb * 1024 * 1024)
        assert captured["size"] == expected_size
        assert captured["backups"] == DummySettings.access_log_rotation_backups
        assert isinstance(logger_instance, DummyLogger)

        access_logger_module._access_logger = None


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
