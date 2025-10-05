"""Secret manager abstractions for MindBridge."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from types import ModuleType
from typing import TYPE_CHECKING, Any, cast

from src.utils.mixins import LoggerMixin

try:  # pragma: no cover - optional dependency
    from google.cloud import secretmanager as _secretmanager_mod
except ImportError:  # pragma: no cover - optional dependency
    _secretmanager_mod = None  # type: ignore[assignment]

secretmanager: ModuleType | None = cast(ModuleType | None, _secretmanager_mod)

if TYPE_CHECKING:
    from google.cloud.secretmanager import SecretManagerServiceAsyncClient


class BaseSecretManager(LoggerMixin, ABC):
    """Common behaviours for different secret backends."""

    def __init__(self, project_id: str | None = None):
        self.project_id = project_id
        self._cache: dict[tuple[str, str], str] = {}

    async def get_secret(self, secret_name: str, version: str = "latest") -> str | None:
        """Return a secret value from the configured backend."""
        cache_key = (secret_name, version)
        if cache_key in self._cache:
            return self._cache[cache_key]

        secret_value = await self._fetch_secret(secret_name, version)
        if secret_value is not None:
            self._cache[cache_key] = secret_value
            self.logger.debug(
                "Retrieved secret", name=secret_name, backend=self.__class__.__name__
            )
        return secret_value

    @abstractmethod
    async def _fetch_secret(self, secret_name: str, version: str) -> str | None:
        """Backend specific implementation that fetches a secret."""

    def clear_cache(self) -> None:
        """Clear cached secrets."""
        if self._cache:
            self.logger.debug("Secret cache cleared", backend=self.__class__.__name__)
        self._cache.clear()


class PersonalSecretManager(BaseSecretManager):
    """Environment-variable based secret manager for personal setups."""

    async def _fetch_secret(self, secret_name: str, version: str) -> str | None:  # noqa: ARG002
        env_var_name = secret_name.replace("-", "_").upper()
        return os.getenv(env_var_name)


class GoogleSecretManager(BaseSecretManager):
    """Google Cloud Secret Manager backed implementation."""

    def __init__(
        self,
        project_id: str,
        client: SecretManagerServiceAsyncClient | None = None,
    ) -> None:
        if not project_id:
            raise ValueError("project_id is required for GoogleSecretManager")
        if (
            client is None and secretmanager is None
        ):  # pragma: no cover - optional dependency
            raise ImportError(
                "google-cloud-secret-manager がインストールされていません。"
                " `uv sync --extra google-api` を実行して有効化してください。"
            )
        super().__init__(project_id=project_id)
        if client is not None:
            self._client = client
        else:
            if secretmanager is None:  # pragma: no cover - defensive
                raise RuntimeError("google-cloud-secret-manager client unavailable")
            self._client = secretmanager.SecretManagerServiceAsyncClient()

    async def _fetch_secret(self, secret_name: str, version: str) -> str | None:
        secret_path = (
            f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
        )
        try:
            response = await self._client.access_secret_version(name=secret_path)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.error(
                "Failed to access Google Secret Manager",
                error=str(exc),
                secret=secret_name,
                version=version,
            )
            return None

        payload = getattr(response.payload, "data", None)
        if payload is None:
            return None
        return (
            payload.decode("utf-8")
            if isinstance(payload, (bytes, bytearray))
            else str(payload)
        )


class ConfigManager(LoggerMixin):
    """Facade for fetching configuration values from a secret manager."""

    def __init__(self, secret_manager: BaseSecretManager | None = None) -> None:
        self.secret_manager = secret_manager or PersonalSecretManager()

    async def get_config_value(
        self, key: str, *, version: str = "latest"
    ) -> str | None:
        normalized = key.replace("_", "-")
        return await self.secret_manager.get_secret(normalized, version=version)

    def clear_cache(self) -> None:
        self.secret_manager.clear_cache()


class PersonalConfigManager(ConfigManager):
    """Convenience wrapper using :class:`PersonalSecretManager`."""

    def __init__(self, project_id: str | None = None) -> None:
        super().__init__(PersonalSecretManager(project_id))


def create_secret_manager(
    strategy: str = "env",
    *,
    project_id: str | None = None,
    client: Any | None = None,
) -> BaseSecretManager:
    """Factory to create secret managers based on deployment strategy."""
    normalized = strategy.lower()
    if normalized in {"gcp", "google", "google-secret-manager"}:
        if project_id is None:
            raise ValueError("project_id must be provided for Google Secret Manager")
        return GoogleSecretManager(project_id=project_id, client=client)

    return PersonalSecretManager(project_id=project_id)


def create_config_manager(
    strategy: str = "env",
    *,
    project_id: str | None = None,
    client: Any | None = None,
) -> ConfigManager:
    """Create a config manager backed by the requested secret manager."""
    manager = create_secret_manager(strategy, project_id=project_id, client=client)
    return ConfigManager(manager)
