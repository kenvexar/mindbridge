# MindBridge セットアップガイド

## 初回セットアップ手順

### 1. 前提条件の確認

#### 必要なソフトウェア
- Python 3.13 (必須)
- uv (Python パッケージマネージャー)
- Docker (デプロイ時)
- Google Cloud CLI (Cloud Run デプロイ時)

#### インストール

```bash
# uv のインストール
curl -LsSf https://astral.sh/uv/install.sh | sh

# Google Cloud CLI のインストール（デプロイ時のみ）
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

### 2. Discord Bot の作成

1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. "New Application" をクリックして新しいアプリケーションを作成
3. "Bot" タブに移動し、"Add Bot" をクリック
4. Bot Token をコピー（後で使用）
5. "Privileged Gateway Intents" で以下を有効化：
   - Message Content Intent
   - Server Members Intent

### 3. Discord サーバーの準備

#### 必要なチャンネルの作成

以下の 3 つのチャンネルを作成してください：

**📝 MEMO SYSTEM:**
- `#memo` - 統合入力チャンネル（テキスト・音声・ファイルすべて対応）

**⚙️ SYSTEM:**
- `#notifications` - ボット通知
- `#commands` - ボットコマンド

**AI 自動分類システム:**
`#memo` チャンネルに投稿されたコンテンツは AI により自動分類され、適切な Obsidian フォルダに保存されます：
- 💰 Finance → 支出・収入情報
- ✅ Tasks → TODO ・プロジェクト管理
- 🏃 Health → 運動・健康データ
- 📚 Learning → 学習・読書記録
- 🎙️ Voice → 音声ファイルの自動文字起こし
- 📁 Files → ファイル共有
- 📝 Memos → その他のメモ

#### チャンネル ID の取得方法

1. Discord の開発者モードを有効化
2. チャンネルを右クリック → "ID をコピー"
3. 各チャンネル ID を記録

### 4. Google Cloud の設定

#### プロジェクトの作成

```bash
# プロジェクト作成
gcloud projects create your-project-id --name="Discord Obsidian Bot"

# プロジェクト設定
gcloud config set project your-project-id

# 請求アカウントの設定（必要に応じて）
gcloud billing projects link your-project-id --billing-account=YOUR-BILLING-ACCOUNT-ID
```

#### API キーの取得

1. **Gemini API Key**
   - [Google AI Studio](https://makersuite.google.com/app/apikey) で API キーを作成

2. **Google Cloud Speech API Key**（オプション）
   - Google Cloud Console で Speech-to-Text API を有効化
   - API キーまたはサービスアカウントキーを作成

### 5. プロジェクトのセットアップ

```bash
# プロジェクトのクローン
git clone <repository-url>
cd mindbridge

# 依存関係のインストール
uv sync
```

### 6. 環境変数の設定

`.env.example` ファイルをコピーして `.env.development` を作成：

```bash
cp .env.example .env.development
```

以下の項目を実際の値に更新してください：

```bash
# Discord 設定
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_discord_guild_id_here

# Google API 設定
GEMINI_API_KEY=your_gemini_api_key_here
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
GOOGLE_CLOUD_SPEECH_API_KEY=your_speech_api_key_here

# Obsidian 設定
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault

# シンプルな設定（チャンネル ID は不要）
# ボットが自動検出: memo, notifications, commands

# Garmin Connect 統合（オプション）
GARMIN_EMAIL=your_garmin_email@example.com
GARMIN_USERNAME=your_garmin_username
GARMIN_PASSWORD=your_garmin_password
GARMIN_CACHE_DIR=/path/to/garmin/cache
GARMIN_CACHE_HOURS=24.0

# API 制限設定
GEMINI_API_DAILY_LIMIT=1500
GEMINI_API_MINUTE_LIMIT=15
SPEECH_API_MONTHLY_LIMIT_MINUTES=60

# ログ設定
LOG_LEVEL=INFO
LOG_FORMAT=json

# 環境設定
ENVIRONMENT=development

# セキュリティ設定（オプション）
GOOGLE_CLOUD_PROJECT=your_gcp_project_id
USE_SECRET_MANAGER=false
ENABLE_ACCESS_LOGGING=true
SECURITY_LOG_PATH=/path/to/security/logs

# Mock Mode 設定（開発・テスト用）
ENABLE_MOCK_MODE=false
MOCK_DISCORD_ENABLED=false
MOCK_GEMINI_ENABLED=false
MOCK_GARMIN_ENABLED=false
MOCK_SPEECH_ENABLED=false
```

### 7. Obsidian Vault の準備

```bash
# Obsidian Vault ディレクトリの作成
mkdir -p obsidian_vault

# 基本フォルダ構造の作成（新構成・使用頻度順）
mkdir -p obsidian_vault/{00_Inbox,01_DailyNotes,02_Tasks,03_Ideas,10_Knowledge,11_Projects,12_Resources,20_Finance,21_Health,30_Archive,80_Attachments,90_Meta}

# テンプレートファイルの作成
mkdir -p obsidian_vault/90_Meta/templates
```

#### テンプレートファイルの作成

`obsidian_vault/99_Meta/templates/daily_note.md`:
```markdown
# {{date}}

## 📝 Daily Summary
{{summary}}

## 🎯 Key Activities
{{activities}}

## 💭 Ideas & Insights
{{ideas}}

## ✅ Tasks Completed
{{completed_tasks}}

## 📊 Metrics
- Messages processed: {{message_count}}
- AI requests: {{ai_requests}}
- Files created: {{files_created}}

## 🔄 Next Actions
{{next_actions}}
```

### 8. 動作確認

#### 基本テストの実行

```bash
# 全テストの実行
uv run pytest

# カバレッジ付きテスト
uv run pytest --cov=src

# 統合テストの実行
uv run pytest tests/integration/

# テストスクリプトを使った実行
python run_tests.py
```

#### ボットの起動テスト

```bash
# 開発モードでボット起動
uv run python -m src.main

# デバッグモードでの起動
uv run python -m src.main --debug
```

#### Discord での動作確認

1. ボットを Discord サーバーに招待
2. `#commands` チャンネルで `/help` コマンドを実行
3. `#memo` チャンネルでメッセージを送信してみる

### 9. コード品質チェック

```bash
# フォーマットとリント（コミット前に実行）
uv run ruff check src/ --fix && uv run ruff format src/

# 型チェック
uv run mypy src/

# 全ての品質チェック
uv run ruff check src/ --fix && uv run ruff format src/ && uv run mypy src/

# pre-commit フックのセットアップ（オプション）
uv run pre-commit install
uv run pre-commit run --all-files
```

### 10. トラブルシューティング

#### よくある問題

**1. ボットが起動しない**
```bash
# ログレベルを DEBUG に変更して詳細を確認
LOG_LEVEL=DEBUG uv run python -m src.main

# 環境変数の確認
cat .env.development
```

**2. チャンネルが見つからない**
- チャンネル ID が正しいか確認（開発者モードで ID をコピー）
- ボットがサーバーに正しく追加されているか確認
- ボットの権限を確認（メッセージ送信、添付ファイル）

**3. API エラー**
```bash
# API キーの確認
echo $GEMINI_API_KEY
echo $DISCORD_BOT_TOKEN

# API 制限の確認
# Gemini: 1500 リクエスト/日, 15 リクエスト/分
# Speech-to-Text: 60 分/月（無料版）
```

**4. Obsidian ファイルが作成されない**
```bash
# Obsidian パスの確認
ls -la obsidian_vault/
chmod -R 755 obsidian_vault/

# フォルダ構造の確認
tree obsidian_vault/
```

**5. Python 依存関係の問題**
```bash
# 依存関係の再インストール
uv sync

# 開発依存関係も含めて
uv sync --dev
```

**6. Mock Mode での動作確認**
```bash
# Mock Mode を有効にしてテスト
ENABLE_MOCK_MODE=true uv run python -m src.main
```

### 11. 次のステップ

#### 本番環境へのデプロイ

```bash
# 本番環境用の設定
cp .env.development .env.production
# .env.production を本番環境用に編集（ SECRET_MANAGER 使用推奨）

# Cloud Run へのデプロイ
PROJECT_ID=your-project-id ./deploy.sh
```

#### カスタマイズ

1. **設定のカスタマイズ**
   - `src/config/settings.py` で基本設定
   - `.env.development` で環境固有設定

2. **テンプレートのカスタマイズ**
   - `obsidian_vault/99_Meta/templates/` でノートテンプレート
   - `src/obsidian/template_system.py` でテンプレート処理

3. **チャンネル設定のカスタマイズ**
   - `src/bot/channel_config.py` でチャンネルカテゴリ
   - 新しいチャンネルを追加する場合は設定ファイルも更新

4. **AI 処理のカスタマイズ**
   - `src/ai/processor.py` で AI 分析ロジック
   - プロンプトとカテゴリ分類の調整

#### 監視とヘルスチェック

```bash
# システム状態の確認
curl http://localhost:8080/health
curl http://localhost:8080/metrics

# ログの確認
tail -f logs/discord_bot.log
```

#### 高度な機能の有効化

1. **Garmin Connect 統合**
   - Garmin 認証情報を設定
   - ヘルスチャンネルを作成
   - `test_garmin_integration.py` でテスト

2. **高度な AI 機能**
   - ベクトル検索の有効化
   - `test_advanced_ai.py` でテスト

3. **ヘルスデータ分析**
   - `test_health_analysis.py` でテスト

## サポート

- 技術的な質問: GitHub の Issue を作成
- ドキュメント: `docs/` ディレクトリを参照
- デプロイメント: `docs/deployment-guide.md` を参照

このガイドに従ってセットアップを完了すれば、 MindBridge が正常に動作するはずです。
