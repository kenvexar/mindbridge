"""Task management data models."""

from datetime import date, datetime, time
from enum import Enum

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class TaskStatus(str, Enum):
    """Task status enum."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    DONE = "done"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority enum."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ScheduleType(str, Enum):
    """Schedule type enum."""

    APPOINTMENT = "appointment"
    MEETING = "meeting"
    EVENT = "event"
    DEADLINE = "deadline"
    REMINDER = "reminder"


class Task(BaseModel):
    """Task data model."""

    id: str = Field(..., description="Unique task ID")
    title: str = Field(..., description="Task title")
    description: str | None = Field(None, description="Task description")
    status: TaskStatus = Field(default=TaskStatus.TODO)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    due_date: date | None = Field(None, description="Task due date")
    estimated_hours: float | None = Field(
        None, description="Estimated hours to complete", gt=0
    )
    actual_hours: float | None = Field(None, description="Actual hours spent", ge=0)
    tags: list[str] = Field(default_factory=list, description="Task tags")
    project: str | None = Field(None, description="Project name")
    parent_task_id: str | None = Field(None, description="Parent task ID for subtasks")
    progress: int = Field(default=0, description="Progress percentage", ge=0, le=100)
    notes: str | None = Field(None, description="Additional notes")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    started_at: datetime | None = Field(None, description="When task was started")
    completed_at: datetime | None = Field(None, description="When task was completed")

    @field_validator("progress")
    @classmethod
    def validate_progress(cls, v: int) -> int:
        """Validate progress is between 0 and 100."""
        if not 0 <= v <= 100:
            raise ValueError("Progress must be between 0 and 100")
        return v

    def is_overdue(self) -> bool:
        """Check if task is overdue."""
        if not self.due_date:
            return False
        return self.due_date < date.today() and self.status not in [
            TaskStatus.DONE,
            TaskStatus.CANCELLED,
        ]

    def is_due_soon(self, days: int = 3) -> bool:
        """Check if task is due within specified days."""
        if not self.due_date:
            return False
        from datetime import timedelta

        return self.due_date <= date.today() + timedelta(days=days)

    def get_duration(self) -> float | None:
        """Get task duration in hours if completed."""
        if self.started_at and self.completed_at:
            duration = self.completed_at - self.started_at
            return duration.total_seconds() / 3600
        return None

    def mark_started(self) -> None:
        """Mark task as started."""
        if self.status == TaskStatus.TODO:
            self.status = TaskStatus.IN_PROGRESS
            self.started_at = datetime.now()
            self.updated_at = datetime.now()

    def mark_completed(self) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.DONE
        self.progress = 100
        self.completed_at = datetime.now()
        self.updated_at = datetime.now()

    def update_progress(self, progress: int) -> None:
        """Update task progress."""
        self.progress = max(0, min(100, progress))
        self.updated_at = datetime.now()

        if self.progress == 100 and self.status != TaskStatus.DONE:
            self.mark_completed()
        elif self.progress > 0 and self.status == TaskStatus.TODO:
            self.mark_started()


class Schedule(BaseModel):
    """Schedule/event data model."""

    id: str = Field(..., description="Unique schedule ID")
    title: str = Field(..., description="Event title")
    description: str | None = Field(None, description="Event description")
    schedule_type: ScheduleType = Field(default=ScheduleType.EVENT)
    start_date: date = Field(..., description="Event start date")
    start_time: time | None = Field(None, description="Event start time")
    end_date: date | None = Field(None, description="Event end date")
    end_time: time | None = Field(None, description="Event end time")
    location: str | None = Field(None, description="Event location")
    attendees: list[str] = Field(default_factory=list, description="Event attendees")
    tags: list[str] = Field(default_factory=list, description="Event tags")
    reminder_minutes: int | None = Field(
        None, description="Reminder minutes before event", gt=0
    )
    notes: str | None = Field(None, description="Additional notes")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: date | None, info: ValidationInfo) -> date | None:
        """Validate end date is not before start date."""
        if v and info.data.get("start_date") and v < info.data["start_date"]:
            raise ValueError("End date cannot be before start date")
        return v

    def is_today(self) -> bool:
        """Check if event is today."""
        return self.start_date == date.today()

    def is_tomorrow(self) -> bool:
        """Check if event is tomorrow."""
        from datetime import timedelta

        return self.start_date == date.today() + timedelta(days=1)

    def is_upcoming(self, days: int = 7) -> bool:
        """Check if event is upcoming within specified days."""
        from datetime import timedelta

        return date.today() <= self.start_date <= date.today() + timedelta(days=days)

    def get_duration_hours(self) -> float | None:
        """Get event duration in hours."""
        if not self.start_time or not self.end_time:
            return None

        start_datetime = datetime.combine(self.start_date, self.start_time)
        end_date = self.end_date or self.start_date
        end_datetime = datetime.combine(end_date, self.end_time)

        if end_datetime <= start_datetime:
            return None

        duration = end_datetime - start_datetime
        return duration.total_seconds() / 3600


class TaskSummary(BaseModel):
    """Task summary data model."""

    total_tasks: int = Field(default=0)
    completed_tasks: int = Field(default=0)
    in_progress_tasks: int = Field(default=0)
    overdue_tasks: int = Field(default=0)
    due_soon_tasks: int = Field(default=0)
    completion_rate: float = Field(default=0.0)
    average_completion_time: float | None = Field(
        None, description="Average completion time in hours"
    )
    priority_breakdown: dict[str, int] = Field(default_factory=dict)
    status_breakdown: dict[str, int] = Field(default_factory=dict)
    project_breakdown: dict[str, int] = Field(default_factory=dict)
    upcoming_schedules: list[Schedule] = Field(default_factory=list)
    period_start: date = Field(...)
    period_end: date = Field(...)

    @property
    def remaining_tasks(self) -> int:
        """Calculate remaining tasks."""
        return self.total_tasks - self.completed_tasks

    @property
    def productivity_score(self) -> float:
        """Calculate productivity score (0-100)."""
        if self.total_tasks == 0:
            return 100.0

        # Base score from completion rate
        base_score = self.completion_rate

        # Penalty for overdue tasks
        overdue_penalty = (self.overdue_tasks / self.total_tasks) * 20

        # Bonus for in-progress tasks
        progress_bonus = min((self.in_progress_tasks / self.total_tasks) * 10, 10)

        score = base_score - overdue_penalty + progress_bonus
        return max(0.0, min(100.0, score))
