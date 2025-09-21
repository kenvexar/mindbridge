"""
Refactored MessageHandler using specialized handlers
"""

from typing import Any

import discord

from src.utils.mixins import LoggerMixin

from .audio_handler import AudioHandler
from .lifelog_handler import LifelogHandler
from .note_handler import NoteHandler


class MessageHandler(LoggerMixin):
    """
    リファクタリング済みメッセージハンドラー
    機能別の専用ハンドラーに処理を委譲
    """

    def __init__(
        self,
        ai_processor=None,
        obsidian_manager=None,
        note_template=None,
        daily_integration=None,
        template_engine=None,
        note_analyzer=None,
        speech_processor=None,
        lifelog_manager=None,
        lifelog_analyzer=None,
        lifelog_message_handler=None,
        lifelog_commands=None,
    ):
        # Core components
        self.ai_processor = ai_processor
        self.obsidian_manager = obsidian_manager
        self.note_template = note_template
        self.daily_integration = daily_integration
        self.template_engine = template_engine
        self.note_analyzer = note_analyzer
        self.speech_processor = speech_processor

        # Lifelog components
        self.lifelog_manager = lifelog_manager
        self.lifelog_analyzer = lifelog_analyzer
        self.lifelog_message_handler = lifelog_message_handler
        self.lifelog_commands = lifelog_commands

        # Specialized handlers
        self.audio_handler = AudioHandler(speech_processor=speech_processor)
        self.note_handler = NoteHandler(
            obsidian_manager=obsidian_manager,
            note_template=note_template,
            daily_integration=daily_integration,
            template_engine=template_engine,
            note_analyzer=note_analyzer,
        )
        self.lifelog_handler = LifelogHandler(
            lifelog_manager=lifelog_manager,
            lifelog_analyzer=lifelog_analyzer,
            lifelog_message_handler=lifelog_message_handler,
            lifelog_commands=lifelog_commands,
        )

        # Monitoring systems
        self.system_metrics = None
        self.api_usage_monitor = None

        # Message processing state
        self._processed_messages = set()
        self._creating_notes = set()
        self._max_processed_messages = 1000

    def set_monitoring_systems(self, system_metrics=None, api_usage_monitor=None):
        """モニタリングシステムの設定"""
        self.system_metrics = system_metrics
        self.api_usage_monitor = api_usage_monitor

    async def initialize(self) -> None:
        """メッセージハンドラーの初期化"""
        self.logger.info("MessageHandler initialized successfully")

    async def initialize_lifelog(self) -> None:
        """ライフログ機能の初期化"""
        # TODO: 必要に応じてライフログ初期化ロジックを実装
        pass

    async def process_message(
        self,
        message: discord.Message,
        message_data: dict[str, Any],
        channel_info: Any,
    ) -> None:
        """
        メッセージ処理のメインエントリーポイント
        各専用ハンドラーに処理を委譲
        """
        try:
            # メッセージの重複処理チェック
            message_id = message.id
            if message_id in self._processed_messages:
                self.logger.debug("Message already processed, skipping", message_id=message_id)
                return

            self._processed_messages.add(message_id)

            # メッセージタイプによる処理の分岐
            metadata = message_data.get("metadata", {})

            # 音声添付ファイルがある場合
            if metadata.get("attachments"):
                await self.audio_handler.handle_audio_attachments(
                    message_data, channel_info, message
                )

            # テキストメッセージの処理
            if message_data.get("content"):
                await self._handle_text_message(message_data, channel_info, message)

            # ライフログ自動検出
            if self.lifelog_handler.is_lifelog_candidate(message_data.get("content", "")):
                await self.lifelog_handler.handle_lifelog_auto_detection(
                    message_data, channel_info, message
                )

        except Exception as e:
            self.logger.error(
                "Error in process_message",
                error=str(e),
                message_id=message.id,
                exc_info=True,
            )

    async def _handle_text_message(
        self,
        message_data: dict[str, Any],
        channel_info: Any,
        original_message: discord.Message,
    ) -> None:
        """テキストメッセージの処理"""
        try:
            # AI 処理が必要な場合
            if self.ai_processor:
                ai_result = await self.ai_processor.process_message(message_data)

                # ノート作成が必要な場合（ AI 結果が存在すればノート作成）
                if ai_result:
                    await self.note_handler.handle_obsidian_note_creation(
                        message_data, channel_info, ai_result, original_message
                    )

        except Exception as e:
            self.logger.error(
                "Error handling text message",
                error=str(e),
                exc_info=True,
            )

    # Legacy method compatibility - 元の巨大なメソッドからの段階的移行用
    async def _handle_audio_attachments(self, *args, **kwargs):
        """Legacy compatibility method"""
        return await self.audio_handler.handle_audio_attachments(*args, **kwargs)

    async def _handle_obsidian_note_creation(self, *args, **kwargs):
        """Legacy compatibility method"""
        return await self.note_handler.handle_obsidian_note_creation(*args, **kwargs)

    async def _handle_lifelog_auto_detection(self, *args, **kwargs):
        """Legacy compatibility method"""
        return await self.lifelog_handler.handle_lifelog_auto_detection(*args, **kwargs)