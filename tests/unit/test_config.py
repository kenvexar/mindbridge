"""Test configuration module"""

import os
from pathlib import Path


def test_config_import() -> None:
    """Test that configuration can be imported without error"""
    # Set required environment variables for testing
    os.environ["DISCORD_BOT_TOKEN"] = "test_token"
    os.environ["DISCORD_GUILD_ID"] = "123456789"
    os.environ["GEMINI_API_KEY"] = "test_api_key"
    os.environ["OBSIDIAN_VAULT_PATH"] = "/tmp/test_vault"
    os.environ["ENVIRONMENT"] = "testing"

    # Import get_settings AFTER setting environment variables
    from src.config import get_settings

    try:
        settings = get_settings()

        assert settings.discord_bot_token.get_secret_value() == "test_token"
        assert settings.discord_guild_id == 123456789
        assert settings.gemini_api_key.get_secret_value() == "test_api_key"
        assert settings.obsidian_vault_path == Path("/tmp/test_vault")
        assert settings.environment == "testing"

    finally:
        # Clean up environment variables
        for key in [
            "DISCORD_BOT_TOKEN",
            "DISCORD_GUILD_ID",
            "GEMINI_API_KEY",
            "OBSIDIAN_VAULT_PATH",
            "ENVIRONMENT",
        ]:
            if key in os.environ:
                del os.environ[key]
