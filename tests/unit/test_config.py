"""Test configuration module"""

from pathlib import Path


def test_config_import(monkeypatch) -> None:
    """設定が環境変数から正しく構築されることを検証する。"""
    # conftest の autouse フィクスチャで既に設定済みだが、ここでは明示上書き
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test_token")
    monkeypatch.setenv("DISCORD_GUILD_ID", "123456789")
    monkeypatch.setenv("GEMINI_API_KEY", "test_api_key")
    monkeypatch.setenv("OBSIDIAN_VAULT_PATH", "/tmp/test_vault")
    monkeypatch.setenv("ENVIRONMENT", "testing")

    # Import get_settings AFTER setting environment variables
    from src.config import get_settings

    settings = get_settings()

    assert settings.discord_bot_token.get_secret_value() == "test_token"
    assert settings.discord_guild_id == 123456789
    assert settings.gemini_api_key.get_secret_value() == "test_api_key"
    assert settings.obsidian_vault_path == Path("/tmp/test_vault")
    assert settings.environment == "testing"
