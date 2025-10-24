"""Test utils module functionality."""

import logging
from collections.abc import Iterator
from unittest.mock import Mock

import pytest

from src.utils.lazy_loader import LazyComponentManager, get_component_manager
from src.utils.logger import get_logger, setup_logging
from src.utils.mixins import LoggerMixin


@pytest.fixture(autouse=True)
def _required_settings_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-token")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")


@pytest.fixture(autouse=True)
def _reset_logging_state() -> Iterator[None]:
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()
    try:
        yield
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            handler.close()
        logging.shutdown()


class TestLogger:
    """Test logging functionality."""

    def test_setup_logging(self):
        """Test logging setup doesn't raise errors."""
        setup_logging()
        assert True  # If no exception, test passes

    def test_setup_logging_writes_plain_message_to_file(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test log file output uses raw message format."""
        monkeypatch.chdir(tmp_path)

        setup_logging()

        test_message = "logging format check"
        logger = logging.getLogger("format-check")
        logger.info(test_message)

        root_logger = logging.getLogger()
        file_handlers = [
            handler
            for handler in root_logger.handlers
            if isinstance(handler, logging.FileHandler)
        ]
        assert file_handlers, "FileHandler が設定されていません"

        for handler in file_handlers:
            handler.flush()
            handler.close()
            root_logger.removeHandler(handler)

        log_file = tmp_path / "logs" / "bot.log"
        assert log_file.exists()
        lines = log_file.read_text(encoding="utf-8").splitlines()
        assert lines, "ログファイルが空です"
        assert lines[-1].endswith(test_message)

    def test_get_logger_returns_logger(self):
        """Test get_logger returns a logger instance."""
        logger = get_logger("test")
        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")


class TestLoggerMixin:
    """Test LoggerMixin functionality."""

    def test_logger_mixin_provides_logger(self):
        """Test LoggerMixin provides logger property."""

        class TestClass(LoggerMixin):
            pass

        instance = TestClass()
        logger = instance.logger

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "error")
        assert hasattr(logger, "warning")


class TestLazyComponentManager:
    """Test lazy loading component manager."""

    def test_get_component_manager_singleton(self):
        """Test component manager is singleton."""
        manager1 = get_component_manager()
        manager2 = get_component_manager()
        assert manager1 is manager2

    def test_component_manager_basic_functionality(self):
        """Test basic component manager operations."""
        manager = LazyComponentManager()

        # Test component registration
        test_component = Mock()
        factory = Mock(return_value=test_component, __name__="test_factory")

        manager.register_component("test_comp", factory, cache_duration=60.0)

        # Test component retrieval
        retrieved = manager.get_component("test_comp")
        assert retrieved == test_component
        factory.assert_called_once()

    def test_component_manager_caching(self):
        """Test component caching works properly."""
        manager = LazyComponentManager()

        test_component = Mock()
        factory = Mock(return_value=test_component, __name__="test_factory")

        manager.register_component("cached_comp", factory, cache_duration=60.0)

        # First call
        comp1 = manager.get_component("cached_comp")
        # Second call should return cached version
        comp2 = manager.get_component("cached_comp")

        assert comp1 == comp2 == test_component
        factory.assert_called_once()  # Factory should only be called once

    def test_component_manager_unregistered_component(self):
        """Test getting unregistered component raises KeyError."""
        manager = LazyComponentManager()

        with pytest.raises(KeyError, match="Component 'nonexistent' not found"):
            manager.get_component("nonexistent")
