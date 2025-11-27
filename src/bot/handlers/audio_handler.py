"""Audio handling functionality for Discord messages."""

from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING, Any

import discord

from src.utils.mixins import LoggerMixin

if TYPE_CHECKING:
    from src.audio.speech_processor import SpeechProcessor


class AudioHandler(LoggerMixin):
    """音声ファイル処理専用ハンドラー"""

    def __init__(self, speech_processor: "SpeechProcessor | None" = None) -> None:
        self.speech_processor = speech_processor
        self._processed_attachment_keys: dict[str, set[str]] = {}
        self._recent_messages: deque[str] = deque()
        self._max_recent_messages = 512

    @staticmethod
    def _get_channel_name(channel_info: Any) -> str:
        """Safely obtain channel name from various channel representations."""
        if hasattr(channel_info, "name"):
            name = channel_info.name
            if isinstance(name, str):
                return name
        if isinstance(channel_info, dict):
            name = channel_info.get("name")
            if isinstance(name, str):
                return name
        return "unknown"

    @staticmethod
    def _build_attachment_identity(attachment: dict[str, Any]) -> str:
        """添付ファイルを一意に識別するキーを生成"""
        attachment_id = attachment.get("id")
        if attachment_id is not None:
            return f"id:{attachment_id}"

        url = attachment.get("url")
        if url:
            return f"url:{url}"

        proxy_url = attachment.get("proxy_url")
        if proxy_url:
            return f"proxy:{proxy_url}"

        filename = attachment.get("filename")
        size = attachment.get("size")
        if filename and size is not None:
            return f"name:{filename}|size:{size}"
        if filename:
            return f"name:{filename}"

        # 最後の手段として辞書内容を利用（順序を固定化）
        items = tuple(sorted(attachment.items()))
        return f"data:{items}"

    def _normalize_message_identity(
        self,
        message_data: dict[str, Any],
        original_message: discord.Message | None,
    ) -> str | None:
        """メッセージを一意に識別する ID を取得"""
        if original_message and getattr(original_message, "id", None) is not None:
            return str(original_message.id)

        metadata = (
            message_data.get("metadata") if isinstance(message_data, dict) else None
        )
        if isinstance(metadata, dict):
            basic_info = metadata.get("basic")
            if isinstance(basic_info, dict):
                message_id = basic_info.get("id")
                if message_id is not None:
                    return str(message_id)

        message_id = message_data.get("id") if isinstance(message_data, dict) else None
        if message_id is not None:
            return str(message_id)

        return None

    def _get_or_create_processed_set(self, message_identity: str | None) -> set[str]:
        """メッセージ単位の処理済み添付セットを取得"""
        if message_identity is None:
            return set()

        processed = self._processed_attachment_keys.get(message_identity)
        if processed is None:
            processed = set()
            self._processed_attachment_keys[message_identity] = processed
            self._recent_messages.append(message_identity)
            while len(self._recent_messages) > self._max_recent_messages:
                oldest = self._recent_messages.popleft()
                self._processed_attachment_keys.pop(oldest, None)

        return processed

    async def handle_audio_attachments(
        self,
        message_data: dict[str, Any],
        channel_info: Any,
        original_message: discord.Message | None = None,
    ) -> None:
        """音声添付ファイルの処理（リアルタイムフィードバック付き）"""
        try:
            metadata = message_data.get("metadata", {})
            attachments = metadata.get("attachments", [])

            # Fallback: build metadata from the raw Discord attachments when
            # structured metadata is not yet available (e.g. voice messages
            # with empty message content).
            if not attachments and original_message and original_message.attachments:
                fallback_attachments: list[dict[str, Any]] = []
                for discord_attachment in original_message.attachments:
                    filename = discord_attachment.filename or "audio"
                    content_type = discord_attachment.content_type or ""
                    is_audio = False
                    if content_type.startswith("audio/"):
                        is_audio = True
                    elif self.speech_processor:
                        try:
                            is_audio = self.speech_processor.is_audio_file(filename)
                        except Exception:  # pragma: no cover - defensive
                            is_audio = False

                    fallback_attachments.append(
                        {
                            "id": discord_attachment.id,
                            "filename": filename,
                            "size": discord_attachment.size,
                            "url": discord_attachment.url,
                            "proxy_url": discord_attachment.proxy_url,
                            "content_type": content_type,
                            "file_extension": Path(filename).suffix.lower(),
                            "file_category": "audio" if is_audio else "other",
                        }
                    )

                if fallback_attachments:
                    attachments = fallback_attachments
                    metadata["attachments"] = fallback_attachments
                    # message_data may be reused later (AI processing), so keep
                    # the reconstructed metadata.
                    message_data["metadata"] = metadata
                    self.logger.debug(
                        "Reconstructed attachment metadata from Discord payload",
                        attachment_count=len(fallback_attachments),
                    )

            channel_name = self._get_channel_name(channel_info)
            message_identity = self._normalize_message_identity(
                message_data, original_message
            )
            processed_for_message = self._get_or_create_processed_set(message_identity)
            seen_attachments: set[str] = set()

            # Log attachment information
            self.logger.debug(
                f"handle_audio_attachments called with {len(attachments)} total attachments"
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

            unique_audio_attachments: list[tuple[dict[str, Any], bool]] = []
            for att in audio_attachments:
                identity = self._build_attachment_identity(att)
                already_processed = identity in processed_for_message
                has_transcription = bool(
                    message_data.get("metadata", {})
                    .get("content", {})
                    .get("audio_transcription_data")
                )

                if identity in seen_attachments:
                    self.logger.debug(
                        "Skipping duplicate audio attachment in current batch",
                        identity=identity,
                        filename=att.get("filename"),
                    )
                    continue

                seen_attachments.add(identity)

                suppress_feedback = False
                if already_processed:
                    if has_transcription:
                        self.logger.debug(
                            "Skipping already processed audio attachment with existing transcription",
                            identity=identity,
                            filename=att.get("filename"),
                        )
                        continue

                    self.logger.debug(
                        "Reprocessing audio attachment to generate transcription data",
                        identity=identity,
                        filename=att.get("filename"),
                    )
                    suppress_feedback = True

                unique_audio_attachments.append((att, suppress_feedback))
                if message_identity is not None:
                    processed_for_message.add(identity)

            if len(unique_audio_attachments) != len(audio_attachments):
                self.logger.info(
                    "Detected duplicate audio attachments",
                    original_count=len(audio_attachments),
                    unique_count=len(unique_audio_attachments),
                )

            self.logger.info(
                "Processing audio attachments",
                count=len(unique_audio_attachments),
                channel=channel_name,
            )

            for attachment, suppress_feedback in unique_audio_attachments:
                self.logger.debug(
                    f"Processing audio attachment: {attachment.get('filename', 'N/A')}"
                )

                # 個別音声処理を実行（エラーハンドリング強化）
                try:
                    self.logger.info(
                        f"About to call process_single_audio_attachment for {attachment.get('filename', 'N/A')}"
                    )
                    await self.process_single_audio_attachment(
                        attachment,
                        message_data,
                        channel_info,
                        original_message,
                        suppress_feedback=suppress_feedback,
                    )
                    self.logger.info(
                        f"Completed process_single_audio_attachment for {attachment.get('filename', 'N/A')}"
                    )
                except Exception as e:
                    self.logger.error(
                        "Error in process_single_audio_attachment",
                        filename=attachment.get("filename", "N/A"),
                        error=str(e),
                        exc_info=True,
                    )
                    # 個別エラーでも他の音声ファイル処理を継続

        except Exception as e:
            self.logger.error(
                "Error processing audio attachments",
                channel_name=channel_name,
                error=str(e),
                exc_info=True,
            )

    async def process_single_audio_attachment(
        self,
        attachment: dict[str, Any],
        message_data: dict[str, Any],
        channel_info: Any,
        original_message: discord.Message | None = None,
        *,
        suppress_feedback: bool = False,
    ) -> None:
        """単一の音声添付ファイルを処理"""
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
            if original_message and not suppress_feedback:
                try:
                    feedback_message = await original_message.reply(
                        f"🎤 音声ファイル `{filename}` の文字起こしを開始します..."
                    )
                except Exception as e:
                    self.logger.warning("Failed to send feedback message", error=str(e))

            # 音声ファイルをダウンロード
            audio_data = await self.download_attachment(attachment_url)
            if not audio_data:
                self.logger.error(f"Failed to download audio file: {filename}")
                await self.update_feedback_message(
                    feedback_message,
                    f"❌ 音声ファイル `{filename}` のダウンロードに失敗しました。",
                )
                return

            # 音声を文字起こし
            if not self.speech_processor:
                self.logger.error("Speech processor not initialized")
                await self.update_feedback_message(
                    feedback_message,
                    "❌ 音声処理システムが初期化されていません。",
                )
                return

            channel_name = self._get_channel_name(channel_info)
            audio_result = await self.speech_processor.process_audio_file(
                file_data=audio_data,
                filename=filename,
                channel_name=channel_name,
            )

            # 結果に応じてフィードバックを更新
            if audio_result.success and audio_result.transcription:
                success_msg = (
                    f"音声文字起こしが完了しました！\n"
                    f"📝 **ファイル**: `{filename}`\n"
                    f"📊 **信頼度**: {audio_result.transcription.confidence:.2f}\n"
                    f"📄 ノートが Obsidian に保存されました。"
                )
                await self.update_feedback_message(feedback_message, success_msg)

                # 文字起こし結果をメッセージデータに統合
                await self._integrate_audio_transcription(
                    message_data, audio_result, channel_info
                )
            else:
                if audio_result.fallback_used:
                    fallback_msg = (
                        f"⚠️ 音声文字起こしが制限されました\n"
                        f"📝 **ファイル**: `{filename}`\n"
                        f"📊 **理由**: {audio_result.fallback_reason}\n"
                        f"📁 音声ファイルは Obsidian に保存されました。"
                    )
                    await self.update_feedback_message(feedback_message, fallback_msg)
                else:
                    error_msg = (
                        f"❌ 音声文字起こしに失敗しました\n"
                        f"📝 **ファイル**: `{filename}`\n"
                        f"⚠️ **エラー**: {audio_result.error_message or '不明なエラー'}"
                    )
                    await self.update_feedback_message(feedback_message, error_msg)

        except Exception as e:
            self.logger.error(
                "Error processing single audio attachment",
                filename=attachment.get("filename", "unknown"),
                error=str(e),
                exc_info=True,
            )

            error_msg = (
                f"❌ 音声処理中に予期しないエラーが発生しました\n"
                f"📝 **ファイル**: `{attachment.get('filename', 'unknown')}`\n"
                f"⚠️ **エラー**: {str(e)}"
            )
            await self.update_feedback_message(feedback_message, error_msg)

    async def _integrate_audio_transcription(
        self, message_data: dict[str, Any], audio_result: Any, channel_info: Any
    ) -> None:
        """音声転写結果をメッセージデータに統合"""
        try:
            if "metadata" not in message_data:
                message_data["metadata"] = {}
            if "content" not in message_data["metadata"]:
                message_data["metadata"]["content"] = {}

            # 音声転写データを追加
            message_data["metadata"]["content"]["audio_transcription_data"] = {
                "transcript": audio_result.transcription.transcript,
                "confidence": audio_result.transcription.confidence,
                "confidence_level": audio_result.transcription.confidence_level,
                "fallback_used": audio_result.fallback_used,
                "fallback_reason": audio_result.fallback_reason,
                "saved_file_path": getattr(audio_result, "saved_file_path", None),
            }

            content_meta = message_data["metadata"]["content"]
            transcript = audio_result.transcription.transcript
            if transcript:
                if not content_meta.get("raw_content"):
                    content_meta["raw_content"] = transcript
                if not message_data.get("content"):
                    message_data["content"] = transcript

        except Exception as e:
            self.logger.error("Failed to integrate audio transcription", error=str(e))

    async def download_attachment(self, attachment_url: str) -> bytes | None:
        """添付ファイルをダウンロード（セキュリティ強化版）"""
        try:
            from urllib.parse import urlparse

            import aiohttp

            # セキュリティ: URL の検証
            if not attachment_url or not isinstance(attachment_url, str):
                self.logger.warning(
                    "Invalid URL provided for attachment download", url=attachment_url
                )
                return None

            # セキュリティ: Discord CDN URL の検証
            allowed_domains = {
                "cdn.discordapp.com",
                "media.discordapp.net",
                "discord.com",
            }

            parsed_url = urlparse(attachment_url)
            if parsed_url.hostname not in allowed_domains:
                self.logger.warning(
                    "Rejected attachment download from unauthorized domain",
                    url=attachment_url,
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
                async with session.get(attachment_url) as response:
                    if response.status != 200:
                        self.logger.error(
                            "Failed to download attachment",
                            url=attachment_url,
                            status=response.status,
                        )
                        return None

                    # セキュリティ: Content-Length チェック
                    content_length = response.headers.get("Content-Length")
                    if content_length and int(content_length) > MAX_FILE_SIZE:
                        self.logger.warning(
                            "Rejected attachment download due to size limit",
                            url=attachment_url,
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
                            url=attachment_url,
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
                                url=attachment_url,
                                downloaded_size=len(data),
                                max_size=MAX_FILE_SIZE,
                            )
                            return None

                    # セキュリティ: マジックバイト検証
                    if len(data) < 12:
                        self.logger.warning(
                            "Rejected attachment download due to insufficient data",
                            url=attachment_url,
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
                            url=attachment_url,
                            header=header.hex()[:24],  # 最初の 12 バイトの hex 表示
                        )
                        return None

                    self.logger.info(
                        "Successfully downloaded and validated audio attachment",
                        url=attachment_url,
                        size=len(data),
                        content_type=content_type,
                    )

                    return bytes(data)

        except Exception as e:
            self.logger.error(
                "Error downloading attachment",
                url=attachment_url,
                error=str(e),
                exc_info=True,
            )
            return None

    async def update_feedback_message(
        self, feedback_message: discord.Message | None, content: str
    ) -> None:
        """フィードバックメッセージを更新"""
        if feedback_message:
            try:
                await feedback_message.edit(content=content)
            except Exception as e:
                self.logger.warning("Failed to update feedback message", error=str(e))
