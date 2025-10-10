"""
外部システム連携モジュール

ライフログシステムと外部サービスの統合
"""

from .base import BaseIntegration, IntegrationConfig, IntegrationStatus
from .bridge import IntegrationBridge, create_default_bridge
from .garmin import GarminIntegration
from .google_calendar import GoogleCalendarIntegration
from .manager import IntegrationManager
from .pipelines.scheduler import (
    IntegrationSyncScheduler,
    IntegrationSyncSchedulerConfig,
)

# Backward compatibility aliases (deprecated)
IntegrationScheduler = IntegrationSyncScheduler
IntegrationSchedulerConfig = IntegrationSyncSchedulerConfig

__all__ = [
    "BaseIntegration",
    "IntegrationConfig",
    "IntegrationStatus",
    "IntegrationBridge",
    "create_default_bridge",
    "GarminIntegration",
    "GoogleCalendarIntegration",
    "IntegrationManager",
    "IntegrationSyncScheduler",
    "IntegrationSyncSchedulerConfig",
]
