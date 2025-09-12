"""
Mock AI processor for development and testing
"""

import asyncio
import hashlib
from datetime import datetime
from typing import Any

from src.ai.models import (
    AIProcessingResult,
    CategoryResult,
    ProcessingCategory,
    ProcessingSettings,
    ProcessingStats,
    SummaryResult,
    TagResult,
)
from src.utils.mixins import LoggerMixin


class MockAIProcessor(LoggerMixin):
    """Mock AI processor that simulates Gemini API responses"""

    def __init__(self, settings: ProcessingSettings | None = None):
        self.settings = settings or ProcessingSettings()
        self.stats = ProcessingStats()
        self.cache: dict[str, Any] = {}

        # Mock responses for different types of content
        self.mock_summaries = [
            "これは重要な情報についてのメモです。",
            "今日の活動ログと振り返りの内容です。",
            "新しいアイデアやインサイトが含まれています。",
            "タスクや予定に関する情報です。",
            "技術的な内容や学習メモです。",
        ]

        self.mock_tags = [
            ["重要", "メモ", "記録"],
            ["活動", "振り返り", "日記"],
            ["アイデア", "企画", "創造"],
            ["タスク", "予定", "管理"],
            ["技術", "学習", "開発"],
        ]

        self.mock_categories = [
            ProcessingCategory.WORK,
            ProcessingCategory.LEARNING,
            ProcessingCategory.PROJECT,
            ProcessingCategory.LIFE,
            ProcessingCategory.IDEA,
        ]

        self.logger.info("Mock AI processor initialized")

    async def process_text(
        self, text: str, message_id: int | None = None, force_reprocess: bool = False
    ) -> AIProcessingResult:
        """Process text using mock responses"""

        # Simulate processing delay
        await asyncio.sleep(0.1)

        # Generate deterministic but varied responses based on content hash
        content_hash = hashlib.md5(text.encode()).hexdigest()
        hash_int = int(content_hash[:8], 16)

        # Use hash to select consistent responses for same content
        summary_idx = hash_int % len(self.mock_summaries)
        tag_idx = hash_int % len(self.mock_tags)
        category_idx = hash_int % len(self.mock_categories)

        # Create mock results
        summary = SummaryResult(
            summary=self.mock_summaries[summary_idx],
            key_points=["重要なポイント1", "重要なポイント2"],
            confidence_score=0.85,
            processing_time_ms=100,
            model_used="mock-gemini-pro",
        )

        tags = TagResult(
            tags=self.mock_tags[tag_idx],
            confidence_scores=dict.fromkeys(self.mock_tags[tag_idx], 0.8),
            processing_time_ms=50,
            model_used="mock-gemini-pro",
        )

        category = CategoryResult(
            category=self.mock_categories[category_idx],
            confidence_score=0.90,
            reasoning="Mock categorization based on content analysis",
            processing_time_ms=70,
            model_used="mock-gemini-pro",
        )

        # Create AIProcessingResult
        result = AIProcessingResult(
            message_id=message_id or 0,
            processed_at=datetime.now(),
            summary=summary,
            tags=tags,
            category=category,
            total_processing_time_ms=220,  # 100 + 50 + 70
            cache_hit=False,
            errors=[],
            warnings=[],
        )

        # Update stats
        self.stats.total_requests += 1
        self.stats.total_tokens_used += len(text.split())
        self.stats.cache_hits += 1 if not force_reprocess else 0

        self.logger.debug(
            "Mock AI processing completed",
            text_length=len(text),
            summary_length=len(summary.summary),
            tag_count=len(tags.tags),
            category=category.category,
        )

        return result

    def generate_content_hash(self, text: str) -> str:
        """Generate content hash for caching"""
        return hashlib.md5(text.encode()).hexdigest()

    def is_text_processable(self, text: str) -> bool:
        """Check if text is suitable for processing"""
        return len(text.strip()) >= self.settings.min_text_length

    async def process_url(self, url: str) -> str | None:
        """Mock URL processing"""
        await asyncio.sleep(0.2)

        self.logger.info("Mock URL processing", url=url)

        return f"模擬URL要約: {url} の内容です。重要な情報が含まれています。"

    async def analyze_notes_relationship(
        self, text: str, existing_notes: list[str]
    ) -> list[str]:
        """Mock note relationship analysis"""
        await asyncio.sleep(0.1)

        # Return some mock related notes
        mock_relations = ["[[関連ノート1]]", "[[類似トピック]]", "[[参考資料]]"]

        # Use text hash to determine number of relations
        hash_val = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        num_relations = (hash_val % 3) + 1

        return mock_relations[:num_relations]

    def get_stats(self) -> ProcessingStats:
        """Get processing statistics"""
        return self.stats

    def get_cache_info(self) -> dict[str, float]:
        """Get cache information"""
        return {
            "total_entries": len(self.cache),
            "memory_usage": 0.0,  # Mock value
            "hit_rate": 0.75 if self.stats.total_requests > 0 else 0.0,
        }

    def clear_cache(self) -> None:
        """Clear processing cache"""
        self.cache.clear()
        self.logger.info("Mock cache cleared")

    async def health_check(self) -> bool:
        """Mock health check - always returns True"""
        self.logger.debug("Mock AI processor health check - OK")
        return True

    async def summarize_url_content(self, content: str, url: str) -> str:
        """Mock URL content summarization"""
        await asyncio.sleep(0.1)  # Simulate processing
        return f"URL要約（モック）: {url[:50]}の内容についてのサマリーです。"

    async def generate_internal_links(
        self, content: str, related_notes: list[dict[str, Any]]
    ) -> list[str]:
        """Mock internal link generation"""
        await asyncio.sleep(0.1)  # Simulate processing
        # Extract note titles/names from the related notes dictionaries
        note_names = [note.get("title", note.get("name", "")) for note in related_notes]
        # Return first few note names as mock links
        return [name for name in note_names if name][:3]

    async def generate_embeddings(self, text: str) -> list[float]:
        """Mock embedding generation"""
        await asyncio.sleep(0.01)  # Simulate a small delay
        # Return a dummy embedding (e.g., a list of zeros or random numbers)
        # The length of the embedding vector can be arbitrary for a mock
        return [0.1] * 768  # Example: a 768-dimensional embedding vector of 0.1s
