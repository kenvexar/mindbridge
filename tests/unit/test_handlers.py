"""
Tests for the new handler modules
"""

from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from src.bot.handlers.audio_handler import AudioHandler
from src.bot.handlers.lifelog_handler import LifelogHandler
from src.bot.handlers.message_handler import MessageHandler
from src.bot.handlers.note_handler import NoteHandler


class TestAudioHandler:
    """Test AudioHandler functionality"""

    @pytest.fixture
    def speech_processor(self):
        processor = MagicMock()
        processor.is_audio_file = MagicMock(return_value=True)
        return processor

    @pytest.fixture
    def audio_handler(self, speech_processor):
        return AudioHandler(speech_processor=speech_processor)

    @pytest.mark.asyncio
    async def test_handle_audio_attachments_no_attachments(self, audio_handler):
        """Test handling when no attachments are present"""
        message_data = {"metadata": {"attachments": []}}
        channel_info = MagicMock(name="test-channel")

        await audio_handler.handle_audio_attachments(message_data, channel_info)
        # Should complete without error

    @pytest.mark.asyncio
    async def test_handle_audio_attachments_with_audio(self, audio_handler):
        """Test handling audio attachments"""
        attachment = {
            "filename": "test.wav",
            "file_category": "audio",
            "content_type": "audio/wav",
            "file_extension": "wav",
        }
        message_data = {"metadata": {"attachments": [attachment]}}
        channel_info = MagicMock(name="test-channel")

        with patch.object(
            audio_handler, "process_single_audio_attachment", new_callable=AsyncMock
        ) as mock_process:
            await audio_handler.handle_audio_attachments(message_data, channel_info)
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_feedback_message_success(self, audio_handler):
        """Test updating feedback message successfully"""
        feedback_message = AsyncMock()
        feedback_message.edit = AsyncMock()

        await audio_handler.update_feedback_message(feedback_message, "Test content")
        feedback_message.edit.assert_called_once_with(content="Test content")

    @pytest.mark.asyncio
    async def test_update_feedback_message_none(self, audio_handler):
        """Test updating feedback message when message is None"""
        await audio_handler.update_feedback_message(None, "Test content")
        # Should complete without error


class TestLifelogHandler:
    """Test LifelogHandler functionality"""

    @pytest.fixture
    def lifelog_handler(self):
        return LifelogHandler(
            lifelog_manager=MagicMock(),
            lifelog_analyzer=MagicMock(),
            lifelog_message_handler=MagicMock(),
            lifelog_commands=MagicMock(),
        )

    def test_is_lifelog_candidate_positive(self, lifelog_handler):
        """Test lifelog candidate detection with positive cases"""
        test_cases = [
            "今日は美味しいラーメンを食べた",
            "コーヒーを飲んだ",
            "早く寝た",
            "朝早く起きた",
            "運動した",
            "勉強した",
            "仕事した",
            "買い物に行った",
            "映画を見た",
            "読書した",
            "散歩した",
            "会議があった",
            "友人と電話した",
        ]

        for message in test_cases:
            assert lifelog_handler.is_lifelog_candidate(message), (
                f"Failed for: {message}"
            )

    def test_is_lifelog_candidate_negative(self, lifelog_handler):
        """Test lifelog candidate detection with negative cases"""
        test_cases = [
            "こんにちは",
            "今日は雨ですね",
            "プログラミングについて話しましょう",
            "音楽が好きです",
            "明日の予定は何ですか",
        ]

        for message in test_cases:
            assert not lifelog_handler.is_lifelog_candidate(message), (
                f"Failed for: {message}"
            )

    @pytest.mark.asyncio
    async def test_handle_lifelog_auto_detection(self, lifelog_handler):
        """Test lifelog auto detection handling"""
        message_data = {"content": "美味しいご飯を食べた"}
        channel_info = MagicMock()

        # Should complete without error (implementation is placeholder)
        await lifelog_handler.handle_lifelog_auto_detection(message_data, channel_info)

    @pytest.mark.asyncio
    async def test_create_lifelog_obsidian_note(self, lifelog_handler):
        """Test lifelog Obsidian note creation"""
        lifelog_entry = {"content": "test entry"}
        message_data = {"content": "test message"}
        channel_info = MagicMock()

        result = await lifelog_handler.create_lifelog_obsidian_note(
            lifelog_entry, message_data, channel_info
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_handle_system_message(self, lifelog_handler):
        """Test system message handling"""
        message_data = {"content": "system message"}
        channel_info = MagicMock()

        # Should complete without error (implementation is placeholder)
        await lifelog_handler.handle_system_message(message_data, channel_info)


class TestNoteHandler:
    """Test NoteHandler functionality"""

    @pytest.fixture
    def note_handler(self):
        return NoteHandler(
            obsidian_manager=MagicMock(),
            note_template=MagicMock(),
            daily_integration=MagicMock(),
            template_engine=MagicMock(),
            note_analyzer=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_handle_obsidian_note_creation(self, note_handler):
        """Test Obsidian note creation"""
        message_data = {"content": "test message"}
        channel_info = MagicMock()
        ai_result = MagicMock()

        result = await note_handler.handle_obsidian_note_creation(
            message_data, channel_info, ai_result
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_organize_note_by_ai_category(self, note_handler):
        """Test note organization by AI category"""
        note_path = "/test/path.md"
        ai_category = "test-category"
        ai_result = MagicMock()

        # Should complete without error (implementation is placeholder)
        await note_handler.organize_note_by_ai_category(
            note_path, ai_category, ai_result
        )

    @pytest.mark.asyncio
    async def test_handle_daily_note_integration(self, note_handler):
        """Test daily note integration"""
        message_data = {"content": "test message"}
        ai_result = MagicMock()

        # Should complete without error (implementation is placeholder)
        await note_handler.handle_daily_note_integration(message_data, ai_result)

    @pytest.mark.asyncio
    async def test_handle_github_direct_sync(self, note_handler):
        """Test GitHub direct sync"""
        note_path = "/test/path.md"
        channel_info = MagicMock()

        # Should complete without error (implementation is placeholder)
        await note_handler.handle_github_direct_sync(note_path, channel_info)

    def test_generate_ai_based_title(self, note_handler):
        """Test AI-based title generation"""
        text_content = "This is a test message"
        result = note_handler.generate_ai_based_title(text_content)
        assert result == "AI Generated Title"

    def test_generate_text_based_title(self, note_handler):
        """Test text-based title generation"""
        text_content = "This is a test message"
        result = note_handler.generate_text_based_title(text_content)
        assert result == "Text Based Title"

    def test_get_fallback_title(self, note_handler):
        """Test fallback title generation"""
        channel_name = "test-channel"
        result = note_handler.get_fallback_title(channel_name)
        assert result == "Note from test-channel"

    def test_generate_activity_log_title(self, note_handler):
        """Test activity log title generation"""
        text_content = "This is a test activity"
        result = note_handler.generate_activity_log_title(text_content)
        assert result == "Activity Log"


class TestMessageHandler:
    """Test MessageHandler functionality"""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies for MessageHandler"""
        return {
            "ai_processor": MagicMock(),
            "obsidian_manager": MagicMock(),
            "note_template": MagicMock(),
            "daily_integration": MagicMock(),
            "template_engine": MagicMock(),
            "note_analyzer": MagicMock(),
            "speech_processor": MagicMock(),
            "lifelog_manager": MagicMock(),
            "lifelog_analyzer": MagicMock(),
            "lifelog_message_handler": MagicMock(),
            "lifelog_commands": MagicMock(),
        }

    @pytest.fixture
    def message_handler(self, mock_dependencies):
        return MessageHandler(**mock_dependencies)

    @pytest.mark.asyncio
    async def test_initialize(self, message_handler):
        """Test MessageHandler initialization"""
        await message_handler.initialize()
        # Should complete without error

    @pytest.mark.asyncio
    async def test_initialize_lifelog(self, message_handler):
        """Test lifelog initialization"""
        await message_handler.initialize_lifelog()
        # Should complete without error

    def test_set_monitoring_systems(self, message_handler):
        """Test setting monitoring systems"""
        system_metrics = MagicMock()
        api_usage_monitor = MagicMock()

        message_handler.set_monitoring_systems(system_metrics, api_usage_monitor)
        assert message_handler.system_metrics == system_metrics
        assert message_handler.api_usage_monitor == api_usage_monitor

    @pytest.mark.asyncio
    async def test_process_message_duplicate(self, message_handler):
        """Test processing duplicate message"""
        message = MagicMock(spec=discord.Message)
        message.id = 12345
        message_data = {"content": "test message"}
        channel_info = MagicMock()

        # Process message first time
        await message_handler.process_message(message, message_data, channel_info)

        # Process same message again (should be skipped)
        await message_handler.process_message(message, message_data, channel_info)

        # Should complete without error

    @pytest.mark.asyncio
    async def test_process_message_with_audio(self, message_handler):
        """Test processing message with audio attachments"""
        message = MagicMock(spec=discord.Message)
        message.id = 12346
        message_data = {
            "content": "test message",
            "metadata": {
                "attachments": [{"filename": "test.wav", "file_category": "audio"}]
            },
        }
        channel_info = MagicMock()

        with patch.object(
            message_handler.audio_handler,
            "handle_audio_attachments",
            new_callable=AsyncMock,
        ) as mock_audio:
            await message_handler.process_message(message, message_data, channel_info)
            mock_audio.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_with_text_and_ai_result(self, message_handler):
        """Test processing text message with AI result"""
        message = MagicMock(spec=discord.Message)
        message.id = 12347
        message_data = {"content": "test message"}
        channel_info = MagicMock()

        # Mock AI processor to return a result
        ai_result = MagicMock()
        message_handler.ai_processor.process_message = AsyncMock(return_value=ai_result)

        with patch.object(
            message_handler.note_handler,
            "handle_obsidian_note_creation",
            new_callable=AsyncMock,
        ) as mock_note:
            await message_handler.process_message(message, message_data, channel_info)
            mock_note.assert_called_once_with(
                message_data, channel_info, ai_result, message
            )

    @pytest.mark.asyncio
    async def test_process_message_lifelog_candidate(self, message_handler):
        """Test processing message that is a lifelog candidate"""
        message = MagicMock(spec=discord.Message)
        message.id = 12348
        message_data = {"content": "今日は美味しいラーメンを食べた"}
        channel_info = MagicMock()

        with patch.object(
            message_handler.lifelog_handler,
            "handle_lifelog_auto_detection",
            new_callable=AsyncMock,
        ) as mock_lifelog:
            await message_handler.process_message(message, message_data, channel_info)
            mock_lifelog.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_message_error_handling(self, message_handler):
        """Test error handling in process_message"""
        message = MagicMock(spec=discord.Message)
        message.id = 12349
        message_data = {"content": "test message"}
        channel_info = MagicMock()

        # Make audio handler raise an exception
        message_handler.audio_handler.handle_audio_attachments = AsyncMock(
            side_effect=Exception("Test error")
        )

        # Should not raise exception despite error in audio handler
        await message_handler.process_message(message, message_data, channel_info)

    @pytest.mark.asyncio
    async def test_handle_text_message_no_ai_processor(self, message_handler):
        """Test handling text message without AI processor"""
        message_handler.ai_processor = None
        message_data = {"content": "test message"}
        channel_info = MagicMock()
        original_message = MagicMock()

        # Should complete without error
        await message_handler._handle_text_message(
            message_data, channel_info, original_message
        )

    @pytest.mark.asyncio
    async def test_handle_text_message_no_ai_result(self, message_handler):
        """Test handling text message with no AI result"""
        message_data = {"content": "test message"}
        channel_info = MagicMock()
        original_message = MagicMock()

        # Mock AI processor to return None
        message_handler.ai_processor.process_message = AsyncMock(return_value=None)

        with patch.object(
            message_handler.note_handler,
            "handle_obsidian_note_creation",
            new_callable=AsyncMock,
        ) as mock_note:
            await message_handler._handle_text_message(
                message_data, channel_info, original_message
            )
            # Note creation should not be called when AI result is None
            mock_note.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_text_message_error_handling(self, message_handler):
        """Test error handling in _handle_text_message"""
        message_data = {"content": "test message"}
        channel_info = MagicMock()
        original_message = MagicMock()

        # Make AI processor raise an exception
        message_handler.ai_processor.process_message = AsyncMock(
            side_effect=Exception("AI error")
        )

        # Should not raise exception despite AI processor error
        await message_handler._handle_text_message(
            message_data, channel_info, original_message
        )

    @pytest.mark.asyncio
    async def test_legacy_compatibility_methods(self, message_handler):
        """Test legacy compatibility methods"""
        # These methods should delegate to their respective handlers

        # Test audio handler compatibility
        with patch.object(
            message_handler.audio_handler,
            "handle_audio_attachments",
            new_callable=AsyncMock,
        ) as mock_audio:
            await message_handler._handle_audio_attachments(
                "arg1", "arg2", kwarg1="test"
            )
            mock_audio.assert_called_once_with("arg1", "arg2", kwarg1="test")

        # Test note handler compatibility
        with patch.object(
            message_handler.note_handler,
            "handle_obsidian_note_creation",
            new_callable=AsyncMock,
        ) as mock_note:
            await message_handler._handle_obsidian_note_creation(
                "arg1", "arg2", kwarg1="test"
            )
            mock_note.assert_called_once_with("arg1", "arg2", kwarg1="test")

        # Test lifelog handler compatibility
        with patch.object(
            message_handler.lifelog_handler,
            "handle_lifelog_auto_detection",
            new_callable=AsyncMock,
        ) as mock_lifelog:
            await message_handler._handle_lifelog_auto_detection(
                "arg1", "arg2", kwarg1="test"
            )
            mock_lifelog.assert_called_once_with("arg1", "arg2", kwarg1="test")
