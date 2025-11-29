# 継続メンテナンスのメモ

ドキュメントや構成を整理する際の現状把握と次の一手をまとめています。更新したらここにメモを残してください。

## 1. 構成メモ
- トップ階層は「ランタイム (`src/`)」「テスト (`tests/`)」「ドキュメント (`docs/`)」「デプロイ/ツール (`deploy/`, `scripts/`, `docker*`)」「生成物 (`vault/`, `logs/`)」の 5 系統。
- 2025 Q1 に `docs/` を再編し、インデックスを `docs/README.md` として整理済み。
- Garmin / Calendar 連携はランタイム向けクライアント（`src/garmin/`）と Integration Manager 側（`src/integrations/garmin/`, `src/lifelog/integrations/`）に分離済み。両方触るときは依存を確認。
- `tests/manual/` は用途別の手動スクリプト置き場。必要に応じて README と前提条件を追記する。
- `logs/`, `vault/` は `.gitkeep` のみコミットし、生成物は `./scripts/manage.sh clean` で削除可能。

| パス | 役割 | 現状 | 次のアクション |
| --- | --- | --- | --- |
| `src/ai/`, `src/audio/`, `src/bot/` | AI / 音声 / Discord Bot | README と型ヒント整備済み | 新ワークフロー追加時に README とテストを更新 |
| `src/integrations/`, `src/lifelog/` | 外部サービス統合 | Integration Manager / Scheduler 共通化済み | 設定スキーマを将来的に JSON Schema 化する |
| `docs/` | プロジェクトドキュメント | インデックスと主要ガイドを更新済み | 新モジュール追加時に該当ガイドとインデックスを追記 |
| `tests/manual/` | 手動テスト | 音声/ガーミン/管理スクリプト例あり | 各スクリプトに README と必要環境を明記 |
| `scripts/manage.sh` | 管理 CLI | env/secrets/deploy/clean などを実装 | 新タスクはここへ統合する方針 |

## 2. 依存の棚卸し
| 区分 | 主要パッケージ | 用途 | 備考 |
| --- | --- | --- | --- |
| ランタイム | `discord.py`, `PyNaCl` | Bot と音声 | 音声機能で必須 |
| ランタイム | `google-genai`, `aiohttp`, `tenacity` | Gemini 呼び出し | モデル更新時は `MODEL_NAME` を変更 |
| ランタイム | `google-cloud-speech`, `pydub` | 音声文字起こし | オプション依存 |
| データ処理 | `numpy`, `scikit-learn`, `beautifulsoup4`, `python-dateutil` | ライフログ解析、URL パース、統計 | `lifelog` で利用 |
| 設定/セキュリティ | `pydantic`, `pydantic-settings`, `cryptography`, `pyyaml` | 設定管理・暗号化・YAML | Secret 暗号化に `Fernet` |
| 開発 | `pytest`, `pytest-asyncio`, `mypy`, `ruff`, `pre-commit` | テスト/静的解析/整形 | CI でも使用 |
| 任意 | `google-cloud-secret-manager`, `google-api-python-client` | Secret Manager / Google API | `pyproject.toml` の optional deps |

追加・アップデート時は `pyproject.toml` とこのファイルを更新し、理由を記しておく。脆弱性確認は `uv run pip-audit --progress-spinner off` を活用。

## 3. ドキュメント整備状況
- 2025 Q1: `README.md`、`docs/README.md`、`docs/deploy/local.md`、`docs/basic-usage.md` を刷新済み。
- 未整備: `tests/manual/` 各スクリプトの README 充実、`src/` 各パッケージの内部ドキュメント更新頻度アップ。

## 4. よく使う整理コマンド
- `./scripts/manage.sh clean --with-uv-cache`
- `uv pip list --tree`
- `rg -g"*.py" "import <pkg>" src tests`
- `rg -g"*.md" "TODO" docs`

## 5. 進捗メモ
- [x] セキュリティ監査ログに 5 MB × 5 世代のローテーションを導入（2025-02-14）。`ACCESS_LOG_ROTATION_SIZE_MB` / `ACCESS_LOG_ROTATION_BACKUPS` で調整可能。
