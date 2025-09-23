# MindBridge ユーザーガイド

AI 駆動の知識管理システム「 MindBridge 」の使い方ガイドです。 Discord を通じて音声メモやメッセージを AI で処理し、自動的に Obsidian ノートに整理するシステムです。

## 📋 目次

- [1. 概要](#1-概要)
- [2. セットアップ](#2-セットアップ)
- [3. 基本的な使い方](#3-基本的な使い方)
- [4. Discord コマンド](#4-discord-コマンド)
- [5. 音声メモ機能](#5-音声メモ機能)
- [6. タスク・財務管理](#6-タスク財務管理)
- [7. 健康・ライフログ](#7-健康ライフログ)
- [8. 設定・カスタマイズ](#8-設定カスタマイズ)
- [9. トラブルシューティング](#9-トラブルシューティング)

## 1. 概要

### ✨ 主要機能

- **AI メッセージ処理** - Discord メッセージを自動分析・分類してノート生成
- **音声メモ変換** - 音声ファイルを自動でテキスト化して構造化ノート作成
- **Obsidian 統合** - 自動的に Daily Note や専用ノートに整理
- **タスク管理** - TODO の作成・追跡・プロジェクト管理
- **財務管理** - 支出追跡・サブスクリプション管理・予算分析
- **健康ログ** - Garmin Connect 連携で自動ヘルスデータ取得
- **外部連携** - Google Calendar 、 GitHub 同期

### 🏗️ システム構成

```
Discord → AI 処理 (Google Gemini) → Obsidian ノート生成
    ↓
外部サービス連携 (Garmin/Google Calendar) → ライフログ統合
```

## 2. セットアップ

### 2.1 必要な環境

- Python 3.13 以上
- Discord アカウント・サーバー
- Google Cloud アカウント（ AI ・音声認識用）
- Obsidian Vault （推奨）

### 2.2 インストール

```bash
# 1. リポジトリをクローン
git clone https://github.com/your-username/mindbridge.git
cd mindbridge

# 2. 依存関係をインストール
uv sync --dev

# 3. 環境設定（対話式）
./scripts/manage.sh init

# 4. ローカル実行
uv run python -m src.main
```

### 2.3 基本設定

初回セットアップで以下の情報が必要です：

#### 必須設定
- **Discord Bot Token** - Discord Developer Portal で取得
- **Google AI API Key** - Google AI Studio で取得
- **Obsidian Vault Path** - ローカルの Obsidian Vault パス

#### オプション設定
- **Garmin Connect** - ユーザー名・パスワード（健康データ取得用）
- **Google Calendar** - サービスアカウント認証情報
- **GitHub Token** - Vault 同期用（推奨）

### 2.4 Discord Bot セットアップ

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーション作成
2. Bot トークンを取得
3. 必要な権限を設定：
   - Send Messages
   - Read Message History
   - Attach Files
   - Use Slash Commands
4. サーバーに Bot を招待

## 3. 基本的な使い方

### 3.1 Discord でのメッセージ処理

普通にメッセージを送信するだけで AI が自動処理します：

```
[あなた] 今日のミーティングでプロジェクトの進捗について話し合った。
来週までにデザインを完成させる必要がある。

[Bot] 📝 メッセージを処理しました
✅ ノート作成: "2024-01-15 ミーティング議事録"
🏷️ タグ: #会議 #プロジェクト #デザイン
📅 期限: 2024-01-22 (デザイン完成)
```

### 3.2 URL の自動要約

URL を含むメッセージは自動で要約されます：

```
[あなた] この記事が面白い https://example.com/article

[Bot] 📰 記事を要約しました
📄 タイトル: "AI の最新動向について"
📝 要約: AI の発展により...
🏷️ カテゴリ: #AI #技術
```

### 3.3 音声メモの処理

音声ファイルを添付するだけで自動処理：

```
[あなた] [音声ファイル添付]

[Bot] 🎤 音声メモを処理しました
📝 内容: "明日のプレゼンテーションの準備で..."
🏷️ タグ: #プレゼン #準備
⏰ 推定時間: 45 分
```

## 4. Discord コマンド

### 4.1 基本コマンド

#### `/help` - ヘルプ表示
利用可能なコマンド一覧を表示

#### `/status` - システム状態確認
```
/status
```
- Bot の動作状況
- AI プロセッサーの状態
- 外部サービス接続状況

#### `/stats` - 統計情報
```
/stats [period]
```
- `daily` - 本日の処理件数
- `weekly` - 今週の処理件数
- `monthly` - 今月の処理件数

### 4.2 ノート管理

#### `/search` - ノート検索
```
/search query:検索キーワード [limit:件数]
```

#### `/daily` - Daily Note 表示
```
/daily [date:2024-01-15]
```
指定日（デフォルト：今日）の Daily Note を表示

#### `/recent` - 最近のノート
```
/recent [limit:10]
```
最近作成されたノートを表示

### 4.3 タスク管理

#### `/task create` - タスク作成
```
/task create title:タスク名 [due:2024-01-20] [priority:high]
```

#### `/task list` - タスク一覧
```
/task list [status:pending] [project:プロジェクト名]
```

#### `/task complete` - タスク完了
```
/task complete id:task_123
```

### 4.4 財務管理

#### `/expense add` - 支出記録
```
/expense add amount:1500 category:食費 [description:ランチ代]
```

#### `/expense report` - 支出レポート
```
/expense report [period:monthly] [category:食費]
```

#### `/subscription` - サブスクリプション管理
```
/subscription list
/subscription add name:Netflix amount:1200 billing_cycle:monthly
```

### 4.5 健康・ライフログ

#### `/health sync` - 健康データ同期
```
/health sync [date:2024-01-15]
```
Garmin Connect から健康データを取得

#### `/health report` - 健康レポート
```
/health report [period:weekly]
```

#### `/lifelog` - ライフログエントリ
```
/lifelog add content:今日は良い一日だった mood:good energy:high
```

## 5. 音声メモ機能

### 5.1 対応フォーマット

- MP3 、 WAV 、 FLAC 、 OGG 、 M4A 、 WEBM
- 最大ファイルサイズ： 25MB （ Discord 制限）
- 最大音声長： 10 分

### 5.2 音声処理の流れ

1. **音声ファイル添付** - Discord チャンネルに音声ファイルをアップロード
2. **音声認識** - Google Cloud Speech-to-Text で自動転写
3. **AI 分析** - Google Gemini で内容分析・構造化
4. **ノート生成** - Obsidian 形式で自動保存

### 5.3 音声メモのカスタマイズ

`.env` ファイルで設定可能：

```env
# 音声認識設定
SPEECH_LANGUAGE_CODE=ja-JP
SPEECH_ALTERNATIVE_LANGUAGE_CODES=en-US
SPEECH_PROFANITY_FILTER=false

# 音声品質設定
SPEECH_ENHANCED_MODELS=true
SPEECH_PUNCTUATION=true
```

### 5.4 音声メモテンプレート

生成されるノートの構造：

```markdown
---
type: voice_memo
date: 2024-01-15
tags: [音声メモ, 自動生成]
duration: "2:45"
confidence: 0.92
---

# 音声メモ - 2024-01-15 14:30

## 📝 内容

[転写されたテキスト]

## 🏷️ 分析結果

- **カテゴリ**: 会議
- **感情**: ポジティブ
- **緊急度**: 中
- **関連トピック**: プロジェクト管理

## ✅ アクションアイテム

- [ ] デザイン資料の準備
- [ ] 来週のミーティング設定
```

## 6. タスク・財務管理

### 6.1 タスク管理機能

#### プロジェクト管理
```
/task project create name:新プロジェクト description:説明
/task project list
/task project archive name:プロジェクト名
```

#### タスクの詳細管理
- **優先度設定**： low, medium, high, urgent
- **期限設定**：自然言語での日付指定対応
- **タグ機能**：自動タグ付けとカスタムタグ
- **進捗追跡**：進捗率の記録

#### 定期タスク
```
/task recurring create title:定期報告 frequency:weekly day:friday
```

### 6.2 財務管理機能

#### 支出追跡
- **カテゴリ自動分類**： AI による支出カテゴリの自動判定
- **レシート処理**：画像添付でのレシート情報抽出（将来実装予定）
- **月次・年次レポート**：自動集計とグラフ生成

#### 予算管理
```
/budget set category:食費 amount:50000 period:monthly
/budget status [category]
```

#### サブスクリプション監視
- **更新通知**：期限前の自動アラート
- **コスト分析**：月次・年次のサブスクリプション費用集計
- **重複検出**：類似サービスの重複チェック

## 7. 健康・ライフログ

### 7.1 Garmin Connect 連携

#### セットアップ
```env
GARMIN_USERNAME=your_username
GARMIN_PASSWORD=your_password
```

#### 自動データ取得
- **活動データ**：歩数、距離、カロリー、心拍数
- **睡眠データ**：睡眠時間、睡眠質、深い睡眠時間
- **ストレス**：ストレスレベルの記録
- **体重・体組成**：対応デバイスからの自動取得

#### 健康レポート生成
週次・月次で自動生成される健康レポート：

```markdown
# 健康レポート - 2024 年 1 月第 3 週

## 📊 活動サマリー
- 平均歩数: 8,543 歩/日
- 総距離: 45.2 km
- 活動カロリー: 12,450 kcal

## 😴 睡眠分析
- 平均睡眠時間: 7 時間 15 分
- 平均睡眠質: 76%
- 深い睡眠: 平均 1 時間 45 分

## 💪 フィットネス目標
- ✅ 週間歩数目標達成 (60,000 歩)
- ⚠️ 運動回数目標未達成 (2/4 回)
```

### 7.2 Google Calendar 連携

#### 会議・イベント自動インポート
- 会議時間とタイトルの自動記録
- 移動時間の考慮
- 繰り返しイベントの処理

#### ライフログとの統合
カレンダーイベントとの組み合わせで詳細なライフログを生成：

```markdown
## 2024-01-15 のタイムライン

### 09:00-10:00 朝のジョギング
- 距離: 5.2 km
- 心拍数: 平均 145 bpm
- カロリー: 287 kcal

### 10:30-12:00 プロジェクト会議
- 参加者: 5 名
- 議題: Q1 計画の確認
- アクション: デザイン資料の準備

### 12:00-13:00 ランチ
- 支出: ¥1,200 (カテゴリ: 食費)
- 場所: オフィス近くのレストラン
```

## 8. 設定・カスタマイズ

### 8.1 環境変数設定

主要な設定項目：

```env
# Discord Bot
DISCORD_TOKEN=your_bot_token
DISCORD_GUILD_ID=your_guild_id

# AI 処理
GOOGLE_AI_API_KEY=your_api_key
AI_MODEL=gemini-pro
AI_TEMPERATURE=0.7

# Obsidian
OBSIDIAN_VAULT_PATH=/path/to/your/vault
OBSIDIAN_DAILY_NOTE_FOLDER=Daily Notes
OBSIDIAN_TEMPLATE_FOLDER=Templates

# 外部サービス
GARMIN_USERNAME=your_username
GARMIN_PASSWORD=your_password
GOOGLE_CALENDAR_CREDENTIALS_PATH=/path/to/credentials.json

# GitHub 同期
GITHUB_TOKEN=your_token
GITHUB_REPO=username/obsidian-vault
```

### 8.2 ノートテンプレートのカスタマイズ

`{OBSIDIAN_VAULT_PATH}/Templates/` フォルダにカスタムテンプレートを配置：

#### `voice_memo_template.md`
```markdown
---
type: voice_memo
date: {{date}}
tags: {{tags}}
duration: {{duration}}
---

# {{title}}

## 内容
{{content}}

## 分析
{{analysis}}

## 次のアクション
{{action_items}}
```

### 8.3 AI プロンプトのカスタマイズ

`src/ai/prompts/` フォルダのプロンプトテンプレートを編集して AI の動作をカスタマイズ可能。

### 8.4 通知設定

```env
# Discord 通知
DISCORD_NOTIFY_CHANNELS=general,private-log
DISCORD_NOTIFY_LEVEL=info

# システム通知
HEALTH_CHECK_INTERVAL=300
ERROR_NOTIFICATION_WEBHOOK=your_webhook_url
```

## 9. トラブルシューティング

### 9.1 よくある問題

#### Bot が応答しない
```bash
# 1. Bot の状態確認
/status

# 2. ログ確認
uv run python -m src.main --debug

# 3. 権限確認（ Discord サーバー設定）
```

#### 音声認識が失敗する
- ファイル形式を確認（対応形式： MP3, WAV, FLAC など）
- ファイルサイズを確認（ 25MB 以下）
- 音声品質を確認（ノイズが多い場合は失敗しやすい）

#### Obsidian ノートが生成されない
```bash
# Vault パスの確認
echo $OBSIDIAN_VAULT_PATH

# 権限確認
ls -la $OBSIDIAN_VAULT_PATH
```

### 9.2 ログレベルの設定

```env
# デバッグレベルのログ出力
LOG_LEVEL=DEBUG
STRUCTLOG_LEVEL=DEBUG

# 特定コンポーネントのログ
AI_PROCESSOR_LOG_LEVEL=DEBUG
DISCORD_BOT_LOG_LEVEL=INFO
```

### 9.3 パフォーマンス最適化

#### メモリ使用量の監視
```bash
# システム状態確認
/status

# 詳細メモリ情報
uv run python -c "from src.utils.memory_tracker import MemoryTracker; MemoryTracker.get_detailed_usage()"
```

#### キャッシュ設定の調整
```env
# コンポーネントキャッシュ時間
AI_PROCESSOR_CACHE_TTL=3600  # 1 時間
GARMIN_CLIENT_CACHE_TTL=1800  # 30 分
```

### 9.4 バックアップとリストア

#### Obsidian Vault のバックアップ
```bash
# 手動バックアップ
cp -r $OBSIDIAN_VAULT_PATH ~/backups/vault-$(date +%Y%m%d)

# GitHub 同期でのバックアップ
git -C $OBSIDIAN_VAULT_PATH add .
git -C $OBSIDIAN_VAULT_PATH commit -m "Auto backup $(date)"
git -C $OBSIDIAN_VAULT_PATH push
```

#### 設定のバックアップ
```bash
# 環境設定のバックアップ
cp .env .env.backup.$(date +%Y%m%d)
```

### 9.5 サポート・フィードバック

問題が解決しない場合：

1. **ログファイルの確認**：`logs/` フォルダの最新ログを確認
2. **GitHub Issues**：バグレポートや機能要求を投稿
3. **デバッグモード**：`--debug` フラグでの詳細ログ出力

---

## 🎯 次のステップ

1. **基本機能を試す**： Discord でメッセージや音声メモを送信
2. **外部サービス連携**： Garmin や Google Calendar の設定
3. **カスタマイズ**：テンプレートやプロンプトの調整
4. **自動化**：定期タスクやヘルスチェックの設定

MindBridge を使って効率的な知識管理とライフログを始めましょう！

---

*最終更新: 2024-01-15*
*バージョン: 1.0*
