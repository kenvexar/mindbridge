# MindBridge ユーザーガイド

初期セットアップから日常運用、外部連携、トラブル対応までを一冊にまとめました。

## 1. 何ができるか
- Discord Bot が投稿・添付・URL を受け取り、AI で要約・タグ付けして Obsidian ノートを作成。
- Garmin / Google Calendar などのデータを同期し、日次ノートや統計に反映。
- タスク・家計の Slash コマンド、音声文字起こし、Vault の GitHub バックアップを提供。

## 2. 初期セットアップ

### 2.1 前提
- Python 3.13 以上、`uv` が導入済み
- Discord Bot トークンとギルド ID
- Google Gemini API キー
- Obsidian Vault の保存先ディレクトリ

### 2.2 手順
```bash
git clone https://github.com/your-username/mindbridge.git
cd mindbridge
uv sync --dev                     # 依存インストール
./scripts/manage.sh init          # 対話で .env を生成
./scripts/manage.sh run           # 起動（内部で uv run python -m src.main）
```
Slash コマンドの同期に数秒〜数十秒かかります。`/status` が応答すれば完了です。

### 2.3 必須と推奨の環境変数

| 変数 | 役割 | 必須 | 備考 |
| --- | --- | --- | --- |
| `DISCORD_BOT_TOKEN` | Bot トークン | ✅ | Developer Portal で取得 |
| `DISCORD_GUILD_ID` | 同期対象ギルド | ✅ | 複数ギルド運用は未対応 |
| `GEMINI_API_KEY` | Gemini API キー | ✅ | `models/gemini-2.5-flash` が既定 |
| `OBSIDIAN_VAULT_PATH` | Vault 保存先 | 推奨 | 既定は `./vault` |
| `ENVIRONMENT` | 環境ラベル | 推奨 | `personal` / `development` / `production` |
| `LOG_LEVEL`, `LOG_FORMAT` | ログ制御 | 任意 | `INFO` / `json` が既定 |

### 2.4 オプション（必要になったら追加）
- 音声文字起こし: `GOOGLE_CLOUD_SPEECH_API_KEY` または `GOOGLE_CLOUD_SPEECH_CREDENTIALS`
- Garmin: `GARMIN_EMAIL`, `GARMIN_PASSWORD`
- Google Calendar: `GOOGLE_CALENDAR_CLIENT_ID`, `GOOGLE_CALENDAR_CLIENT_SECRET` または `GOOGLE_CALENDAR_SERVICE_ACCOUNT`
- GitHub バックアップ: `GITHUB_TOKEN`, `OBSIDIAN_BACKUP_REPO`, `OBSIDIAN_BACKUP_BRANCH`
- モックモード: `ENABLE_MOCK_MODE=true` と各 `MOCK_*_ENABLED`

### 2.5 Discord Bot の準備
1. Developer Portal でアプリを作成し Bot を有効化。
2. `MESSAGE CONTENT INTENT` をオンにしてトークンを取得。
3. OAuth2 URL Generator で `bot` と `applications.commands` を選択し、`Send Messages` / `Read Message History` / `Use Slash Commands` を付けてサーバへ招待。
4. `.env` に `DISCORD_BOT_TOKEN` と `DISCORD_GUILD_ID` を設定して起動。再招待時も `/sync` は不要です。

## 3. 日常の使い方
1. 監視チャンネル（既定: `memo`, `notifications`, `commands`）へ投稿。
2. `MessageProcessor` がテキストや添付を整形し、`AIProcessor` / `AdvancedNoteAnalyzer` が要約とタグ付け。
3. `TemplateEngine` が Markdown を生成し、`ObsidianFileManager` が Vault に保存。
4. `DailyNoteIntegration` が日次ノートに統計を反映し、必要に応じて GitHub 同期。

主要コマンドは `docs/basic-usage.md` に一覧があります。応答が遅いときは `/system_status` で各コンポーネントの状態を確認してください。

## 4. 外部サービス連携

### Garmin
1. `.env` に `GARMIN_EMAIL`, `GARMIN_PASSWORD` を設定。
2. 起動後 `/integration_status` で `garmin` が `active` か確認。
3. `/garmin_today`, `/garmin_sleep` で手動取得。バックグラウンドでは `HealthAnalysisScheduler` が日次ノートを更新します。

### Google Calendar
1. OAuth クライアント ID/Secret を設定して再起動。
2. `/calendar_auth` で表示された URL にアクセスし、認可コードを `/calendar_token` へ渡す。
3. `/calendar_test` で予定が取得できれば完了。日次ノートへ自動追記されます。

### GitHub Vault バックアップ
- `GITHUB_TOKEN` と `OBSIDIAN_BACKUP_REPO` を設定すると、起動時に `git pull`、終了時に `git push` を実行します。
- SSH 鍵で運用する場合は Deploy Key を用意し、Vault ディレクトリに `known_hosts` を配置してください。
- 詳細な運用ノートは `docs/maintenance/github-sync.md` へ。

## 5. 音声メモ
| 項目 | 内容 |
| --- | --- |
| 対応フォーマット | MP3 / WAV / FLAC / OGG / M4A / WEBM |
| 認証 | `GOOGLE_CLOUD_SPEECH_API_KEY` またはサービスアカウント JSON |
| フロー | 認証確認 → Speech-to-Text → 要約を YAML/本文に追加 |
| フォールバック | API 不通時はファイルのみ保存し `pending` として記録 |
| 使用量監視 | `SpeechAPIUsage` が月次累計を追跡し、閾値超過を通知 |

## 6. カスタマイズのヒント
- **テンプレート**: `vault/90_Meta/Templates/` に Markdown を置くと `TemplateEngine` が利用します（`{title}`, `{timestamp}` などのプレースホルダー対応）。
- **チャンネル**: `src/bot/channel_config.py` の `ChannelConfig` を更新。再起動すれば `/status` に反映。
- **モックモード**: 外部 API を呼びたくない CI・検証では `ENABLE_MOCK_MODE=true` を設定。
- **ログ**: `LOG_LEVEL=DEBUG`, `LOG_FORMAT=text` で詳細ログ。セキュリティイベントは `access_logger` 経由で JSON 出力。

## 7. トラブルシュート速見表
| 症状 | 確認ポイント |
| --- | --- |
| Bot がオンラインにならない | `.env` のトークン類、`./scripts/manage.sh run` のログに例外がないか |
| Slash コマンドが見えない | 招待時の権限、`DISCORD_GUILD_ID`、起動直後は同期待ち時間がある |
| ノートが増えない | `OBSIDIAN_VAULT_PATH` の書き込み権限、`logs/` のエラー、有効なテンプレートがあるか |
| 音声が文字起こしされない | Speech API キー/サービスアカウント、`GOOGLE_APPLICATION_CREDENTIALS` のパス権限 |
| Garmin/Calendar が止まる | `/integration_status` と `/manual_sync` の結果、期限切れ認証のログ |
| GitHub 同期が失敗 | PAT/SSH の権限、Vault ディレクトリで `git status`、`logs/github_sync.log` |

## 8. 参考リンク
- クイックスタート: `docs/quick-start.md`
- コマンド詳細: `docs/basic-usage.md`
- システム構成: `docs/architecture.md`
- デプロイ手順: `docs/deploy/overview.md`, `docs/deploy/local.md`, `docs/deploy/beelink-fedora.md`
- YAML スキーマ: `docs/yaml-front-matter.md`
- 運用ノート: `docs/maintenance/housekeeping.md`

不明点があれば Issue やサポートチャンネルで相談してください。
