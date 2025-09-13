"""
共通フィクスチャと収集設定。

- `manual/` 配下の手動テストは pytest の自動収集から除外
- テスト向けの環境変数を毎テスト自動設定（autouse）
- ルートを `sys.path` に追加して `import src.*` を解決
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# プロジェクトルート（このファイルの親の親）をパスに追加
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# manual ディレクトリは手動実行専用のため収集対象から除外
collect_ignore = ["manual"]
collect_ignore_glob = ["manual/*.py"]


@pytest.fixture(autouse=True)
def _test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """テスト用の必須環境変数を毎テストで設定。

    各テスト終了時に `monkeypatch` により自動で復元されます。
    実際の秘密情報は使用せず、最小限のダミー値を設定します。
    """

    env: dict[str, str] = {
        "DISCORD_BOT_TOKEN": "test_token",
        "DISCORD_GUILD_ID": "123456789",
        "GEMINI_API_KEY": "test_api_key",
        "OBSIDIAN_VAULT_PATH": "/tmp/test_vault",
        # チャンネル ID（数値文字列）
        "CHANNEL_INBOX": "111111111",
        "CHANNEL_VOICE": "222222222",
        "CHANNEL_FILES": "333333333",
        "CHANNEL_MONEY": "444444444",
        "CHANNEL_FINANCE_REPORTS": "555555555",
        "CHANNEL_TASKS": "666666666",
        "CHANNEL_PRODUCTIVITY_REVIEWS": "777777777",
        "CHANNEL_NOTIFICATIONS": "888888888",
        "CHANNEL_COMMANDS": "999999999",
        # 明示環境名
        "ENVIRONMENT": "testing",
    }

    for k, v in env.items():
        monkeypatch.setenv(k, v)


@pytest.fixture
def template_engine_tmp(tmp_path):
    """TemplateEngine を一時ディレクトリで提供する共通フィクスチャ。"""
    from src.obsidian.template_system import TemplateEngine

    return TemplateEngine(tmp_path)
