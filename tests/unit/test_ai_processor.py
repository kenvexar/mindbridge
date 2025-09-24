from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from src.ai.models import ProcessingSettings

if TYPE_CHECKING:
    from src.ai.processor import AIProcessor


class DummyMemoryManager:
    """Minimal stub for memory manager registration."""

    def register_component(self, component) -> None:  # pragma: no cover - trivial
        return None


@pytest.fixture()
def processor_factory(monkeypatch: pytest.MonkeyPatch) -> Callable[[int], AIProcessor]:
    from src.ai import processor as ai_processor_module

    monkeypatch.setattr(ai_processor_module, "GeminiClient", lambda config: object())
    monkeypatch.setattr(
        ai_processor_module, "get_memory_manager", lambda: DummyMemoryManager()
    )

    def _factory(min_length: int) -> AIProcessor:
        settings = ProcessingSettings(min_text_length=min_length)
        return ai_processor_module.AIProcessor(settings=settings)

    return _factory


def test_min_text_length_respected(
    processor_factory: Callable[[int], AIProcessor],
) -> None:
    processor = processor_factory(10)

    short_result = processor._check_text_processability("short")
    assert short_result["is_processable"] is False
    assert "10" in short_result["reason"]

    valid_result = processor._check_text_processability("x" * 10)
    assert valid_result["is_processable"] is True


def test_min_text_length_lower_threshold(
    processor_factory: Callable[[int], AIProcessor],
) -> None:
    processor = processor_factory(2)

    assert processor._check_text_processability("ok")["is_processable"] is True
    assert processor._check_text_processability("o")["is_processable"] is False
