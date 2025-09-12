"""Test message processor functionality"""

import os
from datetime import datetime
from unittest.mock import Mock

import discord

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

from src.bot.message_processor import MessageProcessor


class TestMessageProcessor:
    """Test message processor functionality"""

    def setup_method(self) -> None:
        """Setup test fixtures"""
        self.processor = MessageProcessor()

    def test_initialization(self) -> None:
        """Test processor initialization"""
        assert self.processor is not None
        assert hasattr(self.processor, "url_pattern")
        assert hasattr(self.processor, "mention_patterns")

    def test_clean_content(self) -> None:
        """Test content cleaning functionality"""
        # Test with mentions and URLs
        content = "Hello <@123456> check this out: https://example.com and <#987654>"
        cleaned = self.processor._clean_content(content)

        # Should remove mentions and URLs, leaving clean text
        assert "Hello" in cleaned
        assert "check this out" in cleaned
        assert "<@123456>" not in cleaned
        assert "https://example.com" not in cleaned
        assert "<#987654>" not in cleaned

    def test_markdown_formatting_detection(self) -> None:
        """Test markdown formatting detection"""
        # Test various markdown formats
        test_cases = [
            ("**bold text**", True),
            ("*italic text*", True),
            ("~~strikethrough~~", True),
            ("`inline code`", True),
            ("```code block```", True),
            ("> quote", True),
            ("plain text", False),
            ("", False),
        ]

        for content, expected in test_cases:
            result = self.processor._has_markdown_formatting(content)
            assert result == expected, f"Failed for content: {content}"

    def test_language_detection(self) -> None:
        """Test basic language detection"""
        # Test Japanese content
        japanese_content = "こんにちは世界"
        result = self.processor._detect_language(japanese_content)
        assert result == "ja"

        # Test English content
        english_content = "Hello world"
        result = self.processor._detect_language(english_content)
        assert result == "en"

        # Test empty content
        result = self.processor._detect_language("")
        assert result is None

    def test_file_categorization(self) -> None:
        """Test file categorization"""
        # Test different file types
        test_cases = [
            ("image.png", "image/png", "image"),
            ("audio.mp3", "audio/mpeg", "audio"),
            ("video.mp4", "video/mp4", "video"),
            ("document.pdf", "application/pdf", "document"),
            ("script.py", "text/plain", "code"),
            ("archive.zip", "application/zip", "archive"),
            ("unknown.xyz", None, "other"),
        ]

        for filename, content_type, expected_category in test_cases:
            mock_attachment = Mock(spec=discord.Attachment)
            mock_attachment.filename = filename
            mock_attachment.content_type = content_type

            result = self.processor._categorize_file(mock_attachment)
            assert result == expected_category, f"Failed for {filename}"

    def test_extract_basic_metadata(self) -> None:
        """Test basic metadata extraction"""
        # Create mock message
        mock_message = Mock(spec=discord.Message)
        mock_message.id = 123456789
        mock_message.type = discord.MessageType.default
        mock_message.flags = discord.MessageFlags()
        mock_message.pinned = False
        mock_message.tts = False

        # Mock author
        mock_message.author = Mock(spec=discord.Member, id=987654321)
        mock_message.author.display_name = "Test User"
        mock_message.author.name = "testuser"
        mock_message.author.discriminator = "1234"
        mock_message.author.bot = False
        mock_message.author.avatar = None
        mock_message.author.mention = "<@987654321>"

        # Mock channel
        mock_message.channel.id = 111111111
        mock_message.channel.name = "test-channel"
        mock_message.channel.type = discord.ChannelType.text
        mock_message.channel.category = None

        # Mock guild
        mock_message.guild.id = 555555555
        mock_message.guild.name = "Test Guild"

        result = self.processor._extract_basic_metadata(mock_message)

        assert result is not None
        assert result["id"] == 123456789
        assert result["author"]["id"] == 987654321
        assert result["author"]["name"] == "Test User"
        assert result["channel"]["id"] == 111111111
        if result["guild"] is not None:
            assert result["guild"]["id"] == 555555555

    def test_extract_content_metadata(self) -> None:
        """Test content metadata extraction"""
        # Create mock message with rich content
        mock_message = Mock(spec=discord.Message)
        mock_message.content = (
            "Hello **world**! Check this: https://example.com `code` @user"
        )

        result = self.processor._extract_content_metadata(mock_message)

        assert result["raw_content"] == mock_message.content
        assert result["word_count"] > 0
        assert result["char_count"] == len(mock_message.content)
        assert len(result["urls"]) > 0
        assert "https://example.com" in result["urls"]
        assert result["has_formatting"] is True

    def test_extract_timing_metadata(self) -> None:
        """Test timing metadata extraction"""
        # Create mock message
        mock_message = Mock(spec=discord.Message)
        test_time = datetime(2024, 1, 1, 12, 0, 0)
        mock_message.created_at = test_time
        mock_message.edited_at = None

        result = self.processor._extract_timing_metadata(mock_message)

        assert result is not None
        assert "created_at" in result
        assert "edited_at" in result
        assert result["created_at"]["date"] == "2024-01-01"
        assert result["created_at"]["time"] == "12:00:00"
        assert result["created_at"]["hour"] == 12
        if result["edited_at"] is not None and "was_edited" in result["edited_at"]:
            assert result["edited_at"]["was_edited"] is False

    def test_extract_attachment_metadata(self) -> None:
        """Test attachment metadata extraction"""
        # Create mock attachment
        mock_attachment = Mock(spec=discord.Attachment)
        mock_attachment.id = 111111111
        mock_attachment.filename = "test_image.png"
        mock_attachment.size = 1024
        mock_attachment.url = "https://example.com/image.png"
        mock_attachment.proxy_url = "https://proxy.example.com/image.png"
        mock_attachment.content_type = "image/png"
        mock_attachment.width = 800
        mock_attachment.height = 600
        mock_attachment.ephemeral = False
        mock_attachment.description = None
        mock_attachment.is_spoiler.return_value = False

        # Create mock message with attachment
        mock_message = Mock(spec=discord.Message)
        mock_message.attachments = [mock_attachment]

        result = self.processor._extract_attachment_metadata(mock_message)

        assert len(result) == 1
        attachment_data = result[0]
        assert attachment_data["id"] == 111111111
        assert attachment_data["filename"] == "test_image.png"
        assert attachment_data["file_category"] == "image"
        assert attachment_data["file_extension"] == ".png"
        assert "image_info" in attachment_data

    def test_comprehensive_metadata_extraction(self) -> None:
        """Test complete metadata extraction"""
        # Create a comprehensive mock message
        mock_message = Mock(spec=discord.Message)
        mock_message.id = 123456789
        mock_message.content = (
            "Test message with **formatting** and https://example.com"
        )
        mock_message.type = discord.MessageType.default
        mock_message.flags = discord.MessageFlags()
        mock_message.pinned = False
        mock_message.tts = False
        mock_message.created_at = datetime(2024, 1, 1, 12, 0, 0)
        mock_message.edited_at = None
        mock_message.attachments = []
        mock_message.embeds = []
        mock_message.reactions = []
        mock_message.stickers = []
        mock_message.mentions = []
        mock_message.role_mentions = []
        mock_message.channel_mentions = []
        mock_message.mention_everyone = False
        mock_message.reference = None

        # Mock author
        mock_message.author = Mock(spec=discord.Member, id=987654321)
        mock_message.author.display_name = "Test User"
        mock_message.author.name = "testuser"
        mock_message.author.discriminator = "1234"
        mock_message.author.bot = False
        mock_message.author.avatar = None
        mock_message.author.mention = "<@987654321>"

        # Mock channel
        mock_message.channel.id = 111111111
        mock_message.channel.name = "test-channel"
        mock_message.channel.type = discord.ChannelType.text
        mock_message.channel.category = None

        # Mock guild
        mock_message.guild.id = 555555555
        mock_message.guild.name = "Test Guild"

        metadata = self.processor.extract_metadata(mock_message)

        # Verify all metadata sections are present
        assert "basic" in metadata
        assert "content" in metadata
        assert "attachments" in metadata
        assert "references" in metadata
        assert "discord_features" in metadata
        assert "timing" in metadata

        # Verify basic metadata
        assert metadata["basic"]["id"] == 123456789
        assert metadata["basic"]["author"]["id"] == 987654321

        # Verify content metadata
        assert "Test message" in metadata["content"]["raw_content"]
        assert len(metadata["content"]["urls"]) > 0
        assert metadata["content"]["has_formatting"] is True
