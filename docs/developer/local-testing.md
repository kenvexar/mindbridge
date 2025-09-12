# ローカルテスト手順

MindBridge をローカル環境でテストする方法を説明します。

## 🏗️ モックモードでのテスト（推奨）

**実際の API キーを必要とせず、安全にテストできます。**

### 1. モック環境の設定

```bash
# モック用設定ファイルをコピー
cp .env.development .env
```

`.env.development`は既にモック設定になっています：

```env
# モック環境設定（ API 不要）
ENVIRONMENT=development
ENABLE_MOCK_MODE=true
MOCK_DISCORD_ENABLED=true
MOCK_GEMINI_ENABLED=true
MOCK_GARMIN_ENABLED=true
MOCK_SPEECH_ENABLED=true

# ローカルボルト（自動作成）
OBSIDIAN_VAULT_PATH=./test_vault
```

### 2. テスト実行

```bash
# 依存関係インストール
uv sync

# モックボット起動
uv run python -m src.main
```

### 3. モックテストの動作確認

モックモードでは以下の機能をシミュレートします：

- **Discord**: モックメッセージ処理
- **Gemini AI**: 固定レスポンス返却
- **Obsidian**: `test_vault/`フォルダに実際にファイル作成
- **音声認識**: 音声ファイルの模擬変換

### 4. 個別機能テスト

```bash
# AI 処理のテスト
uv run python test_advanced_ai.py

# 音声処理のテスト
uv run python test_speech_processor.py

# Garmin 統合のテスト
uv run python test_garmin_integration.py

# 健康データ分析のテスト
uv run python test_health_analysis.py

# URL 処理のテスト
uv run python test_url_processor_only.py
```

### チャンネル名機能のテスト

新しいチャンネル名による管理機能をテストする方法：

```bash
# ボット起動後、ログでチャンネル検出状況を確認
uv run python -m src.main | grep "Discovered channel"

# 特定チャンネルの検索テスト
python -c "
from src.bot.channel_config import ChannelConfig
from src.config import get_settings
import asyncio

async def test_channels():
    config = ChannelConfig()
    # モックボットを設定（実際のテストでは Discord ボットを使用）

    # チャンネル名での検索
    memo = config.get_channel_by_name('memo')
    print(f'Memo channel: {memo}')

    # 監視チャンネル一覧
    monitored = config.get_all_monitored_channel_names()
    print(f'Monitored channels: {monitored}')

asyncio.run(test_channels())
"
```

## 🎯 実 API を使用したテスト

実際の API を使用してテストする場合は `ENVIRONMENT=testing` を設定します。
(`staging`、`integration` も同等に機能します)

### 前提条件

1. **Discord Bot 設定**
   - [Discord Developer Portal](https://discord.com/developers/applications) で Bot を作成
   - 適切な権限を付与（ Send Messages 、 Read Message History 、 Attach Files 、 Use Slash Commands ）

2. **Gemini API キー**
   - Google AI Studio でキーを取得
   - `GEMINI_API_KEY`に設定

3. **チャンネル設定**
   - テスト用 Discord サーバーで標準名のチャンネルを作成
   - 最低限`#memo`, `#notifications`, `#commands`を作成
   - ボットが自動的にチャンネルを検出することを確認

### 実行方法

```bash
# テスト用設定ファイル作成
cp .env.example .env.testing
```

`.env.testing`を編集：

```env
# テスト環境設定
ENVIRONMENT=testing

# 実際の API 設定
DISCORD_BOT_TOKEN=your_actual_discord_token
DISCORD_GUILD_ID=your_discord_server_id
GEMINI_API_KEY=your_actual_gemini_api_key
OBSIDIAN_VAULT_PATH=/path/to/your/obsidian/vault

# Discord チャンネル（以下のチャンネルを作成するだけ）
# 必須チャンネル（ 3 つのみ）：
# - #memo            (統合メイン入力 - テキスト・音声・ファイル全て統合)
# - #notifications   (システム通知)
# - #commands        (ボットコマンド)
# - #money           (家計簿)
# - #tasks           (タスク管理)
#
# チャンネル ID の設定は不要です

# 環境設定とモックモード
ENVIRONMENT=testing
ENABLE_MOCK_MODE=false

# オプション機能
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GARMIN_EMAIL=your_garmin_email
GARMIN_PASSWORD=your_garmin_password
```

### テスト実行

```bash
# 設定ファイルを使用してテスト
DOTENV_PATH=.env.testing uv run python -m src.main
```

## 🧪 単体テスト実行

```bash
# 全テスト実行
uv run pytest

# 特定テストファイル
uv run pytest tests/unit/test_obsidian.py

# カバレッジ付きテスト
uv run pytest --cov=src

# 統合テスト
uv run pytest tests/integration/

# 非同期テスト（詳細ログ付き）
uv run pytest tests/unit/test_ai_processing.py -v
```

### テストカテゴリ

- **Unit Tests** (`tests/unit/`): 個別コンポーネントのテスト
- **Integration Tests** (`tests/integration/`): コンポーネント間統合テスト
- **Feature Tests**: 特定機能の動作確認

## 🔧 品質チェック

```bash
# コード品質チェック
uv run ruff check src/ --fix && uv run ruff format src/

# 型チェック
uv run mypy src/

# すべての品質チェック実行
uv run ruff check src/ --fix && uv run ruff format src/ && uv run mypy src/
```

## 🚨 よくある問題

### モックモードが動作しない

**確認項目:**
- `.env`ファイルに`ENVIRONMENT=development`が設定されているか
- `ENABLE_MOCK_MODE=true`になっているか
- `test_vault/`ディレクトリに書き込み権限があるか

### テストが失敗する

**確認項目:**
```bash
# 依存関係を再インストール
uv sync

# テスト用一時ファイルをクリーンアップ
rm -rf test_vault/ .pytest_cache/

# 最新の設定でテスト実行
uv run pytest tests/unit/ -v
```

### 実 API テストで認証エラー

**確認項目:**
- Discord Bot トークンの有効性
- Gemini API キーの有効性
- ボットが Discord サーバーに参加済みか
- 必要なチャンネル（#memo 、#notifications 、#commands ）が作成済みか

## 📊 テスト結果の確認

```bash
# 生成されたファイルを確認
ls -la test_vault/

# ログ出力の確認
tail -f bot.log

# テストレポートの確認
uv run pytest --html=report.html
open report.html
```

## 💡 ヒント

1. **段階的テスト**: モック→単体テスト→統合テスト→実 API の順で進める
2. **ログ活用**: `LOG_LEVEL=DEBUG`でより詳細な情報を確認
3. **安全テスト**: 本番環境の API キーは絶対に使用しない
4. **継続的テスト**: 変更後は必ずテストを実行して動作確認

このガイドに従って、安全かつ効率的にローカルテストを実行してください。
