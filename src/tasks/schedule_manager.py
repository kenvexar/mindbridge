"""Schedule and event management functionality."""

import json
import uuid
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import aiofiles
from structlog import get_logger

from src.config.settings import get_settings
from src.obsidian import ObsidianFileManager
from src.tasks.models import Schedule, ScheduleType

logger = get_logger(__name__)
settings = get_settings()


class ScheduleManager:
    """Manage schedule and event creation, updates, and tracking."""

    def __init__(self, file_manager: ObsidianFileManager):
        self.file_manager = file_manager
        self.data_file = settings.obsidian_vault_path / "02_Tasks" / "schedules.json"

        # Ensure tasks directory exists
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

    async def create_schedule(
        self,
        title: str,
        start_date: date,
        description: str | None = None,
        schedule_type: ScheduleType = ScheduleType.EVENT,
        start_time: time | None = None,
        end_date: date | None = None,
        end_time: time | None = None,
        location: str | None = None,
        attendees: list[str] | None = None,
        tags: list[str] | None = None,
        reminder_minutes: int | None = None,
    ) -> Schedule:
        """Create a new schedule/event."""
        schedule = Schedule(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            schedule_type=schedule_type,
            notes=None,
            start_date=start_date,
            start_time=start_time,
            end_date=end_date,
            end_time=end_time,
            location=location,
            attendees=attendees or [],
            tags=tags or [],
            reminder_minutes=reminder_minutes,
        )

        schedules = await self._load_schedules()
        schedules[schedule.id] = schedule
        await self._save_schedules(schedules)

        # Create Obsidian note for the schedule
        await self._create_schedule_note(schedule)

        logger.info(
            "Schedule created",
            schedule_id=schedule.id,
            title=title,
            start_date=start_date.isoformat(),
            schedule_type=schedule_type.value,
        )

        return schedule

    async def get_schedule(self, schedule_id: str) -> Schedule | None:
        """Get schedule by ID."""
        schedules = await self._load_schedules()
        schedule_data = schedules.get(schedule_id)

        if schedule_data:
            return (
                Schedule(**schedule_data)
                if isinstance(schedule_data, dict)
                else schedule_data
            )
        return None

    async def list_schedules(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        schedule_type: ScheduleType | None = None,
        upcoming_only: bool = False,
    ) -> list[Schedule]:
        """List schedules with optional filtering."""
        schedules = await self._load_schedules()

        result = []
        for schedule_data in schedules.values():
            schedule = (
                Schedule(**schedule_data)
                if isinstance(schedule_data, dict)
                else schedule_data
            )

            # Apply filters
            if start_date and schedule.start_date < start_date:
                continue

            if end_date and schedule.start_date > end_date:
                continue

            if schedule_type and schedule.schedule_type != schedule_type:
                continue

            if upcoming_only and schedule.start_date < date.today():
                continue

            result.append(schedule)

        # Sort by start date and time
        return sorted(result, key=lambda x: (x.start_date, x.start_time or time.min))

    async def update_schedule(
        self,
        schedule_id: str,
        **updates: Any,
    ) -> Schedule | None:
        """Update schedule details."""
        schedules = await self._load_schedules()

        if schedule_id not in schedules:
            return None

        schedule_data = schedules[schedule_id]
        schedule = (
            Schedule(**schedule_data)
            if isinstance(schedule_data, dict)
            else schedule_data
        )

        # Update fields
        for field, value in updates.items():
            if hasattr(schedule, field):
                setattr(schedule, field, value)

        schedule.updated_at = datetime.now()
        schedules[schedule_id] = schedule
        await self._save_schedules(schedules)

        # Update Obsidian note
        await self._update_schedule_note(schedule)

        logger.info(
            "Schedule updated",
            schedule_id=schedule_id,
            updates=updates,
        )

        return schedule

    async def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        schedules = await self._load_schedules()

        if schedule_id not in schedules:
            return False

        # Remove schedule
        del schedules[schedule_id]
        await self._save_schedules(schedules)

        logger.info("Schedule deleted", schedule_id=schedule_id)
        return True

    async def get_today_schedules(self) -> list[Schedule]:
        """Get all schedules for today."""
        today = date.today()
        return await self.list_schedules(start_date=today, end_date=today)

    async def get_tomorrow_schedules(self) -> list[Schedule]:
        """Get all schedules for tomorrow."""
        from datetime import timedelta

        tomorrow = date.today() + timedelta(days=1)
        return await self.list_schedules(start_date=tomorrow, end_date=tomorrow)

    async def get_upcoming_schedules(self, days: int = 7) -> list[Schedule]:
        """Get schedules for the next specified days."""
        from datetime import timedelta

        today = date.today()
        end_date = today + timedelta(days=days)
        return await self.list_schedules(start_date=today, end_date=end_date)

    async def get_schedules_with_reminders(self) -> list[Schedule]:
        """Get schedules that have reminder settings."""
        schedules = await self.list_schedules(upcoming_only=True)
        return [s for s in schedules if s.reminder_minutes is not None]

    async def _load_schedules(self) -> dict[str, Schedule]:
        """Load schedules from JSON file."""
        if not self.data_file.exists():
            return {}

        try:
            async with aiofiles.open(self.data_file, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

                schedules = {}
                for schedule_id, schedule_data in data.items():
                    if isinstance(schedule_data, dict):
                        schedules[schedule_id] = Schedule(**schedule_data)
                    else:
                        schedules[schedule_id] = schedule_data

                return schedules
        except Exception as e:
            logger.error("Failed to load schedules", error=str(e))
            return {}

    async def _save_schedules(self, schedules: dict[str, Schedule]) -> None:
        """Save schedules to JSON file."""
        try:
            data = {}
            for schedule_id, schedule in schedules.items():
                if isinstance(schedule, Schedule):
                    data[schedule_id] = schedule.dict()
                else:
                    data[schedule_id] = schedule

            async with aiofiles.open(self.data_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(data, indent=2, default=str, ensure_ascii=False)
                )
        except Exception as e:
            logger.error("Failed to save schedules", error=str(e))

    async def _create_schedule_note(self, schedule: Schedule) -> None:
        """Create Obsidian note for schedule."""
        try:
            filename = (
                f"{schedule.start_date}_{schedule.title.replace(' ', '_')}_schedule.md"
            )
            file_path = Path("02_Tasks") / "Schedules" / filename

            # Type emoji mapping
            type_emoji = {
                ScheduleType.APPOINTMENT: "👥",
                ScheduleType.MEETING: "🤝",
                ScheduleType.EVENT: "📅",
                ScheduleType.DEADLINE: "⏰",
                ScheduleType.REMINDER: "🔔",
            }

            content = f"""---
schedule_id: {schedule.id}
title: {schedule.title}
type: {schedule.schedule_type.value}
start_date: {schedule.start_date}
start_time: {schedule.start_time or ""}
end_date: {schedule.end_date or ""}
end_time: {schedule.end_time or ""}
location: {schedule.location or ""}
attendees: {schedule.attendees}
tags: {schedule.tags}
reminder_minutes: {schedule.reminder_minutes or ""}
created: {schedule.created_at.isoformat()}
updated: {schedule.updated_at.isoformat()}
---

# {type_emoji.get(schedule.schedule_type, "📋")} {schedule.title}

## 基本情報
- **種類**: {type_emoji.get(schedule.schedule_type, "📋")} {schedule.schedule_type.value}
- **開始日時**: {schedule.start_date} {schedule.start_time or "時間未設定"}
- **終了日時**: {schedule.end_date or "同日"} {schedule.end_time or "時間未設定"}
- **場所**: {schedule.location or "未設定"}

## 説明
{schedule.description or "説明なし"}

## 参加者
{", ".join(schedule.attendees) if schedule.attendees else "参加者なし"}

## リマインダー
{f"{schedule.reminder_minutes}分前" if schedule.reminder_minutes else "リマインダーなし"}

## タグ
{", ".join(schedule.tags) if schedule.tags else "タグなし"}

## 関連リンク
- [[Daily Schedule]]
- [[Weekly Planning]]
"""

            from src.obsidian.models import NoteFrontmatter, ObsidianNote

            frontmatter = NoteFrontmatter(
                ai_processed=True,
                ai_summary=f"Schedule: {schedule.title}",
                ai_tags=[],
                ai_category="schedule",
                tags=[],
                obsidian_folder="Schedules",
            )
            note = ObsidianNote(
                filename=file_path.name,
                file_path=file_path,
                content=content,
                frontmatter=frontmatter,
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            await self.file_manager.save_note(note)

        except Exception as e:
            logger.error(
                "Failed to create schedule note",
                schedule_id=schedule.id,
                error=str(e),
            )

    async def _update_schedule_note(self, schedule: Schedule) -> None:
        """Update schedule note with current information."""
        try:
            filename = (
                f"{schedule.start_date}_{schedule.title.replace(' ', '_')}_schedule.md"
            )
            Path("02_Tasks") / "Schedules" / filename

            # Re-create the note with updated information
            await self._create_schedule_note(schedule)

        except Exception as e:
            logger.error(
                "Failed to update schedule note",
                schedule_id=schedule.id,
                error=str(e),
            )
