# MindBridge ユーザーガイド

AI が Discord のメッセージや添付ファイルを整理し、 Obsidian ノートに保存するワークフローの利用手順をまとめています。

## 目次

1. [概要](#1-概要)
2. [初期セットアップ](#2-初期セットアップ)
   - [必要な環境](#21-必要な環境)
   - [インストール手順](#22-インストール手順)
   - [主要な環境変数](#23-主要な環境変数)
   - [Discord Bot 準備](#24-discord-bot-準備)
3. [基本的な使い方](#3-基本的な使い方)
4. [利用可能な Slash コマンド](#4-利用可能な-slash-コマンド)
5. [外部サービス連携](#5-外部サービス連携)
6. [音声メモの処理](#6-音声メモの処理)
7. [カスタマイズのヒント](#7-カスタマイズのヒント)
8. [トラブルシューティング](#8-トラブルシューティング)

---

## 1. 概要

MindBridge は以下の処理を自動で実行します。

- Discord の `#memo` チャンネルからテキストや添付ファイルを取得
- Google Gemini を用いた要約・タグ付け・カテゴリ分類
- 生成結果を Obsidian Vault の Markdown ノートとして保存
- Garmin Connect や Google Calendar から取得したデータを日次ノートに統合
- GitHub リポジトリに Vault を同期（クラウド環境向け）

---

## 2. 初期セットアップ

### 2.1 必要な環境

- Python 3.13
- [uv](https://github.com/astral-sh/uv) パッケージマネージャー
- Discord アカウント（Bot 用）
- Google Gemini API Key
- Obsidian Vault のローカルパス

### 2.2 インストール手順

```bash
# リポジトリを取得
git clone https://github.com/your-username/mindbridge.git
cd mindbridge

# 依存関係をインストール
uv sync --dev

# .env を対話式で作成
./scripts/manage.sh init

# ローカル起動
uv run python -m src.main
```

### 2.3 主要な環境変数

`.env` または `.env.docker` に設定する主なキーは以下のとおりです。

| 変数 | 用途 |
| --- | --- |
| `DISCORD_BOT_TOKEN` | Discord Bot のトークン |
| `DISCORD_GUILD_ID`  | Slash コマンドを同期するサーバー ID |
| `GEMINI_API_KEY`    | Google Gemini API キー |
| `OBSIDIAN_VAULT_PATH` | ノートを保存するディレクトリ |
| `ENVIRONMENT` | `personal` / `development` / `production` |
| `LOG_LEVEL`, `LOG_FORMAT` | ログ出力制御 |
| `ENABLE_ACCESS_LOGGING` | セキュリティイベントロギングの有効/無効 |

### オプションの環境変数

| 変数 | 用途 |
| --- | --- |
| `GOOGLE_CLOUD_SPEECH_API_KEY` または `GOOGLE_CLOUD_SPEECH_CREDENTIALS` | 音声文字起こし用の認証情報 |
| `GARMIN_EMAIL`, `GARMIN_PASSWORD` | Garmin Connect 連携用資格情報 |
| `GITHUB_TOKEN`, `OBSIDIAN_BACKUP_REPO` | GitHub 同期設定 |
| `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET` | Google Calendar OAuth 用クライアント情報 |
| `GOOGLE_CALENDAR_ACCESS_TOKEN`, `GOOGLE_CALENDAR_REFRESH_TOKEN` | 既存のトークンを再利用する場合 |
| `ENABLE_MOCK_MODE`, `MOCK_*_ENABLED` | モック環境でのテスト設定 |

### 2.4 Discord Bot 準備

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成
2. **Bot** タブでトークンを発行し、必要な権限に `Send Messages`, `Read Message History`, `Use Slash Commands` を含める
3. OAuth2 → URL Generator で `bot` と `applications.commands` を選択し、サーバーへ招待
4. `.env` に `DISCORD_BOT_TOKEN` と `DISCORD_GUILD_ID` を記入

---

## 3. 基本的な使い方

### 3.1 テキストメッセージ

Discord の `#memo` チャンネルに文章を投稿すると、以下の処理が走ります。

1. Gemini で要約・タグ・カテゴリを推定
2. `vault/` 配下に Markdown ノートを作成
3. Daily Note に概要を反映（`Daily Note Integration` が有効な場合）

### 3.2 URL を含むメッセージ

本文に URL がある場合は自動でコンテンツを取得し、ノート末尾に「URL 要約」セクションを追加します。同じ URL は重複整理されます。

### 3.3 音声ファイル

MP3 / WAV / FLAC / OGG / M4A / WEBM を添付すると Speech-to-Text で文字起こしを実行します。認証情報が設定されていない場合はファイルを保存し、処理待ちとして記録します。

---

## 4. 利用可能な Slash コマンド

### 基本コマンド

| コマンド | 説明 |
| --- | --- |
| `/help` | 利用可能なコマンドの概要を表示 |
| `/status` | Bot の稼働状況と接続状態を表示 |
| `/search query:<キーワード> [limit]` | Obsidian ノートを検索 |
| `/random` | ランダムなノートを表示 |

### 統計コマンド

| コマンド | 説明 |
| --- | --- |
| `/bot` | Bot の稼働統計 (uptime, メモリ等) |
| `/obsidian` | ノート総数や最新更新などの統計 |
| `/finance` | 家計関連統計 (今月の支出など) |
| `/tasks` | タスク統計 (アクティブ数、完了率など) |

### 外部連携・ヘルスチェック

| コマンド | 説明 |
| --- | --- |
| `/integration_status` | 外部連携モジュールの状態一覧 |
| `/system_status` | スケジューラや監視メトリクスの状況 |
| `/manual_sync name:<連携名>` | 指定連携の手動同期 (`garmin` など) |
| `/integration_config` | 現在の連携設定を確認 |
| `/scheduler_status` | 実行中ジョブと次回実行予定を確認 |
| `/lifelog_stats` | ライフログの要約レポートを表示 |
| `/garmin_today` | 当日の Garmin アクティビティサマリー |
| `/garmin_sleep` | Garmin 睡眠データの要約 |
| `/calendar_auth` | Google Calendar OAuth を開始 |
| `/calendar_token code:<認証コード>` | OAuth で取得したコードを登録 |
| `/calendar_test` | Google Calendar 接続テスト |

### 設定コマンド

| コマンド | 説明 |
| --- | --- |
| `/show [setting]` | 既知の設定値を表示（現在は検出済みチャンネル数を返答） |
| `/set setting:<キー> value:<値>` | 設定更新リクエスト（永続化は順次実装中） |
| `/history` | 設定変更履歴（履歴が無い場合は案内のみ） |

> **補足:** Slash コマンドはギルド専用同期です。 Bot を再起動した直後は反映まで数秒〜1分程度かかる場合があります。

---

## 5. 外部サービス連携

### 5.1 Garmin Connect

1. `.env` に `GARMIN_EMAIL` と `GARMIN_PASSWORD` を設定
2. Bot 起動後 `/integration_status` で `garmin` が有効になっているか確認
3. `/garmin_today` や `/garmin_sleep` で同期結果を確認

Garmin 連携は `HealthAnalysisScheduler` によりバックグラウンドで実行され、 Daily Note にアクティビティレポートが追記されます。

### 5.2 Google Calendar

1. `.env` に `GOOGLE_CALENDAR_CLIENT_ID` と `GOOGLE_CALENDAR_CLIENT_SECRET` を設定
2. `/calendar_auth` で表示される URL にブラウザからアクセスし、 Google アカウントで認証
3. 取得したコードを `/calendar_token code:<...>` で登録
4. `/calendar_test` で接続を検証

Calendar イベントはライフログの一部として日次ノートに統合されます。

### 5.3 GitHub バックアップ

- `GITHUB_TOKEN` と `OBSIDIAN_BACKUP_REPO` を設定すると、 GitHub リポジトリに Vault を保存できます。
- `ENVIRONMENT=production` のとき、起動時にリモートから pull、終了時に push を試行します。

---

## 6. 音声メモの処理

| 項目 | 内容 |
| --- | --- |
| 対応フォーマット | MP3 / WAV / FLAC / OGG / M4A / WEBM |
| 最大ファイルサイズ | Discord 制限に準拠 (25MB) |
| 認証情報 | `GOOGLE_CLOUD_SPEECH_API_KEY` もしくは JSON を `GOOGLE_CLOUD_SPEECH_CREDENTIALS` に設定 |
| フォールバック | 認証情報が無い場合はファイルを保存して再処理待ちにする |

処理結果は通常ノートと同じフォーマットで作成され、音声トラックのメタデータや AI 要約が追記されます。

---

## 7. カスタマイズのヒント

- **テンプレート**: `vault/90_Meta/Templates/` にカスタムテンプレートを配置すると `TemplateEngine` が読み込みます。
- **ログ**: `LOG_LEVEL=DEBUG` や `LOG_FORMAT=text` を設定すると詳細なログを確認できます。
- **モックモード**: `ENABLE_MOCK_MODE=true` と `MOCK_GEMINI_ENABLED=true` などを組み合わせると外部 API へ接続せずに開発できます。
- **Vault パス**: デフォルトでは `./vault`。別ディレクトリを指定する場合は `.env` の `OBSIDIAN_VAULT_PATH` を更新してください。

---

## 8. トラブルシューティング

### Bot が応答しない

1. `/status` で稼働確認
2. `.env` のトークン/ギルド ID を再確認
3. `uv run python -m src.main` を再実行し、コンソールログでエラーを確認

### Slash コマンドが表示されない

- Bot を招待する際に `applications.commands` 権限が付与されているか確認
- `DISCORD_GUILD_ID` が正しく設定されているか確認
- Bot を再起動して Discord 側の同期を待つ

### 音声文字起こしに失敗する

- `GOOGLE_CLOUD_SPEECH_API_KEY` または `GOOGLE_CLOUD_SPEECH_CREDENTIALS` が設定されているか確認
- Google Cloud Console で Speech-to-Text API が有効か確認

### Obsidian ノートが生成されない

- `OBSIDIAN_VAULT_PATH` が存在し、書き込み権限があるか確認
- `/integration_status` で関連する連携にエラーがないか確認

### GitHub 同期に失敗する

- `GITHUB_TOKEN` に `repo` 権限があるか確認
- Bot 実行ユーザーが Vault ディレクトリで `git` コマンドを利用できるか確認

---

必要に応じて `logs/` ディレクトリを参照すると詳細なデバッグ情報を取得できます。追加の質問があれば Issue やサポートチャンネルで共有してください。
