"""
Google Cloud Secret Manager integration for secure credential management
"""

import os
from typing import TYPE_CHECKING

from src.utils.mixins import LoggerMixin

if TYPE_CHECKING:
    pass


class PersonalSecretManager(LoggerMixin):
    """Simplified secret manager for personal use - uses environment variables only"""

    def __init__(self, project_id: str | None = None):
        self.project_id = project_id  # Not used for personal setup
        self._cache: dict[str, str] = {}

    async def get_secret(self, secret_name: str, version: str = "latest") -> str | None:
        """Retrieve a secret from environment variables

        Args:
            secret_name: Name of the secret
            version: Ignored for personal use

        Returns:
            Secret value or None if not found
        """
        # Check cache first
        if secret_name in self._cache:
            return self._cache[secret_name]

        # Get from environment variable
        env_var_name = secret_name.replace("-", "_").upper()
        secret_value = os.getenv(env_var_name)

        if secret_value:
            # Cache the secret
            self._cache[secret_name] = secret_value
            self.logger.debug(f"Retrieved secret: {secret_name}")

        return secret_value

    def clear_cache(self) -> None:
        """Clear the secret cache"""
        self._cache.clear()
        self.logger.debug("Secret cache cleared")


class PersonalConfigManager(LoggerMixin):
    """Personal configuration manager using environment variables only"""

    def __init__(self, project_id: str | None = None):
        self.secret_manager = PersonalSecretManager(project_id)

    async def get_config_value(self, key: str) -> str | None:
        """Get configuration value from environment variables"""
        return await self.secret_manager.get_secret(key.replace("_", "-"))
