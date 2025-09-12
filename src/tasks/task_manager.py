"""Task management functionality."""

import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

import aiofiles
from structlog import get_logger

from src.config.settings import get_settings
from src.obsidian import ObsidianFileManager
from src.obsidian.models import VaultFolder
from src.tasks.models import Task, TaskPriority, TaskStatus

logger = get_logger(__name__)
settings = get_settings()


class TaskManager:
    """Manage task creation, updates, and tracking."""

    def __init__(self, file_manager: ObsidianFileManager):
        self.file_manager = file_manager
        self.data_file = (
            settings.obsidian_vault_path / VaultFolder.TASKS.value / "tasks.json"
        )

        # Ensure tasks directory exists
        self.data_file.parent.mkdir(parents=True, exist_ok=True)

    async def create_task(
        self,
        title: str,
        description: str | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        due_date: date | None = None,
        estimated_hours: float | None = None,
        tags: list[str] | None = None,
        project: str | None = None,
        parent_task_id: str | None = None,
    ) -> Task:
        """Create a new task."""
        task = Task(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            estimated_hours=estimated_hours,
            actual_hours=None,
            tags=tags or [],
            notes=None,
            started_at=None,
            completed_at=None,
            project=project,
            parent_task_id=parent_task_id,
        )

        tasks = await self._load_tasks()
        tasks[task.id] = task
        await self._save_tasks(tasks)

        # Create Obsidian note for the task
        await self._create_task_note(task)

        logger.info(
            "Task created",
            task_id=task.id,
            title=title,
            priority=priority.value,
        )

        return task

    async def get_task(self, task_id: str) -> Task | None:
        """Get task by ID."""
        tasks = await self._load_tasks()
        task_data = tasks.get(task_id)

        if task_data:
            return Task(**task_data) if isinstance(task_data, dict) else task_data
        return None

    async def list_tasks(
        self,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        project: str | None = None,
        active_only: bool = False,
        include_subtasks: bool = True,
    ) -> list[Task]:
        """List tasks with optional filtering."""
        tasks = await self._load_tasks()

        result = []
        for task_data in tasks.values():
            task = Task(**task_data) if isinstance(task_data, dict) else task_data

            # Apply filters
            if status and task.status != status:
                continue

            if priority and task.priority != priority:
                continue

            if project and task.project != project:
                continue

            if active_only and task.status in [TaskStatus.DONE, TaskStatus.CANCELLED]:
                continue

            if not include_subtasks and task.parent_task_id:
                continue

            result.append(task)

        # Sort by priority, then due date, then created date
        def sort_key(task: Task) -> tuple[int, date | None, datetime]:
            priority_order = {
                TaskPriority.URGENT: 0,
                TaskPriority.HIGH: 1,
                TaskPriority.MEDIUM: 2,
                TaskPriority.LOW: 3,
            }

            return (
                priority_order.get(task.priority, 4),
                task.due_date or date.max,
                task.created_at,
            )

        return sorted(result, key=sort_key)

    async def update_task(
        self,
        task_id: str,
        **updates: Any,
    ) -> Task | None:
        """Update task details."""
        tasks = await self._load_tasks()

        if task_id not in tasks:
            return None

        task_data = tasks[task_id]
        task = Task(**task_data) if isinstance(task_data, dict) else task_data

        # Update fields
        for field, value in updates.items():
            if hasattr(task, field):
                setattr(task, field, value)

        task.updated_at = datetime.now()
        tasks[task_id] = task
        await self._save_tasks(tasks)

        # Update Obsidian note
        await self._update_task_note(task)

        logger.info(
            "Task updated",
            task_id=task_id,
            updates=updates,
        )

        return task

    async def update_progress(
        self,
        task_id: str,
        progress: int,
        notes: str | None = None,
    ) -> Task | None:
        """Update task progress."""
        task = await self.get_task(task_id)
        if not task:
            return None

        old_status = task.status
        task.update_progress(progress)

        # Add notes if provided
        if notes:
            if task.notes:
                task.notes += (
                    f"\n\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {notes}"
                )
            else:
                task.notes = f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {notes}"

        # Save updated task
        tasks = await self._load_tasks()
        tasks[task_id] = task
        await self._save_tasks(tasks)

        # Update Obsidian note
        await self._update_task_note(task)

        # Log status change
        if old_status != task.status:
            logger.info(
                "Task status changed",
                task_id=task_id,
                old_status=old_status.value,
                new_status=task.status.value,
                progress=progress,
            )

        return task

    async def complete_task(
        self,
        task_id: str,
        actual_hours: float | None = None,
        completion_notes: str | None = None,
    ) -> Task | None:
        """Mark task as completed."""
        task = await self.get_task(task_id)
        if not task:
            return None

        task.mark_completed()

        if actual_hours is not None:
            task.actual_hours = actual_hours

        if completion_notes:
            if task.notes:
                task.notes += f"\n\n[完了] {completion_notes}"
            else:
                task.notes = f"[完了] {completion_notes}"

        # Save updated task
        tasks = await self._load_tasks()
        tasks[task_id] = task
        await self._save_tasks(tasks)

        # Update Obsidian note
        await self._update_task_note(task)

        logger.info(
            "Task completed",
            task_id=task_id,
            title=task.title,
            actual_hours=actual_hours,
        )

        return task

    async def get_overdue_tasks(self) -> list[Task]:
        """Get all overdue tasks."""
        tasks = await self.list_tasks(active_only=True)
        return [task for task in tasks if task.is_overdue()]

    async def get_due_soon_tasks(self, days: int = 3) -> list[Task]:
        """Get tasks due within specified days."""
        tasks = await self.list_tasks(active_only=True)
        return [task for task in tasks if task.is_due_soon(days)]

    async def get_subtasks(self, parent_task_id: str) -> list[Task]:
        """Get all subtasks for a parent task."""
        tasks = await self._load_tasks()

        result = []
        for task_data in tasks.values():
            task = Task(**task_data) if isinstance(task_data, dict) else task_data

            if task.parent_task_id == parent_task_id:
                result.append(task)

        return sorted(result, key=lambda x: x.created_at)

    async def get_tasks_by_project(self, project: str) -> list[Task]:
        """Get all tasks for a specific project."""
        return await self.list_tasks(project=project)

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        tasks = await self._load_tasks()

        if task_id not in tasks:
            return False

        # Check for subtasks
        subtasks = await self.get_subtasks(task_id)
        if subtasks:
            logger.warning(
                "Cannot delete task with subtasks",
                task_id=task_id,
                subtask_count=len(subtasks),
            )
            return False

        # Remove task
        tasks[task_id]
        del tasks[task_id]
        await self._save_tasks(tasks)

        logger.info("Task deleted", task_id=task_id)
        return True

    async def _load_tasks(self) -> dict[str, Task]:
        """Load tasks from JSON file."""
        if not self.data_file.exists():
            return {}

        try:
            async with aiofiles.open(self.data_file, encoding="utf-8") as f:
                content = await f.read()
                data = json.loads(content)

                tasks = {}
                for task_id, task_data in data.items():
                    if isinstance(task_data, dict):
                        tasks[task_id] = Task(**task_data)
                    else:
                        tasks[task_id] = task_data

                return tasks
        except Exception as e:
            logger.error("Failed to load tasks", error=str(e))
            return {}

    async def _save_tasks(self, tasks: dict[str, Task]) -> None:
        """Save tasks to JSON file."""
        try:
            data = {}
            for task_id, task in tasks.items():
                if isinstance(task, Task):
                    data[task_id] = task.dict()
                else:
                    data[task_id] = task

            async with aiofiles.open(self.data_file, "w", encoding="utf-8") as f:
                await f.write(
                    json.dumps(data, indent=2, default=str, ensure_ascii=False)
                )
        except Exception as e:
            logger.error("Failed to save tasks", error=str(e))

    async def _create_task_note(self, task: Task) -> None:
        """Create Obsidian note for task."""
        try:
            filename = f"{task.title.replace(' ', '_')}_task.md"
            from src.obsidian.models import VaultFolder

            file_path = Path(VaultFolder.TASKS.value) / filename

            # Status emoji mapping
            status_emoji = {
                TaskStatus.TODO: "⏳",
                TaskStatus.IN_PROGRESS: "🔄",
                TaskStatus.WAITING: "⏸️",
                TaskStatus.DONE: "✅",
                TaskStatus.CANCELLED: "❌",
            }

            # Priority emoji mapping
            priority_emoji = {
                TaskPriority.LOW: "🔵",
                TaskPriority.MEDIUM: "🟡",
                TaskPriority.HIGH: "🟠",
                TaskPriority.URGENT: "🔴",
            }

            # Generate task content for file
            task_content = f"""---
task_id: {task.id}
title: {task.title}
status: {task.status.value}
priority: {task.priority.value}
progress: {task.progress}
due_date: {task.due_date or ""}
estimated_hours: {task.estimated_hours or ""}
project: {task.project or ""}
tags: {task.tags}
created: {task.created_at.isoformat()}
updated: {task.updated_at.isoformat()}
---

# {status_emoji.get(task.status, "📋")} {task.title}

## 基本情報
- **ステータス**: {status_emoji.get(task.status, "📋")} {task.status.value}
- **優先度**: {priority_emoji.get(task.priority, "⚪")} {task.priority.value}
- **進捗**: {task.progress}%
- **期限**: {task.due_date or "未設定"}
- **予想時間**: {task.estimated_hours or "未設定"}時間
- **実績時間**: {task.actual_hours or "未設定"}時間

## プロジェクト
{task.project or "未設定"}

## 説明
{task.description or "説明なし"}

## メモ
{task.notes or "メモなし"}

## タグ
{", ".join(task.tags) if task.tags else "タグなし"}

## 関連リンク
- [[Daily Tasks]]
- [[Project Overview]]
"""

            task_content = f"""# Task: {task.title}

## Description
{task.description or "No description"}

## Details
- **Priority**: {task.priority}
- **Status**: {task.status}
- **Due Date**: {task.due_date or "Not set"}
- **Estimated Hours**: {task.estimated_hours or "Not set"}
- **Tags**: {", ".join(task.tags) if task.tags else "None"}
- **Project**: {task.project or "None"}

## Progress
Progress: {task.progress}%

## Links
- [[Daily Tasks]]
- [[Project Overview]]
"""

            from src.obsidian.models import NoteFrontmatter, ObsidianNote

            frontmatter = NoteFrontmatter(
                ai_processed=True,
                ai_summary=f"Task: {task.title}",
                ai_tags=task.tags,
                ai_category="task",
                tags=task.tags,
                obsidian_folder=VaultFolder.TASKS.value,
            )
            note = ObsidianNote(
                filename=file_path.name,
                file_path=file_path,
                content=task_content,
                frontmatter=frontmatter,
                created_at=datetime.now(),
                modified_at=datetime.now(),
            )
            await self.file_manager.save_note(note)

        except Exception as e:
            logger.error(
                "Failed to create task note",
                task_id=task.id,
                error=str(e),
            )

    async def _update_task_note(self, task: Task) -> None:
        """Update task note with current information."""
        try:
            # Re-create the note with updated information
            await self._create_task_note(task)

        except Exception as e:
            logger.error(
                "Failed to update task note",
                task_id=task.id,
                error=str(e),
            )
