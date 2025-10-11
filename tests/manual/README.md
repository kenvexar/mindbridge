# Manual Tests

手動テスト用スクリプトは以下のカテゴリに整理されています。
実行時はプロジェクトルートで `uv sync --dev` を実行し、
依存関係を揃えてください。
依存が不足する場合は `uv sync --dev` を再実行してください。
必要な認証情報は `.env` 等に設定してから実行してください。

## 必須・推奨環境変数サンプル

```env
# Discord / AI
DISCORD_BOT_TOKEN=xxxx
DISCORD_GUILD_ID=123456789012345678
GEMINI_API_KEY=xxxx

# Vault & ログ
OBSIDIAN_VAULT_PATH=/Users/you/Obsidian/Vault
LOG_LEVEL=INFO

# Integrations (必要なものだけ有効化)
GARMIN_EMAIL=example@example.com
GARMIN_PASSWORD=changeme
GOOGLE_CALENDAR_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CALENDAR_CLIENT_SECRET=yyyyy
```

Speech API を利用するテストでは `GOOGLE_CLOUD_SPEECH_API_KEY` または
`GOOGLE_CLOUD_SPEECH_CREDENTIALS` を設定してください。
GitHub 連携を確認する場合は `GITHUB_TOKEN` と `OBSIDIAN_BACKUP_REPO` を追加し、
`.env` は `chmod 600` などでアクセス制御すると安全です。

## 1. Audio / Speech
| ファイル | 目的 | 実行コマンド | 前提条件 |
| --- | --- | --- | --- |
| `quick_voice_test.py` | SpeechProcessor のモック音声確認 | `uv run python tests/manual/quick_voice_test.py` | モック環境で十分 |
| `test_voice_memo.py` | 音声メモ全体フローの統合テスト | `uv run python tests/manual/test_voice_memo.py` | Discord/Obsidian 設定が必要 |
| `test_real_voice.py` | 実音声ファイルを使った精度テスト | `uv run python tests/manual/test_real_voice.py` | `pydub` が利用可能であること |

## 2. Calendar / Integrations
| ファイル | 目的 | 実行コマンド | 前提条件 |
| --- | --- | --- | --- |
| `test_garmin_integration.py` | Garmin Connect 認証とデータ取得の検証 | `uv run python tests/manual/test_garmin_integration.py` | Garmin 認証情報が必要 |
| `test_google_calendar_fix.py` | Google Calendar API フローの手動確認 | `uv run python tests/manual/test_google_calendar_fix.py` | Google OAuth 資格情報 (`credentials.json`) |

## 3. Utility / Script Checks
| ファイル | 目的 | 実行コマンド | 前提条件 |
| --- | --- | --- | --- |
| `simple_test.py` | Mock AIProcessor を使った軽量検証 | `uv run python tests/manual/simple_test.py` | 特になし |
| `test_manage.sh` | `scripts/manage.sh` の smoke テスト | `bash tests/manual/test_manage.sh` | gcloud CLI がインストール済みであること |

## 実行のベストプラクティス
- 事前に `./scripts/manage.sh clean` を実行し、
  キャッシュ由来の差分を排除する。
- 外部 API を利用するテストは `.env` または Secret Manager に最新の資格情報が
  登録されていることを確認する。
- 大量のログが出るテスト（音声メモなど）は `LOG_LEVEL=DEBUG` を設定し、
  必要ならログをファイルへリダイレクトする。

## トラブルシューティング
- 認証エラーが発生した場合は `uv run python -m src.security.simple_admin` で
  Secrets を再読み込みする。
- Garmin や Google API の rate limit に達した場合は、
  一定時間待機した上で再実行する。
- Speech API 関連のテストで `pydub` ImportError が出る場合は
  `brew install ffmpeg` などでデコーダを導入する。
