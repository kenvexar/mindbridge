"""
Advanced message processing and metadata extraction
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict, cast

import aiofiles
import aiohttp
import discord

from src.utils.mixins import LoggerMixin


class ContentMetadata(TypedDict):
    raw_content: str
    cleaned_content: str
    word_count: int
    char_count: int
    line_count: int
    urls: list[str]
    mentions: dict[str, list[str]]
    code_blocks: int
    inline_code: int
    has_formatting: bool
    language: str | None


class BasicMetadata(TypedDict):
    id: int
    type: str
    flags: list[str]
    pinned: bool
    tts: bool
    author: dict[str, Any]
    channel: dict[str, Any]
    guild: dict[str, Any] | None


class DiscordFeatures(TypedDict):
    embeds: list[dict[str, Any]]
    reactions: list[dict[str, Any]]
    mentions: dict[str, Any]
    stickers: list[dict[str, Any]]


class ReferenceMetadata(TypedDict):
    is_reply: bool
    reply_to: dict[str, Any] | None
    mentions_reply_author: bool


class TimingMetadata(TypedDict):
    created_at: dict[str, Any]
    edited_at: dict[str, Any] | None
    age_seconds: int


class AttachmentMetadata(TypedDict):
    id: int
    filename: str
    size: int
    url: str
    proxy_url: str
    content_type: str | None
    width: int | None
    height: int | None
    ephemeral: bool
    description: str | None
    file_extension: str
    file_category: str
    is_spoiler: bool
    image_info: dict[str, Any] | None


class MessageMetadata(TypedDict):
    basic: BasicMetadata
    content: ContentMetadata
    attachments: list[AttachmentMetadata]
    references: ReferenceMetadata
    discord_features: DiscordFeatures
    timing: TimingMetadata


class MessageProcessor(LoggerMixin):
    """Advanced message processing and metadata extraction"""

    def __init__(self) -> None:
        self.url_pattern = re.compile(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
        )
        self.mention_patterns = {
            "user": re.compile(r"<@!?(\d+)>"),
            "channel": re.compile(r"<#(\d+)>"),
            "role": re.compile(r"<@&(\d+)>"),
            "emoji": re.compile(r"<a?:(\w+):(\d+)>"),
        }
        self.logger.info("Message processor initialized")

    def extract_metadata(self, message: discord.Message) -> MessageMetadata:
        """
        Extract comprehensive metadata from a Discord message

        Args:
            message: Discord message object

        Returns:
            Dictionary containing extracted metadata
        """
        metadata: MessageMetadata = {
            "basic": self._extract_basic_metadata(message),
            "content": self._extract_content_metadata(message),
            "attachments": self._extract_attachment_metadata(message),
            "references": self._extract_reference_metadata(message),
            "discord_features": self._extract_discord_features(message),
            "timing": self._extract_timing_metadata(message),
        }

        self.logger.debug(
            "Metadata extracted",
            message_id=message.id,
            content_length=len(message.content),
            attachment_count=len(message.attachments),
            url_count=(
                len(metadata["content"]["urls"])
                if "urls" in metadata["content"]
                and isinstance(metadata["content"]["urls"], list | tuple)
                else 0
            ),
        )

        return metadata

    def _extract_basic_metadata(self, message: discord.Message) -> BasicMetadata:
        """Extract basic message information"""
        # Safely extract flags
        flags_list = []
        # discord.MessageFlags の各フラグを明示的にチェック
        if message.flags.crossposted:
            flags_list.append("crossposted")

        if message.flags.suppress_embeds:
            flags_list.append("suppress_embeds")
        if message.flags.source_message_deleted:
            flags_list.append("source_message_deleted")
        if message.flags.urgent:
            flags_list.append("urgent")
        if message.flags.has_thread:
            flags_list.append("has_thread")
        if message.flags.ephemeral:
            flags_list.append("ephemeral")
        if message.flags.loading:
            flags_list.append("loading")
        if message.flags.failed_to_mention_some_roles_in_thread:
            flags_list.append("failed_to_mention_some_roles_in_thread")
        if message.flags.suppress_notifications:
            flags_list.append("suppress_notifications")

        return {
            "id": message.id,
            "type": str(message.type),
            "flags": flags_list,
            "pinned": message.pinned,
            "tts": message.tts,
            "author": {
                "id": message.author.id,
                "name": message.author.display_name,
                "username": message.author.name,
                "discriminator": message.author.discriminator,
                "bot": message.author.bot,
                "avatar_url": (
                    str(message.author.avatar.url) if message.author.avatar else None
                ),
                "mention": message.author.mention,
            },
            "channel": {
                "id": message.channel.id,
                "name": getattr(message.channel, "name", "Unknown"),
                "type": str(message.channel.type),
                "category": (
                    getattr(message.channel.category, "name", None)
                    if hasattr(message.channel, "category")
                    else None
                ),
            },
            "guild": (
                {
                    "id": message.guild.id if message.guild else None,
                    "name": message.guild.name if message.guild else None,
                }
                if message.guild
                else None
            ),
        }

    def _extract_content_metadata(self, message: discord.Message) -> ContentMetadata:
        """Extract content-related metadata"""
        content = message.content

        # Extract URLs
        urls = self.url_pattern.findall(content)

        # Extract mentions
        mentions: dict[str, list[str]] = {}
        for mention_type, pattern in self.mention_patterns.items():
            matches_raw: list[Any] = pattern.findall(content)
            # matches_raw は list[str] または list[tuple[str, ...]] の可能性がある
            # ここでは、グループが 1 つなので list[str] に変換
            matches = [m[0] if isinstance(m, tuple) else m for m in matches_raw]
            mentions[mention_type] = matches

        # Analyze content characteristics
        word_count = len(content.split()) if content else 0
        char_count = len(content)
        line_count = content.count("\n") + 1 if content else 0

        # Check for code blocks
        code_blocks = re.findall(r"```[\s\S]*?```", content)
        inline_code = re.findall(r"`[^`]+`", content)

        return cast(
            "ContentMetadata",
            {
                "raw_content": content,
                "cleaned_content": self._clean_content(content),
                "word_count": word_count,
                "char_count": char_count,
                "line_count": line_count,
                "urls": urls,
                "mentions": mentions,
                "code_blocks": len(code_blocks),
                "inline_code": len(inline_code),
                "has_formatting": self._has_markdown_formatting(content),
                "language": self._detect_language(content),
            },
        )

    def _extract_attachment_metadata(
        self, message: discord.Message
    ) -> list[AttachmentMetadata]:
        """Extract detailed attachment metadata"""
        attachments = []

        for attachment in message.attachments:
            file_category = self._categorize_file(attachment)

            attachment_data: AttachmentMetadata = {
                "id": attachment.id,
                "filename": attachment.filename,
                "size": attachment.size,
                "url": attachment.url,
                "proxy_url": attachment.proxy_url,
                "content_type": attachment.content_type,
                "width": attachment.width,
                "height": attachment.height,
                "ephemeral": attachment.ephemeral,
                "description": attachment.description,
                "file_extension": Path(attachment.filename).suffix.lower(),
                "file_category": file_category,
                "is_spoiler": attachment.is_spoiler(),
                "image_info": None,  # デフォルト値を追加
            }

            # Additional analysis for specific file types
            if attachment_data["file_category"] == "image":
                attachment_data["image_info"] = {
                    "dimensions": (
                        f"{attachment.width}x{attachment.height}"
                        if attachment.width and attachment.height
                        else None
                    ),
                    "aspect_ratio": (
                        attachment.width / attachment.height
                        if attachment.width and attachment.height
                        else None
                    ),
                }

            attachments.append(attachment_data)

        return attachments

    def _extract_reference_metadata(
        self, message: discord.Message
    ) -> ReferenceMetadata:
        """Extract message reference information (replies, etc.)"""
        reference_data: ReferenceMetadata = {
            "is_reply": message.reference is not None,
            "reply_to": None,
            "mentions_reply_author": False,
        }

        if message.reference:
            reference_data["reply_to"] = {
                "message_id": message.reference.message_id,
                "channel_id": message.reference.channel_id,
                "guild_id": message.reference.guild_id,
            }

            # Check if the reply mentions the original author
            if message.reference.resolved and isinstance(
                message.reference.resolved, discord.Message
            ):
                original_author_id = message.reference.resolved.author.id
                reference_data["mentions_reply_author"] = any(
                    user.id == original_author_id for user in message.mentions
                )

        return reference_data

    def _extract_discord_features(self, message: discord.Message) -> DiscordFeatures:
        """Extract Discord-specific features"""
        return cast(
            "DiscordFeatures",
            {
                "embeds": [
                    {
                        "type": embed.type,
                        "title": embed.title,
                        "description": embed.description,
                        "url": embed.url,
                        "color": getattr(embed.color, "value", None)
                        if embed.color is not None
                        else None,
                        "field_count": len(embed.fields),
                    }
                    for embed in message.embeds
                ],
                "reactions": [
                    {
                        "emoji": str(reaction.emoji),
                        "count": reaction.count,
                        "me": reaction.me,
                    }
                    for reaction in message.reactions
                ],
                "mentions": {
                    "users": [
                        {
                            "id": user.id,
                            "name": user.display_name,
                            "username": user.name,
                        }
                        for user in message.mentions
                    ],
                    "roles": [
                        {
                            "id": role.id,
                            "name": role.name,
                            "color": role.color.value,
                        }
                        for role in message.role_mentions
                    ],
                    "channels": [
                        {
                            "id": channel.id,
                            "name": channel.name,
                            "type": str(channel.type),
                        }
                        for channel in message.channel_mentions
                    ],
                    "everyone": message.mention_everyone,
                },
                "stickers": [
                    {
                        "id": sticker.id,
                        "name": sticker.name,
                        "format": str(sticker.format),
                        "url": sticker.url,
                    }
                    for sticker in message.stickers
                ],
            },
        )

    def _extract_timing_metadata(self, message: discord.Message) -> TimingMetadata:
        """Extract timing-related metadata"""
        created_at = message.created_at
        edited_at = message.edited_at

        # Convert to local timezone for better usability
        created_at.replace(tzinfo=UTC)
        edited_at.replace(tzinfo=UTC) if edited_at else None

        return {
            "created_at": {
                "iso": created_at.isoformat(),
                "timestamp": int(created_at.timestamp()),
                "date": created_at.strftime("%Y-%m-%d"),
                "time": created_at.strftime("%H:%M:%S"),
                "weekday": created_at.strftime("%A"),
                "hour": created_at.hour,
            },
            "edited_at": (
                {
                    "iso": edited_at.isoformat() if edited_at else None,
                    "timestamp": int(edited_at.timestamp()) if edited_at else None,
                    "was_edited": edited_at is not None,
                }
                if edited_at
                else {"was_edited": False}
            ),
            "age_seconds": int(
                (datetime.now(UTC) - created_at.replace(tzinfo=UTC)).total_seconds()
            ),
        }

    def _clean_content(self, content: str) -> str:
        """Clean message content for processing"""
        if not content:
            return ""

        # Remove Discord formatting
        cleaned = content

        # Remove mentions
        for pattern in self.mention_patterns.values():
            cleaned = pattern.sub("", cleaned)

        # Remove URLs
        cleaned = self.url_pattern.sub("", cleaned)

        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    def _has_markdown_formatting(self, content: str) -> bool:
        """Check if content contains Markdown formatting"""
        if not content:
            return False

        markdown_patterns = [
            r"\*\*.*?\*\*",  # Bold
            r"\*.*?\*",  # Italic
            r"__.*?__",  # Underline
            r"~~.*?~~",  # Strikethrough
            r"`.*?`",  # Inline code
            r"```[\s\S]*?```",  # Code blocks
            r"> .*",  # Quotes
        ]

        return any(re.search(pattern, content) for pattern in markdown_patterns)

    def _detect_language(self, content: str) -> str | None:
        """Basic language detection for content"""
        if not content:
            return None

        # Simple heuristics for Japanese vs English
        japanese_chars = re.findall(
            r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]", content
        )
        english_chars = re.findall(r"[a-zA-Z]", content)

        if len(japanese_chars) > len(english_chars):
            return "ja"
        if len(english_chars) > 0:
            return "en"

        return "unknown"

    def _categorize_file(self, attachment: discord.Attachment) -> str:
        """Categorize file type based on extension and content type"""
        extension = Path(attachment.filename).suffix.lower()
        content_type = attachment.content_type or ""

        # Image files
        if extension in {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
            ".svg",
            ".bmp",
        } or content_type.startswith("image/"):
            return "image"

        # Audio files
        if extension in {
            ".mp3",
            ".wav",
            ".ogg",
            ".m4a",
            ".flac",
            ".aac",
        } or content_type.startswith("audio/"):
            return "audio"

        # Video files
        if extension in {
            ".mp4",
            ".mov",
            ".avi",
            ".mkv",
            ".webm",
            ".flv",
        } or content_type.startswith("video/"):
            return "video"

        # Document files
        if extension in {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt"}:
            return "document"

        # Archive files
        if extension in {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"}:
            return "archive"

        # Code files
        if extension in {
            ".py",
            ".js",
            ".html",
            ".css",
            ".json",
            ".xml",
            ".yml",
            ".yaml",
            ".md",
        }:
            return "code"

        return "other"

    async def download_attachment(
        self, attachment: discord.Attachment, save_path: Path
    ) -> bool:
        """
        Download attachment to local filesystem

        Args:
            attachment: Discord attachment object
            save_path: Path where to save the file

        Returns:
            True if download was successful, False otherwise
        """
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)

            async with (
                aiohttp.ClientSession() as session,
                session.get(attachment.url) as response,
            ):
                if response.status == 200:
                    async with aiofiles.open(save_path, "wb") as file:
                        async for chunk in response.content.iter_chunked(8192):
                            await file.write(chunk)

                    self.logger.info(
                        "Attachment downloaded",
                        filename=attachment.filename,
                        size=attachment.size,
                        save_path=str(save_path),
                    )
                    return True
                self.logger.error(
                    "Failed to download attachment",
                    filename=attachment.filename,
                    status=response.status,
                )
                return False

        except Exception as e:
            self.logger.error(
                "Error downloading attachment",
                filename=attachment.filename,
                error=str(e),
                exc_info=True,
            )
            return False
