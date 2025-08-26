# 🛠️ 開発ガイド

Discord-Obsidian Memo Bot の開発環境構築から実装まで、開発者向けの包括的なガイドです。

## 📋 目次

1. [開発環境セットアップ](#開発環境セットアップ)
2. [プロジェクト構造の理解](#プロジェクト構造の理解)
3. [開発ワークフロー](#開発ワークフロー)
4. [コードスタイルとガイドライン](#コードスタイルとガイドライン)
5. [テスト戦略](#テスト戦略)
6. [デバッグ手法](#デバッグ手法)
7. [新機能開発フロー](#新機能開発フロー)
8. [パフォーマンス最適化](#パフォーマンス最適化)

## 🚀 開発環境セットアップ

### 必要なツール

```bash
# 必須ツール
python --version          # 3.13 以上
uv --version              # 最新版
git --version             # 2.20 以上
docker --version          # 20.10 以上（オプション）

# 推奨ツール
code --version            # VS Code
curl --version            # HTTP テスト用
jq --version              # JSON 処理用
```

### 開発環境の構築

```bash
# 1. リポジトリのクローン
git clone https://github.com/kenvexar/mindbridge.git
cd mindbridge

# 2. 開発用依存関係のインストール
uv sync --dev

# 3. pre-commit フックの設定
uv run pre-commit install

# 4. 環境変数の設定
cp .env.example .env.development
```

### VS Code 設定

`.vscode/settings.json`:
```json
{
    "python.interpreter": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "ruff",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".mypy_cache": true,
        ".pytest_cache": true
    }
}
```

`.vscode/extensions.json`:
```json
{
    "recommendations": [
        "ms-python.python",
        "charliermarsh.ruff",
        "ms-python.mypy-type-checker",
        "ms-vscode.vscode-json",
        "redhat.vscode-yaml"
    ]
}
```

### 開発用設定

`.env.development`:
```env
# 開発環境設定
ENVIRONMENT=development
LOG_LEVEL=DEBUG
LOG_FORMAT=pretty

# モックモード（ API キー不要でテスト可能）
ENABLE_MOCK_MODE=true
MOCK_DISCORD_ENABLED=true
MOCK_GEMINI_ENABLED=true
MOCK_GARMIN_ENABLED=true
MOCK_SPEECH_ENABLED=true

# テスト用 Obsidian ボルト
OBSIDIAN_VAULT_PATH=./test_vault

# 基本設定（実際の値でも動作）
DISCORD_GUILD_ID=your_guild_id_here
```

## 📁 プロジェクト構造の理解

### 主要ディレクトリの役割

```
src/
├── bot/           # Discord インターフェース層
│   ├── client.py         # メイン Bot クライアント
│   ├── handlers.py       # イベント処理
│   ├── commands/         # コマンドモジュール
│   ├── mixins/           # 再利用可能なミックスイン
│   ├── message_processor.py # メッセージ処理
│   ├── notification_system.py # 通知システム
│   └── review_system.py  # レビューシステム
├── ai/            # AI 処理層
│   ├── processor.py      # AI 分析エンジン
│   ├── gemini_client.py  # Gemini API クライアント
│   ├── url_processor.py  # URL 処理
│   └── models.py         # データモデル
├── obsidian/      # Obsidian 統合層
│   ├── core/             # コア機能
│   ├── search/           # 検索機能
│   ├── backup/           # バックアップ機能
│   ├── analytics/        # 分析機能
│   ├── file_manager.py   # ファイル操作
│   └── template_system.py # テンプレート
├── tasks/         # タスク管理システム
│   ├── task_manager.py   # タスク管理
│   ├── schedule_manager.py # スケジュール管理
│   └── reminder_system.py # リマインダーシステム
├── finance/       # 財務管理システム
│   ├── expense_manager.py # 支出管理
│   ├── budget_manager.py # 予算管理
│   └── subscription_manager.py # サブスクリプション管理
├── security/      # セキュリティ層
│   ├── secret_manager.py # シークレット管理
│   └── access_logger.py  # アクセスログ
├── monitoring/    # 監視層
│   └── health_server.py  # ヘルスチェック
├── config/        # 設定管理
├── utils/         # 共通ユーティリティ
└── main.py        # エントリーポイント

tests/
├── unit/          # 単体テスト
├── integration/   # 統合テスト
└── fixtures/      # テストデータ

docs/              # ドキュメント
├── user/          # ユーザー向け
├── developer/     # 開発者向け
└── operations/    # 運用者向け
```

### 重要なファイル

| ファイル | 役割 | 重要度 |
|----------|------|--------|
| `src/main.py` | アプリケーションエントリーポイント | ⭐⭐⭐ |
| `src/config/settings.py` | 設定管理 | ⭐⭐⭐ |
| `src/bot/client.py` | Discord Bot メイン | ⭐⭐⭐ |
| `src/ai/processor.py` | AI 処理エンジン | ⭐⭐⭐ |
| `src/obsidian/file_manager.py` | ファイル管理 | ⭐⭐⭐ |
| `pyproject.toml` | プロジェクト設定 | ⭐⭐ |
| `.env.example` | 環境変数テンプレート | ⭐⭐ |

## 🔄 開発ワークフロー

### 基本的な開発サイクル

```bash
# 1. 新しいブランチの作成
git checkout -b feature/new-amazing-feature

# 2. コードの実装
# ... 開発作業 ...

# 3. コード品質チェック
uv run ruff check src/ --fix
uv run ruff format src/
uv run mypy src/

# 4. テストの実行
uv run pytest tests/unit/
uv run pytest tests/integration/

# 5. 変更のコミット
git add .
git commit -m "feat: add amazing new feature"

# 6. プッシュとプルリクエスト
git push origin feature/new-amazing-feature
```

### コミットメッセージ規約

[Conventional Commits](https://www.conventionalcommits.org/) に従います：

```bash
# 機能追加
git commit -m "feat: add voice memo processing"

# バグ修正
git commit -m "fix: resolve discord connection timeout"

# ドキュメント更新
git commit -m "docs: update installation guide"

# リファクタリング
git commit -m "refactor: optimize AI processing pipeline"

# テスト追加
git commit -m "test: add unit tests for message processor"

# ビルド・設定変更
git commit -m "build: update dependencies"
```

### ブランチ戦略

```
main           # 本番リリース・開発統合ブランチ
├── feature/*  # 新機能開発
├── bugfix/*   # バグ修正
└── hotfix/*   # 緊急修正
```

## 🎨 コードスタイルとガイドライン

### Python コーディング規約

```python
# 1. 型ヒントの必須使用
async def process_message(
    self,
    message: str,
    channel_id: int,
    user_id: Optional[int] = None
) -> ProcessingResult:
    """メッセージを処理して Obsidian に保存する."""
    pass

# 2. docstring の記述
class AIProcessor:
    """AI 分析エンジン.

    Gemini API を使用してメッセージの分析・分類・要約を行う。
    キャッシュ機能とレート制限を内蔵。

    Attributes:
        api_key: Gemini API キー
        cache: 処理結果のキャッシュ
        rate_limiter: API 呼び出し制限管理
    """

    def __init__(self, api_key: str, cache_size: int = 1000):
        """AIProcessor を初期化する.

        Args:
            api_key: Gemini API キー
            cache_size: キャッシュサイズ上限
        """
        pass

# 3. エラーハンドリング
try:
    result = await self.ai_processor.analyze(content)
except APIError as e:
    logger.error("AI analysis failed", error=str(e), content_length=len(content))
    raise ProcessingError(f"AI analysis failed: {e}") from e
except Exception as e:
    logger.exception("Unexpected error in AI processing")
    raise

# 4. ログ記録
logger.info(
    "Message processed successfully",
    user_id=message.author.id,
    channel_id=message.channel.id,
    processing_time=processing_time
)
```

### 設計原則

1. **Single Responsibility**: 1 つのクラス・関数は 1 つの責任のみ
2. **Dependency Injection**: 依存性は外部から注入
3. **Interface Segregation**: 小さく特化したインターフェース
4. **Don't Repeat Yourself**: コードの重複を避ける

```python
# Good: 単一責任
class MessageAnalyzer:
    async def analyze_content(self, content: str) -> ContentAnalysis:
        pass

class MessageSaver:
    async def save_to_obsidian(self, analysis: ContentAnalysis) -> SaveResult:
        pass

# Good: 依存性注入
class MessageProcessor:
    def __init__(
        self,
        analyzer: MessageAnalyzer,
        saver: MessageSaver
    ):
        self.analyzer = analyzer
        self.saver = saver
```

## 🧪 テスト戦略

### テストの種類と実行

```bash
# 全テスト実行
uv run pytest

# 特定のテストファイル
uv run pytest tests/unit/test_ai_processing.py

# 特定のテストケース
uv run pytest tests/unit/test_ai_processing.py::test_content_analysis

# カバレッジ付き実行
uv run pytest --cov=src --cov-report=html

# 並列実行
uv run pytest -n auto

# 詳細出力
uv run pytest -v -s
```

### テストの書き方

```python
# tests/unit/test_ai_processing.py
import pytest
from unittest.mock import AsyncMock, patch

from src.ai.processor import AIProcessor
from src.ai.models import ProcessingResult

class TestAIProcessor:
    @pytest.fixture
    def processor(self, mock_settings):
        return AIProcessor(mock_settings)

    @pytest.mark.asyncio
    async def test_content_analysis_success(self, processor):
        # Arrange
        content = "今日は良い天気です。散歩に行きたい。"
        expected_tags = ["weather", "activity"]

        # Act
        with patch.object(processor.gemini_client, 'analyze') as mock_analyze:
            mock_analyze.return_value = ProcessingResult(
                summary="天気と散歩について",
                tags=expected_tags,
                category="personal"
            )

            result = await processor.analyze_content(content)

        # Assert
        assert result.summary == "天気と散歩について"
        assert result.tags == expected_tags
        assert result.category == "personal"
        mock_analyze.assert_called_once_with(content)

    @pytest.mark.asyncio
    async def test_content_analysis_api_error(self, processor):
        # Arrange
        content = "テスト内容"

        # Act & Assert
        with patch.object(processor.gemini_client, 'analyze') as mock_analyze:
            mock_analyze.side_effect = APIError("API limit exceeded")

            with pytest.raises(ProcessingError, match="AI analysis failed"):
                await processor.analyze_content(content)
```

### モックとフィクスチャ

```python
# tests/conftest.py
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_settings():
    settings = AsyncMock()
    settings.gemini_api_key = "test-api-key"
    settings.obsidian_vault_path = "/tmp/test-vault"
    settings.environment = "testing"
    return settings

@pytest.fixture
async def test_obsidian_manager(tmp_path):
    vault_path = tmp_path / "test_vault"
    vault_path.mkdir()

    from src.obsidian.file_manager import ObsidianFileManager
    manager = ObsidianFileManager(str(vault_path))
    await manager.initialize_vault()

    yield manager
```

## 🐛 デバッグ手法

### ログレベルの活用

```python
# 開発時のログ設定
import structlog

logger = structlog.get_logger(__name__)

async def debug_message_processing(self, message: str):
    logger.debug("Starting message processing", message_length=len(message))

    try:
        # AI 分析
        logger.debug("Calling AI analysis")
        analysis = await self.ai_processor.analyze(message)
        logger.info("AI analysis completed",
                   tags=analysis.tags,
                   category=analysis.category)

        # Obsidian 保存
        logger.debug("Saving to Obsidian", folder=analysis.category)
        result = await self.obsidian_manager.save(analysis)
        logger.info("Save completed", file_path=result.file_path)

    except Exception as e:
        logger.exception("Message processing failed",
                        error=str(e),
                        message_preview=message[:100])
        raise
```

### デバッグ用コマンド

```bash
# デバッグモードで起動
LOG_LEVEL=DEBUG uv run python -m src.main

# 特定モジュールのデバッグ
PYTHONPATH=src python -c "
from src.ai.processor import AIProcessor
import asyncio

async def debug():
    processor = AIProcessor('test-key')
    result = await processor.analyze('テストメッセージ')
    print(result)

asyncio.run(debug())
"

# インタラクティブデバッグ
python -m pdb -c continue -m src.main
```

### デバッガー設定

VS Code launch.json:
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Discord Bot Debug",
            "type": "python",
            "request": "launch",
            "module": "src.main",
            "console": "integratedTerminal",
            "env": {
                "ENVIRONMENT": "development",
                "LOG_LEVEL": "DEBUG"
            }
        },
        {
            "name": "Run Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": ["tests/unit/", "-v"],
            "console": "integratedTerminal"
        }
    ]
}
```

## 🚀 新機能開発フロー

### 1. 機能設計

```python
# 機能仕様書 (docs/features/new-feature.md)
"""
# 新機能: 自動タグ学習

## 概要
ユーザーの過去のタグ付けパターンを学習し、より精度の高い自動タグ付けを実現

## 要件
- 過去のメッセージとタグの関連性を分析
- 機械学習モデルによる予測
- ユーザーフィードバックによる継続学習

## 実装計画
1. データ収集機能の実装
2. 機械学習モデルの訓練
3. 予測 API の実装
4. フィードバック機能の実装
"""
```

### 2. データモデル定義

```python
# src/ai/models.py
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class TagLearningData(BaseModel):
    """タグ学習用データモデル."""
    content: str
    user_tags: List[str]
    ai_tags: List[str]
    feedback_score: Optional[float] = None
    created_at: datetime

class TagPrediction(BaseModel):
    """タグ予測結果."""
    predicted_tags: List[str]
    confidence_scores: Dict[str, float]
    learning_source: str  # 'ml_model' or 'rule_based'
```

### 3. 実装

```python
# src/ai/tag_learner.py
class TagLearner:
    """自動タグ学習システム."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model: Optional[Any] = None
        self.training_data: List[TagLearningData] = []

    async def collect_training_data(self,
                                  content: str,
                                  user_tags: List[str],
                                  ai_tags: List[str]) -> None:
        """学習データを収集する."""
        data = TagLearningData(
            content=content,
            user_tags=user_tags,
            ai_tags=ai_tags,
            created_at=datetime.utcnow()
        )
        self.training_data.append(data)

        # 一定数蓄積されたら自動学習
        if len(self.training_data) >= self.settings.auto_training_threshold:
            await self.train_model()

    async def train_model(self) -> None:
        """機械学習モデルを訓練する."""
        logger.info("Starting model training",
                   data_count=len(self.training_data))

        # 特徴量抽出
        features, labels = self._prepare_training_data()

        # モデル訓練
        self.model = await self._train_ml_model(features, labels)

        # モデル保存
        await self._save_model()

        logger.info("Model training completed")

    async def predict_tags(self, content: str) -> TagPrediction:
        """コンテンツに対してタグを予測する."""
        if not self.model:
            await self._load_model()

        features = self._extract_features(content)
        predictions = self.model.predict(features)

        return TagPrediction(
            predicted_tags=predictions['tags'],
            confidence_scores=predictions['scores'],
            learning_source='ml_model'
        )
```

### 4. テスト実装

```python
# tests/unit/test_tag_learner.py
class TestTagLearner:
    @pytest.fixture
    def learner(self, mock_settings):
        return TagLearner(mock_settings)

    @pytest.mark.asyncio
    async def test_collect_training_data(self, learner):
        # データ収集のテスト
        content = "今日は#プログラミング を勉強した"
        user_tags = ["programming", "study"]
        ai_tags = ["programming", "learning"]

        await learner.collect_training_data(content, user_tags, ai_tags)

        assert len(learner.training_data) == 1
        assert learner.training_data[0].content == content
        assert learner.training_data[0].user_tags == user_tags

    @pytest.mark.asyncio
    async def test_tag_prediction(self, learner):
        # 予測機能のテスト
        with patch.object(learner, 'model') as mock_model:
            mock_model.predict.return_value = {
                'tags': ['programming', 'study'],
                'scores': {'programming': 0.9, 'study': 0.8}
            }

            content = "Python の勉強をした"
            prediction = await learner.predict_tags(content)

            assert prediction.predicted_tags == ['programming', 'study']
            assert prediction.confidence_scores['programming'] == 0.9
```

### 5. 統合とデプロイ

```python
# src/ai/processor.py (既存クラスの拡張)
class AIProcessor:
    def __init__(self, settings: Settings):
        # 既存の初期化...
        self.tag_learner = TagLearner(settings)

    async def analyze_content(self, content: str) -> ProcessingResult:
        # 既存の分析...
        base_analysis = await self._base_analysis(content)

        # 学習済みタグ予測の追加
        if self.settings.enable_tag_learning:
            tag_prediction = await self.tag_learner.predict_tags(content)
            base_analysis.tags.extend(tag_prediction.predicted_tags)
            base_analysis.confidence_scores = tag_prediction.confidence_scores

        return base_analysis
```

## ⚡ パフォーマンス最適化

### プロファイリング

```python
# パフォーマンス測定
import cProfile
import pstats
from functools import wraps

def profile_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()

        try:
            result = await func(*args, **kwargs)
        finally:
            profiler.disable()

            # 結果の分析
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            stats.print_stats(10)  # トップ 10 を表示

        return result
    return wrapper

# 使用例
@profile_performance
async def process_large_batch(self, messages: List[str]):
    tasks = [self.process_message(msg) for msg in messages]
    return await asyncio.gather(*tasks)
```

### メモリ最適化

```python
# メモリ効率的な大量データ処理
async def process_large_dataset(self, data_source: AsyncIterator[str]):
    """大量データを効率的に処理する."""
    batch_size = 100
    batch = []

    async for item in data_source:
        batch.append(item)

        if len(batch) >= batch_size:
            await self._process_batch(batch)
            batch.clear()  # メモリ解放

            # GC 強制実行（必要に応じて）
            import gc
            gc.collect()

    # 残りのバッチを処理
    if batch:
        await self._process_batch(batch)
```

### 非同期最適化

```python
# 効率的な並行処理
class OptimizedProcessor:
    def __init__(self, max_concurrent: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.rate_limiter = AsyncLimiter(15, 60)  # 15 requests per minute

    async def process_with_limits(self, content: str) -> ProcessingResult:
        async with self.semaphore:
            async with self.rate_limiter:
                return await self._actual_processing(content)

    async def process_batch_optimized(self,
                                    contents: List[str]) -> List[ProcessingResult]:
        """最適化されたバッチ処理."""
        tasks = [
            self.process_with_limits(content)
            for content in contents
        ]

        # as_completed を使用して完了次第処理
        results = []
        for coro in asyncio.as_completed(tasks):
            try:
                result = await coro
                results.append(result)
            except Exception as e:
                logger.error("Processing failed", error=str(e))
                results.append(None)

        return results
```

## 📚 リソースとツール

### 有用なライブラリ

```python
# pyproject.toml の推奨依存関係
[tool.uv.dependencies]
# 非同期処理
aiohttp = "^3.8.0"
aiofiles = "^23.0.0"

# データバリデーション
pydantic = "^2.0.0"

# ログ
structlog = "^23.0.0"
rich = "^13.0.0"

# テスト
pytest = "^7.0.0"
pytest-asyncio = "^0.21.0"
pytest-cov = "^4.0.0"

# 開発ツール
ruff = "^0.0.280"
mypy = "^1.5.0"
pre-commit = "^3.0.0"
```

### 開発ツールの設定

```toml
# pyproject.toml
[tool.ruff]
select = ["E", "F", "W", "I", "N", "UP", "B", "S", "C4", "PIE", "T20"]
ignore = ["E501"]  # Line too long
line-length = 88
target-version = "py313"

[tool.mypy]
python_version = "3.13"
disallow_untyped_defs = true
disallow_any_generics = true
warn_unused_configs = true
warn_redundant_casts = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
```

### 推奨 VS Code 拡張機能

1. **Python** - Python 言語サポート
2. **Ruff** - リンタ・フォーマッタ
3. **mypy Type Checker** - 型チェック
4. **Python Test Explorer** - テスト実行
5. **GitLens** - Git 統合
6. **Thunder Client** - API テスト
7. **YAML** - YAML ファイルサポート

## 📞 サポートとコミュニティ

### 質問・相談

- **GitHub Discussions**: 一般的な質問・議論
- **GitHub Issues**: バグ報告・機能要求
- **Code Review**: プルリクエストでのコードレビュー

### 継続的学習

1. **Python 非同期プログラミング**
   - asyncio 公式ドキュメント
   - "Using Asyncio in Python" by Caleb Hattingh

2. **Discord Bot 開発**
   - discord.py 公式ドキュメント
   - Discord Developer Portal

3. **AI/ML 統合**
   - Google AI Platform ドキュメント
   - Hugging Face Transformers

4. **テストベストプラクティス**
   - pytest 公式ドキュメント
   - "Test-Driven Development with Python" by Harry Percival

---

このガイドを参考に、効率的で保守性の高いコードの開発を進めてください。質問や改善提案があれば、遠慮なく GitHub Discussions で相談してください。
