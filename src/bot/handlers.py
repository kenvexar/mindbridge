"""
Message handlers for Discord bot
"""

from datetime import datetime
from pathlib import Path
from typing import Any, cast

import discord

from src.ai import AIProcessor
from src.ai.mock_processor import MockAIProcessor
from src.ai.models import AIProcessingResult
from src.ai.note_analyzer import AdvancedNoteAnalyzer
from src.audio import SpeechProcessor
from src.bot.channel_config import ChannelCategory, ChannelConfig
from src.bot.message_processor import MessageMetadata
from src.obsidian import ObsidianFileManager
from src.obsidian.daily_integration import DailyNoteIntegration
from src.obsidian.models import NoteFrontmatter, ObsidianNote
from src.obsidian.template_system import TemplateEngine
from src.utils.mixins import LoggerMixin


class MessageHandler(LoggerMixin):
    """Handle Discord message processing and routing"""

    ai_processor: AIProcessor | MockAIProcessor
    obsidian_manager: ObsidianFileManager | None
    note_template: str | None  # 古いテンプレートシステムは無効化
    daily_integration: DailyNoteIntegration | None
    template_engine: TemplateEngine | None
    note_analyzer: AdvancedNoteAnalyzer | None
    speech_processor: SpeechProcessor | None
    # ライフログシステム（オプション）
    lifelog_manager: Any | None
    lifelog_analyzer: Any | None
    lifelog_message_handler: Any | None
    lifelog_commands: Any | None

    def set_monitoring_systems(
        self, system_metrics: Any, api_usage_monitor: Any
    ) -> None:
        """監視システムの設定"""
        self.system_metrics = system_metrics
        self.api_usage_monitor = api_usage_monitor

    def __init__(
        self,
        ai_processor: AIProcessor | MockAIProcessor,
        obsidian_manager: ObsidianFileManager,
        note_template: str,
        daily_integration: DailyNoteIntegration,
        template_engine: TemplateEngine,
        note_analyzer: AdvancedNoteAnalyzer,
        speech_processor: SpeechProcessor | None = None,
        channel_config: ChannelConfig | None = None,
    ) -> None:
        """Initialize message handler with dependencies"""
        # Track processed messages and notes being created to prevent duplicates
        self._processed_messages: set[str] = set()  # メッセージキーの文字列を格納
        self._creating_notes: set[str] = set()  # ノート作成中のメッセージキーを追跡
        self._max_processed_messages = 1000  # メモリ管理のため最大数を制限

        self.ai_processor = ai_processor
        self.obsidian_manager = obsidian_manager
        self.note_template = note_template
        self.daily_integration = daily_integration
        self.template_engine = template_engine
        self.note_analyzer = note_analyzer
        self.speech_processor = speech_processor

        # ライフログシステム初期化
        self.lifelog_manager = None
        self.lifelog_analyzer = None
        self.lifelog_message_handler = None
        self.lifelog_commands = None

        # Logger is already available through LoggerMixin

        # Initialize dependencies
        from src.bot.message_processor import MessageProcessor

        # Use shared ChannelConfig instance or create new one
        if channel_config is not None:
            self.channel_config = channel_config
        else:
            from src.bot.channel_config import ChannelConfig

            self.channel_config = ChannelConfig()

        self.message_processor = MessageProcessor()

        # Optional monitoring systems (will be set by main.py if available)
        # Note: These are already defined in set_monitoring_systems method

        self.logger.info("MessageHandler initialized")

        # Initialize message processing components
        try:
            # Test basic functionality
            test_channel_id = 123456789  # Dummy channel ID for testing
            is_monitored = self.channel_config.is_monitored_channel(test_channel_id)
            self.logger.info(
                f"Channel config test: is_monitored({test_channel_id}) = {is_monitored}"
            )

            # Test message processor
            test_result = self.message_processor._clean_content("Test content   ")
            self.logger.info(
                f"Message processor test: cleaned_content = '{test_result}'"
            )

        except Exception as e:
            self.logger.error(
                f"Error during MessageHandler initialization testing: {e}"
            )
            # Continue initialization despite test failures

        self.logger.info(
            "MessageHandler fully initialized with enhanced duplicate prevention",
            processed_messages_capacity=self._max_processed_messages,
        )

    async def initialize(self) -> None:
        """非同期初期化処理"""
        if self.template_engine:
            try:
                await self.template_engine.create_default_templates()
                self.logger.info("Default templates created")
            except Exception as e:
                self.logger.error("Failed to create default templates", error=str(e))

    async def initialize_lifelog(self, settings) -> None:
        """ライフログシステムを初期化"""
        try:
            from ..lifelog import (
                LifelogAnalyzer,
                LifelogCommands,
                LifelogManager,
                LifelogMessageHandler,
            )

            # ライフログマネージャーを初期化
            self.lifelog_manager = LifelogManager(settings)
            await self.lifelog_manager.initialize()

            # アナライザーを初期化
            from typing import cast

            from ..ai.processor import AIProcessor

            self.lifelog_analyzer = LifelogAnalyzer(
                self.lifelog_manager, cast(AIProcessor, self.ai_processor)
            )

            # メッセージハンドラーを初期化
            self.lifelog_message_handler = LifelogMessageHandler(
                self.lifelog_manager, cast(AIProcessor, self.ai_processor)
            )

            # コマンドハンドラーを初期化
            self.lifelog_commands = LifelogCommands(
                self.lifelog_manager, self.lifelog_analyzer
            )

            self.logger.info("ライフログシステムを初期化しました")

        except Exception as e:
            self.logger.warning("ライフログシステムの初期化に失敗", error=str(e))
            # ライフログなしでも動作を継続

    async def process_message(self, message: discord.Message) -> dict[str, Any] | None:
        """
        Process incoming Discord message and extract metadata

        Args:
            message: Discord message object

        Returns:
            Dictionary containing processed message data or None if ignored
        """
        processing_start = datetime.now()

        # Prevent duplicate processing
        try:
            if hasattr(message.created_at, "timestamp") and callable(
                getattr(message.created_at, "timestamp", None)
            ):
                timestamp = message.created_at.timestamp()
            else:
                timestamp = 0
        except (AttributeError, TypeError):
            timestamp = 0

        try:
            timestamp_int = int(timestamp)
        except (ValueError, TypeError):
            timestamp_int = 0

        message_key = f"{message.id}_{message.channel.id}_{timestamp_int}"

        if message_key in self._processed_messages:
            self.logger.debug(
                f"Message {message.id} already processed, skipping duplicate processing",
                message_key=message_key,
            )
            return None

        # Mark message as processed at start
        self._processed_messages.add(message_key)

        # Log processed message tracking
        self.logger.debug(
            "Added message to processed set",
            message_key=message_key,
            total_processed=len(self._processed_messages),
        )

        # メモリ管理：処理済みメッセージ数が上限を超えた場合、古いものを削除
        if len(self._processed_messages) > self._max_processed_messages:
            # セットから最初の 100 個を削除（ FIFO 的な動作）
            old_messages = list(self._processed_messages)[:100]
            for old_msg_id in old_messages:
                self._processed_messages.discard(old_msg_id)
            self.logger.debug(
                f"Cleaned up {len(old_messages)} old processed message IDs"
            )

        # Log channel monitoring check
        self.logger.debug(
            f"Processing message for channel {message.channel.id} (#{getattr(message.channel, 'name', 'unknown')})"
        )

        # Skip bot messages (but log what's happening for debugging)
        # Allow processing bot messages with TEST: or debug prefix
        if message.author.bot and not (
            message.content.startswith("🔧") or message.content.startswith("TEST:")
        ):
            self.logger.debug(
                f"Skipping bot message from {message.author} (bot={message.author.bot})"
            )
            # Remove from processed set when skipping bot messages
            self._processed_messages.discard(message_key)
            return None
        elif message.author.bot and (
            message.content.startswith("🔧") or message.content.startswith("TEST:")
        ):
            content_preview = (
                str(message.content)[:50]
                if hasattr(message.content, "__getitem__")
                else str(message.content)
            )
            self.logger.debug(
                f"Processing bot message for testing - from {message.author} (content preview: {content_preview}...)"
            )

        # Check if channel is monitored
        is_monitored = self.channel_config.is_monitored_channel(message.channel.id)
        self.logger.debug(
            f"Channel monitoring check: {message.channel.id} = {is_monitored}"
        )
        try:
            channels_info = (
                list(self.channel_config.channels.keys())
                if hasattr(self.channel_config, "channels")
                else []
            )
            self.logger.debug(f"Available channels: {channels_info}")
        except Exception as e:
            self.logger.debug(f"Could not list channels: {e}")

        # Force processing memo channel even if not properly discovered
        channel_name = getattr(message.channel, "name", "unknown").lower()
        if not is_monitored:
            if channel_name == "memo":
                self.logger.warning(
                    f"Channel #{channel_name} not in discovered channels, but forcing processing for memo channel"
                )
                # Continue processing anyway
            else:
                self.logger.warning(
                    f"Channel {message.channel.id} (#{channel_name}) is not monitored. Skipping processing."
                )
                # Remove from processed set when skipping unmonitored channels
                self._processed_messages.discard(message_key)
                return None

        channel_info = self.channel_config.get_channel_info(message.channel.id)

        # Record message processing for monitoring
        if hasattr(self, "system_metrics"):
            self.system_metrics.record_message_processed()

        self.logger.info(
            "Processing message",
            channel_id=message.channel.id,
            channel_name=channel_info.name,
            category=channel_info.category.value,
            author=str(message.author),
            message_id=message.id,
        )

        # Extract comprehensive metadata using the message processor
        metadata = self.message_processor.extract_metadata(message)

        # Process audio first, then AI processing
        # Initial AI processing result is None
        ai_result: AIProcessingResult | None = None

        # Combine with channel information (初期状態)
        message_data = {
            "metadata": metadata,
            "ai_processing": None,  # 初期状態では None
            "channel_info": {
                "name": channel_info.name,
                "category": channel_info.category.value,
                "description": channel_info.description,
            },
            "processing_timestamp": datetime.now().isoformat(),
            "status": "success",
            "message_id": message.id,
            "processed_content": metadata["content"]["cleaned_content"]
            if "content" in metadata
            else message.content,
        }

        # Process audio first and integrate transcription results
        attachments_data: Any = metadata.get("attachments", {})
        has_audio = (
            attachments_data.get("has_audio", False)
            if isinstance(attachments_data, dict)
            else False
        )

        # 添付ファイルがある場合は音声ファイルかどうかチェック
        if not has_audio and message.attachments:
            for attachment in message.attachments:
                if any(
                    attachment.filename.lower().endswith(ext)
                    for ext in [".ogg", ".mp3", ".wav", ".flac", ".m4a", ".webm"]
                ):
                    has_audio = True
                    break

        self.logger.debug(
            f"Audio detection - has_audio={has_audio}, attachments_count={len(message.attachments)}, attachments_data_type={type(attachments_data)}"
        )

        # Audio processing is handled centrally in _handle_capture_message
        # Don't process audio here to prevent duplicate notifications
        if has_audio and message.attachments:
            self.logger.debug(
                "Audio detected - will be processed in _handle_capture_message"
            )

        # メタデータを更新
        metadata = cast(MessageMetadata, message_data.get("metadata", metadata))

        # Execute AI processing after audio processing (including transcription results)
        final_content = ""
        original_content = message.content if message.content else ""
        transcription_content = ""

        # 文字起こし結果があれば取得
        if "content" in metadata and "raw_content" in metadata["content"]:
            final_content = metadata["content"]["raw_content"]
            # 音声文字起こし部分を抽出
            if "🎤 音声文字起こし" in final_content:
                transcription_content = final_content.split("🎤 音声文字起こし")[
                    -1
                ].strip()
        else:
            final_content = original_content

        content_length = len(final_content.strip())
        self.logger.debug(
            f"Checking AI processing conditions - final_content_length={content_length}, original_content_length={len(original_content)}, has_transcription={bool(transcription_content)}"
        )

        # AI 処理の実行（音声文字起こし結果も含めて）
        if final_content and content_length > 5:
            try:
                result = await self.ai_processor.process_text(
                    text=final_content, message_id=message.id
                )
                ai_result = result if isinstance(result, AIProcessingResult) else None

                # Record AI request metrics
                if hasattr(self, "system_metrics"):
                    processing_time = (
                        datetime.now() - processing_start
                    ).total_seconds() * 1000
                    self.system_metrics.record_ai_request(True, int(processing_time))

                if hasattr(self, "api_usage_monitor"):
                    self.api_usage_monitor.track_gemini_usage()

                self.logger.info(
                    "AI processing completed",
                    message_id=message.id,
                    has_summary=getattr(ai_result, "summary", None) is not None,
                    has_tags=getattr(ai_result, "tags", None) is not None,
                    has_category=getattr(ai_result, "category", None) is not None,
                    total_time_ms=getattr(ai_result, "total_processing_time_ms", 0),
                    processed_transcription=bool(transcription_content),
                )

            except Exception as e:
                # Record AI request failure
                if hasattr(self, "system_metrics"):
                    processing_time = (
                        datetime.now() - processing_start
                    ).total_seconds() * 1000
                    self.system_metrics.record_ai_request(False, int(processing_time))
                    self.system_metrics.record_error("ai_processing", str(e))

                if hasattr(self, "api_usage_monitor"):
                    self.api_usage_monitor.track_gemini_usage(success=False)

                self.logger.error(
                    "AI processing failed",
                    message_id=message.id,
                    error=str(e),
                    exc_info=True,
                )

        # AI 処理結果をメッセージデータに更新
        message_data["ai_processing"] = ai_result.model_dump() if ai_result else None

        # Check for duplicate note creation before processing
        if message_key in getattr(self, "_creating_notes", set()):
            self.logger.warning(
                f"Duplicate creation detected: Message {message.id} is already being processed for note creation"
            )
            return message_data

        # ノート作成中のメッセージを記録
        if not hasattr(self, "_creating_notes"):
            self._creating_notes = set()
        self._creating_notes.add(message_key)

        try:
            # Route message based on channel category
            self.logger.debug(
                f"Routing message to category handler - category={channel_info.category.value}"
            )
            await self._route_message_by_category(
                message_data, channel_info.category, message
            )

            self.logger.debug(
                f"Message processing completed successfully for message {message.id}"
            )

        finally:
            # ノート作成完了後にセットから削除
            self._creating_notes.discard(message_key)

        return message_data

    async def _update_feedback_message(
        self, message: discord.Message | None, content: str
    ) -> None:
        """フィードバックメッセージを更新"""
        if not message:
            return

        try:
            await message.edit(content=content)
        except Exception as e:
            self.logger.warning(
                "Failed to update feedback message", error=str(e), message_id=message.id
            )

    async def _route_message_by_category(
        self,
        message_data: dict[str, Any],
        category: ChannelCategory,
        original_message: discord.Message | None = None,
    ) -> None:
        """Route message processing based on channel category"""

        if category == ChannelCategory.CAPTURE:
            await self._handle_capture_message(message_data, original_message)
        elif category == ChannelCategory.SYSTEM:
            await self._handle_system_message(message_data)
        else:
            self.logger.warning("Unknown channel category", category=category.value)

    async def _handle_capture_message(
        self,
        message_data: dict[str, Any],
        original_message: discord.Message | None = None,
    ) -> None:
        """Handle messages from capture channels"""
        self.logger.debug("_handle_capture_message called")
        self.logger.info(
            "Handling capture message",
            channel_name=message_data["channel_info"]["name"],
        )

        # Process audio attachments before note generation to include transcription
        from src.bot.channel_config import ChannelCategory, ChannelInfo

        channel_info_dict = message_data.get("channel_info", {})
        if channel_info_dict and original_message:
            # ChannelInfo オブジェクトを再構築
            category_str = channel_info_dict.get("category", "capture")
            category = (
                ChannelCategory.CAPTURE
                if category_str == "capture"
                else ChannelCategory.SYSTEM
            )

            channel_info = ChannelInfo(
                id=original_message.channel.id,
                name=channel_info_dict.get("name", "unknown"),
                category=category,
                description=channel_info_dict.get("description", ""),
            )

            # 音声処理を先に実行して message_data を更新
            await self._handle_audio_attachments(
                message_data, channel_info, original_message
            )
            await self._handle_document_attachments(
                message_data, channel_info, original_message
            )

        # Execute AI analysis after audio processing
        ai_processing = message_data.get("ai_processing")

        # 音声処理が完了した後、最終コンテンツで AI 処理を実行
        if not ai_processing:
            metadata = message_data.get("metadata", {})
            content_info = metadata.get("content", {})
            final_content = ""

            # 文字起こし結果があれば取得（ raw_content または audio_transcription_data から）
            if "raw_content" in content_info:
                final_content = content_info["raw_content"]

            # Handle case where audio data is only saved in metadata
            audio_data = content_info.get("audio_transcription_data")
            if audio_data and not final_content.strip():
                final_content = audio_data["transcript"]
                self.logger.debug(
                    "Using audio transcript for AI processing",
                    transcript_length=len(final_content),
                )

            content_length = len(final_content.strip())
            self.logger.debug(
                f"Post-audio AI processing check - final_content_length={content_length}, has_transcription={bool('🎤 音声文字起こし' in final_content)}"
            )

            # 文字起こし結果がある場合に AI 処理を実行
            if final_content and content_length > 5:
                try:
                    result = await self.ai_processor.process_text(
                        text=final_content,
                        message_id=original_message.id if original_message else 0,
                    )
                    if isinstance(result, AIProcessingResult):
                        # AI 処理結果をメッセージデータに追加
                        message_data["ai_processing"] = result.model_dump()
                        ai_processing = message_data["ai_processing"]

                        self.logger.debug(
                            "Post-audio AI processing completed",
                            has_summary=getattr(result, "summary", None) is not None,
                            has_tags=getattr(result, "tags", None) is not None,
                            has_category=getattr(result, "category", None) is not None,
                        )

                except Exception as e:
                    self.logger.error(
                        "Post-audio AI processing failed",
                        error=str(e),
                        exc_info=True,
                    )

        if ai_processing:
            self.logger.info(
                "Processing capture message with AI results",
                has_summary=ai_processing.get("summary") is not None,
                has_tags=ai_processing.get("tags") is not None,
                has_category=ai_processing.get("category") is not None,
            )

            # 要約とタグをログ出力（デバッグ用）
            if ai_processing.get("summary"):
                summary_text = ai_processing["summary"]["summary"]
                self.logger.debug(
                    "Generated summary",
                    summary=(
                        summary_text[:100] + "..."
                        if len(summary_text) > 100
                        else summary_text
                    ),
                )

            if ai_processing.get("tags"):
                tags = ai_processing["tags"]["tags"]
                self.logger.debug("Generated tags", tags=tags)

            if ai_processing.get("category"):
                category = ai_processing["category"]["category"]
                confidence = ai_processing["category"]["confidence_score"]
                self.logger.debug(
                    "Generated category", category=category, confidence=confidence
                )

        # AI 処理結果を AIProcessingResult オブジェクトに変換
        ai_result: AIProcessingResult | None = None
        if ai_processing:
            try:
                ai_result = AIProcessingResult.model_validate(ai_processing)
            except Exception as e:
                self.logger.warning(
                    "Failed to validate AI processing result - continuing with fallback",
                    error=str(e),
                    ai_processing_keys=list(ai_processing.keys())
                    if isinstance(ai_processing, dict)
                    else "not_dict",
                )
                # AI 処理失敗時でも処理を継続するため、 ai_result は None のままにする

        # Generate and save Obsidian note (with GitHub direct sync integration)
        self.logger.debug("About to call _handle_obsidian_note_creation")
        await self._handle_obsidian_note_creation(ai_result, message_data)
        self.logger.debug("_handle_obsidian_note_creation completed")

        # Daily Note Integration disabled to prevent duplicates
        # await self._handle_daily_note_integration(message_data, channel_info)
        self.logger.debug("Daily Note Integration disabled to prevent duplicates")

        # Lifelog auto-detection and generation
        await self._handle_lifelog_auto_detection(message_data, original_message)

    async def _handle_obsidian_note_creation(
        self,
        ai_result: AIProcessingResult | None,
        message_data: dict[str, Any],
    ) -> None:
        """Enhanced note creation with comprehensive YAML frontmatter: GitHub Direct + Local Fallback + Auto Sync"""
        self.logger.info(
            "Enhanced note creation with comprehensive YAML frontmatter: Starting note creation"
        )

        try:
            import base64
            import os
            from datetime import datetime, timedelta, timezone
            from pathlib import Path

            import aiofiles
            import aiohttp

            from src.obsidian.template_system.yaml_generator import (
                YAMLFrontmatterGenerator,
            )

            # 日本時間で統一処理
            jst = timezone(timedelta(hours=9))
            now_jst = datetime.now(jst)
            timestamp = now_jst.strftime("%Y-%m-%d-%H%M%S")

            # メッセージ内容を取得
            raw_content = (
                message_data.get("metadata", {})
                .get("content", {})
                .get("raw_content", "新しいメモ")
            )

            # Integrate audio data if available (centralized management)
            content_info = message_data.get("metadata", {}).get("content", {})
            audio_data = content_info.get("audio_transcription_data")

            if audio_data and "🎤 音声文字起こし" not in raw_content:
                # Add audio section
                audio_section = (
                    f"\n\n## 🎤 音声文字起こし\n\n{audio_data['transcript']}"
                )
                if audio_data.get("confidence", 0) > 0.0:
                    audio_section += f"\n\n**信頼度**: {audio_data['confidence']:.2f} ({audio_data['confidence_level']})"
                if audio_data.get("fallback_used"):
                    audio_section += f"\n\n**注意**: {audio_data['fallback_reason']}"
                    if audio_data.get("saved_file_path"):
                        audio_section += (
                            f"\n**保存先**: `{audio_data['saved_file_path']}`"
                        )

                raw_content += audio_section
                self.logger.debug(
                    "Audio section added from metadata",
                    transcript_length=len(audio_data["transcript"]),
                )

            # Inline duplicate removal (reliable operation)
            content = raw_content
            audio_marker = "## 🎤 音声文字起こし"
            audio_count_before = content.count(audio_marker)

            self.logger.debug(
                f"Starting deduplication. Found {audio_count_before} audio sections"
            )

            if audio_count_before > 1:
                # シンプルな文字列置換アプローチ
                lines = content.split("\n")
                result_lines = []
                audio_section_encountered = False
                skip_mode = False

                for line in lines:
                    if line.strip() == audio_marker.strip():
                        if not audio_section_encountered:
                            # First audio section - keep
                            audio_section_encountered = True
                            result_lines.append(line)
                            self.logger.debug("Keeping first audio section")
                        else:
                            # Duplicate audio section - start skipping
                            skip_mode = True
                            self.logger.debug("Skipping duplicate audio section")
                            continue
                    elif line.startswith("##") and skip_mode:
                        # 新しいセクションが始まったらスキップ終了
                        skip_mode = False
                        result_lines.append(line)
                    elif not skip_mode:
                        # スキップモードでない場合は追加
                        result_lines.append(line)

                content = "\n".join(result_lines)
                audio_count_after = content.count(audio_marker)
                self.logger.debug(
                    f"Deduplication completed. {audio_count_before} -> {audio_count_after} audio sections"
                )
            else:
                self.logger.debug("No duplicates found")

            # Clean up markdown symbols and audio-related text for title generation
            title_preview = content[:30].replace("\n", " ").strip()
            # Remove markdown header symbols (#) and asterisks (*)
            import re

            title_preview = re.sub(
                r"^[#\s*]+", "", title_preview
            )  # Remove leading # and *
            title_preview = re.sub(
                r"[#*]+$", "", title_preview
            )  # Remove trailing # and *
            title_preview = re.sub(
                r"#{1,6}\s*", "", title_preview
            )  # Remove intermediate ##
            # Remove audio-related text
            title_preview = re.sub(
                r"🎤\s*音声文字起こし\s*", "", title_preview
            )  # Remove 🎤 音声文字起こし
            title_preview = re.sub(
                r"音声文字起こし\s*", "", title_preview
            )  # Remove 音声文字起こし
            title_preview = title_preview.strip()

            # AI 分析に基づくカテゴリ決定（シンプル化）
            category = "memo"
            category_folder = "00_Inbox"
            if ai_result and ai_result.category:
                cat_val = ai_result.category.category.value
                if "task" in cat_val.lower() or "タスク" in cat_val:
                    category = "task"
                    category_folder = "02_Tasks"
                elif (
                    "finance" in cat_val.lower()
                    or "金融" in cat_val
                    or "お金" in cat_val
                ):
                    category = "finance"
                    category_folder = "20_Finance"
                elif "health" in cat_val.lower() or "健康" in cat_val:
                    category = "health"
                    category_folder = "21_Health"
                elif "idea" in cat_val.lower() or "アイデア" in cat_val:
                    category = "idea"
                    category_folder = "03_Ideas"
                elif (
                    "knowledge" in cat_val.lower()
                    or "学習" in cat_val
                    or "知識" in cat_val
                ):
                    category = "knowledge"
                    category_folder = "10_Knowledge"
                elif "project" in cat_val.lower() or "プロジェクト" in cat_val:
                    category = "project"
                    category_folder = "11_Projects"

            # 安全なファイル名生成
            safe_title = "".join(
                c for c in title_preview if c.isalnum() or c in "-_あ-んア-ン一-龯"
            )[:40]
            filename = f"{timestamp}-{safe_title}.md"
            file_path = f"{category_folder}/{filename}"

            # Use comprehensive YAML frontmatter generator
            yaml_generator = YAMLFrontmatterGenerator()

            # Discord コンテキスト情報の準備
            discord_context = {
                "source": "Discord",
                "channel_name": message_data.get("channel_name", "unknown"),
                "message_id": message_data.get("message_id"),
                "user_id": message_data.get("author_id"),
                "timestamp": now_jst,
            }

            # 音声メモの場合の追加情報
            if message_data.get("attachments"):
                for attachment in message_data["attachments"]:
                    if attachment.get("content_type", "").startswith("audio/"):
                        discord_context["is_voice_memo"] = True
                        discord_context["audio_duration"] = attachment.get(
                            "duration", 0
                        )
                        discord_context["input_method"] = "voice"
                        break

            # Generate comprehensive frontmatter
            yaml_frontmatter = yaml_generator.create_comprehensive_frontmatter(
                title=title_preview,
                content_type=category,
                ai_result=ai_result,
                content=content,
                context=discord_context,
                # 追加のメタデータ
                vault_section=category_folder,
                processing_timestamp=now_jst,
                auto_generated=True,
                data_quality="high" if ai_result else "medium",
            )

            # Generate comprehensive YAML frontmatter markdown content
            markdown_parts = [
                yaml_frontmatter,
                "",  # フロントマター後の空行
                f"# {title_preview}",
                "",
                "## 📝 内容",
                "",
                content,
            ]

            # AI 分析結果がある場合は追加情報を含める
            if ai_result:
                markdown_parts.extend(["", "---", "", "## AI 分析情報", ""])

                if ai_result.category:
                    confidence = getattr(ai_result.category, "confidence_score", 0)
                    markdown_parts.append(
                        f"- **カテゴリ**: {ai_result.category.category.value} ({confidence:.0%})"
                    )

                if ai_result.summary:
                    markdown_parts.extend(
                        [
                            f"- **要約**: {ai_result.summary.summary}",
                        ]
                    )

                if hasattr(ai_result, "tags") and ai_result.tags:
                    # TagsResult オブジェクトの場合、 tags.tags でアクセス
                    if hasattr(ai_result.tags, "tags"):
                        tags_list: list[str] = ai_result.tags.tags
                    else:
                        # TagResult の場合は適切に変換
                        if hasattr(ai_result.tags, "__iter__") and not isinstance(
                            ai_result.tags, str
                        ):
                            # TagResult の iteration を安全に処理
                            try:
                                tags_list = [str(tag) for tag in ai_result.tags]
                            except (TypeError, AttributeError):
                                tags_list = [str(ai_result.tags)]
                        else:
                            tags_list = [str(ai_result.tags)]

                    # タグリストを文字列に変換（各要素を文字列として処理）
                    if isinstance(tags_list, list | tuple):
                        tags_str = ", ".join(str(tag) for tag in tags_list)
                    else:
                        tags_str = str(tags_list)

                    markdown_parts.append(f"- **推奨タグ**: {tags_str}")

            # 最終的なクリーンなマークダウン
            clean_markdown = "\n".join(markdown_parts)

            self.logger.info(
                "Creating comprehensive YAML frontmatter note",
                file_path=file_path,
                category=category,
                title=title_preview,
                has_ai_analysis=bool(ai_result),
                is_voice_memo=discord_context.get("is_voice_memo", False),
            )

            # GitHub API 失敗フラグ
            github_success = False

            # STEP 1: Try GitHub API
            github_token = os.getenv("GITHUB_TOKEN")
            github_repo = "kenvexar/obsidian-vault-test"  # テストリポジトリに修正

            if github_token and github_repo:
                try:
                    # GitHub API に直接送信
                    headers = {
                        "Authorization": f"token {github_token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "MindBridge-Bot",
                    }

                    url = f"https://api.github.com/repos/{github_repo}/contents/{file_path}"

                    payload = {
                        "message": f"Enhanced YAML: {title_preview}",
                        "content": base64.b64encode(
                            clean_markdown.encode("utf-8")
                        ).decode("utf-8"),
                        "branch": "main",
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.put(
                            url, headers=headers, json=payload
                        ) as response:
                            result_data = await response.json()

                            if response.status == 201:
                                self.logger.info(
                                    "Enhanced YAML frontmatter note created on GitHub",
                                    file_path=file_path,
                                    sha=result_data.get("content", {}).get("sha"),
                                )
                                github_success = True
                            else:
                                self.logger.warning(
                                    "GitHub creation failed, falling back to local",
                                    status=response.status,
                                    response=result_data,
                                )

                except Exception as e:
                    self.logger.warning(
                        "GitHub API error, falling back to local",
                        error=str(e),
                    )
            else:
                self.logger.info("No GitHub credentials, using local fallback")

            # STEP 2: Local file creation fallback
            local_file_created = False
            if not github_success:
                try:
                    # ローカル vault パスの設定
                    vault_path = Path("/app/vault")

                    local_folder = vault_path / category_folder

                    # フォルダが存在しない場合は作成
                    local_folder.mkdir(parents=True, exist_ok=True)

                    local_file_path = local_folder / filename

                    # ローカルファイルに保存
                    async with aiofiles.open(
                        local_file_path, "w", encoding="utf-8"
                    ) as f:
                        await f.write(clean_markdown)

                    self.logger.info(
                        "Enhanced YAML frontmatter note created locally",
                        local_path=str(local_file_path),
                        category=category,
                        folder=category_folder,
                    )
                    local_file_created = True

                except Exception as e:
                    self.logger.error(
                        "Local fallback also failed",
                        error=str(e),
                        exc_info=True,
                    )

            # STEP 3: GitHub sync (only if local file was created)
            if local_file_created:
                try:
                    from src.obsidian.github_sync import GitHubObsidianSync

                    self.logger.info("Starting automatic GitHub sync...")

                    # Create GitHub sync instance
                    sync_client = GitHubObsidianSync()

                    # Check configuration
                    if not sync_client.is_configured:
                        self.logger.warning(
                            "GitHub sync not configured, skipping auto sync"
                        )
                    else:
                        # Execute auto sync
                        sync_success = await sync_client.sync_to_github(
                            commit_message=f"Auto-sync Enhanced YAML: {title_preview}"
                        )

                        if sync_success:
                            self.logger.info("Auto GitHub sync completed")
                        else:
                            self.logger.warning("GitHub auto sync failed")

                except Exception as e:
                    self.logger.warning(
                        "GitHub auto sync error (note still saved locally)",
                        error=str(e),
                    )

        except Exception as e:
            self.logger.error(
                "Enhanced YAML note creation completely failed",
                error=str(e),
                exc_info=True,
            )

    def _deduplicate_audio_sections(self, content: str) -> str:
        """Remove duplicate audio sections using simple string processing approach"""
        try:
            if not content or "🎤 音声文字起こし" not in content:
                self.logger.debug("No audio sections found in content")
                return content

            # Count audio sections
            audio_marker = "## 🎤 音声文字起こし"
            section_count = content.count(audio_marker)

            self.logger.debug(f"Found {section_count} audio sections in content")

            if section_count <= 1:
                self.logger.debug("No duplicates to remove")
                return content

            # シンプルなアプローチ：最初の音声セクションの位置を見つけて、それ以降の同じセクションを削除
            lines = content.split("\n")
            result_lines = []
            audio_section_found = False
            skip_until_next_section = False

            i = 0
            while i < len(lines):
                line = lines[i]

                # 音声セクションの開始を検出
                if line.strip() == audio_marker.strip():
                    if not audio_section_found:
                        # First audio section - keep
                        audio_section_found = True
                        result_lines.append(line)
                        self.logger.debug("Keeping first audio section")
                    else:
                        # Subsequent audio sections - start skipping
                        skip_until_next_section = True
                        self.logger.debug("Skipping duplicate audio section")
                        i += 1
                        continue

                # 他のセクション（## で始まる）が来たらスキップ終了
                elif line.startswith("##") and skip_until_next_section:
                    skip_until_next_section = False
                    result_lines.append(line)

                # スキップモードでない場合は行を追加
                elif not skip_until_next_section:
                    result_lines.append(line)

                i += 1

            result_content = "\n".join(result_lines)
            final_count = result_content.count(audio_marker)

            self.logger.debug(
                f"Audio deduplication completed: {section_count} -> {final_count} sections"
            )

            return result_content

        except Exception as e:
            self.logger.error(f"Error in audio deduplication: {e}", exc_info=True)
            # Return original content on error
            return content

    def _remove_bot_attribution_messages(self, content: str) -> str:
        """自動生成メッセージを除去する"""
        import re

        # 日本語と英語の自動生成メッセージを削除
        patterns_to_remove = [
            r"\*Created by Discord-Obsidian Memo Bot\*[。\s]*",
            r"^---\s*\*Created by Discord-Obsidian Memo Bot\*\s*$",
            r"^\*Created by Discord-Obsidian Memo Bot\*\s*$",
            r".*Discord-Obsidian.*Memo.*Bot.*自動生成.*",
            r".*自動生成.*Discord-Obsidian.*Memo.*Bot.*",
        ]

        for pattern in patterns_to_remove:
            content = re.sub(pattern, "", content, flags=re.MULTILINE | re.IGNORECASE)

        # 空行の連続を整理
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)
        content = content.strip()

        return content

    async def _handle_github_direct_sync(
        self, ai_result: AIProcessingResult | None, note, saved_file_path
    ) -> None:
        """Execute GitHub direct sync in Cloud Run environment - sync local note content as-is"""
        self.logger.debug(
            "_handle_github_direct_sync called",
            note_title=getattr(note, "title", "unknown"),
            saved_file_path=str(saved_file_path),
            has_ai_result=ai_result is not None,
        )
        try:
            from src.obsidian.github_direct import GitHubDirectClient

            # GitHub Direct Client を初期化
            github_client = GitHubDirectClient()

            self.logger.debug(
                "GitHubDirectClient initialized",
                is_configured=github_client.is_configured,
                has_token=bool(github_client.github_token),
                has_repo_url=bool(github_client.github_repo_url),
                owner=github_client.owner,
                repo=github_client.repo,
            )

            if not github_client.is_configured:
                self.logger.warning(
                    "GitHub direct sync not configured - file saved locally only"
                )
                return

            # AI 結果からカテゴリフォルダーを決定
            category = "Memos"  # デフォルト
            if ai_result and ai_result.category:
                category = github_client.get_category_folder(
                    ai_result.category.category
                )

            # ファイル名とパスを生成（重複を避けるため、ローカルと同じ名前を使用）
            from datetime import timedelta, timezone

            jst = timezone(timedelta(hours=9))
            timestamp = datetime.now(jst).strftime("%Y-%m-%d-%H%M%S")

            # ノートのタイトルからファイル名を生成
            title = note.title.replace(" ", "-")
            safe_title = "".join(c for c in title if c.isalnum() or c in "-_")[:50]
            filename = f"{timestamp}-{safe_title}.md"

            file_path = f"{category}/{filename}"

            # ローカルノートの完全な内容を GitHub に同期（重複作成を避ける）
            full_markdown_content = note.to_markdown()

            self.logger.info(
                "Syncing existing local note to GitHub",
                category=category,
                file_path=file_path,
                content_length=len(full_markdown_content),
                note_title=note.title,
            )

            # Sync local note content to GitHub as-is
            result = await github_client.create_or_update_file(
                file_path=file_path,
                content=full_markdown_content,
                commit_message=f"Auto-sync: {note.title} from Discord",
            )

            if result:
                self.logger.info(
                    "GitHub direct sync completed successfully",
                    file_path=file_path,
                    commit_sha=result.get("content", {}).get("sha"),
                    category=category,
                )
            else:
                self.logger.warning(
                    "GitHub direct sync failed",
                    file_path=file_path,
                    reason="create_or_update_file returned None",
                )

        except ImportError:
            self.logger.warning(
                "GitHubDirectClient not available - falling back to traditional sync"
            )
        except Exception as github_error:
            self.logger.error(
                "GitHub direct sync failed with error",
                file_path=str(saved_file_path),
                error=str(github_error),
                exc_info=True,
            )

    # Removed methods: functionality integrated into _handle_obsidian_note_creation

    def _extract_transcription_text(self, cleaned_content: str) -> str:
        """音声転写テキストを抽出"""
        if "🎤 音声文字起こし" not in cleaned_content:
            return ""

        import re

        pattern = r"🎤 音声文字起こし\s*(.*?)\s*\*\*信頼度\*\*"
        match = re.search(pattern, cleaned_content, re.DOTALL)
        return match.group(1).strip() if match else ""

    def _create_transcription_summary(self, transcription_text: str) -> str:
        """転写テキストの要約を作成"""
        if len(transcription_text) <= 30:
            return transcription_text

        summary = transcription_text[:30].rsplit("。", 1)[0]
        return summary + "..." if not summary.endswith("。") else summary

    def _generate_audio_title(
        self, content_info: dict[str, Any], channel_name: str
    ) -> str | None:
        """音声メッセージのタイトルを生成"""
        cleaned_content = content_info.get("cleaned_content", "")
        transcription_text = self._extract_transcription_text(cleaned_content)

        if transcription_text:
            summary = self._create_transcription_summary(transcription_text)
            return f"🎤 音声メモ: {summary} - #{channel_name}"

        return None

    def _generate_ai_based_title(
        self, ai_result: AIProcessingResult | None, channel_name: str
    ) -> str | None:
        """AI 結果に基づくタイトルを生成"""
        if not ai_result:
            return None

        # AI 要約がある場合
        if ai_result.summary:
            summary_text = ai_result.summary.summary
            if len(summary_text) > 40:
                summary_text = summary_text[:40] + "..."
            return f"📝 {summary_text} - #{channel_name}"

        # AI 分類がある場合
        if ai_result.category:
            category = ai_result.category.category
            return f"📝 {category}メモ - #{channel_name}"

        return None

    def _generate_text_based_title(
        self, content_info: dict[str, Any], channel_name: str
    ) -> str | None:
        """テキストコンテンツに基づくタイトルを生成"""
        raw_content = content_info.get("raw_content", "").strip()
        if raw_content and len(raw_content) > 10:
            return f"📝 {raw_content} - #{channel_name}"
        return None

    def _get_fallback_title(
        self, message_data: dict[str, Any], error: Exception
    ) -> str:
        """エラー時のフォールバックタイトル"""
        self.logger.warning(
            "Failed to generate activity log title, using fallback", error=str(error)
        )
        channel_name = message_data.get("channel_info", {}).get("name", "unknown")
        return f"📝 メモ - #{channel_name}"

    def _generate_activity_log_title(
        self,
        message_data: dict[str, Any],
        ai_result: AIProcessingResult | None,
        note: Any,
    ) -> str:
        """Activity Log エントリの意味のあるタイトルを生成"""
        try:
            content_info = message_data.get("metadata", {}).get("content", {})
            channel_name = message_data["channel_info"]["name"]

            # 音声メッセージの処理
            if content_info.get("has_audio_transcription", False):
                if title := self._generate_audio_title(content_info, channel_name):
                    return title

            # AI 結果に基づくタイトル生成
            if title := self._generate_ai_based_title(ai_result, channel_name):
                return title

            # テキストコンテンツに基づくタイトル生成
            if title := self._generate_text_based_title(content_info, channel_name):
                return title

            # フォールバック
            return f"📝 {note.title} - #{channel_name}"

        except Exception as e:
            return self._get_fallback_title(message_data, e)

    async def _organize_note_by_ai_category(self, note, ai_result) -> None:
        """AI 分類結果に基づいてノートを適切なフォルダに移動"""
        if not ai_result or not ai_result.category:
            self.logger.debug(
                "No AI category found, keeping note in current location",
                note_path=str(note.file_path),
            )
            return

        try:
            from src.obsidian.models import FolderMapping

            # AI 分類結果から目標フォルダを決定
            category = ai_result.category.category
            subcategory = getattr(ai_result.category, "subcategory", None)

            target_folder = FolderMapping.get_folder_for_category(category, subcategory)

            # 現在のフォルダパスを確認
            if self.obsidian_manager is None:
                self.logger.warning("Obsidian manager not available for organization")
                return

            current_folder = note.file_path.parent
            target_path = self.obsidian_manager.vault_path / target_folder.value

            # 既に適切なフォルダにある場合はスキップ
            if current_folder == target_path:
                self.logger.debug(
                    "Note already in correct folder",
                    current_folder=str(current_folder),
                    target_folder=target_folder.value,
                )
                # obsidian_folder メタデータを正しい値に更新
                note.frontmatter.obsidian_folder = target_folder.value
                await self.obsidian_manager.update_note(note.file_path, note)
                return

            # ファイル移動を実行
            new_file_path = target_path / note.file_path.name

            # 移動先ディレクトリを作成
            target_path.mkdir(parents=True, exist_ok=True)

            # ファイルを移動
            note.file_path.rename(new_file_path)

            # ノートオブジェクトのパスとメタデータを更新
            note.file_path = new_file_path
            note.frontmatter.obsidian_folder = target_folder.value
            note.frontmatter.modified = datetime.now().isoformat()

            # 階層構造メタデータの追加
            note.frontmatter.vault_hierarchy = target_folder.value
            if subcategory:
                note.frontmatter.organization_level = "subcategory"
            else:
                note.frontmatter.organization_level = "category"

            # フロントマターを更新
            await self.obsidian_manager.update_note(note.file_path, note)

            self.logger.info(
                "Note organized by AI category",
                note_title=note.title,
                from_folder=str(
                    current_folder.relative_to(self.obsidian_manager.vault_path)
                ),
                to_folder=target_folder.value,
                category=category,
                subcategory=subcategory,
                confidence=ai_result.category.confidence_score,
            )

        except Exception as e:
            self.logger.error(
                "Failed to organize note by AI category",
                note_title=note.title,
                category=category if "category" in locals() else "unknown",
                error=str(e),
                exc_info=True,
            )

    async def _handle_daily_note_integration(
        self, message_data: dict[str, Any], channel_info: Any
    ) -> None:
        """デイリーノート統合の処理"""
        try:
            from src.config import get_settings

            settings = get_settings()

            channel_id = channel_info.id

            # Activity Log チャンネルの処理
            if (
                self.daily_integration
                and hasattr(settings, "channel_activity_log")
                and settings.channel_activity_log
                and channel_id == settings.channel_activity_log
            ):
                success = await self.daily_integration.add_activity_log_entry(
                    message_data
                )
                if success:
                    self.logger.info("Activity log entry added to daily note")
                else:
                    self.logger.warning("Failed to add activity log entry")

            # Daily Tasks チャンネルの処理
            elif (
                self.daily_integration
                and hasattr(settings, "channel_daily_tasks")
                and settings.channel_daily_tasks
                and channel_id == settings.channel_daily_tasks
            ):
                success = await self.daily_integration.add_daily_task_entry(
                    message_data
                )
                if success:
                    self.logger.info("Daily task entry added to daily note")
                else:
                    self.logger.warning("Failed to add daily task entry")

        except Exception as e:
            self.logger.error(
                "Error in daily note integration",
                channel_name=channel_info.name,
                error=str(e),
                exc_info=True,
            )

    async def _handle_audio_attachments(
        self,
        message_data: dict[str, Any],
        channel_info: Any,
        original_message: discord.Message | None = None,
    ) -> None:
        """音声添付ファイルの処理（リアルタイムフィードバック付き）"""
        try:
            metadata = message_data.get("metadata", {})
            attachments = metadata.get("attachments", [])

            # Log attachment information
            self.logger.debug(
                f"_handle_audio_attachments called with {len(attachments)} total attachments"
            )

            for i, att in enumerate(attachments):
                self.logger.debug(
                    f"Attachment {i}: filename={att.get('filename', 'N/A')}, "
                    f"file_category={att.get('file_category', 'N/A')}, "
                    f"content_type={att.get('content_type', 'N/A')}, "
                    f"extension={att.get('file_extension', 'N/A')}"
                )

            # 音声ファイルをフィルタリング
            audio_attachments = [
                att
                for att in attachments
                if att.get("file_category") == "audio"
                or (
                    self.speech_processor
                    and self.speech_processor.is_audio_file(att.get("filename", ""))
                )
            ]

            self.logger.debug(
                f"Found {len(audio_attachments)} audio attachments after filtering"
            )

            if not audio_attachments:
                self.logger.debug("No audio attachments found, returning early")
                return

            self.logger.info(
                "Processing audio attachments",
                count=len(audio_attachments),
                channel=channel_info.name,
            )

            for attachment in audio_attachments:
                self.logger.debug(
                    f"Processing audio attachment: {attachment.get('filename', 'N/A')}"
                )

                # 個別音声処理を実行（エラーハンドリング強化）
                try:
                    self.logger.info(
                        f"About to call _process_single_audio_attachment for {attachment.get('filename', 'N/A')}"
                    )
                    await self._process_single_audio_attachment(
                        attachment, message_data, channel_info, original_message
                    )
                    self.logger.info(
                        f"Completed _process_single_audio_attachment for {attachment.get('filename', 'N/A')}"
                    )
                except Exception as e:
                    self.logger.error(
                        "Error in _process_single_audio_attachment",
                        filename=attachment.get("filename", "N/A"),
                        error=str(e),
                        exc_info=True,
                    )
                    # 個別エラーでも他の音声ファイル処理を継続

        except Exception as e:
            self.logger.error(
                "Error processing audio attachments",
                channel_name=channel_info.name,
                error=str(e),
                exc_info=True,
            )

    async def _handle_document_attachments(
        self,
        message_data: dict[str, Any],
        channel_info: Any,
        original_message: Any,
    ) -> None:
        """Handle document, image, and other file attachments"""

        try:
            attachments = message_data.get("attachments", [])
            if not attachments:
                return

            # Filter out audio attachments (already handled)
            audio_extensions = {".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".wma"}
            document_attachments = [
                att
                for att in attachments
                if not any(
                    att.get("filename", "").lower().endswith(ext)
                    for ext in audio_extensions
                )
            ]

            if not document_attachments:
                return

            self.logger.info(
                f"Processing {len(document_attachments)} document attachment(s)",
                channel=channel_info.name if channel_info else "unknown",
            )

            for attachment in document_attachments:
                filename = attachment.get("filename", "unknown_file")
                file_size = attachment.get("size", 0)

                # Add attachment info to message data for obsidian integration
                if "file_attachments" not in message_data:
                    message_data["file_attachments"] = []

                message_data["file_attachments"].append(
                    {
                        "filename": filename,
                        "url": attachment.get("url"),
                        "size": file_size,
                        "type": "document",
                    }
                )

                self.logger.debug(
                    "Added document attachment to processing queue",
                    filename=filename,
                    size=file_size,
                )

        except Exception as e:
            self.logger.error(
                "Failed to handle document attachments",
                error=str(e),
                exc_info=True,
            )

    async def _process_single_audio_attachment(
        self,
        attachment: dict[str, Any],
        message_data: dict[str, Any],
        channel_info: Any,
        original_message: discord.Message | None = None,
    ) -> None:
        """単一の音声添付ファイルを処理（リアルタイムフィードバック付き）"""
        feedback_message = None

        try:
            self.logger.debug(
                f"Starting _process_single_audio_attachment for {attachment.get('filename', 'unknown')}"
            )

            attachment_url = attachment.get("url")
            filename = attachment.get("filename", "audio.mp3")

            if not attachment_url:
                self.logger.warning(
                    "No URL found for audio attachment", filename=filename
                )
                return

            self.logger.debug(f"Audio attachment URL: {attachment_url}")

            # Discord へのリアルタイムフィードバックを開始
            if original_message:
                try:
                    feedback_message = await original_message.reply(
                        f"🎤 音声ファイル `{filename}` の文字起こしを開始します..."
                    )
                    self.logger.debug("Feedback message sent successfully")
                except Exception as e:
                    self.logger.warning("Failed to send feedback message", error=str(e))

            # 音声ファイルをダウンロード
            self.logger.debug(f"Downloading audio file: {filename}")
            audio_data = await self._download_attachment(attachment_url)
            if not audio_data:
                self.logger.error(f"Failed to download audio file: {filename}")
                await self._update_feedback_message(
                    feedback_message,
                    f"❌ 音声ファイル `{filename}` のダウンロードに失敗しました。",
                )
                return

            self.logger.debug(
                f"Audio file downloaded successfully, size: {len(audio_data)} bytes"
            )

            # 音声を文字起こし
            if not self.speech_processor:
                self.logger.error("Speech processor not initialized")
                await self._update_feedback_message(
                    feedback_message,
                    "❌ 音声処理システムが初期化されていません。",
                )
                return

            self.logger.debug(f"Starting speech processing for: {filename}")
            audio_result = await self.speech_processor.process_audio_file(
                file_data=audio_data, filename=filename, channel_name=channel_info.name
            )
            self.logger.debug(
                f"Speech processing completed, success: {audio_result.success}"
            )

            # 結果に応じてフィードバックを更新
            if audio_result.success and audio_result.transcription:
                self.logger.info(
                    "Audio transcription completed",
                    filename=filename,
                    transcript_length=len(audio_result.transcription.transcript),
                    confidence=audio_result.transcription.confidence,
                )

                # 成功メッセージ
                success_msg = (
                    f"音声文字起こしが完了しました！\n"
                    f"📝 **ファイル**: `{filename}`\n"
                    f"📊 **信頼度**: {audio_result.transcription.confidence:.2f}\n"
                    f"📄 ノートが Obsidian に保存されました。"
                )
                await self._update_feedback_message(feedback_message, success_msg)

                # 文字起こし結果をメッセージデータに追加
                await self._integrate_audio_transcription(
                    message_data, audio_result, channel_info
                )
            else:
                self.logger.warning(
                    "Audio transcription failed or used fallback",
                    filename=filename,
                    error=audio_result.error_message,
                    fallback_used=audio_result.fallback_used,
                )

                # エラーまたはフォールバックメッセージ
                if audio_result.fallback_used:
                    fallback_msg = (
                        f"⚠️ 音声文字起こしが制限されました\n"
                        f"📝 **ファイル**: `{filename}`\n"
                        f"📊 **理由**: {audio_result.fallback_reason}\n"
                        f"📁 音声ファイルは Obsidian に保存されました。"
                    )
                    await self._update_feedback_message(feedback_message, fallback_msg)
                else:
                    error_msg = (
                        f"❌ 音声文字起こしに失敗しました\n"
                        f"📝 **ファイル**: `{filename}`\n"
                        f"⚠️ **エラー**: {audio_result.error_message or '不明なエラー'}"
                    )
                    await self._update_feedback_message(feedback_message, error_msg)

                # フォールバック結果も統合
                if audio_result.transcription:
                    await self._integrate_audio_transcription(
                        message_data, audio_result, channel_info
                    )

        except Exception as e:
            self.logger.error(
                "Error processing single audio attachment",
                filename=attachment.get("filename", "unknown"),
                error=str(e),
                exc_info=True,
            )

            # 予期しないエラーのフィードバック
            error_msg = (
                f"❌ 音声処理中に予期しないエラーが発生しました\n"
                f"📝 **ファイル**: `{attachment.get('filename', 'unknown')}`\n"
                f"⚠️ **エラー**: {str(e)}"
            )
            await self._update_feedback_message(feedback_message, error_msg)

    async def _download_attachment(self, url: str) -> bytes | None:
        """添付ファイルをダウンロード（セキュリティ強化版）"""
        try:
            import aiohttp

            # セキュリティ: URL の検証
            if not url or not isinstance(url, str):
                self.logger.warning(
                    "Invalid URL provided for attachment download", url=url
                )
                return None

            # セキュリティ: Discord CDN URL の検証
            allowed_domains = {
                "cdn.discordapp.com",
                "media.discordapp.net",
                "discord.com",
            }

            from urllib.parse import urlparse

            parsed_url = urlparse(url)
            if parsed_url.hostname not in allowed_domains:
                self.logger.warning(
                    "Rejected attachment download from unauthorized domain",
                    url=url,
                    domain=parsed_url.hostname,
                )
                return None

            # 個人使用向けセキュリティ設定（緩和）
            MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB 制限（個人使用では緩和）
            TIMEOUT = 60  # 60 秒タイムアウト（個人使用では緩和）

            connector = aiohttp.TCPConnector(
                limit=10, limit_per_host=5, ttl_dns_cache=300, use_dns_cache=True
            )

            timeout = aiohttp.ClientTimeout(total=TIMEOUT, connect=10)

            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": "MindBridge-Bot/1.0"},
            ) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(
                            "Failed to download attachment",
                            url=url,
                            status=response.status,
                        )
                        return None

                    # セキュリティ: Content-Length チェック
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > MAX_FILE_SIZE:
                        self.logger.warning(
                            "Rejected attachment download due to size limit",
                            url=url,
                            size=content_length,
                            max_size=MAX_FILE_SIZE,
                        )
                        return None

                    # セキュリティ: Content-Type の検証
                    content_type = response.headers.get("Content-Type", "").lower()
                    allowed_content_types = {
                        "audio/ogg",
                        "audio/mpeg",
                        "audio/mp3",
                        "audio/wav",
                        "audio/webm",
                        "audio/mp4",
                        "audio/m4a",
                        "audio/x-wav",
                        "audio/vnd.wave",
                        "audio/wave",
                    }

                    if content_type and not any(
                        ct in content_type for ct in allowed_content_types
                    ):
                        self.logger.warning(
                            "Rejected attachment download due to invalid content type",
                            url=url,
                            content_type=content_type,
                        )
                        return None

                    # セキュリティ: ストリーミングダウンロードでサイズ制限
                    data = bytearray()
                    async for chunk in response.content.iter_chunked(
                        8192
                    ):  # 8KB チャンク
                        data.extend(chunk)
                        if len(data) > MAX_FILE_SIZE:
                            self.logger.warning(
                                "Rejected attachment download due to size limit during download",
                                url=url,
                                downloaded_size=len(data),
                                max_size=MAX_FILE_SIZE,
                            )
                            return None

                    # セキュリティ: マジックバイト検証
                    if len(data) < 12:
                        self.logger.warning(
                            "Rejected attachment download due to insufficient data",
                            url=url,
                            size=len(data),
                        )
                        return None

                    # 音声ファイルのマジックバイト検証
                    audio_magic_bytes = [
                        b"OggS",  # OGG
                        b"\xff\xfb",
                        b"\xff\xf3",
                        b"\xff\xf2",  # MP3
                        b"RIFF",  # WAV
                        b"\x1a\x45\xdf\xa3",  # WebM/Matroska
                        b"ftypM4A",  # M4A
                        b"ftypisom",  # MP4
                    ]

                    header = bytes(data[:12])
                    is_valid_audio = any(
                        header.startswith(magic) or magic in header[:12]
                        for magic in audio_magic_bytes
                    )

                    if not is_valid_audio:
                        self.logger.warning(
                            "Rejected attachment download due to invalid audio format",
                            url=url,
                            header=header.hex()[:24],  # 最初の 12 バイトの hex 表示
                        )
                        return None

                    self.logger.info(
                        "Successfully downloaded and validated audio attachment",
                        url=url,
                        size=len(data),
                        content_type=content_type,
                    )

                    return bytes(data)

        except aiohttp.ClientError as e:
            self.logger.error(
                "Network error downloading attachment",
                url=url,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None
        except Exception as e:
            self.logger.error(
                "Unexpected error downloading attachment",
                url=url,
                error=str(e),
                exc_info=True,
            )
            return None

    async def _integrate_audio_transcription(
        self, message_data: dict[str, Any], audio_result: Any, channel_info: Any
    ) -> None:
        """音声文字起こし結果を Obsidian ノートに統合"""
        try:
            if not self.obsidian_manager or not self.template_engine:
                return

            # 音声処理結果をメッセージデータに追加
            metadata = message_data.get("metadata", {})
            content_info = metadata.get("content", {})

            # 既存のコンテンツに音声文字起こし結果を追加
            transcription_text = audio_result.transcription.transcript

            # Enhanced duplication check: strict duplicate prevention
            # Check if existing content contains audio sections or transcription text
            # Variables not used, removed

            # Audio sections are centrally managed in _handle_obsidian_note_creation
            # Only save audio data to metadata here
            content_info["audio_transcription_data"] = {
                "transcript": transcription_text,
                "confidence": audio_result.transcription.confidence,
                "confidence_level": audio_result.transcription.confidence_level.value,
                "fallback_used": audio_result.fallback_used,
                "fallback_reason": audio_result.fallback_reason
                if audio_result.fallback_used
                else None,
                "saved_file_path": audio_result.saved_file_path
                if hasattr(audio_result, "saved_file_path")
                else None,
            }

            self.logger.debug(
                "Audio transcription data saved to metadata only",
                transcript_length=len(transcription_text),
                confidence=audio_result.transcription.confidence,
            )

            # Only metadata management needed, content processing not required
            content_info["has_audio_transcription"] = True
            content_info["audio_confidence"] = audio_result.transcription.confidence

            self.logger.info(
                "Audio transcription metadata integrated",
                channel=channel_info.name,
                transcript_length=len(transcription_text),
                fallback_used=audio_result.fallback_used,
            )

        except Exception as e:
            self.logger.error(
                "Error integrating audio transcription", error=str(e), exc_info=True
            )

    async def _handle_system_message(self, message_data: dict[str, Any]) -> None:
        """Handle messages from system channels"""
        self.logger.info(
            "Handling system message", channel_name=message_data["channel_info"]["name"]
        )

        # Process system-related messages
        try:
            content = message_data.get("content", "").strip()

            # Detect bot commands (starting with / or !)
            if content.startswith(("//", "!!")):
                command = content.split()[0] if content.split() else ""
                self.logger.info("Bot command detected", command=command)
                # Add command tag for future processing
                if "tags" not in message_data["metadata"]:
                    message_data["metadata"]["tags"] = []
                message_data["metadata"]["tags"].append("command")

            # Detect configuration updates
            config_keywords = ["config", "setting", "configure", "設定", "環境設定"]
            if any(keyword in content.lower() for keyword in config_keywords):
                self.logger.info("Configuration-related content detected")
                # Add config tag for future processing
                if "tags" not in message_data["metadata"]:
                    message_data["metadata"]["tags"] = []
                message_data["metadata"]["tags"].append("config")

            # Log system notifications for monitoring
            if (
                content and len(content) > 10
            ):  # Avoid logging empty or very short messages
                self.logger.debug("System message logged", content_length=len(content))

        except Exception as e:
            self.logger.error("Error processing system message", error=str(e))

    async def _handle_lifelog_auto_detection(
        self,
        message_data: dict[str, Any],
        original_message: discord.Message | None = None,
    ) -> None:
        """ライフログ自動検出・生成処理"""
        if not self.lifelog_message_handler or not original_message:
            return

        try:
            # メッセージ内容を取得
            metadata = message_data.get("metadata", {})
            content_info = metadata.get("content", {})
            final_content = ""

            # 音声転写結果も含めた最終コンテンツを取得
            if "raw_content" in content_info:
                final_content = content_info["raw_content"]
            elif original_message.content:
                final_content = original_message.content

            # 音声データがある場合は転写結果も考慮
            audio_data = content_info.get("audio_transcription_data")
            if audio_data and audio_data.get("transcript"):
                if final_content:
                    final_content += f"\n\n 音声転写: {audio_data['transcript']}"
                else:
                    final_content = audio_data["transcript"]

            if not final_content or len(final_content.strip()) < 10:
                return

            # ライフログエントリーを自動分析・生成
            lifelog_entry = (
                await self.lifelog_message_handler.analyze_message_for_lifelog(
                    final_content, str(original_message.author.id)
                )
            )

            if lifelog_entry and self.lifelog_manager:
                # ライフログエントリーを保存
                entry_id = await self.lifelog_manager.add_entry(lifelog_entry)

                # Obsidian ノートを生成
                await self._create_lifelog_obsidian_note(lifelog_entry, entry_id)

                self.logger.info(
                    "ライフログエントリーを自動生成しました",
                    entry_id=entry_id,
                    category=lifelog_entry.category,
                    type=lifelog_entry.type,
                    title=lifelog_entry.title,
                )

                # Discord に通知（オプション）
                if hasattr(original_message, "add_reaction"):
                    try:
                        await original_message.add_reaction(
                            "📝"
                        )  # ライフログ記録を示すリアクション
                    except Exception as e:
                        self.logger.debug("リアクション追加に失敗", error=str(e))

        except Exception as e:
            self.logger.warning("ライフログ自動検出でエラー", error=str(e))

    async def _create_lifelog_obsidian_note(self, entry: Any, entry_id: str) -> None:
        """ライフログエントリーの Obsidian ノートを作成"""
        if not self.obsidian_manager:
            return

        try:
            from ..lifelog.templates import LifelogTemplates

            # テンプレートを使用してノート内容を生成
            note_content = LifelogTemplates.generate_entry_note(entry)

            # カテゴリに基づいてフォルダを決定
            folder_map = {
                "health": "21_Health",
                "work": "11_Projects",
                "learning": "10_Knowledge",
                "finance": "20_Finance",
                "mood": "01_DailyNotes",
                "routine": "01_DailyNotes",
                "reflection": "01_DailyNotes",
                "goal": "02_Tasks",
                "relationship": "01_DailyNotes",
                "entertainment": "01_DailyNotes",
            }

            folder = folder_map.get(entry.category, "00_Inbox")

            # ファイル名を生成
            timestamp = entry.timestamp.strftime("%Y%m%d_%H%M")
            safe_title = "".join(
                c for c in entry.title if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            safe_title = safe_title[:50] if len(safe_title) > 50 else safe_title
            filename = f"lifelog_{timestamp}_{safe_title}.md"

            # ノートを保存
            file_path = f"{folder}/{filename}"

            # ObsidianNote オブジェクトを作成
            frontmatter = NoteFrontmatter(
                obsidian_folder=folder, tags=[entry.category, "lifelog"]
            )

            note = ObsidianNote(
                filename=filename,
                file_path=Path(file_path),
                frontmatter=frontmatter,
                content=note_content,
            )

            await self.obsidian_manager.save_note(note)

            self.logger.info(
                "ライフログ Obsidian ノートを作成しました",
                file_path=file_path,
                entry_id=entry_id,
                category=entry.category,
            )

        except Exception as e:
            self.logger.error("ライフログ Obsidian ノート作成でエラー", error=str(e))
