# テストガイド

変更規模に合わせてどのテストを回すかを素早く判断できるようにまとめました。

## 1. 自動テスト
```bash
uv run pytest -q                                # 単体 + 統合まとめて
uv run pytest tests/unit                        # 単体だけ
uv run pytest tests/integration                 # 統合だけ
uv run pytest --cov=src --cov-report=term-missing   # カバレッジを取りたいとき
```
- `pytest.ini` で asyncio プラグインや共通フィクスチャを設定済み。
- 統合テストはモックされた Discord/ファイルシステムを使うため、実サービスには接続しません。

## 2. 手動テスト / 外部サービス検証
| シナリオ | コマンド | 目的 |
| --- | --- | --- |
| 音声文字起こし | `uv run python tests/manual/quick_voice_test.py` | Speech-to-Text とノート生成の確認 |
| Garmin 連携 | `uv run python tests/manual/test_garmin_integration.py` | 実認証で日次ノート反映を確認 |
| 管理スクリプト | `bash tests/manual/test_manage.sh` | `scripts/manage.sh` の主要サブコマンドを dry-run |
| Discord UI | Discord 上で `/status`, `/task_add` などを実行 | Slash / Prefix コマンドの目視確認 |

外部サービスを呼ぶ場合はテスト用クレデンシャルやサンドボックス環境を使用してください。

## 3. モックモード
外部 API を呼びたくない場合は `.env` に以下を設定します。
```env
ENABLE_MOCK_MODE=true
MOCK_DISCORD_ENABLED=true
MOCK_GEMINI_ENABLED=true
MOCK_GARMIN_ENABLED=true
MOCK_SPEECH_ENABLED=true
```
統合テストでは自動でこれらの設定を前提にしています。

## 4. 失敗時の後処理
- ログは `logs/` と `tests/.pytest_cache` に残ります。不要なら `./scripts/manage.sh clean`。
- GitHub へ送る前に `uv run pre-commit run --all-files` を実行し、lint/format/型結果を確認。
- CI で落としたい場合は `uv run pytest --maxfail=1 --disable-warnings -q` を参考にしてください。

テスト結果とカバレッジは PR の Verification セクションへ短く記載することを推奨します。
