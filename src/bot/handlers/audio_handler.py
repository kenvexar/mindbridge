"""
Audio handling functionality for Discord messages
"""

from typing import Any

import discord

from src.utils.mixins import LoggerMixin


class AudioHandler(LoggerMixin):
    """音声ファイル処理専用ハンドラー"""

    def __init__(self, speech_processor=None):
        self.speech_processor = speech_processor

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
                        f"About to call process_single_audio_attachment for {attachment.get('filename', 'N/A')}"
                    )
                    await self.process_single_audio_attachment(
                        attachment, message_data, channel_info, original_message
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
                channel_name=channel_info.name,
                error=str(e),
                exc_info=True,
            )

    async def process_single_audio_attachment(
        self,
        attachment: dict[str, Any],
        message_data: dict[str, Any],
        channel_info: Any,
        original_message: discord.Message | None = None,
    ) -> None:
        """単一の音声添付ファイルを処理"""
        # この実装は元のメソッドから移動予定
        # TODO: MessageHandler から_process_single_audio_attachment を移動
        pass

    async def download_attachment(self, attachment_url: str) -> bytes | None:
        """添付ファイルをダウンロード"""
        # この実装は元のメソッドから移動予定
        # TODO: MessageHandler から_download_attachment を移動
        pass

    async def update_feedback_message(
        self, feedback_message: discord.Message | None, content: str
    ) -> None:
        """フィードバックメッセージを更新"""
        if feedback_message:
            try:
                await feedback_message.edit(content=content)
            except Exception as e:
                self.logger.warning("Failed to update feedback message", error=str(e))
