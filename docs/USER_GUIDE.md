# MindBridge ユーザーガイド

MindBridge は Discord のメッセージ、添付ファイル、外部サービスのデータを AI で整理し、Obsidian Vault に構造化ノートとして保存する自動化プラットフォームです。本ガイドでは初期セットアップから日常運用、トラブルシュートまでをまとめます。

## 目次

1. [概要](#1-概要)
2. [初期セットアップ](#2-初期セットアップ)
   - [必要な環境](#21-必要な環境)
   - [インストール手順](#22-インストール手順)
   - [必須/推奨環境変数](#23-必須推奨環境変数)
   - [オプション設定](#24-オプション設定)
   - [Discord Bot 準備](#25-discord-bot-準備)
3. [基本的な使い方](#3-基本的な使い方)
4. [外部サービス連携](#4-外部サービス連携)
5. [音声メモの処理](#5-音声メモの処理)
6. [カスタマイズと開発 Tips](#6-カスタマイズと開発-tips)
7. [トラブルシューティング](#7-トラブルシューティング)
8. [付録: 参考リンク](#8-付録-参考リンク)

---

## 1. 概要

MindBridge は次のコンポーネントで構成されます。

- **Discord Bot (`src/bot/`)** – Slash / Prefix コマンド、メッセージ処理、通知。
- **AI パイプライン (`src/ai/`)** – Gemini 2.5 Flash を利用した要約・タグ・分類、URL 解析、ベクターストア。
- **Obsidian 連携 (`src/obsidian/`)** – Markdown 生成、テンプレート、Daily Note 統合、統計、GitHub 同期。
- **外部連携 (`src/lifelog/`, `src/integrations/`, `src/health_analysis/`)** – Garmin、Google Calendar、ライフログ解析、スケジューラ。
- **生産性ツール (`src/tasks/`, `src/finance/`)** – タスク管理や家計管理の Slash コマンドとノート生成。
- **運用基盤 (`src/security/`, `src/monitoring/`)** – Secret Manager 抽象化、アクセスログ、ヘルスチェックサーバ。

---

## 2. 初期セットアップ

### 2.1 必要な環境

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) パッケージマネージャー
- Discord Bot（トークン/ギルド ID）
- Google Gemini API キー
- Obsidian Vault の保存先（書き込み権限が必要）

### 2.2 インストール手順

```bash
git clone https://github.com/your-username/mindbridge.git
cd mindbridge

# 依存関係と開発ツールをインストール
uv sync --dev

# 対話式に .env を生成（必要なシークレットを登録）
./scripts/manage.sh init

# ローカル起動（uv run python -m src.main をラップ）
./scripts/manage.sh run
```

初回起動では Slash コマンドが同期されるまで数秒〜数十秒かかります。Discord 側で `/status` が利用可能になれば準備完了です。

### 2.3 必須/推奨環境変数

`.env`（ローカル）や Secret Manager（クラウド）に設定します。変数名は大文字推奨ですが、`pydantic` が小文字属性にマッピングします。

| 変数 | 説明 | 必須 |
| --- | --- | --- |
| `DISCORD_BOT_TOKEN` | Discord Bot トークン | ✅ |
| `DISCORD_GUILD_ID` | Slash コマンドを同期するギルド ID | ✅ |
| `GEMINI_API_KEY` | Google Gemini API キー | ✅ |
| `OBSIDIAN_VAULT_PATH` | Vault 保存ディレクトリ（既定: `./vault`） | 推奨 |
| `ENVIRONMENT` | `personal` / `development` / `production` | 推奨 |
| `LOG_LEVEL` / `LOG_FORMAT` | ログ出力制御 (`INFO` / `json` が既定) | 任意 |
| `ENABLE_ACCESS_LOGGING` | セキュリティイベントログを有効化 (`true` 推奨) | 任意 |

### 2.4 オプション設定

| 変数 | 用途 |
| --- | --- |
| `GOOGLE_CLOUD_SPEECH_API_KEY` または `GOOGLE_CLOUD_SPEECH_CREDENTIALS` | Google Speech-to-Text 認証情報（JSON を base64 で格納可能） |
| `GOOGLE_APPLICATION_CREDENTIALS` | Service Account JSON ファイルパス（Speech/GCP 共通） |
| `GARMIN_EMAIL`, `GARMIN_PASSWORD` | Garmin Connect 連携用資格情報 |
| `GITHUB_TOKEN`, `OBSIDIAN_BACKUP_REPO`, `OBSIDIAN_BACKUP_BRANCH` | Vault の GitHub 同期設定 |
| `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET` | Google Calendar OAuth クライアント |
| `GOOGLE_CALENDAR_SERVICE_ACCOUNT` | Service Account を用いた Calendar 認証 |
| `SECRET_MANAGER_STRATEGY`, `SECRET_MANAGER_PROJECT_ID` | `google` を指定して Secret Manager を利用する場合に設定 |
| `ENABLE_MOCK_MODE`, `MOCK_*_ENABLED` | 外部 API を呼び出さずにテストするモックフラグ |
| `MODEL_NAME`, `AI_TEMPERATURE`, `AI_MAX_TOKENS` | Gemini 推論パラメータ (`models/gemini-2.5-flash` が既定) |

必要に応じて `./scripts/manage.sh secrets <PROJECT_ID> --with-optional` を利用すると Secret Manager に一括登録できます。

### 2.5 Discord Bot 準備

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成。
2. **Bot** タブでトークンを発行し、`MESSAGE CONTENT INTENT` を有効化。
3. OAuth2 → URL Generator で `bot` と `applications.commands` を選択し、権限に `Send Messages`, `Read Message History`, `Use Slash Commands` を含めてサーバへ招待。
4. `.env` / Secret Manager に `DISCORD_BOT_TOKEN` と `DISCORD_GUILD_ID` を設定。

Bot を再招待した際は `/sync` コマンドは不要です。起動時に `client.py` が Slash コマンドをギルドスコープで同期します。

---

## 3. 基本的な使い方

1. Discord の監視チャンネル（既定は `memo`, `notifications`, `commands`）へ投稿。
2. `MessageProcessor` がテキスト整形・URL 抽出・メタデータ解析を実施。
3. `AIProcessor` と `AdvancedNoteAnalyzer` が要約・タグ・カテゴリ・関連ノートを生成。
4. `TemplateEngine` が YAML フロントマター付き Markdown を出力し、`ObsidianFileManager` が Vault に保存。
5. 必要に応じて `DailyNoteIntegration` が日次サマリーを更新し、`GitHubObsidianSync` が push/pull を行います。

### コマンド操作

- Slash コマンド一覧や詳細は `docs/basic-usage.md` を参照してください。
- ライフログ機能では `!log`, `!mood`, `!habit`, `!goal` などの Prefix コマンドも利用可能です。
- コマンド応答が遅い場合は `/system_status` で Integration Manager とスケジューラの状態を確認できます。

---

## 4. 外部サービス連携

### 4.1 Garmin Connect

1. `.env` に `GARMIN_EMAIL`, `GARMIN_PASSWORD` を設定。
2. Bot 起動後に `/integration_status` で `garmin` エントリが有効か確認。
3. `/garmin_today`, `/garmin_sleep` で日次アクティビティや睡眠データを取得。
4. バックグラウンドでは `HealthAnalysisScheduler` が `HealthDataAnalyzer` と `HealthActivityIntegrator` を用いて日次ノートへ統合します。

### 4.2 Google Calendar

1. OAuth クレデンシャル（クライアント ID / シークレット）を設定し、Bot を再起動。
2. `/calendar_auth` で表示された URL にアクセスし、Google アカウントで認証。
3. 得られたコードを `/calendar_token code:<...>` で登録。
4. `/calendar_test` で接続確認。成功すると予定のプレビューが表示されます。
5. カレンダーイベントはライフログ経由で日次ノートへ追記されます。

### 4.3 GitHub Vault バックアップ

- `GITHUB_TOKEN`（`repo` 権限）と `OBSIDIAN_BACKUP_REPO` を設定すると、
  起動時に `git pull`・終了時に `git push` を実行します。
- `.gitignore` は自動生成され、`logs/` や一時ファイルを除外します。
- 運用面の詳細やトラブル対策は `docs/maintenance/github-sync.md` を参照してください。

### 4.4 Integration Manager とスケジューラ

- `IntegrationManager` は `~/.mindbridge/integrations/settings.json`（コンテナでは `/app/.mindbridge/...`）を管理し、暗号化済みクレデンシャル (`credentials.json.encrypted`) を扱います。
- `/integration_config` で設定を閲覧・保存、`/manual_sync` で即時同期をトリガー。
- `/scheduler_status` は `IntegrationSyncScheduler` のジョブ状態（次回実行時刻や直近の結果）を表示します。

---

## 5. 音声メモの処理

| 項目 | 内容 |
| --- | --- |
| 対応フォーマット | MP3 / WAV / FLAC / OGG / M4A / WEBM |
| 認証情報 | `GOOGLE_CLOUD_SPEECH_API_KEY` または `GOOGLE_CLOUD_SPEECH_CREDENTIALS`（サービスアカウント JSON） |
| 処理フロー | `SpeechProcessor` が認証情報を検証 → Google Speech API へ送信 → 文字起こし結果と要約を YAML フロントマター・本文に追加 |
| フォールバック | API が利用できない場合は音声ファイルのみ保存し、ステータスを `pending` として記録 |
| 使用量監視 | `SpeechAPIUsage` が月次使用時間を追跡し、閾値超過時は通知します |

---

## 6. カスタマイズと開発 Tips

- **テンプレート**: `vault/90_Meta/Templates/` に Markdown テンプレートを配置すると `TemplateEngine` が自動作成します。`{title}` や `{timestamp}` プレースホルダーが利用可能です。
- **チャンネル設定**: `src/bot/channel_config.py` の `ChannelConfig` で監視チャンネルや通知宛先を制御。起動後は `/status` に反映されます。
- **モックモード**: `ENABLE_MOCK_MODE=true` と各 `MOCK_*_ENABLED` を設定すると外部 API を呼ばずに処理を検証できます。CI や手動テストで活用してください。
- **ロギング**: `LOG_LEVEL=DEBUG`、`LOG_FORMAT=text` にすると詳細ログが `logs/` に保存されます。セキュリティイベントは `access_logger` を通じて JSON 形式で出力されます。
- **メモリ/キャッシュ調整**: `ProcessingSettings`（AI）や `MemoryOptimizedCache` のパラメータは `src/ai/models.py` から変更可能です。

---

## 7. トラブルシューティング

| 症状 | チェックポイント |
| --- | --- |
| Bot がオンラインにならない | `.env` の `DISCORD_BOT_TOKEN`/`GEMINI_API_KEY` が正しいか、`./scripts/manage.sh run` のログで例外が出ていないか確認。 |
| Slash コマンドが表示されない | Bot 招待時に `applications.commands` 権限を付与したか、`DISCORD_GUILD_ID` が正しいか。再起動後に同期完了まで数十秒待機。 |
| ノートが作成されない | `OBSIDIAN_VAULT_PATH` の書き込み権限、Vault パスが存在するか、`logs/` の `Failed to create note` を確認。 |
| 音声文字起こしが失敗する | Speech API キー or サービスアカウント設定、`GOOGLE_APPLICATION_CREDENTIALS` のファイル権限を確認。 |
| Garmin/Calendar データが更新されない | `/integration_status` でエラーを確認し、`/manual_sync` で再同期。認証情報の期限切れは `IntegrationConfigManager` がログに出力します。 |
| GitHub 同期が失敗する | `GITHUB_TOKEN` の権限 (`repo`) を確認し、Vault ディレクトリで `git status` を実行。`GitHubObsidianSync` のログにエラーが残ります。 |

追加情報は `logs/` ディレクトリの最新ファイル、または `/system_status` コマンドで概要を確認できます。

---

## 8. 付録: 参考リンク

- クイックスタート: `docs/quick-start.md`
- Slash コマンド詳細: `docs/basic-usage.md`
- システム構成: `docs/architecture.md`
- 開発フロー: `docs/development-guide.md`
- デプロイ手順: `docs/deploy/overview.md`, `docs/deploy/cloud-run.md`, `docs/deploy/local.md`
- YAML フロントマター仕様: `docs/yaml-front-matter.md`
- 継続メンテナンスメモ: `docs/maintenance/housekeeping.md`

不明点がある場合は Issue を起票するか、チームのサポートチャンネルで相談してください。
