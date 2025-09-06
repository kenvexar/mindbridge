"""Template system base classes and protocols"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class GeneratedNote:
    """生成されたノートを表すクラス"""

    filename: str
    content: str
    frontmatter: Any  # Can be dict or SimpleNamespace


class ITemplateProcessor(Protocol):
    """Template processor interface for dependency inversion."""

    async def process(self, content: str, context: dict[str, Any]) -> str:
        """Process template content with given context."""
        ...
