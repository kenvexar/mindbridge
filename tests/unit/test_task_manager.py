"""Unit tests for task manager persistence and note generation."""

import json

import pytest

from src.obsidian import ObsidianFileManager
from src.obsidian.models import VaultFolder
from src.tasks.task_manager import TaskManager


@pytest.fixture
def patched_task_manager(tmp_path, monkeypatch) -> TaskManager:
    """Provide a TaskManager instance rooted in a temporary vault."""

    from src.tasks import task_manager as task_manager_module

    new_settings = task_manager_module.settings.model_copy(
        update={"obsidian_vault_path": tmp_path}
    )
    monkeypatch.setattr(task_manager_module, "settings", new_settings)

    file_manager = ObsidianFileManager(tmp_path, enable_local_data=False)
    return TaskManager(file_manager)


@pytest.mark.asyncio
async def test_create_task_generates_distinct_notes(
    patched_task_manager: TaskManager, tmp_path
) -> None:
    manager = patched_task_manager

    task_a = await manager.create_task("Daily Review")
    task_b = await manager.create_task("Daily Review")

    tasks_dir = tmp_path / VaultFolder.TASKS.value
    note_a = tasks_dir / f"{task_a.id}.md"
    note_b = tasks_dir / f"{task_b.id}.md"

    assert note_a.exists()
    assert note_b.exists()
    assert note_a != note_b

    tasks_file = tasks_dir / "tasks.json"
    data = json.loads(tasks_file.read_text(encoding="utf-8"))
    assert task_a.id in data
    assert task_b.id in data

    # Confirm no temporary files remain from atomic writes
    assert not list(tasks_dir.glob("tasks_*.json"))


@pytest.mark.asyncio
async def test_update_task_keeps_note_path_and_updates_content(
    patched_task_manager: TaskManager, tmp_path
) -> None:
    manager = patched_task_manager

    task = await manager.create_task("Initial Task")
    note_path = tmp_path / VaultFolder.TASKS.value / f"{task.id}.md"
    assert note_path.exists()

    updated = await manager.update_task(task.id, title="Renamed Task")

    assert updated is not None
    assert updated.title == "Renamed Task"
    assert note_path.exists()

    content = note_path.read_text(encoding="utf-8")
    assert "Renamed Task" in content

    tasks_file = tmp_path / VaultFolder.TASKS.value / "tasks.json"
    data = json.loads(tasks_file.read_text(encoding="utf-8"))
    assert data[task.id]["title"] == "Renamed Task"
