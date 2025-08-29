# 📦 詳細インストール手順

Discord-Obsidian Memo Bot の完全なインストールと設定方法を説明します。全機能を活用したい場合はこちらのガイドに従ってください。

> 💡 **クイックスタートをお探しの方へ**: 5 分で動かしたい場合は [EASY_SETUP.md](../EASY_SETUP.md) をご覧ください。

## 📋 目次

1. [システム要件](#システム要件)
2. [事前準備](#事前準備)
3. [本体インストール](#本体インストール)
4. [Discord 設定](#discord-設定)
5. [API 設定](#api-設定)
6. [チャンネル設定](#チャンネル設定)
7. [Obsidian 設定](#obsidian-設定)
8. [オプション機能](#オプション機能)
9. [動作確認](#動作確認)
10. [トラブルシューティング](#トラブルシューティング)

## 💻 システム要件

### 必須要件
- **OS**: macOS 10.15+, Ubuntu 20.04+, Windows 10+ (WSL2 推奨)
- **Python**: 3.13 以上（プロジェクトは 3.13 で開発）
- **メモリ**: 最小 512MB 、推奨 1GB 以上
- **ディスク**: 最小 1GB 、推奨 5GB 以上（ Obsidian ボルト含む）
- **ネットワーク**: インターネット接続必須

### 推奨環境
- **CPU**: 2 コア以上
- **メモリ**: 2GB 以上
- **SSD**: 推奨（高速なファイル I/O ）

## 🔧 事前準備

### 1. Python 3.13 のインストール

**macOS (Homebrew)**
```bash
brew install python@3.13
python3.13 --version
```

**Ubuntu/Debian**
```bash
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.13 python3.13-venv python3.13-pip
```

**Windows (WSL2 推奨)**
```bash
# WSL2 Ubuntu 環境で上記 Ubuntu 手順を実行
```

### 2. uv パッケージマネージャーのインストール

```bash
# Unix 系 OS (macOS/Linux) - 推奨
curl -LsSf https://astral.sh/uv/install.sh | sh

# 手動インストール（ pip 経由）
pip install uv

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# インストール確認
uv --version
```

### 3. Git のインストール

```bash
# macOS
brew install git

# Ubuntu
sudo apt install git

# Windows
# Git for Windows をダウンロード・インストール
```

## 📥 本体インストール

### 1. リポジトリの取得

```bash
# GitHub からクローン
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# プロジェクト構造確認
ls -la
```

### 2. 依存関係のインストール

```bash
# 本番用依存関係のインストール
uv sync

# 開発用依存関係も含める場合（開発者向け）
uv sync --dev

# インストール済みパッケージ確認
uv pip list
```

### 3. 環境設定ファイルの準備

```bash
# サンプル設定をコピー
cp .env.example .env

# 設定ファイル確認
cat .env.example
```

## 🤖 Discord 設定

### 1. Discord Bot の作成

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. "New Application" をクリック
3. アプリケーション名を入力（例: "My Knowledge Bot"）
4. 作成後、アプリケーション ID をメモ

### 2. Bot の設定

1. 左メニューから "Bot" を選択
2. "Add Bot" をクリック
3. Bot 設定を行う：
   - **Public Bot**: オフ（個人利用のため）
   - **Requires OAuth2 Code Grant**: オフ
   - **Message Content Intent**: オン（必須）
   - **Server Members Intent**: オン（推奨）
   - **Presence Intent**: オフ

### 3. Bot トークンの取得

1. "Token" セクションで "Copy" をクリック
2. トークンを安全な場所に保存
3. `.env` ファイルの `DISCORD_BOT_TOKEN` に設定

### 4. Bot 権限の設定

1. 左メニューから "OAuth2" → "URL Generator" を選択
2. **Scopes** を選択：
   - `bot`
   - `applications.commands`

3. **Bot Permissions** を選択：
   - **Text Permissions**:
     - Send Messages
     - Send Messages in Threads
     - Embed Links
     - Attach Files
     - Read Message History
     - Add Reactions
   - **Voice Permissions**:
     - Connect
     - Speak
   - **General Permissions**:
     - Use Slash Commands

### 5. Bot をサーバーに招待

1. 生成された URL をコピー
2. URL にアクセスして Bot を招待
3. 適切なサーバーを選択
4. 権限を確認して認証

## 🔑 API 設定

### 1. Google Gemini API

**API キーの取得:**
1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. Google アカウントでログイン
3. "Get API key" をクリック
4. "Create API key in new project" を選択
5. API キーをコピーして `.env` の `GEMINI_API_KEY` に設定

**使用量制限の確認:**
- 無料版: 1 日 1500 リクエスト、 1 分 15 リクエスト
- 有料版が必要な場合は [Google Cloud Console](https://console.cloud.google.com/) で設定

### 2. Google Cloud Speech-to-Text API （オプション）

**サービスアカウントの作成:**
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを作成または選択
3. "APIs & Services" → "Credentials"
4. "Create Credentials" → "Service Account"
5. サービスアカウント名を入力
6. 役割を選択: "Cloud Speech Client"
7. JSON キーをダウンロード

**設定:**
```bash
# サービスアカウントキーの配置
mkdir -p ~/.config/gcloud/
cp ~/Downloads/service-account-key.json ~/.config/gcloud/speech-key.json

# 環境変数設定
echo "GOOGLE_APPLICATION_CREDENTIALS=$HOME/.config/gcloud/speech-key.json" >> .env
```

### 3. Garmin Connect （オプション）

```env
# Garmin Connect 認証情報
GARMIN_EMAIL=your_email@example.com
GARMIN_USERNAME=your_username
GARMIN_PASSWORD=your_password
```

## 📺 チャンネル設定

### 🆕 シンプル化されたチャンネル構成

Discord サーバーで以下の **3 つのチャンネルのみ** 作成します：

**📝 MEMO SYSTEM （必須）:**
```
#memo           - 🆕 統合入力チャンネル（すべてのコンテンツタイプ対応）
```

**⚙️ SYSTEM （必須）:**
```
#notifications  - ボット通知
#commands       - ボットコマンド
```

**🎯 AI 自動分類システム**

`#memo` チャンネルに投稿されたすべてのコンテンツ（テキスト・音声・ファイル）は AI により自動分類され、 Obsidian の適切なフォルダに保存されます：

- **💰 Finance** → 「 1500 ランチ」「¥3000 本」などの支出情報
- **✅ Tasks** → 「 TODO: 資料作成」「期限: 明日まで」などのタスク
- **🏃 Health** → 「体重 70kg 」「ランニング 5km 」などの健康データ
- **📚 Learning** → 「 Python 学習」「読書メモ」などの学習記録
- **🎙️ Voice Memos** → 音声ファイルの自動文字起こし
- **📁 Files** → ファイル共有の適切なフォルダ分類
- **📝 Memos** → その他の一般的なメモ

> **🆕 大幅な簡素化**: 従来の複雑な多チャンネル構成（ 17 個以上）から、 3 チャンネルの AI 自動分類システムに移行しました。

### 🆕 自動チャンネル検出

**チャンネル ID の取得は不要です！** ボットは以下のチャンネル名で自動検出します：

- `memo` - メイン入力チャンネル
- `notifications` - システム通知
- `commands` - ボットコマンド

> 💡 **ポイント**: 正確なチャンネル名（ memo 、 notifications 、 commands ）で作成すれば、ボットが自動的に見つけて接続します。

### 2. サーバー ID の取得

1. Discord で開発者モードを有効化：設定 → 詳細設定 → 開発者モード をオン
2. Discord サーバー名を右クリック → "ID をコピー"
3. `.env` の `DISCORD_GUILD_ID` に設定

## 📚 Obsidian 設定

### 1. Obsidian ボルトの準備

**新規ボルトの作成:**
```bash
# ボルトディレクトリ作成
mkdir -p ~/Documents/ObsidianVault
cd ~/Documents/ObsidianVault

# AI 自動分類に対応したフォルダ構造作成
mkdir -p {00_Inbox,01_Projects,02_DailyNotes,03_Ideas,04_Archive,05_Resources}
mkdir -p {Finance,Tasks,Health,Learning,"Voice Memos",Files,"Quick Notes",Memos}
mkdir -p {10_Attachments,99_Meta/Templates}
```

**既存ボルトを使用する場合:**
```bash
# 既存ボルトパスを確認
ls -la /path/to/your/existing/vault

# .env ファイルにパス設定
echo "OBSIDIAN_VAULT_PATH=/path/to/your/existing/vault" >> .env
```

### 2. テンプレートファイルの作成

**基本テンプレート:**
```bash
# デイリーノートテンプレート
cat > ~/Documents/ObsidianVault/99_Meta/Templates/daily_note.md << 'EOF'
# {{date}}

## 📝 Today's Summary
{{summary}}

## 🎯 Key Activities
{{activities}}

## 💭 Ideas & Insights
{{ideas}}

## ✅ Tasks Completed
{{completed_tasks}}

## 📊 AI Processing Metrics
- Messages processed: {{message_count}}
- AI requests: {{ai_requests}}
- Files created: {{files_created}}
- Categories detected: {{categories_used}}

## 🔄 Next Actions
{{next_actions}}

---
Created: {{timestamp}}
Tags: #daily-note #ai-processed
EOF
```

### 3. Obsidian 設定

**プラグイン推奨設定:**
1. Obsidian でボルトを開く
2. 設定 → コミュニティプラグイン → セーフモードをオフ
3. 推奨プラグインをインストール：
   - **Calendar** - 日次レビュー用
   - **Templater** - 高度なテンプレート処理
   - **Dataview** - AI 分類データの可視化
   - **Tag Wrangler** - AI タグの整理

## 🔧 オプション機能

### 1. 音声処理の有効化

```env
# Speech-to-Text 設定
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
SPEECH_API_MONTHLY_LIMIT_MINUTES=60
```

> 💡 **音声メモの使い方**: `#memo` チャンネルに音声ファイルをアップロードすると、自動的に文字起こしされて Voice Memos フォルダに分類されます。

### 2. 健康データ統合

```env
# Garmin Connect 設定
GARMIN_EMAIL=your_email@example.com
GARMIN_USERNAME=your_username
GARMIN_PASSWORD=your_password
GARMIN_CACHE_HOURS=24.0
```

> 💡 **健康データの処理**: Garmin のデータは自動取得され、健康関連のメッセージと同様に AI が Health フォルダに分類します。

### 3. 高度な AI 機能

```env
# ベクトル検索の有効化
ENABLE_VECTOR_SEARCH=true

# AI キャッシュ設定
AI_CACHE_SIZE_MB=100
AI_CACHE_HOURS=24

# AI 分類の調整
AI_CLASSIFICATION_CONFIDENCE_THRESHOLD=0.7
```

### 4. セキュリティ設定

```env
# Google Cloud Secret Manager 使用
USE_SECRET_MANAGER=false  # ローカル環境では通常 false
GOOGLE_CLOUD_PROJECT=your-project-id

# アクセスログ
ENABLE_ACCESS_LOGGING=true
SECURITY_LOG_PATH=/path/to/security/logs
```

## ✅ 動作確認

### 1. 設定の検証

```bash
# 環境変数の確認
cat .env | grep -E "(DISCORD_|GEMINI_|OBSIDIAN_)"

# Python 環境の確認
uv run python --version
uv run python -c "import discord; print('discord.py version:', discord.__version__)"
uv run python -c "import google.generativeai as genai; print('Gemini API available')"
```

### 2. テスト実行

```bash
# 全テストの実行
uv run pytest

# 基本機能テスト
uv run pytest tests/unit/test_config.py -v

# 統合テスト
uv run pytest tests/integration/ -v
```

### 3. Bot 起動とテスト

```bash
# Bot を起動
uv run python -m src.main

# 起動ログでチャンネル検出を確認:
# "Found memo channel: 123456789"
# "Found notifications channel: 987654321"
# "Found commands channel: 456789123"

# 別ターミナルで動作確認
# Discord で以下のコマンドを実行:
# /ping
# /status
# /help
```

### 4. 機能別テスト

**🆕 統合メモ機能:**
1. `#memo` チャンネルにテキストメッセージ投稿 → AI が内容を分析して適切なフォルダに分類
2. `#memo` チャンネルに音声ファイルアップロード → 自動文字起こし + AI 分類
3. `#memo` チャンネルにファイル添付 → AI が内容を分析してファイル分類
4. Obsidian ボルトで適切なフォルダに保存されることを確認

**AI 分類テスト:**
- 「 1500 円 ランチ代」→ Finance フォルダ
- 「 TODO: 明日資料作成」→ Tasks フォルダ  
- 「今日のジョギング 3km 」→ Health フォルダ
- 「 Python の勉強メモ」→ Learning フォルダ

**コマンド機能:**
1. `/vault_stats` で統計情報を確認
2. `/search_notes keyword` で検索機能を確認
3. `/ai_stats` で AI 処理状況を確認

## 🔧 トラブルシューティング

### よくある問題

**1. Bot が起動しない**
```bash
# Python バージョン確認
python --version  # 3.13 以上必要

# 依存関係の再インストール
uv sync --reinstall

# ログの確認
tail -f logs/bot.log

# 詳細デバッグ
LOG_LEVEL=DEBUG uv run python -m src.main
```

**2. Discord 認証エラー**
```bash
# トークンの確認
echo $DISCORD_BOT_TOKEN

# Bot 権限の確認
# Discord Developer Portal で以下の権限を確認:
# - Message Content Intent: ON （必須）
# - Send Messages, Read Message History
```

**3. Obsidian ファイル作成エラー**
```bash
# パスと権限の確認
ls -la $OBSIDIAN_VAULT_PATH
chmod 755 $OBSIDIAN_VAULT_PATH

# AI 分類フォルダの確認
tree $OBSIDIAN_VAULT_PATH
# Finance, Tasks, Health, Learning フォルダが存在することを確認
```

**4. API 制限エラー**
```bash
# Gemini API 使用量確認
# Discord で `/ai_stats` コマンド実行
# 無料版制限: 1 日 1500 リクエスト、 1 分 15 リクエスト

# Speech API 確認
# Google Cloud Console で使用量確認
# 無料版制限: 月 60 分
```

### ボットがチャンネルを見つけられない

**症状:** ボットがチャンネルを認識しない

**解決方法:**
1. チャンネル名が正確か確認（`memo`, `notifications`, `commands`）
2. ボットにチャンネル表示権限があるか確認
3. `DISCORD_GUILD_ID` が正しいか確認
4. 起動ログで "Found memo channel" メッセージを確認

### ボットがメッセージに反応しない

**症状:** `#memo` チャンネルにメッセージを投稿しても何も起こらない

**解決方法:**
1. ボットがオンラインか確認
2. ボットに Message Content Intent が有効か確認
3. `#notifications` チャンネルでエラーメッセージを確認
4. AI 分類処理中は数秒待つ

### セットアップ状況の確認

ボット起動時のログで Discord チャンネル検出状況を確認：
```
INFO: Discord bot starting...
INFO: Found memo channel: 123456789
INFO: Found notifications channel: 987654321
INFO: Found commands channel: 456789123
INFO: AI classification system ready
```

### デバッグモード

```bash
# 詳細ログでの起動
LOG_LEVEL=DEBUG uv run python -m src.main

# 特定モジュールのデバッグ
PYTHONPATH=src python -c "from src.config.settings import get_settings; print(get_settings())"
```

### サポート

問題が解決しない場合：
1. [GitHub Issues](https://github.com/kenvexar/mindbridge/issues) で問題を報告
2. ログファイルとエラーメッセージを添付
3. Discord の開発者モードで取得した ID 情報を含める

## 📚 次のステップ

インストールが完了したら：
1. **[簡単セットアップガイド](../EASY_SETUP.md)** - 5 分でのクイックスタート
2. **[開発者向けドキュメント](../CLAUDE.md)** - 技術的な詳細とアーキテクチャ
3. **AI 分類の確認** - 各種コンテンツを `#memo` に投稿してフォルダ分類をテスト

> 💡 **おすすめ**: まずは `#memo` チャンネルに「 1500 円 ランチ代」「 TODO: 明日資料作成」「今日のジョギング 3km 」などを投稿して AI 分類を体験してみてください！

---

🆕 **簡素化されたインストールガイド**: 3 つのチャンネルと AI 自動分類で、従来の複雑な設定が大幅に簡単になりました。問題があれば GitHub Issues でお知らせください。