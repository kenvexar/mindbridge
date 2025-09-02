"""
Message handlers for Discord bot
"""

from datetime import datetime
from typing import Any

import discord

from ..ai import AIProcessor
from ..ai.mock_processor import MockAIProcessor
from ..ai.models import AIProcessingResult
from ..ai.note_analyzer import AdvancedNoteAnalyzer
from ..audio import SpeechProcessor
from ..obsidian import ObsidianFileManager
from ..obsidian.daily_integration import DailyNoteIntegration
from ..obsidian.template_system import TemplateEngine
from ..utils.mixins import LoggerMixin
from .channel_config import ChannelCategory, ChannelConfig


class MessageHandler(LoggerMixin):
    """Handle Discord message processing and routing"""

    ai_processor: AIProcessor | MockAIProcessor
    obsidian_manager: ObsidianFileManager | None
    note_template: str | None  # 古いテンプレートシステムは無効化
    daily_integration: DailyNoteIntegration | None
    template_engine: TemplateEngine | None
    note_analyzer: AdvancedNoteAnalyzer | None
    speech_processor: SpeechProcessor | None

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
        # 🔧 FIX: 処理済みメッセージを追跡するためのセット追加（重複処理防止）
        self._processed_messages: set[int] = set()
        self._max_processed_messages = 1000  # メモリ管理のため最大数を制限

        self.ai_processor = ai_processor
        self.obsidian_manager = obsidian_manager
        self.note_template = note_template
        self.daily_integration = daily_integration
        self.template_engine = template_engine
        self.note_analyzer = note_analyzer
        self.speech_processor = speech_processor

        # Logger is already available through LoggerMixin

        # Initialize dependencies
        from src.bot.message_processor import MessageProcessor

        # 🔧 FIX: 共有された ChannelConfig インスタンスを使用、または新規作成
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

        self.logger.info("MessageHandler fully initialized with all components")

    async def initialize(self) -> None:
        """非同期初期化処理"""
        if self.template_engine:
            try:
                await self.template_engine.create_default_templates()
                self.logger.info("Default templates created")
            except Exception as e:
                self.logger.error("Failed to create default templates", error=str(e))

    async def process_message(self, message: discord.Message) -> dict[str, Any] | None:
        """
        Process incoming Discord message and extract metadata

        Args:
            message: Discord message object

        Returns:
            Dictionary containing processed message data or None if ignored
        """
        processing_start = datetime.now()

        # 🔧 FIX: 重複処理防止 - 既に処理済みのメッセージをスキップ
        if message.id in self._processed_messages:
            self.logger.info(
                f"🔄 DEBUG: Message {message.id} already processed, skipping duplicate processing"
            )
            return None

        # 🔧 FIX: メッセージを処理済みとして記録（処理開始時に追加）
        self._processed_messages.add(message.id)

        # メモリ管理：処理済みメッセージ数が上限を超えた場合、古いものを削除
        if len(self._processed_messages) > self._max_processed_messages:
            # セットから最初の 100 個を削除（ FIFO 的な動作）
            old_messages = list(self._processed_messages)[:100]
            for old_msg_id in old_messages:
                self._processed_messages.discard(old_msg_id)
            self.logger.debug(
                f"Cleaned up {len(old_messages)} old processed message IDs"
            )

        # 🔍 DEBUG: Add detailed logging for channel monitoring check
        self.logger.info(
            f"🔍 DEBUG: process_message called for channel {message.channel.id} (#{getattr(message.channel, 'name', 'unknown')})"
        )

        # Skip bot messages (but log what's happening for debugging)
        # 🔧 TEMPORARY FIX: Allow processing bot messages for testing MCP integration
        if message.author.bot and not message.content.startswith("🔧"):
            self.logger.info(
                f"🤖 DEBUG: Skipping bot message from {message.author} (bot={message.author.bot})"
            )
            return None
        elif message.author.bot and message.content.startswith("🔧"):
            content_preview = (
                str(message.content)[:50]
                if hasattr(message.content, "__getitem__")
                else str(message.content)
            )
            self.logger.info(
                f"🧪 DEBUG: Processing bot message for testing - from {message.author} (content preview: {content_preview}...)"
            )

        # Check if channel is monitored
        is_monitored = self.channel_config.is_monitored_channel(message.channel.id)
        self.logger.info(
            f"🔍 DEBUG: is_monitored_channel({message.channel.id}) = {is_monitored}"
        )
        try:
            channels_info = (
                list(self.channel_config.channels.keys())
                if hasattr(self.channel_config, "channels")
                else []
            )
            self.logger.info(f"🔍 DEBUG: Available channels: {channels_info}")
        except Exception as e:
            self.logger.info(f"🔍 DEBUG: Could not list channels: {e}")

        # 🔧 TEMPORARY FIX: Force processing memo channel even if not properly discovered
        channel_name = getattr(message.channel, "name", "unknown").lower()
        if not is_monitored:
            if channel_name == "memo":
                self.logger.warning(
                    f"🔧 OVERRIDE: Channel #{channel_name} not in discovered channels, but forcing processing for memo channel"
                )
                # Continue processing anyway
            else:
                self.logger.warning(
                    f"Channel {message.channel.id} (#{channel_name}) is not monitored. Skipping processing."
                )
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

        # AI 処理を実行（テキストがある場合のみ）
        ai_result: AIProcessingResult | None = None
        content_length = len(message.content.strip()) if message.content else 0
        self.logger.info(
            f"🤖 DEBUG: Checking AI processing conditions - content_length={content_length}, threshold=20"
        )

        if message.content and content_length > 5:  # より緩い条件に変更
            try:
                result = await self.ai_processor.process_text(
                    text=message.content, message_id=message.id
                )
                ai_result = result if isinstance(result, AIProcessingResult) else None

                # Record AI request metrics
                if hasattr(self, "system_metrics"):
                    processing_time = (
                        datetime.now() - processing_start
                    ).total_seconds() * 1000
                    self.system_metrics.record_ai_request(True, int(processing_time))

                if hasattr(self, "api_usage_monitor"):
                    # Estimate token usage (rough calculation)
                    estimated_tokens = len(message.content.split()) * 1.3
                    self.api_usage_monitor.track_gemini_usage(
                        int(estimated_tokens), True
                    )

                self.logger.info(
                    "AI processing completed",
                    message_id=message.id,
                    has_summary=getattr(ai_result, "summary", None) is not None,
                    has_tags=getattr(ai_result, "tags", None) is not None,
                    has_category=getattr(ai_result, "category", None) is not None,
                    total_time_ms=getattr(ai_result, "total_processing_time_ms", 0),
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
                    estimated_tokens = (
                        len(message.content.split()) * 1.3 if message.content else 0
                    )
                    self.api_usage_monitor.track_gemini_usage(
                        int(estimated_tokens), False
                    )

                self.logger.error(
                    "AI processing failed",
                    message_id=message.id,
                    error=str(e),
                    exc_info=True,
                )

        # Combine with channel information
        message_data = {
            "metadata": metadata,
            "ai_processing": ai_result.model_dump() if ai_result else None,
            "channel_info": {
                "name": channel_info.name,
                "category": channel_info.category.value,
                "description": channel_info.description,
            },
            "processing_timestamp": datetime.now().isoformat(),
        }

        # Route message based on channel category
        self.logger.info(
            f"🚀 DEBUG: Routing message to category handler - category={channel_info.category.value}"
        )
        await self._route_message_by_category(
            message_data, channel_info.category, message
        )

        self.logger.info(
            f"✅ DEBUG: Message processing completed successfully for message {message.id}"
        )
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
        self.logger.info(
            "Handling capture message",
            channel_name=message_data["channel_info"]["name"],
        )

        # 🔧 FIX: 音声添付ファイルの処理をノート生成の前に実行（転写内容をノートに含めるため）
        from ..bot.channel_config import ChannelCategory, ChannelInfo

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

        # AI 処理結果を取得
        ai_processing = message_data.get("ai_processing")

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
                # AI処理失敗時でも処理を継続するため、ai_result は None のままにする

        # Obsidian ノートの生成と保存（GitHub 直接同期統合版）
        await self._handle_obsidian_note_creation(ai_result, message_data)

        # Daily Note Integration の処理
        await self._handle_daily_note_integration(message_data, channel_info)

    async def _handle_obsidian_note_creation(
        self,
        ai_result: AIProcessingResult | None,
        message_data: dict[str, Any],
    ) -> None:
        """Obsidian ノート作成とファイルシステム統合（GitHub 直接同期対応）"""
        self.logger.info(
            f"📝 DEBUG: Starting Obsidian note creation - obsidian_manager={self.obsidian_manager is not None}, template_engine={self.template_engine is not None}"
        )

        if self.obsidian_manager and self.template_engine:
            try:
                # 新しい TemplateEngine で Obsidian ノートを生成
                note = await self.template_engine.generate_note_from_template(
                    template_name="daily_note",
                    message_data=message_data,
                    ai_result=ai_result,
                )

                if note:
                    # Vault の初期化（初回のみ）
                    await self.obsidian_manager.initialize_vault()

                    # 高度な AI 分析を実行（ノート分析器が利用可能な場合）
                    enhanced_content = note.content
                    if self.note_analyzer and note.content:
                        try:
                            self.logger.info(
                                "Running advanced AI analysis on note content",
                                note_title=note.title,
                            )

                            # Discord メタデータを構築
                            discord_metadata = None
                            if message_data.get("metadata"):
                                try:
                                    discord_metadata = {
                                        "channel_name": message_data["channel_info"][
                                            "name"
                                        ],
                                        "channel_category": message_data[
                                            "channel_info"
                                        ]["category"],
                                        # 🔧 FIX: timing 構造を使用（ basic ではなく）
                                        "timestamp": message_data["metadata"]
                                        .get("timing", {})
                                        .get("created_at", {})
                                        .get("timestamp", None),
                                        "user_id": message_data["metadata"]["basic"][
                                            "author"
                                        ]["id"],
                                    }
                                except KeyError as e:
                                    self.logger.warning(
                                        f"Failed to construct Discord metadata: missing key {e}"
                                    )
                                    discord_metadata = None

                            # 包括的なノート分析を実行
                            analysis_result = await self.note_analyzer.analyze_note_content(
                                content=note.content,
                                title=note.title,
                                file_path=str(
                                    note.file_path.relative_to(
                                        self.obsidian_manager.vault_path
                                    )
                                ),
                                include_url_processing=True,
                                include_related_notes=True,
                                discord_metadata=discord_metadata,  # Discord メタデータを渡す
                            )

                            # 分析結果から強化されたコンテンツを取得
                            if analysis_result.get("enhanced_content", {}).get(
                                "content"
                            ):
                                enhanced_content = analysis_result["enhanced_content"][
                                    "content"
                                ]
                                self.logger.info(
                                    "Enhanced note content with AI analysis",
                                    has_related_notes=bool(
                                        analysis_result.get("related_notes", {}).get(
                                            "results"
                                        )
                                    ),
                                    has_internal_links=bool(
                                        analysis_result.get("internal_links", {}).get(
                                            "suggestions"
                                        )
                                    ),
                                    has_discord_analysis=bool(
                                        analysis_result.get("discord_analysis")
                                    ),
                                )

                        except Exception as e:
                            self.logger.warning(
                                "Failed to run advanced AI analysis",
                                note_title=note.title,
                                error=str(e),
                            )

                    # 強化されたコンテンツでノートを更新
                    if enhanced_content != note.content:
                        note.content = enhanced_content

                    # ローカルにノートを保存
                    saved_file_path = await self.obsidian_manager.save_note(note)

                    if saved_file_path is None:
                        self.logger.error("Failed to save note to Obsidian vault")
                        # Set a fallback path for error logging
                        saved_file_path = f"failed_to_save_{note.title}"

                    # 🔧 FIX: Record file creation in metrics
                    if hasattr(self, "system_metrics"):
                        self.system_metrics.record_file_created()

                    # 🔧 NEW: 詳細ログ出力（ファイル内容のプレビューも含む） - AttributeError修正
                    content_preview = (
                        enhanced_content[:200] + "..."
                        if len(enhanced_content) > 200
                        else enhanced_content
                    )

                    # 🔧 FIX: Safe AI category extraction to prevent AttributeError
                    ai_category = "none"
                    try:
                        if (
                            ai_result
                            and hasattr(ai_result, "category")
                            and ai_result.category
                        ):
                            if (
                                hasattr(ai_result.category, "category")
                                and ai_result.category.category
                            ):
                                ai_category = ai_result.category.category.value
                    except (AttributeError, TypeError):
                        ai_category = "none"

                    self.logger.info(
                        "📝 SUCCESS: Note saved successfully with detailed info",
                        title=note.title,
                        file_path="saved successfully",
                        absolute_path="saved successfully",
                        content_length=len(enhanced_content),
                        content_preview=content_preview,
                        note_tags=getattr(note.frontmatter, "tags", []),
                        obsidian_folder=getattr(
                            note.frontmatter, "obsidian_folder", "unknown"
                        ),
                        ai_category=ai_category,
                    )

                    # AI 分類結果に基づいてノートを適切なフォルダに移動
                    await self._organize_note_by_ai_category(note, ai_result)

                    # GitHub 直接同期の実行
                    await self._handle_github_direct_sync(
                        ai_result, note, saved_file_path
                    )

                    # Daily Integration の実行
                    if self.daily_integration:
                        try:
                            # 🔧 FIX: より意味のある Activity Log エントリタイトルを生成
                            activity_title = self._generate_activity_log_title(
                                message_data, ai_result, note
                            )

                            # メモ保存を Activity Log に追加するためのメッセージデータを構築
                            activity_data = {
                                "metadata": {
                                    "content": {"raw_content": activity_title},
                                    "timing": message_data["metadata"].get(
                                        "timing", {}
                                    ),
                                }
                            }
                            await self.daily_integration.add_activity_log_entry(
                                activity_data
                            )
                        except Exception as e:
                            self.logger.warning(
                                "Failed to add daily integration entry", error=str(e)
                            )

            except Exception as e:
                self.logger.error(
                    "Failed to create Obsidian note",
                    error=str(e),
                    exc_info=True,
                    message_id=message_data.get("metadata", {})
                    .get("basic", {})
                    .get("id"),
                    template_engine_available=self.template_engine is not None,
                    obsidian_manager_available=self.obsidian_manager is not None,
                )
        else:
            self.logger.warning(
                f"📝 DEBUG: Skipping Obsidian note creation - missing dependencies: obsidian_manager={self.obsidian_manager is not None}, template_engine={self.template_engine is not None}"
            )

        # GitHub 同期 - シンプル版（従来の GitHubSync のフォールバック）
        if (
            hasattr(self, "github_sync")
            and self.github_sync
            and self.github_sync.is_configured
        ):
            try:
                await self.github_sync.sync_to_github("Auto-sync from Discord message")
                self.logger.info("GitHub sync completed successfully")
            except Exception as e:
                self.logger.error(f"GitHub sync failed: {e}")

    async def _handle_github_direct_sync(
        self, ai_result: AIProcessingResult | None, note, saved_file_path
    ) -> None:
        """Cloud Run 環境での GitHub 直接同期を実行"""
        self.logger.info(
            "🔧 DEBUG: _handle_github_direct_sync called",
            note_title=getattr(note, "title", "unknown"),
            saved_file_path=str(saved_file_path),
            has_ai_result=ai_result is not None,
        )
        try:
            from ..obsidian.github_direct import GitHubDirectClient

            # GitHub Direct Client を初期化
            github_client = GitHubDirectClient()

            self.logger.info(
                "🔧 DEBUG: GitHubDirectClient initialized",
                is_configured=github_client.is_configured,
                has_token=bool(github_client.github_token),
                has_repo_url=bool(github_client.github_repo_url),
                owner=github_client.owner,
                repo=github_client.repo,
            )

            if not github_client.is_configured:
                self.logger.warning(
                    "❌ GitHub direct sync not configured - file saved locally only"
                )
                return

            # AI 結果からカテゴリフォルダーを決定
            category = "Memos"  # デフォルト
            if ai_result and ai_result.category:
                category = github_client.get_category_folder(
                    ai_result.category.category
                )

            self.logger.info(
                "Processing GitHub direct sync",
                category=category,
                has_ai_result=ai_result is not None,
                ai_errors=ai_result.errors if ai_result else [],
            )

            # Discord メッセージデータから note_data を構築
            note_data = {
                "title": note.title,
                "content": note.content,
                "tags": getattr(note.frontmatter, "tags", [])
                if hasattr(note, "frontmatter")
                else [],
            }

            # AI 分析結果も追加
            if ai_result:
                note_data["ai_analysis"] = {
                    "category": ai_result.category.category.value
                    if ai_result.category
                    else None,
                    "confidence": ai_result.category.confidence_score
                    if ai_result.category
                    else None,
                    "tags": ai_result.tags.tags if ai_result.tags else [],
                    "summary": ai_result.summary.summary if ai_result.summary else None,
                }

            # GitHub に直接ノートを作成
            result = await github_client.create_note_from_discord(
                note_data=note_data, category=category
            )

            if result:
                self.logger.info(
                    "✅ GitHub direct sync completed successfully",
                    file_path=result["file_path"],
                    commit_sha=result["github_result"].get("commit", {}).get("sha"),
                    category=category,
                )
            else:
                self.logger.warning(
                    "⚠️ GitHub direct sync failed",
                    file_path=str(saved_file_path),
                    reason="create_note_from_discord returned None",
                )

        except ImportError:
            self.logger.warning(
                "GitHubDirectClient not available - falling back to traditional sync"
            )
        except Exception as github_error:
            self.logger.error(
                "❌ GitHub direct sync failed with error",
                file_path=str(saved_file_path),
                error=str(github_error),
                exc_info=True,
            )

    def _generate_activity_log_title(
        self,
        message_data: dict[str, Any],
        ai_result: AIProcessingResult | None,
        note: Any,
    ) -> str:
        """Activity Log エントリの意味のあるタイトルを生成"""
        try:
            # 音声文字起こし内容を確認
            content_info = message_data.get("metadata", {}).get("content", {})
            has_audio = content_info.get("has_audio_transcription", False)
            channel_name = message_data["channel_info"]["name"]

            if has_audio:
                # 音声メッセージの場合、転写内容から短い要約を作成
                cleaned_content = content_info.get("cleaned_content", "")

                # 音声転写部分を抽出
                transcription_text = ""
                if "🎤 音声文字起こし" in cleaned_content:
                    # 音声セクションから実際の転写テキストを抽出
                    import re

                    pattern = r"🎤 音声文字起こし\s*(.*?)\s*\*\*信頼度\*\*"
                    match = re.search(pattern, cleaned_content, re.DOTALL)
                    if match:
                        transcription_text = match.group(1).strip()

                if transcription_text:
                    # 転写内容から適切な長さの要約を作成
                    if len(transcription_text) > 30:
                        # 最初の文またはフレーズを使用
                        summary = transcription_text[:30].rsplit("。", 1)[0]
                        if not summary.endswith("。"):
                            summary += "..."
                    else:
                        summary = transcription_text

                    return f"🎤 音声メモ: {summary} - #{channel_name}"

            # AI 要約がある場合
            if ai_result and ai_result.summary:
                summary_text = ai_result.summary.summary
                if len(summary_text) > 40:
                    summary_text = summary_text[:40] + "..."
                return f"📝 {summary_text} - #{channel_name}"

            # AI 分類がある場合
            if ai_result and ai_result.category:
                category = ai_result.category.category
                return f"📝 {category}メモ - #{channel_name}"

            # 通常のテキストメッセージ（全文表示）
            raw_content = content_info.get("raw_content", "").strip()
            if raw_content and len(raw_content) > 10:
                # 全文を表示（省略なし）
                preview = raw_content
                return f"📝 {preview} - #{channel_name}"

            # フォールバック: ノートタイトルを使用
            return f"📝 {note.title} - #{channel_name}"

        except Exception as e:
            self.logger.warning(
                "Failed to generate activity log title, using fallback", error=str(e)
            )
            # エラー時のフォールバック
            channel_name = message_data.get("channel_info", {}).get("name", "unknown")
            return f"📝 メモ - #{channel_name}"

    async def _organize_note_by_ai_category(self, note, ai_result) -> None:
        """AI 分類結果に基づいてノートを適切なフォルダに移動"""
        if not ai_result or not ai_result.category:
            self.logger.debug(
                "No AI category found, keeping note in current location",
                note_path=str(note.file_path),
            )
            return

        try:
            from ..obsidian.models import FolderMapping

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
            from ..config import get_settings

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

            # 🔧 DEBUG: 添付ファイル情報をログ出力
            self.logger.info(
                f"🎵 DEBUG: _handle_audio_attachments called with {len(attachments)} total attachments"
            )

            for i, att in enumerate(attachments):
                self.logger.info(
                    f"🎵 DEBUG: Attachment {i}: filename={att.get('filename', 'N/A')}, "
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

            self.logger.info(
                f"🎵 DEBUG: Found {len(audio_attachments)} audio attachments after filtering"
            )

            if not audio_attachments:
                self.logger.info(
                    "🎵 DEBUG: No audio attachments found, returning early"
                )
                return

            self.logger.info(
                "Processing audio attachments",
                count=len(audio_attachments),
                channel=channel_info.name,
            )

            for attachment in audio_attachments:
                self.logger.info(
                    f"🎵 DEBUG: Processing audio attachment: {attachment.get('filename', 'N/A')}"
                )
                await self._process_single_audio_attachment(
                    attachment, message_data, channel_info, original_message
                )

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
            attachment_url = attachment.get("url")
            filename = attachment.get("filename", "audio.mp3")

            if not attachment_url:
                self.logger.warning(
                    "No URL found for audio attachment", filename=filename
                )
                return

            # Discord へのリアルタイムフィードバックを開始
            if original_message:
                try:
                    feedback_message = await original_message.reply(
                        f"🎤 音声ファイル `{filename}` の文字起こしを開始します..."
                    )
                except Exception as e:
                    self.logger.warning("Failed to send feedback message", error=str(e))

            # 音声ファイルをダウンロード
            audio_data = await self._download_attachment(attachment_url)
            if not audio_data:
                await self._update_feedback_message(
                    feedback_message,
                    f"❌ 音声ファイル `{filename}` のダウンロードに失敗しました。",
                )
                return

            # 音声を文字起こし
            if not self.speech_processor:
                await self._update_feedback_message(
                    feedback_message,
                    "❌ 音声処理システムが初期化されていません。",
                )
                return

            audio_result = await self.speech_processor.process_audio_file(
                file_data=audio_data, filename=filename, channel_name=channel_info.name
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
                    f"✅ 音声文字起こしが完了しました！\n"
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
        """添付ファイルをダウンロード"""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session, session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                self.logger.error(
                    "Failed to download attachment",
                    url=url,
                    status=response.status,
                )
                return None

        except Exception as e:
            self.logger.error(
                "Error downloading attachment", url=url, error=str(e), exc_info=True
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
            original_content = content_info.get("raw_content", "")
            transcription_text = audio_result.transcription.transcript

            # 音声セクションを追加
            audio_section = f"\n\n## 🎤 音声文字起こし\n\n{transcription_text}"

            if audio_result.transcription.confidence > 0.0:
                confidence_level = audio_result.transcription.confidence_level.value
                audio_section += f"\n\n**信頼度**: {audio_result.transcription.confidence:.2f} ({confidence_level})"

            if audio_result.fallback_used:
                audio_section += f"\n\n**注意**: {audio_result.fallback_reason}"
                if audio_result.saved_file_path:
                    audio_section += f"\n**保存先**: `{audio_result.saved_file_path}`"

            # コンテンツを更新
            enhanced_content = original_content + audio_section
            content_info["raw_content"] = enhanced_content

            # 🔧 FIX: cleaned_content も更新して、 Obsidian ノートに音声内容を反映
            if self.message_processor:
                content_info["cleaned_content"] = self.message_processor._clean_content(
                    enhanced_content
                )
            else:
                # message_processor がない場合の fallback
                import re

                cleaned = re.sub(r"\s+", " ", enhanced_content).strip()
                content_info["cleaned_content"] = cleaned

            content_info["has_audio_transcription"] = True
            content_info["audio_confidence"] = audio_result.transcription.confidence

            # AI で処理する場合は、音声文字起こし結果も含めて処理
            if original_content.strip() or transcription_text.strip():
                # 通常の AI 処理フローに任せる（ AIProcessor が音声テキストも処理する）
                pass

            self.logger.info(
                "Audio transcription integrated into message",
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
