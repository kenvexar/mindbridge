# Manual Tests

手動テスト用スクリプトは以下のカテゴリに整理されています。実行時はプロジェクトルートで `uv sync --dev` 済みであること、および必要な認証情報を `.env` などで設定しておくことを推奨します。

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
- 事前に `./scripts/manage.sh clean` を実行し、キャッシュ由来の差分を排除する。
- 外部 API を利用するテストは `.env` または Secret Manager に最新の資格情報が登録されていることを確認する。
- 大量のログが出力されるテスト（音声メモなど）は `LOG_LEVEL=DEBUG` を設定し、必要に応じてログファイルへリダイレクトする。

## トラブルシューティング
- 認証エラーが発生した場合は `uv run python -m src.security.simple_admin` で Secrets を再読み込みする。
- Garmin や Google API の rate limit に達した場合は、一定時間待機した上で再実行する。
- Speech API 関連のテストで `pydub` ImportError が出る場合は `brew install ffmpeg` などでデコーダを導入する。
