"""
Data models for Discord message processing
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FileCategory(Enum):
    """File categorization enum"""

    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    CODE = "code"
    OTHER = "other"


class AuthorInfo(BaseModel):
    """Discord user information"""

    id: int
    name: str
    username: str
    discriminator: str
    bot: bool
    avatar_url: str | None = None
    mention: str


class ChannelInfo(BaseModel):
    """Discord channel information"""

    id: int
    name: str
    type: str
    category: str | None = None


class GuildInfo(BaseModel):
    """Discord guild information"""

    id: int
    name: str


class AttachmentInfo(BaseModel):
    """Discord attachment information"""

    id: int
    filename: str
    size: int
    url: str
    proxy_url: str
    content_type: str | None = None
    width: int | None = None
    height: int | None = None
    ephemeral: bool
    description: str | None = None
    file_extension: str
    file_category: FileCategory
    is_spoiler: bool
    image_info: dict[str, Any] | None = None


class MentionInfo(BaseModel):
    """Message mention information"""

    users: list[dict[str, Any]] = Field(default_factory=list)
    roles: list[dict[str, Any]] = Field(default_factory=list)
    channels: list[dict[str, Any]] = Field(default_factory=list)
    everyone: bool = False


class EmbedInfo(BaseModel):
    """Discord embed information"""

    type: str
    title: str | None = None
    description: str | None = None
    url: str | None = None
    color: int | None = None
    field_count: int


class ReactionInfo(BaseModel):
    """Discord reaction information"""

    emoji: str
    count: int
    me: bool


class StickerInfo(BaseModel):
    """Discord sticker information"""

    id: int
    name: str
    format: str
    url: str


class ReferenceInfo(BaseModel):
    """Message reference information (replies)"""

    is_reply: bool
    reply_to: dict[str, int] | None = None
    mentions_reply_author: bool = False


class TimingInfo(BaseModel):
    """Message timing information"""

    created_at: dict[str, Any]
    edited_at: dict[str, Any]
    age_seconds: int


class ContentInfo(BaseModel):
    """Message content analysis"""

    raw_content: str
    cleaned_content: str
    word_count: int
    char_count: int
    line_count: int
    urls: list[str] = Field(default_factory=list)
    mentions: dict[str, list[Any]] = Field(default_factory=dict)
    code_blocks: int = 0
    inline_code: int = 0
    has_formatting: bool = False
    language: str | None = None


class DiscordFeatures(BaseModel):
    """Discord-specific features"""

    embeds: list[EmbedInfo] = Field(default_factory=list)
    reactions: list[ReactionInfo] = Field(default_factory=list)
    mentions: MentionInfo = Field(default_factory=MentionInfo)
    stickers: list[StickerInfo] = Field(default_factory=list)


class BasicMetadata(BaseModel):
    """Basic message metadata"""

    id: int
    type: str
    flags: list[str] = Field(default_factory=list)
    pinned: bool = False
    tts: bool = False
    author: AuthorInfo
    channel: ChannelInfo
    guild: GuildInfo | None = None


class MessageMetadata(BaseModel):
    """Complete message metadata"""

    basic: BasicMetadata
    content: ContentInfo
    attachments: list[AttachmentInfo] = Field(default_factory=list)
    references: ReferenceInfo
    discord_features: DiscordFeatures
    timing: TimingInfo


class ProcessedMessage(BaseModel):
    """Processed Discord message with complete metadata"""

    metadata: MessageMetadata
    channel_info: dict[str, str]
    processing_timestamp: str

    model_config = ConfigDict(use_enum_values=True)
