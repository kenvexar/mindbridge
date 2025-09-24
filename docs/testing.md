# ローカルテスト

## テスト実行

### 基本テスト

```bash
# 全テスト
uv run pytest

# 単体テスト
uv run pytest tests/unit/

# 統合テスト
uv run pytest tests/integration/

# カバレッジ
uv run pytest --cov=src --cov-report=term-missing
```

### 手動テスト

個別実行が必要な実サービステスト：

```bash
# 音声テスト
uv run python tests/manual/quick_voice_test.py

# Garmin 統合テスト
uv run python tests/manual/test_garmin_integration.py

# 管理スクリプトテスト
bash tests/manual/test_manage.sh
```

## モック設定

開発時に外部サービスへ接続したくない場合は `.env` に以下を追加します。

```env
ENABLE_MOCK_MODE=true
MOCK_DISCORD_ENABLED=true
MOCK_GEMINI_ENABLED=true
MOCK_GARMIN_ENABLED=true
MOCK_SPEECH_ENABLED=true
```

`ENABLE_MOCK_MODE` を `true` にするとモック設定が優先され、 Discord 接続も安全にスキップできます。
