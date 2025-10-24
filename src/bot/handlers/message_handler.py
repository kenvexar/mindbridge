"""
Refactored MessageHandler using specialized handlers
"""

from typing import TYPE_CHECKING, Any

import discord

from src.utils.mixins import LoggerMixin

from ..message_processor import MessageProcessor
from .audio_handler import AudioHandler
from .lifelog_handler import LifelogHandler
from .note_handler import NoteHandler

if TYPE_CHECKING:
    from src.config.settings import Settings
    from src.lifelog import (
        LifelogAnalyzer,
        LifelogCommands,
        LifelogManager,
        LifelogMessageHandler,
    )


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

        # Unified metadata extractor
        self.message_processor = MessageProcessor()

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

    def _load_lifelog_components(
        self,
    ) -> tuple[
        type["LifelogManager"],
        type["LifelogAnalyzer"],
        type["LifelogMessageHandler"],
        type["LifelogCommands"],
    ]:
        from src.lifelog import (
            LifelogAnalyzer,
            LifelogCommands,
            LifelogManager,
            LifelogMessageHandler,
        )

        return (LifelogManager, LifelogAnalyzer, LifelogMessageHandler, LifelogCommands)

    async def initialize_lifelog(
        self,
        settings: "Settings | None" = None,
    ) -> None:
        """ライフログ機能の初期化"""
        try:
            (
                manager_cls,
                analyzer_cls,
                message_handler_cls,
                commands_cls,
            ) = self._load_lifelog_components()
        except Exception as exc:
            self.logger.warning("ライフログモジュールの読み込みに失敗", error=str(exc))
            return

        manager = self.lifelog_manager
        if manager is None:
            if settings is None:
                self.logger.info("ライフログ設定が未提供のため初期化をスキップします")
                return
            manager = manager_cls(settings)
            self.lifelog_manager = manager

        await manager.initialize()

        analyzer = self.lifelog_analyzer
        if analyzer is None:
            if self.ai_processor is None:
                self.logger.warning(
                    "AI プロセッサーが未設定のためライフログアナライザーを構築できません"
                )
            else:
                analyzer = analyzer_cls(manager, self.ai_processor)
                self.lifelog_analyzer = analyzer

        message_handler = self.lifelog_message_handler
        if message_handler is None:
            if self.ai_processor is None:
                self.logger.warning(
                    "AI プロセッサーが未設定のためライフログメッセージハンドラーを構築できません"
                )
            else:
                message_handler = message_handler_cls(manager, self.ai_processor)
                self.lifelog_message_handler = message_handler

        commands = self.lifelog_commands
        if commands is None:
            if analyzer is None:
                self.logger.warning(
                    "ライフログアナライザーが未初期化のためコマンド登録をスキップします"
                )
            else:
                commands = commands_cls(manager, analyzer)
                self.lifelog_commands = commands

        self.lifelog_handler = LifelogHandler(
            lifelog_manager=manager,
            lifelog_analyzer=analyzer,
            lifelog_message_handler=message_handler,
            lifelog_commands=commands,
        )

        self.logger.info("ライフログ機能を初期化しました")

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
                self.logger.debug(
                    "Message already processed, skipping", message_id=message_id
                )
                return

            self._processed_messages.add(message_id)

            # メッセージタイプによる処理の分岐
            metadata = message_data.get("metadata")
            if metadata is None:
                try:
                    metadata = self.message_processor.extract_metadata(message)
                except Exception as exc:
                    self.logger.warning(
                        "Falling back to minimal metadata extraction",
                        message_id=message_id,
                        error=str(exc),
                    )
                    metadata = self._build_fallback_metadata(message, message_data)

                message_data["metadata"] = metadata

                # Update convenience fields used by downstream handlers
                content_info = metadata.get("content", {})
                if not message_data.get("content"):
                    message_data["content"] = content_info.get("raw_content", "")
                message_data["attachments"] = metadata.get("attachments", [])

            # 音声添付ファイルがある場合
            if metadata.get("attachments") or message_data.get("attachments"):
                await self.audio_handler.handle_audio_attachments(
                    message_data, channel_info, message
                )

            # テキストメッセージの処理
            if message_data.get("content"):
                await self._handle_text_message(message_data, channel_info, message)

            # ライフログ自動検出
            if self.lifelog_handler.is_lifelog_candidate(
                message_data.get("content", "")
            ):
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
            ai_result = None

            if self.ai_processor:
                ai_result = await self.ai_processor.process_message(message_data)

            if self.note_handler and ai_result:
                content_meta = (
                    message_data.get("metadata", {}).get("content", {})
                    if isinstance(message_data.get("metadata"), dict)
                    else {}
                )
                raw_content = content_meta.get("raw_content")
                if not raw_content and isinstance(message_data.get("content"), str):
                    raw_content = message_data["content"]

                if raw_content and raw_content.strip():
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

    def _build_fallback_metadata(
        self, message: discord.Message, message_data: dict[str, Any]
    ) -> dict[str, Any]:
        """テストやモック環境向けに最小限のメタデータを組み立てる"""
        raw_content = message_data.get("content")
        if not isinstance(raw_content, str):
            msg_content = getattr(message, "content", "")
            raw_content = msg_content if isinstance(msg_content, str) else ""

        cleaned_content = raw_content.strip()

        basic_info: dict[str, Any] = {
            "id": getattr(message, "id", 0),
            "type": str(getattr(message, "type", "message")),
            "flags": [],
            "pinned": bool(getattr(message, "pinned", False)),
            "tts": bool(getattr(message, "tts", False)),
            "author": {},
            "channel": {},
            "guild": None,
        }

        content_meta: dict[str, Any] = {
            "raw_content": raw_content,
            "cleaned_content": cleaned_content,
            "word_count": len(cleaned_content.split()) if cleaned_content else 0,
            "char_count": len(cleaned_content),
            "line_count": cleaned_content.count("\n") + (1 if cleaned_content else 0),
            "urls": [],
            "mentions": {},
            "code_blocks": 0,
            "inline_code": 0,
            "has_formatting": False,
            "language": None,
        }

        fallback_metadata: dict[str, Any] = {
            "basic": basic_info,
            "content": content_meta,
            "attachments": message_data.get("attachments", []),
            "references": {
                "is_reply": False,
                "reply_to": None,
                "mentions_reply_author": False,
            },
            "discord_features": {
                "embeds": [],
                "reactions": [],
                "mentions": {},
                "stickers": [],
            },
            "timing": {
                "created_at": {},
                "edited_at": {"was_edited": False},
                "age_seconds": 0,
            },
        }

        return fallback_metadata
