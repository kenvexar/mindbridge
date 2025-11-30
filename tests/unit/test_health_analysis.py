"""Tests for health analysis components"""

from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.garmin.models import HealthData

if TYPE_CHECKING:
    pass


@pytest.mark.asyncio
async def test_analyzer_public_change_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.health_analysis import analyzer as analyzer_module

    monkeypatch.setattr(
        analyzer_module, "AIProcessor", lambda *args, **kwargs: object()
    )
    instance = analyzer_module.HealthDataAnalyzer()

    called_args: dict[str, Any] = {}

    async def stub_detect(data: list[Any]) -> list[str]:
        called_args["data"] = data
        return ["change"]

    monkeypatch.setattr(instance, "_detect_significant_changes", stub_detect)

    sample_data = cast(list[HealthData], [MagicMock(spec=HealthData) for _ in range(3)])
    result = await instance.detect_significant_changes(sample_data)
    assert result == ["change"]
    assert called_args["data"] == sample_data


@pytest.mark.asyncio
async def test_scheduler_uses_public_change_detection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.health_analysis.scheduler import HealthAnalysisScheduler

    analyzer = MagicMock()
    analyzer.detect_significant_changes = AsyncMock(return_value=[])

    scheduler = HealthAnalysisScheduler(
        garmin_client=MagicMock(),
        analyzer=analyzer,
        integrator=MagicMock(),
        daily_integration=MagicMock(),
    )

    monkeypatch.setattr(
        scheduler,
        "_collect_week_health_data",
        AsyncMock(
            return_value=cast(
                list[HealthData], [MagicMock(spec=HealthData) for _ in range(5)]
            )
        ),
    )
    monkeypatch.setattr(scheduler, "_send_urgent_health_alert", AsyncMock())

    await scheduler._check_significant_changes()

    analyzer.detect_significant_changes.assert_called_once()
