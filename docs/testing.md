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

開発時は `.env` で以下を設定：

```env
MOCK_DISCORD=true
MOCK_GEMINI=true
MOCK_GARMIN=true
```
