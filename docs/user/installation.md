# インストールガイド

MindBridge の完全インストール・セットアップガイド。

> 最短手順は [クイックスタート](quick-start.md) を参照してください。

## 前提条件

### システム要件
- **OS**: macOS 10.15+, Ubuntu 20.04+, Windows 10+ (WSL2 推奨)
- **Python**: >=3.13 (プロジェクトは 3.13 で開発)
- **メモリ**: 最小 512MB 、推奨 1GB+
- **ストレージ**: 最小 1GB 、推奨 5GB+ (Obsidian ボルトを含む)
- **ネットワーク**: インターネット接続が必要

### 必要ソフトウェア

**1. Python 3.13**

macOS (Homebrew):
```bash
brew install python@3.13
python3.13 --version
```

Ubuntu/Debian:
```bash
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.13 python3.13-venv python3.13-pip
```

**2. uv パッケージマネージャー**

```bash
# Unix システム (macOS/Linux) - 推奨
curl -LsSf https://astral.sh/uv/install.sh | sh

# pip 経由での手動インストール
curl -LsSf https://astral.sh/uv/install.sh | sh
# macOS の場合（ Homebrew ）: brew install uv

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# インストールを確認
uv --version
```

## インストール

### 1. コードを取得

```bash
# リポジトリをクローン
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# プロジェクト構造を確認
ls -la
```

### 2. 依存関係をインストール

```bash
# 本番用依存関係をインストール
uv sync

# 開発者用（開発依存関係を含む）
uv sync --dev

# インストールを確認
uv pip list
```

### 3. 設定セットアップ

```bash
# サンプル設定をコピー
cp .env.example .env

# 設定ファイルを編集
nano .env  # またはお好みのエディタで
```

## Discord セットアップ

Discord Bot の作成手順は [クイックスタートガイド](quick-start.md#discord-bot-setup) を参照してください。

## API 設定

### 1. Google Gemini API

Gemini API キーの取得手順は [クイックスタートガイド](quick-start.md#gemini-api-setup) を参照してください。

### 2. Google Cloud Speech-to-Text (Optional)

**サービスアカウントを作成:**
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを作成または選択
3. "APIs & Services" → "Credentials" に移動
4. "Create Credentials" → "Service Account" をクリック
5. サービスアカウント名を入力
6. ロールを割り当て: "Cloud Speech Client"
7. JSON キーをダウンロード

**設定:**
```bash
# サービスアカウントキーを配置
mkdir -p ~/.config/gcloud/
cp ~/Downloads/service-account-key.json ~/.config/gcloud/speech-key.json

# 環境変数を設定
echo "GOOGLE_APPLICATION_CREDENTIALS=$HOME/.config/gcloud/speech-key.json" >> .env
```

## Discord チャンネル設定

Discord サーバーに以下の 3 つのチャンネルを作成:

```
memo           ← メイン入力チャンネル（テキスト、音声、ファイル）
notifications  ← システム通知
commands       ← Bot コマンド
```

**重要**: チャンネル名は正確に (`memo`、`notifications`、`commands`) 自動検出のためです。手順は [クイックスタート](quick-start.md) を参照してください。

### サーバー ID の取得

1. Discord で開発者モードを有効化: 設定 → 高度な設定 → 開発者モード
2. サーバー名を右クリック → "Copy ID"
3. `.env` に `DISCORD_GUILD_ID` として追加

## Obsidian セットアップ

### 1. Obsidian ボルトを準備

**新しいボルトを作成:**
```bash
# ボルトディレクトリを作成
mkdir -p ~/Documents/ObsidianVault
cd ~/Documents/ObsidianVault

# AI 分類に最適化されたフォルダ構造を作成
mkdir -p {00_Inbox,01_DailyNotes,02_Tasks,03_Ideas}
mkdir -p {10_Knowledge,11_Projects,12_Resources}
mkdir -p {20_Finance,21_Health}
mkdir -p {30_Archive,80_Attachments,90_Meta/Templates}

# .env にボルトパスを設定
echo "OBSIDIAN_VAULT_PATH=$HOME/Documents/ObsidianVault" >> .env
```

**既存のボルトを使用:**
```bash
# 既存のボルトパスを確認
ls -la /path/to/your/existing/vault

# .env に設定
echo "OBSIDIAN_VAULT_PATH=/path/to/your/existing/vault" >> .env
```

### 2. Obsidian を設定

**推奨プラグイン:**
1. Obsidian でボルトを開く
2. 設定 → コミュニティプラグイン → セーフモードをオフ
3. 推奨プラグインをインストール:
   - **Calendar** - 日記ナビゲーション
   - **Templater** - 高度なテンプレート
   - **Dataview** - データ視覚化
   - **Tag Wrangler** - タグ整理

## 環境変数

完全な `.env` 設定:

```env
# Required
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_guild_id
GEMINI_API_KEY=your_gemini_api_key
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault

# Optional: Speech-to-Text
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Optional: Garmin Connect
GARMIN_EMAIL=your_email@example.com
GARMIN_USERNAME=your_username
GARMIN_PASSWORD=your_password

# Optional: Security
USE_SECRET_MANAGER=false  # Usually false for local setup
ENABLE_ACCESS_LOGGING=true
```

## インストールテスト

### 1. 設定を確認

```bash
# 環境変数を確認
cat .env | grep -E "(DISCORD_|GEMINI_|OBSIDIAN_)"

# Python 環境を確認
uv run python --version
uv run python -c "import discord; print('discord.py version:', discord.__version__)"
uv run python -c "import google.generativeai as genai; print('Gemini API available')"
```

### 2. テストを実行

```bash
# Run all tests
uv run pytest

# Run basic configuration tests
uv run pytest tests/unit/test_config.py -v

# Run integration tests
uv run pytest tests/integration/ -v
```

### 3. Bot を開始

```bash
# Bot を開始
uv run python -m src.main

# 起動ログでチャンネル検出を確認:
# "Found memo channel: 123456789"
# "Found notifications channel: 987654321"
# "Found commands channel: 456789123"
```

### 4. 機能をテスト

**基本機能:**
1. `#memo` にテキストメッセージを投稿 → AI 分類を確認
2. `#memo` に音声ファイルをアップロード → 文字起こしを確認
3. `#commands` でコマンドをテスト:
   - `/ping`
   - `/status`
   - `/help`

**AI 分類テスト:**
- "昨食 1500 円" → 20_Finance フォルダ
- "TODO: レポート完成" → 02_Tasks フォルダ
- "ワークアウト 3km" → 21_Health フォルダ
- "Python 学習ノート" → 10_Knowledge フォルダ

## トラブルシューティング

### よくある問題

**Bot が起動しない:**
```bash
# Python バージョンを確認
python --version  # 3.13+ である必要

# 依存関係を再インストール
uv sync --reinstall

# ログを確認
tail -f logs/bot.log

# デバッグモード
LOG_LEVEL=DEBUG uv run python -m src.main
```

**Discord 認証エラー:**
```bash
# トークンを確認
echo $DISCORD_BOT_TOKEN

# Discord Developer Portal でボット権限を確認:
# - Message Content Intent: ON （必須）
# - メッセージ送信、メッセージ履歴閲覧権限
```

**Obsidian ファイル作成エラー:**
```bash
# パスと権限を確認
ls -la $OBSIDIAN_VAULT_PATH
chmod 755 $OBSIDIAN_VAULT_PATH

# フォルダ構造を確認
tree $OBSIDIAN_VAULT_PATH
```

**API レート制限:**
```bash
# Gemini API 使用量を確認
# Discord: /ai_stats コマンド
# 無料ティア制限: 1,500/日、 15/分

# Google Cloud Console で Speech API 使用量を確認
# 無料ティア: 60 分/月
```

### チャンネル検出の問題

**問題**: Bot がチャンネルを見つけられない

**解決策:**
1. 正確なチャンネル名 (`memo`、`notifications`、`commands`) を確認
2. Bot がチャンネル表示権限を持っているか確認
3. `DISCORD_GUILD_ID` が正しいか確認
4. 起動ログで "Found memo channel" メッセージを確認

### メッセージに応答しない

**問題**: Bot が `#memo` の投稿に応答しない

**解決策:**
1. Bot がオンラインか確認
2. Message Content Intent が有効になっているか確認
3. `#notifications` でエラーメッセージを確認
4. AI 処理のため数秒待つ

## 次のステップ

インストール後:
1. **[クイックスタート](quick-start.md)** - 素早く始める
2. **[基本的な使用方法](basic-usage.md)** - 日常的な使用方法
3. **[コマンドリファレンス](commands-reference.md)** - 利用可能なコマンド

## サポート

問題が発生した場合:
1. **[GitHub Issues](https://github.com/kenvexar/mindbridge/issues)** - バグレポートと機能リクエスト
2. **[トラブルシューティングガイド](../operations/troubleshooting.md)** - よくある解決策
3. レポートにはログファイルとエラーメッセージを含める
