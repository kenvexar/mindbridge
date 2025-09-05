"""
Message handlers for Discord bot
"""

import asyncio
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from src.utils.logger import logger


class BaseHandler:
    """ハンドラーの基底クラス - 共通パターンを提供"""

    def __init__(self) -> None:
        self.logger = logger
        self._processing_cache: set[str] = set()
        self._max_cache_size = 1000

    async def handle_with_retry(
        self,
        operation_name: str,
        operation_func: Callable[..., Awaitable[Any]],
        *args: Any,
        max_retries: int = 3,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """リトライ機能付きで operation を実行"""
        for attempt in range(max_retries):
            try:
                result = await operation_func(*args, **kwargs)
                return {
                    "status": "success",
                    "result": result,
                    "operation": operation_name,
                }

            except Exception as e:
                if attempt == max_retries - 1:
                    self.logger.error(
                        f"{operation_name} failed after {max_retries} attempts: {e}"
                    )
                    return {
                        "status": "error",
                        "error": str(e),
                        "operation": operation_name,
                    }

                self.logger.warning(
                    f"{operation_name} attempt {attempt + 1} failed: {e}"
                )
                await asyncio.sleep(2**attempt)  # Exponential backoff

        # This should never be reached, but mypy requires it
        return {
            "status": "error",
            "error": "Max retries exceeded",
            "operation": operation_name,
        }

    async def handle_with_deduplication(
        self, operation_key: str, operation_func, *args, **kwargs
    ) -> dict:
        """重複処理防止機能付きで operation を実行"""
        if operation_key in self._processing_cache:
            return {
                "status": "duplicate",
                "message": f"Operation {operation_key} already in progress",
            }

        self._processing_cache.add(operation_key)

        try:
            result = await operation_func(*args, **kwargs)
            return {"status": "success", "result": result}
        except Exception as e:
            self.logger.error(f"Operation {operation_key} failed: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            self._processing_cache.discard(operation_key)
            self._cleanup_cache()

    def _cleanup_cache(self) -> None:
        """キャッシュサイズを制限"""
        if len(self._processing_cache) > self._max_cache_size:
            # 古いエントリを削除（簡易実装）
            cache_list = list(self._processing_cache)
            for item in cache_list[:100]:
                self._processing_cache.discard(item)

    async def handle_with_validation(
        self, data: Any, validator_func, operation_func, *args, **kwargs
    ) -> dict:
        """バリデーション機能付きで operation を実行"""
        try:
            # バリデーション実行
            validation_result = (
                await validator_func(data)
                if asyncio.iscoroutinefunction(validator_func)
                else validator_func(data)
            )

            if not validation_result.get("is_valid", False):
                return {
                    "status": "validation_failed",
                    "errors": validation_result.get("errors", []),
                }

            # メイン処理実行
            result = await operation_func(data, *args, **kwargs)
            return {"status": "success", "result": result}

        except Exception as e:
            self.logger.error(f"Validated operation failed: {e}")
            return {"status": "error", "error": str(e)}

    def create_operation_context(self, operation_type: str, **metadata) -> dict:
        """操作コンテキストを作成"""
        import uuid

        return {
            "operation_id": str(uuid.uuid4()),
            "operation_type": operation_type,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata,
        }


class MessageProcessor:
    """メッセージの基本処理を担当"""

    def __init__(self) -> None:
        self._processed_messages: set[int] = set()
        self._max_processed_messages = 1000

    async def should_process_message(self, message: Any) -> bool:
        """メッセージが処理対象かどうか判定"""
        if message.id in self._processed_messages:
            return False

        # メッセージの基本フィルタリング
        if message.author.bot:
            return False

        if not message.content.strip() and not message.attachments:
            return False

        return True

    def mark_processed(self, message_id: int) -> None:
        """メッセージを処理済みとしてマーク"""
        self._processed_messages.add(message_id)

        # キャッシュサイズ制限
        if len(self._processed_messages) > self._max_processed_messages:
            oldest_messages = list(self._processed_messages)[:100]
            for msg_id in oldest_messages:
                self._processed_messages.remove(msg_id)

    def _extract_transcription_text(self, transcription_result: dict) -> str:
        """転写結果からテキストを抽出"""
        if not transcription_result:
            return ""

        if isinstance(transcription_result, dict):
            return transcription_result.get("transcript", "")

        return str(transcription_result)

    def _create_transcription_summary(self, transcript: str) -> str:
        """転写テキストの要約を作成"""
        if len(transcript) <= 100:
            return transcript
        return transcript[:97] + "..."

    def _remove_bot_attribution_messages(self, content: str) -> str:
        """ボット帰属メッセージを除去"""
        patterns_to_remove = [
            r"Generated with.*",
            r"Co-Authored-By:.*",
            r"🤖.*",
            r"\*\*Generated by.*\*\*",
        ]

        for pattern in patterns_to_remove:
            content = re.sub(pattern, "", content, flags=re.MULTILINE | re.IGNORECASE)

        return content.strip()


class AttachmentHandler:
    """添付ファイルの処理を担当"""

    def __init__(self, speech_processor, obsidian_manager):
        self.speech_processor = speech_processor
        self.obsidian_manager = obsidian_manager

    async def handle_audio_attachments(self, message, processed_content: str) -> dict:
        """音声添付ファイルを処理"""
        if not message.attachments:
            return {"has_audio": False}

        audio_attachments = [
            att
            for att in message.attachments
            if any(
                att.filename.lower().endswith(ext)
                for ext in [".mp3", ".wav", ".ogg", ".m4a"]
            )
        ]

        if not audio_attachments:
            return {"has_audio": False}

        results = []
        for attachment in audio_attachments:
            try:
                result = await self._process_single_audio_attachment(
                    attachment, message
                )
                if result:
                    results.append(result)
            except Exception as e:
                logger.error(
                    f"Failed to process audio attachment {attachment.filename}: {e}"
                )

        return {
            "has_audio": len(results) > 0,
            "audio_results": results,
            "total_processed": len(results),
        }

    async def handle_document_attachments(self, message) -> dict:
        """文書添付ファイルを処理"""
        if not message.attachments:
            return {"has_documents": False}

        doc_attachments = [
            att
            for att in message.attachments
            if any(
                att.filename.lower().endswith(ext)
                for ext in [".txt", ".md", ".pdf", ".docx"]
            )
        ]

        if not doc_attachments:
            return {"has_documents": False}

        results = []
        for attachment in doc_attachments:
            try:
                # ファイルダウンロード
                file_path = await self._download_attachment(attachment)

                # Obsidian へ保存
                attachment_folder = (
                    Path(self.obsidian_manager.vault_path) / "80_Attachments"
                )
                attachment_folder.mkdir(exist_ok=True)

                saved_path = attachment_folder / attachment.filename
                if file_path and file_path.exists():
                    import shutil

                    shutil.move(str(file_path), str(saved_path))
                    results.append(
                        {
                            "filename": attachment.filename,
                            "saved_path": str(saved_path),
                            "size": attachment.size,
                        }
                    )

            except Exception as e:
                logger.error(
                    f"Failed to process document attachment {attachment.filename}: {e}"
                )

        return {
            "has_documents": len(results) > 0,
            "document_results": results,
            "total_processed": len(results),
        }

    async def _process_single_audio_attachment(
        self, attachment, message
    ) -> dict[str, Any] | None:
        """単一音声添付ファイルを処理"""
        try:
            # ファイルダウンロード
            temp_file = await self._download_attachment(attachment)
            if not temp_file or not temp_file.exists():
                return None

            # 音声文字起こし
            transcription_result = await self.speech_processor.process_audio_file(
                str(temp_file)
            )

            if not transcription_result or not transcription_result.get("transcript"):
                return {}

            transcript = transcription_result["transcript"]

            # 一時ファイル削除
            if temp_file.exists():
                temp_file.unlink()

            return {
                "filename": attachment.filename,
                "transcript": transcript,
                "confidence": transcription_result.get("confidence", 0.0),
                "duration": transcription_result.get("duration", 0),
            }

        except Exception as e:
            logger.error(f"Audio processing failed for {attachment.filename}: {e}")
            return {}

    async def _download_attachment(self, attachment) -> Path | None:
        """添付ファイルをダウンロード"""
        import tempfile

        import aiohttp

        temp_dir = Path(tempfile.gettempdir())
        temp_file = temp_dir / f"temp_{attachment.id}_{attachment.filename}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as resp:
                    if resp.status == 200:
                        with open(temp_file, "wb") as f:
                            async for chunk in resp.content.iter_chunked(8192):
                                f.write(chunk)
                        return temp_file
        except Exception as e:
            logger.error(f"Failed to download attachment {attachment.filename}: {e}")

        return None


class NoteCreationHandler:
    """ノート作成処理を担当"""

    def __init__(
        self, template_engine: Any, note_analyzer: Any, obsidian_manager: Any
    ) -> None:
        self.template_engine = template_engine
        self.note_analyzer = note_analyzer
        self.obsidian_manager = obsidian_manager
        self._creating_notes: set[str] = set()

    async def handle_obsidian_note_creation(
        self, message, processed_content: str, ai_analysis: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Obsidian ノート作成を処理"""

        # 重複作成防止
        note_key = f"{message.id}_{hash(processed_content)}"
        if note_key in self._creating_notes:
            return {
                "status": "duplicate",
                "message": "Note creation already in progress",
            }

        self._creating_notes.add(note_key)

        try:
            # メタデータ作成
            metadata = {
                "author": str(message.author),
                "timestamp": message.created_at.isoformat(),
                "channel": str(message.channel),
                "message_id": message.id,
            }

            # AI 分析がない場合は実行
            if not ai_analysis and self.note_analyzer:
                try:
                    ai_analysis = (
                        await self.note_analyzer.analyze_content_for_organization(
                            processed_content
                        )
                    )
                except Exception as e:
                    logger.warning(f"AI analysis failed: {e}")
                    ai_analysis = {"category": "general", "tags": [], "summary": ""}

            # テンプレートからノート生成
            note_result = await self.template_engine.generate_note_from_template(
                processed_content, metadata, ai_analysis
            )

            # ファイルパスの決定
            folder = note_result.get("folder", "00_Inbox")
            title = note_result.get("title", "Untitled")

            # 安全なファイル名生成
            safe_filename = self._create_safe_filename(title)
            note_path = (
                Path(self.obsidian_manager.vault_path) / folder / f"{safe_filename}.md"
            )

            # ディレクトリ作成
            note_path.parent.mkdir(parents=True, exist_ok=True)

            # ノート保存
            await self._save_note_file(note_path, note_result["content"])

            return {
                "status": "success",
                "note_path": str(note_path),
                "title": title,
                "folder": folder,
                "ai_analysis": ai_analysis,
            }

        except Exception as e:
            logger.error(f"Note creation failed: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            self._creating_notes.discard(note_key)

    def _create_safe_filename(self, title: str) -> str:
        """安全なファイル名を作成"""
        # 危険な文字を除去
        safe_title = re.sub(r'[<>:"/\\|?*]', "", title)
        safe_title = safe_title.replace("\n", " ").replace("\r", " ")
        safe_title = re.sub(r"\s+", " ", safe_title).strip()

        # 長さ制限
        if len(safe_title) > 100:
            safe_title = safe_title[:97] + "..."

        # 空の場合のフォールバック
        return safe_title if safe_title else "Untitled"

    async def _save_note_file(self, file_path: Path, content: str) -> None:
        """ノートファイルを保存"""
        import aiofiles

        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(content)


class IntegrationHandler:
    """外部サービス統合を担当"""

    def __init__(self, daily_integration=None, github_sync=None):
        self.daily_integration = daily_integration
        self.github_sync = github_sync

    async def handle_daily_note_integration(
        self, note_path: str, ai_analysis: dict
    ) -> dict:
        """デイリーノート統合を処理"""
        if not self.daily_integration:
            return {"status": "skipped", "reason": "Daily integration not configured"}

        try:
            result = await self.daily_integration.integrate_with_daily_note(
                note_path, ai_analysis
            )
            return {"status": "success", "result": result}

        except Exception as e:
            logger.error(f"Daily note integration failed: {e}")
            return {"status": "error", "error": str(e)}

    async def handle_github_direct_sync(self, note_path: str, metadata: dict) -> dict:
        """GitHub 直接同期を処理"""
        if not self.github_sync:
            return {"status": "skipped", "reason": "GitHub sync not configured"}

        try:
            result = await self.github_sync.sync_note_to_github(note_path, metadata)
            return {"status": "success", "result": result}

        except Exception as e:
            logger.error(f"GitHub sync failed: {e}")
            return {"status": "error", "error": str(e)}

    async def handle_system_message(self, message_data: dict) -> None:
        """システムメッセージを処理"""
        try:
            message_type = message_data.get("type", "unknown")

            if message_type == "health_check":
                await self._handle_health_check()
            elif message_type == "metrics_report":
                await self._handle_metrics_report(message_data)
            else:
                logger.info(f"Unknown system message type: {message_type}")

        except Exception as e:
            logger.error(f"System message handling failed: {e}")

    async def _handle_health_check(self) -> None:
        """ヘルスチェック処理"""
        logger.info("Health check received - system is operational")

    async def _handle_metrics_report(self, data: dict) -> None:
        """メトリクスレポート処理"""
        metrics = data.get("metrics", {})
        logger.info(f"Metrics report: {metrics}")


class MessageHandler:
    """統合メッセージハンドラー - 他のコンポーネントを組み合わせる"""

    def __init__(
        self,
        ai_processor,
        obsidian_manager,
        note_template=None,
        daily_integration=None,
        template_engine=None,
        note_analyzer=None,
        speech_processor=None,
    ):
        # 依存関係
        self.ai_processor = ai_processor
        self.obsidian_manager = obsidian_manager
        self.note_template = note_template
        self.daily_integration = daily_integration
        self.template_engine = template_engine
        self.note_analyzer = note_analyzer
        self.speech_processor = speech_processor

        # コンポーネント初期化
        self.message_processor = MessageProcessor()
        self.attachment_handler = AttachmentHandler(speech_processor, obsidian_manager)
        self.note_creation_handler = NoteCreationHandler(
            template_engine, note_analyzer, obsidian_manager
        )
        self.integration_handler = IntegrationHandler(daily_integration)

        # 設定
        self.system_metrics = None
        self.api_usage_monitor = None
        self.channel_config = None
        self.message_processor_component = None

    def set_monitoring_systems(self, system_metrics, api_usage_monitor):
        """モニタリングシステムを設定"""
        self.system_metrics = system_metrics
        self.api_usage_monitor = api_usage_monitor

    async def initialize(self) -> None:
        """初期化処理"""
        logger.info("MessageHandler initialized successfully")

    async def process_message(self, message) -> dict[str, Any]:
        """メッセージ処理のメインエントリーポイント"""

        try:
            # 処理対象チェック
            if not await self.message_processor.should_process_message(message):
                return {"status": "skipped", "reason": "Message filtered out"}

            # メッセージを処理済みとしてマーク
            self.message_processor.mark_processed(message.id)

            # メッセージ内容の前処理
            processed_content = await self._preprocess_message_content(message)

            # 添付ファイル処理
            attachment_results = await self._handle_all_attachments(
                message, processed_content
            )

            # AI 分析（オプション）
            ai_analysis = None
            if self.note_analyzer:
                try:
                    ai_analysis = (
                        await self.note_analyzer.analyze_content_for_organization(
                            processed_content
                        )
                    )
                except Exception as e:
                    logger.warning(f"AI analysis failed: {e}")

            # ノート作成
            note_result = (
                await self.note_creation_handler.handle_obsidian_note_creation(
                    message, processed_content, ai_analysis
                )
            )

            # 統合処理
            integration_results = await self._handle_integrations(
                note_result, ai_analysis
            )

            return {
                "status": "success",
                "message_id": message.id,
                "processed_content": processed_content,
                "attachments": attachment_results,
                "note": note_result,
                "integrations": integration_results,
            }

        except Exception as e:
            logger.error(f"Message processing failed for message {message.id}: {e}")
            return {"status": "error", "message_id": message.id, "error": str(e)}

    async def _preprocess_message_content(self, message) -> str:
        """メッセージ内容の前処理"""
        content = message.content

        # ボット帰属メッセージ除去
        content = self.message_processor._remove_bot_attribution_messages(content)

        # 基本的なクリーンアップ
        content = content.strip()

        return content

    async def _handle_all_attachments(self, message, processed_content: str) -> dict:
        """すべての添付ファイルを処理"""
        results = {}

        # 音声添付ファイル
        if self.speech_processor:
            audio_results = await self.attachment_handler.handle_audio_attachments(
                message, processed_content
            )
            results.update(audio_results)

        # 文書添付ファイル
        doc_results = await self.attachment_handler.handle_document_attachments(message)
        results.update(doc_results)

        return results

    async def _handle_integrations(
        self, note_result: dict[str, Any], ai_analysis: dict[str, Any] | None
    ) -> dict[str, Any]:
        """統合処理を実行"""
        integration_results = {}

        if note_result.get("status") == "success":
            note_path = note_result.get("note_path")

            # デイリーノート統合
            if self.daily_integration and note_path:
                daily_result = (
                    await self.integration_handler.handle_daily_note_integration(
                        note_path, ai_analysis or {}
                    )
                )
                integration_results["daily_note"] = daily_result

        return integration_results

    # 互換性維持のための委譲メソッド
    async def _handle_capture_message(self, message) -> dict:
        """互換性維持: メッセージキャプチャ処理"""
        return await self.process_message(message)

    async def _handle_obsidian_note_creation(
        self, message, content: str, ai_analysis: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """互換性維持: Obsidian ノート作成"""
        return await self.note_creation_handler.handle_obsidian_note_creation(
            message, content, ai_analysis
        )

    async def _handle_audio_attachments(self, message, content: str) -> dict:
        """互換性維持: 音声添付ファイル処理"""
        return await self.attachment_handler.handle_audio_attachments(message, content)

    async def _handle_document_attachments(self, message) -> dict:
        """互換性維持: 文書添付ファイル処理"""
        return await self.attachment_handler.handle_document_attachments(message)

    async def _handle_daily_note_integration(
        self, note_path: str, ai_analysis: dict
    ) -> dict:
        """互換性維持: デイリーノート統合"""
        return await self.integration_handler.handle_daily_note_integration(
            note_path, ai_analysis
        )

    async def _handle_system_message(self, message_data: dict) -> None:
        """互換性維持: システムメッセージ処理"""
        await self.integration_handler.handle_system_message(message_data)

    # ヘルパーメソッド（既存コードとの互換性のため残す）
    def _extract_transcription_text(self, transcription_result: dict) -> str:
        return self.message_processor._extract_transcription_text(transcription_result)

    def _create_transcription_summary(self, transcript: str) -> str:
        return self.message_processor._create_transcription_summary(transcript)

    def _remove_bot_attribution_messages(self, content: str) -> str:
        return self.message_processor._remove_bot_attribution_messages(content)
