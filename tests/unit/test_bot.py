"""Test Discord bot functionality"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import discord
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

from src.bot.channel_config import ChannelConfig
from src.bot.handlers import MessageHandler


class TestChannelConfig:
    """Test channel configuration"""

    def test_channel_config_initialization(self) -> None:
        """Test basic channel configuration initialization"""
        config = ChannelConfig()

        # 新しいアーキテクチャでは、実際の Discord チャンネルが存在しないと
        # チャンネルは発見されないため、基本的な機能をテスト
        assert hasattr(config, "channels")
        assert hasattr(config, "is_monitored_channel")
        assert hasattr(config, "get_channel_info")

    def test_channel_name_mapping(self) -> None:
        """Test channel name mapping functionality

        重要: 2025 年アーキテクチャ変更により、チャンネル設計が大幅に簡素化されました。

        変更内容:
        - 旧システム: 17+ 専用チャンネル (inbox, money, tasks, health, voice, files, etc.)
        - 新システム: 3 チャンネルのみ + AI 自動分類

        新チャンネル構成:
        1. memo: 統合入力チャンネル（全コンテンツタイプ統合）
        2. notifications: システム通知
        3. commands: ボットコマンド

        AI 分類により、 memo チャンネルのコンテンツは適切な Obsidian フォルダへ自動振り分け:
        - 💰 Finance: "1500 ランチ" → Finance フォルダ
        - ✅ Tasks: "TODO: 資料作成" → Tasks フォルダ
        - 🏃 Health: "体重 70kg" → Health フォルダ
        - 🎙️ Voice: 音声ファイル → 文字起こし後分類
        - 📁 Files: ファイル → 内容に応じて分類

        このテストでは新しい 3 チャンネル設計を検証しています。
        """
        from src.config.settings import get_settings

        settings = get_settings()
        channel_mapping = settings.get_channel_name_mapping()

        # 必須チャンネルが含まれていることを確認
        required_channels = settings.get_required_channel_names()
        for channel in required_channels:
            assert channel in channel_mapping.values()

        # 新しい 3 チャンネル設計の検証
        # 注意: "inbox" などの旧チャンネル名は存在しません
        assert "memo" in channel_mapping.values(), "memo チャンネル（統合入力）が必要"
        assert "notifications" in channel_mapping.values(), (
            "notifications チャンネルが必要"
        )
        assert "commands" in channel_mapping.values(), "commands チャンネルが必要"

        # 旧チャンネルが存在しないことを確認（回帰防止）
        deprecated_channels = ["inbox", "money", "tasks", "health", "voice", "files"]
        for old_channel in deprecated_channels:
            assert old_channel not in channel_mapping.values(), (
                f"廃止された {old_channel} チャンネルが検出されました"
            )


class TestMessageHandler:
    """Test message handler functionality"""

    def setup_method(self) -> None:
        """Setup test fixtures"""
        # Mock channel config to avoid dependency on actual Discord channels
        self.channel_config = Mock()
        self.channel_config.is_monitored_channel.return_value = (
            False  # Default to unmonitored
        )
        self.channel_config.get_channel_info.return_value = None
        # Create mock dependencies
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

        self.handler = MessageHandler(
            ai_processor=mock_ai_processor,
            obsidian_manager=mock_obsidian_manager,
            note_template="Test template",
            daily_integration=mock_daily_integration,
            template_engine=mock_template_engine,
            note_analyzer=mock_note_analyzer,
            channel_config=self.channel_config,
        )

    @pytest.mark.asyncio
    async def test_bot_message_ignored(self) -> None:
        """Test that bot messages are ignored"""
        # Create mock bot message
        mock_message = Mock(spec=discord.Message)
        mock_message.author.bot = True

        result = await self.handler.process_message(mock_message)
        assert result is None

    @pytest.mark.asyncio
    async def test_unmonitored_channel_ignored(self) -> None:
        """Test that unmonitored channels are ignored"""
        # Create mock message from unmonitored channel
        mock_message = Mock(spec=discord.Message)
        mock_message.author.bot = False
        mock_message.channel.id = 999999999  # Invalid channel ID

        # Test early return when channel is not monitored
        with patch.object(
            self.channel_config, "is_monitored_channel", return_value=False
        ):
            result = await self.handler.process_message(mock_message)
            assert result is None

    @pytest.mark.asyncio
    async def test_valid_message_processing(self) -> None:
        """Test processing of valid messages"""
        # Mock a valid channel
        from src.bot.channel_config import ChannelCategory, ChannelInfo

        # 注意: 2025 年アーキテクチャ変更により "inbox" は "memo" に統一
        mock_channel_info = ChannelInfo(
            id=123456789,
            name="memo",  # 旧 "inbox" から変更
            category=ChannelCategory.CAPTURE,
            description="Test memo channel (unified input)",
        )

        # Configure mock to return monitored channel
        self.channel_config.is_monitored_channel.return_value = True
        self.channel_config.get_channel_info.return_value = mock_channel_info

        # Create a more complete mock message
        mock_message = Mock(spec=discord.Message)
        mock_message.id = 123456789
        mock_message.content = "Test message"
        mock_message.author.bot = False
        mock_message.author.id = 987654321
        mock_message.author.display_name = "Test User"
        mock_message.author.name = "testuser"
        mock_message.author.discriminator = "1234"
        mock_message.author.avatar = None
        mock_message.author.mention = "<@987654321>"
        mock_message.channel.id = 123456789
        mock_message.channel.name = "test-channel"
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

        # Mock the routing method to avoid actual processing
        with patch.object(
            self.handler, "_route_message_by_category", new_callable=AsyncMock
        ) as mock_route:
            result = await self.handler.process_message(mock_message)

        assert result is not None
        assert "metadata" in result
        assert "channel_info" in result
        assert result["channel_info"]["name"] == mock_channel_info.name
        assert result["channel_info"]["category"] == mock_channel_info.category.value

        # Check metadata structure
        metadata = result["metadata"]
        assert "basic" in metadata
        assert "content" in metadata
        assert "attachments" in metadata
        assert "references" in metadata
        assert "discord_features" in metadata
        assert "timing" in metadata

        # Verify routing was called
        mock_route.assert_called_once()
