"""統合パイプラインブリッジ

各外部連携ごとのパイプラインを登録し、IntegrationData を
LifelogEntry へ変換するためのブリッジ層を提供する。
"""

from __future__ import annotations

import structlog

from ..models import LifelogEntry
from .models import IntegrationData
from .pipelines.base import DefaultIntegrationPipeline, IntegrationPipeline

logger = structlog.get_logger(__name__)


class IntegrationBridge:
    """外部連携ごとのパイプラインを束ねるブリッジ"""

    def __init__(
        self,
        default_pipeline: IntegrationPipeline | None = None,
    ) -> None:
        self._pipelines: dict[str, IntegrationPipeline] = {}
        self._default_pipeline = default_pipeline

    def register_pipeline(self, name: str, pipeline: IntegrationPipeline) -> None:
        """パイプラインを登録"""

        self._pipelines[name] = pipeline
        logger.debug(
            "integration pipeline registered",
            integration=name,
            pipeline=pipeline.__class__.__name__,
        )

    def unregister_pipeline(self, name: str) -> None:
        """登録済みパイプラインを解除"""

        removed: IntegrationPipeline | None = self._pipelines.pop(name, None)
        if removed:
            logger.debug(
                "integration pipeline unregistered",
                integration=name,
                pipeline=removed.__class__.__name__,
            )

    async def convert(self, payload: IntegrationData) -> LifelogEntry | None:
        """IntegrationData を LifelogEntry へ変換"""

        pipeline = self._pipelines.get(payload.integration_type)
        if pipeline is None:
            pipeline = self._default_pipeline

        if pipeline is None:
            logger.warning(
                "no integration pipeline registered",
                integration=payload.integration_type,
            )
            return None

        return await pipeline.convert(payload)


def create_default_bridge() -> IntegrationBridge:
    """標準パイプラインを登録したブリッジを生成"""

    from .pipelines.garmin_pipeline import GarminIntegrationPipeline
    from .pipelines.google_calendar_pipeline import GoogleCalendarPipeline

    bridge = IntegrationBridge(default_pipeline=DefaultIntegrationPipeline())
    bridge.register_pipeline("garmin", GarminIntegrationPipeline())
    bridge.register_pipeline("google_calendar", GoogleCalendarPipeline())
    return bridge


__all__ = ["IntegrationBridge", "create_default_bridge"]
