"""Test utils module functionality."""

from unittest.mock import Mock

import pytest

from src.utils.lazy_loader import LazyComponentManager, get_component_manager
from src.utils.logger import get_logger, setup_logging
from src.utils.mixins import LoggerMixin


class TestLogger:
    """Test logging functionality."""

    def test_setup_logging(self):
        """Test logging setup doesn't raise errors."""
        setup_logging()
        assert True  # If no exception, test passes

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
