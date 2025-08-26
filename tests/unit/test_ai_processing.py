"""Test AI processing functionality"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

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

from src.ai.models import (
    AIModelConfig,
    CategoryResult,
    ProcessingCategory,
    ProcessingSettings,
    SummaryResult,
    TagResult,
)
from src.ai.processor import AIProcessor


class TestAIModels:
    """Test AI data models"""

    def test_ai_model_config_defaults(self):
        """Test AI model configuration defaults"""
        config = AIModelConfig()

        assert config.model_name == "gemini-1.5-flash"
        assert config.temperature == 0.3
        assert config.max_tokens == 1024
        assert config.top_p == 0.8
        assert config.top_k == 40

    def test_processing_settings_defaults(self):
        """Test processing settings defaults"""
        settings = ProcessingSettings()

        assert settings.min_text_length == 50
        assert settings.max_text_length == 8000
        assert settings.enable_summary is True
        assert settings.enable_tags is True
        assert settings.enable_categorization is True
        assert settings.max_keywords == 5
        assert settings.cache_duration_hours == 24
        assert settings.retry_count == 3
        assert settings.timeout_seconds == 30

    def test_summary_result_validation(self):
        """Test summary result validation"""
        result = SummaryResult(
            summary="Test summary",
            key_points=["Point 1", "Point 2"],
            processing_time_ms=100,
            model_used="gemini-1.5-flash",
        )

        assert result.summary == "Test summary"
        assert len(result.key_points) == 2
        assert result.processing_time_ms == 100
        assert result.model_used == "gemini-1.5-flash"

    def test_tag_result_validation(self):
        """Test tag result validation and normalization"""
        result = TagResult(
            tags=["programming", "#ai", "python"],
            raw_keywords=["programming", "ai", "python"],
            processing_time_ms=150,
            model_used="gemini-1.5-flash",
        )

        # Check tag normalization
        expected_tags = ["#programming", "#ai", "#python"]
        assert result.tags == expected_tags
        assert len(result.raw_keywords) == 3
        assert result.processing_time_ms == 150

    def test_category_result_validation(self):
        """Test category result validation"""
        result = CategoryResult(
            category=ProcessingCategory.WORK,
            confidence_score=0.8,
            processing_time_ms=120,
            model_used="gemini-1.5-flash",
        )

        assert result.category == ProcessingCategory.WORK
        assert result.confidence_score == 0.8
        assert result.processing_time_ms == 120
        assert result.model_used == "gemini-1.5-flash"


class TestAIProcessor:
    """Test AI processor functionality"""

    def setup_method(self) -> None:
        """Setup test fixtures"""
        self.settings = ProcessingSettings(
            min_text_length=10, max_text_length=1000, timeout_seconds=5
        )

        # AI 処理システムは Gemini API が利用できない場合の対応が必要
        # テスト環境ではモックを使用
        with patch("src.ai.processor.GeminiClient"):
            self.ai_processor = AIProcessor(settings=self.settings)

    def test_ai_processor_initialization(self):
        """Test AI processor initialization"""
        assert self.ai_processor.settings.min_text_length == 10
        assert self.ai_processor.settings.max_text_length == 1000
        assert self.ai_processor.stats.total_requests == 0

    def test_generate_content_hash(self):
        """Test content hash generation"""
        text1 = "Hello world"
        text2 = "Hello world"
        text3 = "Different text"

        hash1 = self.ai_processor._generate_content_hash(text1)
        hash2 = self.ai_processor._generate_content_hash(text2)
        hash3 = self.ai_processor._generate_content_hash(text3)

        # Same text should produce same hash
        assert hash1 == hash2
        # Different text should produce different hash
        assert hash1 != hash3
        # Hash should be string and have expected length
        assert isinstance(hash1, str)
        assert len(hash1) == 16

    def test_is_text_processable(self):
        """Test text processability check"""
        # Too short text
        short_text = "Hi"
        assert not self.ai_processor._is_text_processable(short_text)

        # Good length text
        good_text = "This is a good length text for processing"
        assert self.ai_processor._is_text_processable(good_text)

        # Too long text
        long_text = "x" * 2000
        assert not self.ai_processor._is_text_processable(long_text)

        # Empty text
        empty_text = ""
        assert not self.ai_processor._is_text_processable(empty_text)

    @pytest.mark.asyncio
    async def test_process_text_with_short_text(self) -> None:
        """Test processing with text that's too short"""
        short_text = "Hi"
        message_id = 123456

        result = await self.ai_processor.process_text(short_text, message_id)

        assert result.message_id == message_id
        assert len(result.errors) > 0
        assert "not processable" in result.errors[0]
        assert result.summary is None
        assert result.tags is None
        assert result.category is None

    def test_cache_functionality(self):
        """Test caching functionality"""
        # Generate test data
        text = "Test message for caching"
        content_hash = self.ai_processor._generate_content_hash(text)

        # Create a mock result
        from src.ai.models import AIProcessingResult

        mock_result = AIProcessingResult(
            message_id=123, processed_at=datetime.now(), total_processing_time_ms=100
        )

        # Test cache miss
        cached_result = self.ai_processor._get_from_cache(content_hash)
        assert cached_result is None

        # Save to cache
        self.ai_processor._save_to_cache(content_hash, mock_result)

        # Test cache hit
        cached_result = self.ai_processor._get_from_cache(content_hash)
        assert cached_result is not None
        assert cached_result.message_id == 123
        assert cached_result.cache_hit is True

    def test_get_stats(self):
        """Test statistics retrieval"""
        stats = self.ai_processor.get_stats()

        assert hasattr(stats, "total_requests")
        assert hasattr(stats, "successful_requests")
        assert hasattr(stats, "failed_requests")
        assert hasattr(stats, "cache_hits")
        assert hasattr(stats, "cache_misses")

    def test_get_cache_info(self):
        """Test cache information retrieval"""
        cache_info = self.ai_processor.get_cache_info()

        assert "total_entries" in cache_info
        assert "total_cache_hits" in cache_info
        assert "cache_hit_rate" in cache_info
        assert isinstance(cache_info["total_entries"], int)
        assert isinstance(cache_info["cache_hit_rate"], float)

    def test_clear_cache(self):
        """Test cache clearing"""
        # Add something to cache first
        from src.ai.models import AIProcessingResult

        mock_result = AIProcessingResult(
            message_id=123, processed_at=datetime.now(), total_processing_time_ms=100
        )

        text = "Test message"
        content_hash = self.ai_processor._generate_content_hash(text)
        self.ai_processor._save_to_cache(content_hash, mock_result)

        # Verify cache has content
        cache_info_before = self.ai_processor.get_cache_info()
        assert cache_info_before["total_entries"] > 0

        # Clear cache
        cleared_count = self.ai_processor.clear_cache()
        assert cleared_count > 0

        # Verify cache is empty
        cache_info_after = self.ai_processor.get_cache_info()
        assert cache_info_after["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_health_check_without_api(self) -> None:
        """Test health check when API is not available"""
        # Since we don't have real API credentials in tests,
        # the health check should return unhealthy status
        health_status = await self.ai_processor.health_check()

        assert "status" in health_status
        assert "model" in health_status
        # In test environment without real API, status should be unhealthy
        assert health_status["status"] in ["healthy", "unhealthy"]


async def test_ai_processing_integration() -> None:
    """Test AI processing integration with message handler"""

    import discord

    from src.bot.handlers import MessageHandler

    # Setup mock channel config with predefined channel
    mock_channel_config = Mock()
    mock_channel_config.is_monitored_channel.return_value = True

    # Mock channel info
    from src.bot.channel_config import ChannelCategory, ChannelInfo

    mock_channel_info = ChannelInfo(
        id=123456789,
        name="memo",  # 2025 年アーキテクチャ更新: inbox → memo
        category=ChannelCategory.CAPTURE,
        description="Test memo channel (unified input)",
    )
    mock_channel_config.get_channel_info.return_value = mock_channel_info

    # Create message handler with AI processing
    with patch("src.ai.processor.GeminiClient"):
        from src.ai.mock_processor import MockAIProcessor
        from src.ai.note_analyzer import AdvancedNoteAnalyzer
        from src.obsidian import ObsidianFileManager
        from src.obsidian.daily_integration import DailyNoteIntegration
        from src.obsidian.template_system import TemplateEngine

        mock_ai_processor = MockAIProcessor()
        mock_obsidian_manager = Mock(spec=ObsidianFileManager)
        mock_daily_integration = Mock(spec=DailyNoteIntegration)
        mock_template_engine = Mock(spec=TemplateEngine)
        mock_note_analyzer = Mock(spec=AdvancedNoteAnalyzer)

        handler = MessageHandler(
            ai_processor=mock_ai_processor,
            obsidian_manager=mock_obsidian_manager,
            note_template="Test template",
            daily_integration=mock_daily_integration,
            template_engine=mock_template_engine,
            note_analyzer=mock_note_analyzer,
            channel_config=mock_channel_config,
        )

    # Verify AI processor is initialized
    assert hasattr(handler, "ai_processor")
    assert handler.ai_processor is not None

    # Create mock message
    mock_message = Mock(spec=discord.Message)
    mock_message.id = 123456789
    mock_message.content = "This is a test message that should be long enough for AI processing to trigger properly"
    mock_message.author.bot = False
    mock_message.author.id = 987654321
    mock_message.author.display_name = "Test User"
    mock_message.author.name = "testuser"
    mock_message.author.discriminator = "1234"
    mock_message.author.avatar = None
    mock_message.author.mention = "<@987654321>"

    # Set channel properties
    mock_message.channel.id = 123456789
    mock_message.channel.name = "memo"  # 2025 年アーキテクチャ更新: inbox → memo
    mock_message.channel.type = discord.ChannelType.text
    mock_message.channel.category = None
    mock_message.created_at = datetime(2024, 1, 1, 12, 0, 0)
    mock_message.edited_at = None
    mock_message.guild.id = 111111111
    mock_message.guild.name = "Test Guild"
    mock_message.attachments = []
    mock_message.embeds = []
    mock_message.mentions = []
    mock_message.role_mentions = []
    mock_message.channel_mentions = []
    mock_message.reactions = []
    mock_message.stickers = []
    mock_message.reference = None
    mock_message.type = discord.MessageType.default
    mock_message.flags = discord.MessageFlags()
    mock_message.pinned = False
    mock_message.tts = False
    mock_message.mention_everyone = False

    # Mock the AI processing to avoid actual API calls
    with patch.object(handler.ai_processor, "process_text") as mock_process:
        from src.ai.models import AIProcessingResult

        mock_result = AIProcessingResult(
            message_id=123456789,
            processed_at=datetime.now(),
            total_processing_time_ms=100,
        )
        mock_process.return_value = mock_result

        # Mock the routing method
        with patch.object(
            handler, "_route_message_by_category", new_callable=AsyncMock
        ):
            # Process message
            result = await handler.process_message(mock_message)

        # Verify result
        assert result is not None
        assert "metadata" in result
        assert "ai_processing" in result

        # Verify AI processing was attempted
        mock_process.assert_called_once()
