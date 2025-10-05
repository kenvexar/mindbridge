"""Typed data objects for Garmin integration service."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ActivityRecord(BaseModel):
    """Structured representation of a Garmin activity."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    activity_id: str
    activity_type: str
    activity_name: str | None = None
    start_time: datetime
    duration: int | None = Field(default=None, description="Duration in seconds")
    distance: float | None = Field(default=None, description="Distance in meters")
    calories: int | None = None
    avg_heart_rate: int | None = None
    max_heart_rate: int | None = None
    elevation_gain: float | None = None
    avg_speed: float | None = Field(default=None, description="Speed in m/s")
    steps: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class DailyHealthMetrics(BaseModel):
    """Aggregated daily health metrics."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    date: datetime
    steps: int | None = None
    distance: float | None = None
    calories: int | None = None
    floors_climbed: int | None = None

    sleep_start_time: datetime | None = None
    sleep_end_time: datetime | None = None
    sleep_duration: int | None = Field(default=None, description="Minutes")
    measurable_sleep_duration: int | None = Field(default=None, description="Minutes")
    body_battery_during_sleep: int | None = None
    deep_sleep: int | None = Field(default=None, description="Minutes")
    light_sleep: int | None = Field(default=None, description="Minutes")
    rem_sleep: int | None = Field(default=None, description="Minutes")
    sleep_score: int | None = None

    resting_heart_rate: int | None = None
    max_heart_rate: int | None = None

    stress_avg: int | None = None
    body_battery_max: int | None = None
    body_battery_min: int | None = None

    weight: float | None = None
    body_fat: float | None = None
    body_water: float | None = None
    muscle_mass: float | None = None

    def has_any_data(self) -> bool:
        """Return True if any meaningful metric is populated."""
        for value in self.model_dump(exclude={"date"}, exclude_none=True).values():
            if isinstance(value, (int, float)) and value != 0:
                return True
            if isinstance(value, datetime):
                return True
        return False


class DailyHealthResult(BaseModel):
    """Daily health metrics alongside the raw payloads used to build them."""

    metrics: DailyHealthMetrics
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    def has_any_data(self) -> bool:
        return self.metrics.has_any_data()
