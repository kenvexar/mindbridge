import pytest

from src.ai.mock_processor import MockAIProcessor


@pytest.mark.asyncio
async def test_mock_ai_processor_prefers_requested_language():
    """MockAIProcessor should select samples from the configured language pool."""
    processor = MockAIProcessor()
    processor.set_preferred_languages(["en"])

    result = await processor.process_text("Weekly planning sync notes", message_id=1)

    english_summaries = {
        "This is a concise project status update with next steps.",
        "Notes from today's learning session and key takeaways.",
        "Outline of the tasks scheduled for this week.",
    }

    assert result.summary.summary in english_summaries
    assert {tag.replace("#", "") for tag in result.tags.tags} <= {
        "project",
        "status",
        "update",
        "learning",
        "notes",
        "recap",
        "tasks",
        "planning",
        "weekly",
    }


def test_mock_ai_processor_available_languages():
    """The mock processor exposes the set of supported languages."""
    processor = MockAIProcessor()
    assert processor.available_languages == {"ja", "en"}
