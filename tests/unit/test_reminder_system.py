"""Tests for the task reminder scheduling logic."""

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import cast

import discord
import pytest

from src.bot.channel_config import ChannelConfig
from src.tasks.reminder_system import TaskReminderSystem
from src.tasks.schedule_manager import ScheduleManager
from src.tasks.task_manager import TaskManager


def _build_system() -> TaskReminderSystem:
    dummy_bot = cast(discord.Client, SimpleNamespace())
    dummy_channel_config = cast(ChannelConfig, SimpleNamespace())
    dummy_task_manager = cast(TaskManager, SimpleNamespace())
    dummy_schedule_manager = cast(ScheduleManager, SimpleNamespace())
    return TaskReminderSystem(
        dummy_bot,
        dummy_channel_config,
        dummy_task_manager,
        dummy_schedule_manager,
    )


@pytest.mark.parametrize(
    "reference, expected",
    [
        (datetime(2025, 1, 1, 7, 30), datetime(2025, 1, 1, 8, 0)),
        (datetime(2025, 1, 1, 8, 2), datetime(2025, 1, 1, 8, 2)),
        (datetime(2025, 1, 1, 9, 0), datetime(2025, 1, 2, 8, 0)),
    ],
)
def test_calculate_next_run(reference: datetime, expected: datetime) -> None:
    system = _build_system()
    result = system._calculate_next_run(reference)
    assert result == expected


def test_next_run_after_execution_skips_to_following_day() -> None:
    system = _build_system()

    first_run = system._calculate_next_run(datetime(2025, 1, 1, 7, 59))
    assert first_run == datetime(2025, 1, 1, 8, 0)

    # Simulate post-run scheduling by advancing beyond the grace window
    next_run = system._calculate_next_run(first_run + timedelta(minutes=6))
    assert next_run == datetime(2025, 1, 2, 8, 0)
