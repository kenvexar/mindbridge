"""
AI処理モジュール
"""

from src.ai.gemini_client import GeminiAPIError, GeminiClient, RateLimitExceeded
from src.ai.models import (
    AIModelConfig,
    AIProcessingResult,
    CategoryResult,
    ProcessingCategory,
    ProcessingPriority,
    ProcessingRequest,
    ProcessingSettings,
    ProcessingStats,
    SummaryResult,
    TagResult,
)
from src.ai.note_analyzer import AdvancedNoteAnalyzer
from src.ai.processor import AIProcessor
from src.ai.url_processor import URLContentExtractor

# 高度なAI機能
from src.ai.vector_store import NoteEmbedding, SemanticSearchResult, VectorStore

__all__ = [
    # クライアント
    "GeminiClient",
    "GeminiAPIError",
    "RateLimitExceeded",
    # モデル
    "AIModelConfig",
    "AIProcessingResult",
    "CategoryResult",
    "ProcessingCategory",
    "ProcessingPriority",
    "ProcessingRequest",
    "ProcessingSettings",
    "ProcessingStats",
    "SummaryResult",
    "TagResult",
    # プロセッサ
    "AIProcessor",
    # 高度なAI機能
    "VectorStore",
    "NoteEmbedding",
    "SemanticSearchResult",
    "URLContentExtractor",
    "AdvancedNoteAnalyzer",
]
