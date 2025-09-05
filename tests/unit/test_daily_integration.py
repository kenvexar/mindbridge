"""Test daily note integration functionality"""

import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

# Set up test environment variables before importing modules
os.environ.update(
    {
        "DISCORD_BOT_TOKEN": "test_token",
        "DISCORD_GUILD_ID": "123456789",
        "GEMINI_API_KEY": "test_api_key",
        "OBSIDIAN_VAULT_PATH": "/tmp/test_vault",
        "CHANNEL_INBOX": "111111111",
        "CHANNEL_VOICE": "222222222",
        "CHANNEL_FILES": "333333333",
        "CHANNEL_MONEY": "444444444",
        "CHANNEL_FINANCE_REPORTS": "555555555",
        "CHANNEL_TASKS": "666666666",
        "CHANNEL_PRODUCTIVITY_REVIEWS": "777777777",
        "CHANNEL_NOTIFICATIONS": "888888888",
        "CHANNEL_COMMANDS": "999999999",
    }
)

from src.obsidian.daily_integration import DailyNoteIntegration
from src.obsidian.refactored_file_manager import ObsidianFileManager


@pytest.mark.asyncio
class TestDailyNoteIntegration:
    """Test daily note integration functionality"""

    def setup_method(self) -> None:
        """Setup test fixtures"""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Create template directory and daily note template
        template_dir = self.temp_dir / "99_Meta" / "Templates"
        template_dir.mkdir(parents=True, exist_ok=True)

        # Create a basic daily note template
        daily_template = template_dir / "daily_note.md"
        daily_template.write_text(
            "---\n"
            "type: daily\n"
            "date: {{date_ymd}}\n"
            "---\n\n"
            "# {{date_full}}\n\n"
            "## 📋 Activity Log\n\n"
            "## ✅ Daily Tasks\n\n"
        )

        self.file_manager = ObsidianFileManager(self.temp_dir)
        self.daily_integration = DailyNoteIntegration(self.file_manager)

    async def test_add_activity_log_entry(self) -> None:
        """Test adding activity log entry to daily note"""
        # Setup message data
        message_data = {
            "metadata": {
                "content": {"raw_content": "Started working on project documentation"},
                "timing": {"created_at": {"iso": "2024-01-15T14:30:00"}},
            }
        }

        date = datetime(2024, 1, 15)

        # Add activity log entry
        success = await self.daily_integration.add_activity_log_entry(
            message_data, date
        )

        assert success is True

        # Verify the daily note was created and contains the activity log entry
        filename = f"{date.strftime('%Y-%m-%d')}.md"
        daily_note_path = self.temp_dir / "01_DailyNotes" / filename

        assert daily_note_path.exists()

        # Load and verify content
        daily_note = await self.file_manager.load_note(daily_note_path)
        assert daily_note is not None
        assert "## 📋 Activity Log" in daily_note.content
        assert "14:30" in daily_note.content
        assert "Started working on project documentation" in daily_note.content

    async def test_add_daily_task_entry(self) -> None:
        """Test adding daily task entry to daily note"""
        # Setup message data with task content
        message_data = {
            "metadata": {
                "content": {
                    "raw_content": "- Review code changes\n- Update documentation\n- Test new features"
                },
                "timing": {"created_at": {"iso": "2024-01-15T09:00:00"}},
            }
        }

        date = datetime(2024, 1, 15)

        # Add daily task entry
        success = await self.daily_integration.add_daily_task_entry(message_data, date)

        assert success is True

        # Verify the daily note was created and contains the task entries
        filename = f"{date.strftime('%Y-%m-%d')}.md"
        daily_note_path = self.temp_dir / "01_DailyNotes" / filename

        assert daily_note_path.exists()

        # Load and verify content
        daily_note = await self.file_manager.load_note(daily_note_path)
        assert daily_note is not None
        assert "## ✅ Daily Tasks" in daily_note.content
        assert "- [ ] Review code changes" in daily_note.content
        assert "- [ ] Update documentation" in daily_note.content
        assert "- [ ] Test new features" in daily_note.content

    async def test_task_parsing(self) -> None:
        """Test task parsing functionality"""
        # Test various task formats
        test_cases = [
            ("- Task item", ["- [ ] Task item"]),
            ("TODO: Important task", ["- [ ] Important task"]),
            ("タスク: 日本語のタスク", ["- [ ] 日本語のタスク"]),
            (
                "1. First task\n2. Second task",
                ["- [ ] First task", "- [ ] Second task"],
            ),
            ("- [x] Completed task", ["- [x] Completed task"]),
            (
                "Simple task without formatting",
                ["- [ ] Simple task without formatting"],
            ),
        ]

        for input_content, expected_tasks in test_cases:
            parsed_tasks = self.daily_integration._parse_tasks(input_content)
            assert parsed_tasks == expected_tasks, f"Failed for input: {input_content}"

    async def test_section_management(self) -> None:
        """Test section management in daily notes"""
        # Create initial daily note
        date = datetime(2024, 1, 15)
        initial_note = await self.daily_integration._get_or_create_daily_note(date)
        assert initial_note is not None

        # Verify base sections are present
        assert "## 📋 Activity Log" in initial_note.content
        assert "## ✅ Daily Tasks" in initial_note.content

        # Test adding to existing sections
        test_content = "Test content for activity log"
        updated_content = self.daily_integration._add_to_section(
            initial_note.content, "## 📋 Activity Log", f"- **12:00** {test_content}"
        )

        assert f"- **12:00** {test_content}" in updated_content

    async def test_multiple_entries_same_day(self) -> None:
        """Test adding multiple entries to the same daily note"""
        date = datetime(2024, 1, 15)

        # Add first activity log entry
        message_data_1 = {
            "metadata": {
                "content": {"raw_content": "First activity"},
                "timing": {"created_at": {"iso": "2024-01-15T09:00:00"}},
            }
        }

        success_1 = await self.daily_integration.add_activity_log_entry(
            message_data_1, date
        )
        assert success_1 is True

        # Add second activity log entry
        message_data_2 = {
            "metadata": {
                "content": {"raw_content": "Second activity"},
                "timing": {"created_at": {"iso": "2024-01-15T15:30:00"}},
            }
        }

        success_2 = await self.daily_integration.add_activity_log_entry(
            message_data_2, date
        )
        assert success_2 is True

        # Add daily task entry
        task_data = {
            "metadata": {
                "content": {"raw_content": "Important task to complete"},
                "timing": {"created_at": {"iso": "2024-01-15T10:00:00"}},
            }
        }

        success_3 = await self.daily_integration.add_daily_task_entry(task_data, date)
        assert success_3 is True

        # Verify all entries are in the same note
        filename = f"{date.strftime('%Y-%m-%d')}.md"
        daily_note_path = self.temp_dir / "01_DailyNotes" / filename

        daily_note = await self.file_manager.load_note(daily_note_path)
        assert daily_note is not None

        # Check all entries are present
        assert "09:00" in daily_note.content and "First activity" in daily_note.content
        assert "15:30" in daily_note.content and "Second activity" in daily_note.content
        assert "- [ ] Important task to complete" in daily_note.content

    async def test_empty_message_handling(self) -> None:
        """Test handling of empty or whitespace-only messages"""
        message_data = {
            "metadata": {
                "content": {"raw_content": "   \n\t  "},
                "timing": {"created_at": {"iso": "2024-01-15T12:00:00"}},
            }
        }

        date = datetime(2024, 1, 15)

        # Both functions should return False for empty content
        activity_success = await self.daily_integration.add_activity_log_entry(
            message_data, date
        )
        task_success = await self.daily_integration.add_daily_task_entry(
            message_data, date
        )

        assert activity_success is False
        assert task_success is False


def test_task_parsing_edge_cases() -> None:
    """Test edge cases in task parsing"""
    # Create a mock file manager with proper Path handling
    mock_file_manager = Mock()
    mock_file_manager.vault_path = Path("/tmp/test_vault")
    daily_integration = DailyNoteIntegration(mock_file_manager)

    # Test empty content
    assert daily_integration._parse_tasks("") == []
    assert daily_integration._parse_tasks("   \n\t  ") == []

    # Test already formatted tasks
    already_formatted = "- [ ] Already formatted task"
    assert daily_integration._parse_tasks(already_formatted) == [
        "- [ ] Already formatted task"
    ]

    # Test completed tasks
    completed_task = "- [x] Completed task"
    assert daily_integration._parse_tasks(completed_task) == ["- [x] Completed task"]

    # Test mixed content
    mixed_content = "Some text\n- Task item\nMore text\nTODO: Another task"
    parsed = daily_integration._parse_tasks(mixed_content)
    assert "- [ ] Task item" in parsed
    assert "- [ ] Another task" in parsed


def test_section_management_edge_cases() -> None:
    """Test edge cases in section management"""
    # Create a mock file manager with proper Path handling
    mock_file_manager = Mock()
    mock_file_manager.vault_path = Path("/tmp/test_vault")
    daily_integration = DailyNoteIntegration(mock_file_manager)

    # Test adding to non-existent section
    content = "# Daily Note\n\nSome content"
    updated = daily_integration._add_to_section(content, "## New Section", "New entry")
    assert "## New Section" in updated
    assert "New entry" in updated

    # Test adding to empty section
    content_with_empty_section = (
        "# Daily Note\n\n## Empty Section\n\n## Other Section\nOther content"
    )
    updated = daily_integration._add_to_section(
        content_with_empty_section, "## Empty Section", "First entry"
    )
    assert "First entry" in updated

    # Verify the entry is in the correct section
    lines = updated.split("\n")
    empty_section_idx = next(
        i for i, line in enumerate(lines) if line.strip() == "## Empty Section"
    )
    other_section_idx = next(
        i for i, line in enumerate(lines) if line.strip() == "## Other Section"
    )
    first_entry_idx = next(i for i, line in enumerate(lines) if "First entry" in line)

    assert empty_section_idx < first_entry_idx < other_section_idx
