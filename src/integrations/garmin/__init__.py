"""Garmin integration package."""

from src.integrations.garmin.client import GarminClient
from src.integrations.garmin.models import (
    ActivityData,
    DataError,
    DataSource,
    GarminAuthenticationError,
    GarminConnectionError,
    GarminDataRetrievalError,
    GarminOfflineError,
    GarminRateLimitError,
    GarminTimeoutError,
    HealthData,
    HeartRateData,
    SleepData,
    StepsData,
)
from src.integrations.garmin.schemas import (
    ActivityRecord,
    DailyHealthMetrics,
    DailyHealthResult,
)

__all__ = [
    "GarminClient",
    "ActivityData",
    "DataError",
    "DataSource",
    "GarminAuthenticationError",
    "GarminConnectionError",
    "GarminDataRetrievalError",
    "GarminOfflineError",
    "GarminRateLimitError",
    "GarminTimeoutError",
    "HealthData",
    "HeartRateData",
    "SleepData",
    "StepsData",
    "ActivityRecord",
    "DailyHealthMetrics",
    "DailyHealthResult",
]
