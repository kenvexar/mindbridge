from datetime import datetime

import pytest

from src.config.settings import Settings
from src.lifelog.integrations.bridge import create_default_bridge
from src.lifelog.integrations.models import IntegrationData
from src.lifelog.manager import LifelogManager
from src.lifelog.models import LifelogCategory


@pytest.mark.asyncio
async def test_bridge_converts_garmin_activity() -> None:
    bridge = create_default_bridge()
    integration_data = IntegrationData(
        integration_type="garmin",
        source_id="activity-001",
        timestamp=datetime(2024, 5, 1, 6, 30),
        data={
            "activity_type": "running",
            "activity_name": "Morning Run",
            "duration": 3600,
            "distance": 5000,
            "calories": 480,
            "avg_heart_rate": 142,
        },
        metadata={"data_type": "activity"},
    )

    entry = await bridge.convert(integration_data)

    assert entry is not None
    assert entry.category == LifelogCategory.HEALTH
    assert entry.source == "garmin_integration"
    assert "Morning Run" in entry.title
    assert "Garmin Connect" in entry.content
    assert "142bpm" in entry.content


@pytest.mark.asyncio
async def test_bridge_falls_back_to_default_pipeline() -> None:
    bridge = create_default_bridge()
    integration_data = IntegrationData(
        integration_type="notion",
        source_id="note-123",
        timestamp=datetime(2024, 5, 2, 9, 0),
        data={"title": "Weekly Review", "content": "Summary of the week"},
        metadata={"data_type": "note"},
    )

    entry = await bridge.convert(integration_data)

    assert entry is not None
    assert entry.category == LifelogCategory.ROUTINE
    assert entry.title == "Weekly Review"
    assert entry.content == "Summary of the week"
    assert entry.source == "notion_integration"
    assert "raw_data" in entry.metadata


@pytest.mark.asyncio
async def test_lifelog_manager_integrates_pipeline_result(tmp_path) -> None:
    vault_dir = tmp_path / "vault"
    vault_dir.mkdir()

    settings = Settings(
        discord_bot_token="token",
        gemini_api_key="key",
        obsidian_vault_path=vault_dir,
    )

    manager = LifelogManager(settings)

    garmin_data = IntegrationData(
        integration_type="garmin",
        source_id="activity-456",
        timestamp=datetime(2024, 5, 3, 7, 15),
        data={
            "activity_type": "cycling",
            "activity_name": "Commute",
            "duration": 1800,
            "distance": 8000,
        },
        metadata={"data_type": "activity"},
    )

    processed_count = await manager.integrate_external_data([garmin_data])

    assert processed_count == 1
    assert len(manager._entries) == 1

    entry = next(iter(manager._entries.values()))
    assert entry.metadata["external_id"] == "activity-456"
    assert entry.source == "garmin_integration"
    assert "Commute" in entry.title
