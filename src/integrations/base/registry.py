"""Registry utilities for integration packages."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

TIntegration = TypeVar("TIntegration")
Factory = Callable[..., TIntegration]


class IntegrationRegistry:
    """Lightweight registry to map integration names to factories."""

    def __init__(self) -> None:
        self._registry: dict[str, Factory[Any]] = {}

    def register(self, name: str, factory: Factory[Any]) -> None:
        """Register a new integration factory under the given name."""
        self._registry[name] = factory

    def unregister(self, name: str) -> None:
        """Remove a factory from the registry if it exists."""
        self._registry.pop(name, None)

    def create(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Instantiate the integration associated with the given name."""
        factory = self._registry.get(name)
        if factory is None:
            raise KeyError(f"Integration '{name}' is not registered")
        return factory(*args, **kwargs)

    def get(self, name: str) -> Factory[Any] | None:
        """Return the raw factory callable for inspection."""
        return self._registry.get(name)

    def available(self) -> dict[str, Factory[Any]]:
        """Return a snapshot of all registered integrations."""
        return dict(self._registry)


integration_registry = IntegrationRegistry()


def register_integration(name: str, factory: Factory[Any]) -> None:
    """Convenience wrapper to register via the global registry."""
    integration_registry.register(name, factory)
