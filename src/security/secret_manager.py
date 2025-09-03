"""
Google Cloud Secret Manager integration for secure credential management
"""

import os
from typing import TYPE_CHECKING

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import secretmanager

from src.utils.mixins import LoggerMixin

if TYPE_CHECKING:
    from google.cloud.secretmanager import SecretManagerServiceClient


class SecretManager(LoggerMixin):
    """Google Cloud Secret Manager client for secure credential management"""

    def __init__(self, project_id: str | None = None):
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.client: SecretManagerServiceClient | None = None
        self._cache: dict[str, str] = {}
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Google Cloud Secret Manager client"""
        if not self.project_id:
            self.logger.warning(
                "Google Cloud project ID not set, Secret Manager disabled"
            )
            return

        try:
            self.client = secretmanager.SecretManagerServiceClient()
            self.logger.info(
                "Secret Manager client initialized", project_id=self.project_id
            )
        except DefaultCredentialsError:
            self.logger.warning(
                "Google Cloud credentials not available, falling back to environment variables"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize Secret Manager client: {e}")

    async def get_secret(self, secret_name: str, version: str = "latest") -> str | None:
        """Retrieve a secret from Google Cloud Secret Manager

        Args:
            secret_name: Name of the secret
            version: Version of the secret (default: "latest")

        Returns:
            Secret value or None if not found/available
        """
        if not self.client:
            # Fallback to environment variable
            env_var_name = secret_name.replace("-", "_").upper()
            return os.getenv(env_var_name)

        # Check cache first
        cache_key = f"{secret_name}:{version}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            name = (
                f"projects/{self.project_id}/secrets/{secret_name}/versions/{version}"
            )
            response = self.client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")

            # Cache the secret
            self._cache[cache_key] = secret_value

            self.logger.debug(f"Retrieved secret: {secret_name}")
            return str(secret_value) if secret_value is not None else None

        except Exception as e:
            self.logger.warning(
                f"Failed to retrieve secret {secret_name}: {e}, falling back to env var"
            )
            # Fallback to environment variable
            env_var_name = secret_name.replace("-", "_").upper()
            return os.getenv(env_var_name)

    async def create_secret(self, secret_name: str, secret_value: str) -> bool:
        """Create a new secret in Google Cloud Secret Manager

        Args:
            secret_name: Name of the secret
            secret_value: Value of the secret

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            self.logger.error("Secret Manager client not available")
            return False

        try:
            parent = f"projects/{self.project_id}"

            # Create the secret
            secret = self.client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_name,
                    "secret": {"replication": {"automatic": {}}},
                }
            )

            # Add secret version
            self.client.add_secret_version(
                request={
                    "parent": secret.name,
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )

            self.logger.info(f"Created secret: {secret_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create secret {secret_name}: {e}")
            return False

    async def update_secret(self, secret_name: str, secret_value: str) -> bool:
        """Update an existing secret in Google Cloud Secret Manager

        Args:
            secret_name: Name of the secret
            secret_value: New value of the secret

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            self.logger.error("Secret Manager client not available")
            return False

        try:
            parent = f"projects/{self.project_id}/secrets/{secret_name}"

            # Add new secret version
            self.client.add_secret_version(
                request={
                    "parent": parent,
                    "payload": {"data": secret_value.encode("UTF-8")},
                }
            )

            # Clear cache
            cache_key = f"{secret_name}:latest"
            if cache_key in self._cache:
                del self._cache[cache_key]

            self.logger.info(f"Updated secret: {secret_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update secret {secret_name}: {e}")
            return False

    async def delete_secret(self, secret_name: str) -> bool:
        """Delete a secret from Google Cloud Secret Manager

        Args:
            secret_name: Name of the secret to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            self.logger.error("Secret Manager client not available")
            return False

        try:
            name = f"projects/{self.project_id}/secrets/{secret_name}"
            self.client.delete_secret(request={"name": name})

            # Clear from cache
            cache_keys_to_remove = [
                k for k in self._cache if k.startswith(f"{secret_name}:")
            ]
            for key in cache_keys_to_remove:
                del self._cache[key]

            self.logger.info(f"Deleted secret: {secret_name}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to delete secret {secret_name}: {e}")
            return False

    def clear_cache(self) -> None:
        """Clear the secret cache"""
        self._cache.clear()
        self.logger.debug("Secret cache cleared")


class SecureConfigManager(LoggerMixin):
    """Secure configuration manager using Secret Manager and environment variables"""

    def __init__(self, project_id: str | None = None):
        self.secret_manager = SecretManager(project_id)
        self.sensitive_keys = {
            "discord_bot_token",
            "gemini_api_key",
            "speech_api_key",
            "garmin_username",
            "garmin_password",
            "backup_encryption_key",
        }

    async def get_config_value(self, key: str) -> str | None:
        """Get configuration value from secure storage or environment"""
        if key.lower() in self.sensitive_keys:
            return await self.secret_manager.get_secret(key.replace("_", "-"))
        return os.getenv(key.upper())

    async def set_secure_config(self, key: str, value: str) -> bool:
        """Store sensitive configuration in Secret Manager"""
        if key.lower() not in self.sensitive_keys:
            self.logger.warning(f"Key {key} is not marked as sensitive")
            return False

        secret_name = key.replace("_", "-")
        return await self.secret_manager.update_secret(secret_name, value)

    async def validate_all_secrets(self) -> dict[str, bool]:
        """Validate that all required secrets are accessible"""
        results = {}

        for key in self.sensitive_keys:
            secret_name = key.replace("_", "-")
            value = await self.secret_manager.get_secret(secret_name)
            results[key] = value is not None and len(value) > 0

        return results

    async def rotate_secret(self, key: str, new_value: str) -> bool:
        """Rotate a secret with the new value"""
        if key.lower() not in self.sensitive_keys:
            self.logger.error(f"Key {key} is not a recognized sensitive key")
            return False

        secret_name = key.replace("_", "-")
        success = await self.secret_manager.update_secret(secret_name, new_value)

        if success:
            self.logger.info(f"Successfully rotated secret: {key}")
        else:
            self.logger.error(f"Failed to rotate secret: {key}")

        return success
