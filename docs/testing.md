# テストガイド

MindBridge の品質確認に使用するテストコマンドと手動検証の手順をまとめます。変更内容に応じて適切なテストセットを選択してください。

## 1. 自動テスト

```bash
# 全テスト（単体 + 統合）
uv run pytest -q

# 単体テストのみ
uv run pytest tests/unit

# 統合テストのみ
uv run pytest tests/integration

# カバレッジレポート（新規機能や大規模修正時に実行）
uv run pytest --cov=src --cov-report=term-missing
```

- `pytest.ini` で asyncio プラグインや共通フィクスチャが設定されています。
- 統合テストではモック済み Discord クライアントやファイルシステムを使用します。実サービスへの接続は行いません。

## 2. 手動テスト / 外部サービス検証

| シナリオ | コマンド | 説明 |
| --- | --- | --- |
| 音声文字起こし | `uv run python tests/manual/quick_voice_test.py` | サンプル音声をアップロードし、Speech-to-Text とノート生成を確認。 |
| Garmin 連携 | `uv run python tests/manual/test_garmin_integration.py` | 実際の Garmin 認証情報で API を呼び出し、Daily Note への反映を確認。 |
| 管理スクリプト | `bash tests/manual/test_manage.sh` | `scripts/manage.sh` の主要サブコマンドを dry-run モードで検証。 |
| Discord UI | Discord クライアント上で `/status`, `/integration_status`, `/task_add` などを実行 | Slash / Prefix コマンドが期待通り動作するか確認。 |

外部サービスを呼び出す手動テストは、専用のテスト用クレデンシャルやサンドボックス環境を利用してください。

## 3. モックモード

外部 API へ接続せずにテストしたい場合は `.env` に以下を設定します。

```env
ENABLE_MOCK_MODE=true
MOCK_DISCORD_ENABLED=true
MOCK_GEMINI_ENABLED=true
MOCK_GARMIN_ENABLED=true
MOCK_SPEECH_ENABLED=true
```

モックモードでは Discord 連携が無効化され、AI/ガーミン/音声処理がモックレスポンスを返します。統合テストではこの設定が自動的に適用されます。

## 4. レポートと後処理

- テスト失敗時のログは `logs/` と `tests/.pytest_cache` に保存されます。不要になった場合は `./scripts/manage.sh clean` でキャッシュを削除してください。
- GitHub へプッシュする前に `uv run pre-commit run --all-files` を実行し、フォーマットや静的解析の結果を含めて報告します。
- CI で追加のテストを走らせる場合は `uv run pytest --maxfail=1 --disable-warnings -q` を参考にします。

テスト結果とカバレッジ状況は PR の Verification セクションに記載することを推奨します。
