"""HTTP helpers for Google Calendar integration."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any

import aiohttp

from src.integrations.google_calendar.schemas import (
    CalendarEventRecord,
    CalendarListEntry,
)
from src.utils.mixins import LoggerMixin

RequestHook = Callable[[], None] | None


class GoogleCalendarService(LoggerMixin):
    """Wrapper around Google Calendar REST API."""

    def __init__(
        self, base_url: str = "https://www.googleapis.com/calendar/v3"
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def get_session(
        self,
        *,
        timeout_seconds: int = 30,
        headers: dict[str, str] | None = None,
    ) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            merged_headers = headers or {}
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout_seconds),
                headers=merged_headers,
            )
        elif headers:
            self._session._default_headers.update(headers)  # type: ignore[attr-defined]
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def fetch_calendar_list(
        self,
        *,
        access_token: str,
        on_request: RequestHook = None,
    ) -> list[CalendarListEntry]:
        url = f"{self.base_url}/users/me/calendarList"
        payload = await self._request_json(
            "GET",
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            on_request=on_request,
        )
        if not isinstance(payload, dict):
            return []
        items = payload.get("items", [])
        records: list[CalendarListEntry] = []
        for item in items:
            try:
                records.append(CalendarListEntry.model_validate(item))
            except Exception as exc:  # pragma: no cover - defensive logging
                self.logger.debug(
                    "Failed to parse calendar entry", error=str(exc), raw=item
                )
        return records

    async def fetch_events(
        self,
        *,
        access_token: str,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
        params: dict[str, Any] | None = None,
        on_request: RequestHook = None,
    ) -> list[dict[str, Any]]:
        url = f"{self.base_url}/calendars/{calendar_id}/events"
        query = {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
        }
        if params:
            query.update(params)
        payload = await self._request_json(
            "GET",
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params=query,
            on_request=on_request,
        )
        if not isinstance(payload, dict):
            return []
        return [item for item in payload.get("items", []) if isinstance(item, dict)]

    def build_event_record(
        self,
        raw_event: dict[str, Any],
        *,
        calendar_id: str,
        calendar_name: str | None,
    ) -> CalendarEventRecord | None:
        try:
            parsed = self._normalize_event_times(raw_event)
            parsed["calendar_id"] = calendar_id
            parsed["calendar_name"] = calendar_name
            parsed["raw"] = raw_event
            return CalendarEventRecord.model_validate(parsed)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.logger.debug(
                "Failed to build calendar event record",
                event_id=raw_event.get("id"),
                error=str(exc),
            )
            return None

    async def _request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, Any] | None = None,
        on_request: RequestHook = None,
    ) -> Any:
        session = await self.get_session(headers=headers)
        if on_request:
            try:
                on_request()
            except Exception:
                pass
        async with session.request(method, url, params=params) as resp:
            if resp.status != 200:
                self.logger.debug(
                    "Google Calendar API request failed",
                    url=url,
                    status=resp.status,
                    params=params,
                )
                return None
            try:
                return await resp.json()
            except aiohttp.ContentTypeError:
                self.logger.debug(
                    "Google Calendar API returned non-JSON response", url=url
                )
                return None

    def _normalize_event_times(self, event: dict[str, Any]) -> dict[str, Any]:
        start_info = event.get("start", {}) if isinstance(event, dict) else {}
        end_info = event.get("end", {}) if isinstance(event, dict) else {}

        start_dt = self._parse_datetime(start_info)
        end_dt = self._parse_datetime(end_info)
        all_day = "date" in start_info or start_info.get("dateTime") is None
        result = dict(event)
        result.update(
            {
                "start_time": start_dt,
                "end_time": end_dt,
                "all_day": all_day,
                "event_type": event.get("eventType", "event"),
                "attendees": self._extract_attendees(event.get("attendees", [])),
                "organizer": self._extract_organizer(event.get("organizer")),
                "recurring": bool(event.get("recurrence")),
                "recurrence_rule": ";".join(event["recurrence"])
                if event.get("recurrence")
                else None,
                "created_time": self._parse_datetime(event.get("created")),
                "updated_time": self._parse_datetime(event.get("updated")),
            }
        )
        return result

    def _parse_datetime(self, value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, dict):
            if "dateTime" in value:
                raw = value.get("dateTime")
            elif "date" in value:
                raw = value.get("date") + "T00:00:00"
            else:
                return None
        else:
            raw = value

        if isinstance(raw, str):
            candidate = raw.strip()
            if candidate.endswith("Z"):
                candidate = candidate[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                return None
        return None

    @staticmethod
    def _extract_attendees(attendees: Iterable[Any]) -> list[str]:
        results: list[str] = []
        for attendee in attendees:
            if isinstance(attendee, dict):
                email = attendee.get("email")
                if email:
                    results.append(email)
        return results

    @staticmethod
    def _extract_organizer(organizer: Any) -> str | None:
        if isinstance(organizer, dict):
            return organizer.get("email") or organizer.get("displayName")
        if isinstance(organizer, str):
            return organizer
        return None
