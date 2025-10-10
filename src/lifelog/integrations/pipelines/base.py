"""統合パイプラインの基底クラス"""

from __future__ import annotations

from abc import ABC, abstractmethod

from structlog import get_logger

from ...models import LifelogCategory, LifelogEntry, LifelogType
from ..models import IntegrationData

logger = get_logger(__name__)


class IntegrationPipeline(ABC):
    """IntegrationData を LifelogEntry に変換するパイプラインの基底"""

    @abstractmethod
    async def convert(self, data: IntegrationData) -> LifelogEntry | None:
        """IntegrationData から LifelogEntry を生成"""


class DefaultIntegrationPipeline(IntegrationPipeline):
    """標準的な汎用パイプライン"""

    async def convert(self, data: IntegrationData) -> LifelogEntry | None:
        title = f"{data.integration_type}: {data.metadata.get('data_type', 'unknown')}"
        content = f"{data.integration_type} から自動取得されたデータ"

        processed_data = data.data
        if isinstance(processed_data, dict):
            if "title" in processed_data:
                title = str(processed_data["title"])
            elif "summary" in processed_data:
                title = str(processed_data["summary"])
            elif "description" in processed_data:
                description: str = str(processed_data["description"])
                title = description[:50]

            if "content" in processed_data:
                content = str(processed_data["content"])
            elif "description" in processed_data:
                content = str(processed_data["description"])

        return LifelogEntry(
            category=LifelogCategory.ROUTINE,
            type=LifelogType.EVENT,
            title=title,
            content=content,
            timestamp=data.timestamp,
            tags=[data.integration_type, "外部連携", "自動記録"],
            source=f"{data.integration_type}_integration",
            metadata={
                "external_id": data.source_id,
                "integration_name": data.integration_type,
                "raw_data": data.data,
            },
        )
