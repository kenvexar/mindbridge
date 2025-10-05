"""Helpers for interacting with Garmin HTTP APIs."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

from src.integrations.garmin.client import GarminClient
from src.integrations.garmin.schemas import (
    ActivityRecord,
    DailyHealthMetrics,
    DailyHealthResult,
)
from src.utils.mixins import LoggerMixin

RequestHook = Callable[[], None] | None


class GarminIntegrationService(LoggerMixin):
    """Low-level helper around Garmin Connect endpoints."""

    def __init__(self, base_url: str = "https://connect.garmin.com") -> None:
        self.base_url = base_url.rstrip("/")
        self._session: aiohttp.ClientSession | None = None

    async def get_session(
        self,
        *,
        user_agent: str = "MindBridge-Lifelog/1.0",
        timeout: int = 30,
    ) -> aiohttp.ClientSession:
        """Return a shared aiohttp session, creating it when needed."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers={"User-Agent": user_agent},
            )
        return self._session

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def authenticate_with_client(self, cache_dir: Path | None = None) -> bool:
        """Use GarminClient to test credential-based authentication."""
        client = GarminClient(cache_dir=cache_dir)
        return await client.authenticate()

    async def test_connection_with_client(
        self, cache_dir: Path | None = None
    ) -> dict[str, Any]:
        """Use GarminClient to test connectivity."""
        client = GarminClient(cache_dir=cache_dir)
        return await client.test_connection()

    async def fetch_activities(
        self,
        *,
        access_token: str,
        start_date: datetime,
        end_date: datetime,
        activity_types: Sequence[str] | None = None,
        on_request: RequestHook = None,
    ) -> list[dict[str, Any]]:
        """Fetch raw activity JSON list between the given dates."""
        url = (
            f"{self.base_url}/modern/proxy/"
            "activitylist-service/activities/search/activities"
        )
        params = {
            "start": "0",
            "limit": "100",
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
        }
        headers = {"Authorization": f"Bearer {access_token}"}

        payload = await self._request_json(
            "GET", url, headers=headers, params=params, on_request=on_request
        )
        if not isinstance(payload, list):
            return []

        filters = {item.lower() for item in activity_types or []}
        if not filters:
            return payload

        filtered: list[dict[str, Any]] = []
        for item in payload:
            activity_type = item.get("activityType", {}).get("typeKey", "").lower()
            if not filters or activity_type in filters:
                filtered.append(item)
        return filtered

    async def fetch_daily_steps(
        self,
        *,
        access_token: str,
        date_str: str,
        on_request: RequestHook = None,
    ) -> dict[str, Any]:
        """Fetch step summary for the given date."""
        url = f"{self.base_url}/modern/proxy/userstats-service/wellness/{date_str}"
        headers = {"Authorization": f"Bearer {access_token}"}
        data = await self._request_json(
            "GET", url, headers=headers, on_request=on_request
        )
        return data if isinstance(data, dict) else {}

    async def fetch_daily_sleep(
        self,
        *,
        access_token: str,
        user_uuid: str,
        date_str: str,
        on_request: RequestHook = None,
    ) -> dict[str, Any]:
        """Fetch daily sleep summary and detailed DTO."""
        headers = {"Authorization": f"Bearer {access_token}"}

        summary_url = f"{self.base_url}/modern/proxy/usersummary-service/usersummary/daily/{user_uuid}"
        summary = await self._request_json(
            "GET",
            summary_url,
            headers=headers,
            params={"calendarDate": date_str},
            on_request=on_request,
        )

        detail_url = f"{self.base_url}/modern/proxy/wellness-service/wellness/dailySleepData/{user_uuid}"
        detailed = await self._request_json(
            "GET",
            detail_url,
            headers=headers,
            params={"date": date_str},
            on_request=on_request,
        )

        return {
            "summary": summary if isinstance(summary, dict) else {},
            "detail": detailed if isinstance(detailed, dict) else {},
        }

    async def fetch_daily_heart_rate(
        self,
        *,
        access_token: str,
        date_str: str,
        on_request: RequestHook = None,
    ) -> dict[str, Any]:
        """Fetch heart rate metrics."""
        url = f"{self.base_url}/modern/proxy/userstats-service/wellness/{date_str}"
        headers = {"Authorization": f"Bearer {access_token}"}
        data = await self._request_json(
            "GET", url, headers=headers, on_request=on_request
        )
        return data if isinstance(data, dict) else {}

    async def fetch_daily_stress(
        self,
        *,
        access_token: str,
        date_str: str,
        on_request: RequestHook = None,
    ) -> dict[str, Any]:
        """Fetch stress metrics."""
        url = f"{self.base_url}/modern/proxy/userstats-service/stress-level/{date_str}"
        headers = {"Authorization": f"Bearer {access_token}"}
        data = await self._request_json(
            "GET", url, headers=headers, on_request=on_request
        )
        return data if isinstance(data, dict) else {}

    async def fetch_body_composition(
        self,
        *,
        access_token: str,
        date_str: str,
        on_request: RequestHook = None,
    ) -> dict[str, Any]:
        """Fetch body composition metrics for a date."""
        url = f"{self.base_url}/modern/proxy/weight-service/weight/dateRange"
        headers = {"Authorization": f"Bearer {access_token}"}
        payload = await self._request_json(
            "GET",
            url,
            headers=headers,
            params={"startDate": date_str, "endDate": date_str},
            on_request=on_request,
        )
        if isinstance(payload, list) and payload:
            first = payload[0]
            return first if isinstance(first, dict) else {}
        return {}

    async def get_activity_records(
        self,
        *,
        access_token: str,
        start_date: datetime,
        end_date: datetime,
        activity_types: Sequence[str] | None = None,
        on_request: RequestHook = None,
    ) -> list[ActivityRecord]:
        """Return structured activity records.

        Low-level fetching errors are logged and skipped so that downstream
        processing can continue gracefully.
        """
        records: list[ActivityRecord] = []
        payload = await self.fetch_activities(
            access_token=access_token,
            start_date=start_date,
            end_date=end_date,
            activity_types=activity_types,
            on_request=on_request,
        )
        for item in payload:
            try:
                record = self._build_activity_record(item)
                if record is not None:
                    records.append(record)
            except Exception as exc:  # pragma: no cover - defensive logging
                activity_id = item.get("activityId") if isinstance(item, dict) else None
                self.logger.debug(
                    "Failed to build activity record",
                    activity_id=activity_id,
                    error=str(exc),
                )
        return records

    async def get_daily_health_result(
        self,
        *,
        access_token: str,
        user_uuid: str,
        target_date: datetime,
        include_body_composition: bool = True,
        on_request: RequestHook = None,
    ) -> DailyHealthResult:
        """Aggregate daily health metrics for the given date."""
        date_str = target_date.strftime("%Y-%m-%d")
        tasks = [
            self.fetch_daily_steps(
                access_token=access_token,
                date_str=date_str,
                on_request=on_request,
            ),
            self.fetch_daily_sleep(
                access_token=access_token,
                user_uuid=user_uuid,
                date_str=date_str,
                on_request=on_request,
            ),
            self.fetch_daily_heart_rate(
                access_token=access_token,
                date_str=date_str,
                on_request=on_request,
            ),
            self.fetch_daily_stress(
                access_token=access_token,
                date_str=date_str,
                on_request=on_request,
            ),
        ]

        if include_body_composition:
            tasks.append(
                self.fetch_body_composition(
                    access_token=access_token,
                    date_str=date_str,
                    on_request=on_request,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        processed: list[dict[str, Any]] = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.debug(
                    "Garmin daily metric fetch failed",
                    index=idx,
                    date=date_str,
                    error=str(result),
                )
                processed.append({})
            else:
                processed.append(result if isinstance(result, dict) else {})

        steps_raw, sleep_raw, heart_raw, stress_raw, *rest = processed
        body_raw = rest[0] if rest else {}

        metrics = self._build_daily_metrics(
            date=target_date,
            steps_payload=steps_raw,
            sleep_payload=sleep_raw,
            heart_payload=heart_raw,
            stress_payload=stress_raw,
            body_payload=body_raw,
        )

        raw_payload = {
            "steps": steps_raw,
            "sleep": sleep_raw,
            "heart_rate": heart_raw,
            "stress": stress_raw,
        }
        if include_body_composition:
            raw_payload["body_composition"] = body_raw

        return DailyHealthResult(metrics=metrics, raw_payload=raw_payload)

    def _build_activity_record(self, item: dict[str, Any]) -> ActivityRecord | None:
        activity_id = item.get("activityId")
        if activity_id is None:
            return None
        activity_type = item.get("activityType", {}).get("typeKey", "").lower()
        start_value = item.get("startTimeLocal")
        start_time = self._normalize_timestamp(start_value)
        if start_time is None:
            return None
        return ActivityRecord(
            activity_id=str(activity_id),
            activity_type=activity_type,
            activity_name=item.get("activityName"),
            start_time=start_time,
            duration=int(item["duration"])
            if item.get("duration") is not None
            else None,
            distance=item.get("distance"),
            calories=item.get("calories"),
            avg_heart_rate=item.get("averageHR"),
            max_heart_rate=item.get("maxHR"),
            elevation_gain=item.get("elevationGain"),
            avg_speed=item.get("averageSpeed"),
            steps=item.get("steps"),
            raw=item,
        )

    def _build_daily_metrics(
        self,
        *,
        date: datetime,
        steps_payload: dict[str, Any],
        sleep_payload: dict[str, Any],
        heart_payload: dict[str, Any],
        stress_payload: dict[str, Any],
        body_payload: dict[str, Any],
    ) -> DailyHealthMetrics:
        stats: dict[str, Any] = {}
        stats.update(self._parse_steps_metrics(steps_payload))
        stats.update(self._parse_sleep_metrics(sleep_payload))
        stats.update(self._parse_heart_rate_metrics(heart_payload))
        stats.update(self._parse_stress_metrics(stress_payload))
        stats.update(self._parse_body_composition_metrics(body_payload))
        normalized_date = datetime.combine(date.date(), datetime.min.time())
        return DailyHealthMetrics(date=normalized_date, **stats)

    @staticmethod
    def _parse_steps_metrics(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        return {
            "steps": payload.get("totalSteps"),
            "distance": payload.get("totalDistance"),
            "calories": payload.get("activeKilocalories"),
            "floors_climbed": payload.get("floorsAscended"),
        }

    def _parse_sleep_metrics(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
        detail = payload.get("detail", {}) if isinstance(payload, dict) else {}
        sleep_dto = detail.get("dailySleepDTO") if isinstance(detail, dict) else None

        result: dict[str, Any] = {}
        sleeping_seconds = summary.get("sleepingSeconds")
        measurable_sleep = summary.get("measurableAsleepDuration")
        body_battery_sleep = summary.get("bodyBatteryDuringSleep")

        result.update(
            {
                "sleep_duration": self._seconds_to_minutes(sleeping_seconds),
                "measurable_sleep_duration": self._seconds_to_minutes(measurable_sleep),
                "body_battery_during_sleep": body_battery_sleep
                if body_battery_sleep and body_battery_sleep > 0
                else None,
            }
        )

        if sleep_dto and isinstance(sleep_dto, dict):
            start_ts = sleep_dto.get("sleepStartTimestampLocal")
            end_ts = sleep_dto.get("sleepEndTimestampLocal")
            result["sleep_start_time"] = self._normalize_timestamp(start_ts)
            result["sleep_end_time"] = self._normalize_timestamp(end_ts)
            result["deep_sleep"] = self._seconds_to_minutes(
                sleep_dto.get("deepSleepSeconds")
            )
            result["light_sleep"] = self._seconds_to_minutes(
                sleep_dto.get("lightSleepSeconds")
            )
            result["rem_sleep"] = self._seconds_to_minutes(
                sleep_dto.get("remSleepSeconds")
            )
            if sleep_dto.get("overallSleepScore") is not None:
                result["sleep_score"] = sleep_dto.get("overallSleepScore")

        return {key: value for key, value in result.items() if value is not None}

    @staticmethod
    def _parse_heart_rate_metrics(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        return {
            "resting_heart_rate": payload.get("restingHeartRate"),
            "max_heart_rate": payload.get("maxHeartRate"),
        }

    @staticmethod
    def _parse_stress_metrics(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        return {
            "stress_avg": payload.get("overallStressLevel"),
            "body_battery_max": payload.get("maxStressLevel"),
            "body_battery_min": payload.get("minStressLevel"),
        }

    @staticmethod
    def _parse_body_composition_metrics(payload: dict[str, Any]) -> dict[str, Any]:
        if not payload:
            return {}
        return {
            "weight": payload.get("weight"),
            "body_fat": payload.get("bodyFat"),
            "body_water": payload.get("bodyWater"),
            "muscle_mass": payload.get("muscleMass"),
        }

    @staticmethod
    def _seconds_to_minutes(value: Any) -> int | None:
        try:
            seconds = int(value)
        except (TypeError, ValueError):
            return None
        if seconds <= 0:
            return None
        minutes = seconds // 60
        return minutes if minutes > 0 else None

    @staticmethod
    def _normalize_timestamp(value: Any) -> datetime | None:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            candidate = value.strip()
            if candidate.endswith("Z"):
                candidate = candidate[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                pass
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
        session = await self.get_session()
        if on_request:
            on_request()
        async with session.request(method, url, headers=headers, params=params) as resp:
            if resp.status != 200:
                self.logger.debug(
                    "Garmin API request failed",
                    url=url,
                    status=resp.status,
                    params=params,
                )
                return None
            try:
                return await resp.json()
            except aiohttp.ContentTypeError:
                self.logger.debug("Garmin API returned non-JSON response", url=url)
                return None
