"""Shared schemas for integration packages."""

from src.lifelog.integrations.base import (
    BaseIntegration,
    IntegrationConfig,
    IntegrationData,
    IntegrationMetrics,
    IntegrationStatus,
)

__all__ = [
    "BaseIntegration",
    "IntegrationConfig",
    "IntegrationData",
    "IntegrationMetrics",
    "IntegrationStatus",
]
