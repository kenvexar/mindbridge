"""
Mock AI processor for development and testing
"""

import asyncio
import hashlib
from datetime import datetime
from typing import Any, TypedDict

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


class MockSample(TypedDict):
    language: str
    summary: str
    key_points: list[str]
    tags: list[str]
    category: ProcessingCategory


class MockAIProcessor(LoggerMixin):
    """Mock AI processor that simulates Gemini API responses"""

    def __init__(
        self,
        settings: ProcessingSettings | None = None,
        preferred_languages: list[str] | None = None,
    ):
        self.settings = settings or ProcessingSettings()
        self.stats = ProcessingStats()
        self.cache: dict[str, Any] = {}

        # Mock responses grouped by language for broader coverage
        self._mock_samples: list[MockSample] = [
            {
                "language": "ja",
                "summary": "これは重要な情報についてのメモです。",
                "key_points": ["重要なポイント 1", "重要なポイント 2"],
                "tags": ["重要", "メモ", "記録"],
                "category": ProcessingCategory.WORK,
            },
            {
                "language": "ja",
                "summary": "今日の活動ログと振り返りの内容です。",
                "key_points": ["活動の振り返り", "次のアクション"],
                "tags": ["活動", "振り返り", "日記"],
                "category": ProcessingCategory.LIFE,
            },
            {
                "language": "ja",
                "summary": "新しいアイデアやインサイトが含まれています。",
                "key_points": ["新規アイデアの概要", "検討が必要な点"],
                "tags": ["アイデア", "企画", "創造"],
                "category": ProcessingCategory.IDEA,
            },
            {
                "language": "en",
                "summary": "This is a concise project status update with next steps.",
                "key_points": ["Summarize progress", "List follow-up owners"],
                "tags": ["project", "status", "update"],
                "category": ProcessingCategory.PROJECT,
            },
            {
                "language": "en",
                "summary": "Notes from today's learning session and key takeaways.",
                "key_points": ["Main takeaway", "Topics to revisit"],
                "tags": ["learning", "notes", "recap"],
                "category": ProcessingCategory.LEARNING,
            },
            {
                "language": "en",
                "summary": "Outline of the tasks scheduled for this week.",
                "key_points": ["Prioritize critical tasks", "Schedule review meeting"],
                "tags": ["tasks", "planning", "weekly"],
                "category": ProcessingCategory.TASKS,
            },
        ]

        self.preferred_languages = (
            [lang.lower() for lang in preferred_languages]
            if preferred_languages
            else ["ja", "en"]
        )

        self.logger.info(
            "Mock AI processor initialized",
            available_languages=list(self.available_languages),
            preferred_languages=self.preferred_languages,
        )

    @property
    def available_languages(self) -> set[str]:
        """Return languages supported by the mock dataset."""
        return {sample["language"] for sample in self._mock_samples}

    def set_preferred_languages(self, languages: list[str] | None) -> None:
        """Restrict mock responses to specific languages."""
        if not languages:
            self.preferred_languages = list(self.available_languages)
        else:
            self.preferred_languages = [lang.lower() for lang in languages]

    async def process_message(self, message_data: dict[str, Any]) -> AIProcessingResult:
        """Process message data (used by MessageHandler)"""
        content = message_data.get("content", "")
        message_id = message_data.get("id")
        return await self.process_text(content, message_id)

    async def process_text(
        self, text: str, message_id: int | None = None, force_reprocess: bool = False
    ) -> AIProcessingResult:
        """Process text using mock responses"""

        # Simulate processing delay
        await asyncio.sleep(0.1)

        # Generate deterministic but varied responses based on content hash
        content_hash = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()
        hash_int = int(content_hash[:8], 16)

        # Filter samples by requested languages (fallback to full dataset)
        samples = [
            sample
            for sample in self._mock_samples
            if sample["language"] in self.preferred_languages
        ] or self._mock_samples

        selected = samples[hash_int % len(samples)]

        # Create mock results
        summary = SummaryResult(
            summary=selected["summary"],
            key_points=selected["key_points"],
            confidence_score=0.85,
            processing_time_ms=100,
            model_used="mock-gemini-pro",
        )

        tags = TagResult(
            tags=selected["tags"],
            confidence_scores={tag: 0.8 for tag in selected["tags"]},
            processing_time_ms=50,
            model_used="mock-gemini-pro",
        )

        category = CategoryResult(
            category=selected["category"],
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
            language=selected["language"],
        )

        return result

    def generate_content_hash(self, text: str) -> str:
        """Generate content hash for caching"""
        return hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()

    def is_text_processable(self, text: str) -> bool:
        """Check if text is suitable for processing"""
        return len(text.strip()) >= self.settings.min_text_length

    async def process_url(self, url: str) -> str | None:
        """Mock URL processing"""
        await asyncio.sleep(0.2)

        self.logger.info("Mock URL processing", url=url)

        return f"模擬 URL 要約: {url} の内容です。重要な情報が含まれています。"

    async def analyze_notes_relationship(
        self, text: str, existing_notes: list[str]
    ) -> list[str]:
        """Mock note relationship analysis"""
        await asyncio.sleep(0.1)

        # Return some mock related notes
        mock_relations = ["[[関連ノート 1]]", "[[類似トピック]]", "[[参考資料]]"]

        # Use text hash to determine number of relations
        hash_val = int(
            hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()[:8], 16
        )
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
        return f"URL 要約（モック）: {url[:50]}の内容についてのサマリーです。"

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
