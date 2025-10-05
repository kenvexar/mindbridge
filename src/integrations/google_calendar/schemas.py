"""Typed data objects for Google Calendar integration service."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CalendarListEntry(BaseModel):
    """Metadata about a calendar returned by the list API."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    calendar_id: str = Field(alias="id")
    summary: str | None = None
    access_role: str | None = None
    selected: bool | None = None
    time_zone: str | None = None

    def should_sync(self) -> bool:
        """Return True if this calendar is marked as selected/primary."""
        return bool(self.selected or self.access_role in {"owner", "writer"})


class CalendarEventRecord(BaseModel):
    """Normalized Google Calendar event."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_id: str = Field(alias="id")
    summary: str | None = None
    description: str | None = None
    location: str | None = None

    start_time: datetime
    end_time: datetime
    all_day: bool = False

    calendar_id: str
    calendar_name: str | None = None

    status: str | None = None
    transparency: str | None = None
    event_type: str | None = None

    attendees: list[str] = Field(default_factory=list)
    organizer: str | None = None

    recurring: bool = False
    recurrence_rule: str | None = None

    created_time: datetime | None = None
    updated_time: datetime | None = None

    raw: dict[str, Any] = Field(default_factory=dict)

    def duration_minutes(self) -> float:
        return max(0.0, (self.end_time - self.start_time).total_seconds() / 60)
