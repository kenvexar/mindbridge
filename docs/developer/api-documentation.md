# YAML フロントマター システム API ドキュメント

## 概要

MindBridge YAML フロントマターシステムのプログラマティック API について詳細に解説します。

## クラス構成

### YAMLFrontmatterGenerator

メインの YAML フロントマター生成クラスです。

#### クラス定義

```python
from src.obsidian.template_system.yaml_generator import YAMLFrontmatterGenerator
from typing import Any, Dict, Optional
from datetime import datetime, date

class YAMLFrontmatterGenerator:
    """包括的な YAML フロントマター生成器"""

    def __init__(self) -> None:
        """初期化"""
        pass
```

#### 主要メソッド

##### 1. create_comprehensive_frontmatter()

最も高レベルな API で、包括的なフロントマターを生成します。

```python
def create_comprehensive_frontmatter(
    self,
    title: str,
    content_type: str = "memo",
    ai_result: Optional[Any] = None,
    content: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> str:
    """
    包括的で実用的なフロントマターを生成する高度なメソッド

    Args:
        title: ノートタイトル
        content_type: コンテンツタイプ（ memo, task, knowledge, project など）
        ai_result: AI 分析結果（ AIProcessingResult オブジェクト）
        content: ノート本文（分析用）
        context: 追加コンテキスト情報
        **kwargs: その他のメタデータ

    Returns:
        完全な YAML フロントマター文字列

    Example:
        >>> generator = YAMLFrontmatterGenerator()
        >>> yaml_str = generator.create_comprehensive_frontmatter(
        ...     title="機械学習プロジェクト",
        ...     content_type="knowledge",
        ...     content="scikit-learn について学習した内容",
        ...     ai_result=ai_processing_result
        ... )
        >>> print(yaml_str)
        ---
        title: "機械学習プロジェクト"
        created: 2025-01-15T14:30:00+09:00
        type: "knowledge"
        category: "learning"
        summary: "scikit-learn の基本的な使い方を学習"
        word_count: 25
        ai_confidence: 0.92
        tags: ["machine-learning", "python", "scikit-learn"]
        ---
    """
```

**引数詳細:**

| 引数 | 型 | 必須 | デフォルト | 説明 |
|------|---|------|-----------|------|
| `title` | str | ✓ | - | ノートのタイトル |
| `content_type` | str | | "memo" | コンテンツタイプ |
| `ai_result` | AIProcessingResult | | None | AI 分析結果 |
| `content` | str | | None | 分析対象コンテンツ |
| `context` | dict | | None | 追加コンテキスト |

**コンテンツタイプ一覧:**
- `"memo"` - 一般メモ
- `"task"` - タスク・ TODO
- `"knowledge"` - 学習・知識
- `"project"` - プロジェクト
- `"finance"` - 財務・経費
- `"health"` - 健康・運動
- `"meeting"` - 会議・ミーティング

##### 2. create_obsidian_enhanced_frontmatter()

Obsidian 特化機能を含む拡張フロントマターを生成します。

```python
def create_obsidian_enhanced_frontmatter(
    self,
    title: str,
    content: str,
    ai_result: Optional[Any] = None,
    generate_permalink: bool = False,
    auto_publish: bool = False,
    extract_wikilinks: bool = True
) -> str:
    """
    Obsidian 拡張機能付きフロントマターを生成

    Args:
        title: ノートタイトル
        content: ノート本文
        ai_result: AI 分析結果
        generate_permalink: パーマリンク自動生成
        auto_publish: 自動公開設定
        extract_wikilinks: Wikilink 自動抽出

    Returns:
        Obsidian 拡張フロントマター

    Example:
        >>> yaml_str = generator.create_obsidian_enhanced_frontmatter(
        ...     title="プロジェクト概要",
        ...     content="この[[重要文書]]を参照してください",
        ...     generate_permalink=True,
        ...     extract_wikilinks=True
        ... )
    """
```

##### 3. create_daily_note_frontmatter()

デイリーノート専用のフロントマターを生成します。

```python
def create_daily_note_frontmatter(
    self,
    target_date: date,
    mood: Optional[str] = None,
    weather: Optional[str] = None,
    goals: Optional[list] = None
) -> str:
    """
    デイリーノート用フロントマターを生成

    Args:
        target_date: 対象日付
        mood: その日の気分
        weather: 天気
        goals: その日の目標

    Returns:
        デイリーノート用 YAML

    Example:
        >>> from datetime import date
        >>> yaml_str = generator.create_daily_note_frontmatter(
        ...     target_date=date(2025, 1, 15),
        ...     mood="positive",
        ...     weather="sunny",
        ...     goals=["プロジェクト進行", "運動する"]
        ... )
    """
```

##### 4. generate_frontmatter()

基本的なフロントマター生成（低レベル API ）。

```python
def generate_frontmatter(
    self,
    frontmatter_data: Dict[str, Any],
    custom_template: Optional[Dict[str, str]] = None
) -> str:
    """
    基本的なフロントマター生成

    Args:
        frontmatter_data: フロントマターデータ辞書
        custom_template: カスタムテンプレート

    Returns:
        YAML フロントマター文字列

    Example:
        >>> data = {
        ...     "title": "テストノート",
        ...     "created": datetime.now(),
        ...     "tags": ["test", "example"],
        ...     "priority": "high"
        ... }
        >>> yaml_str = generator.generate_frontmatter(data)
    """
```

#### 内部メソッド

##### _extract_comprehensive_ai_data()

AI 分析結果から包括的なメタデータを抽出します。

```python
def _extract_comprehensive_ai_data(self, ai_result) -> Dict[str, Any]:
    """
    AI 分析結果から包括的なメタデータを抽出

    Args:
        ai_result: AIProcessingResult オブジェクト

    Returns:
        抽出されたメタデータ辞書

    Note:
        CategoryResult, SummaryResult, TagsResult の
        ネストされた属性を適切に処理
    """
```

##### _convert_value()

値を適切なデータ型に自動変換します。

```python
def _convert_value(self, key: str, value: Any) -> Any:
    """
    値を適切なデータ型に変換

    Args:
        key: フィールド名
        value: 変換対象の値

    Returns:
        変換された値

    Example:
        >>> generator._convert_value("word_count", "1500")
        1500
        >>> generator._convert_value("publish", "true")
        True
        >>> generator._convert_value("tags", "python,ai,ml")
        ["python", "ai", "ml"]
    """
```

##### _map_category_to_type()

AI カテゴリをコンテンツタイプにマッピングします。

```python
def _map_category_to_type(self, category: str) -> str:
    """
    AI カテゴリをコンテンツタイプにマッピング

    Args:
        category: AI 分析によるカテゴリ

    Returns:
        対応するコンテンツタイプ

    Mapping:
        "learning" -> "knowledge"
        "tasks" -> "task"
        "finance" -> "finance"
        "health" -> "health"
        "projects" -> "project"
        その他 -> "memo"
    """
```

## AI 統合 API

### AIProcessingResult オブジェクト

AI 分析結果を表現する Pydantic モデルです。

```python
class AIProcessingResult(BaseModel):
    """AI 処理結果"""

    category: CategoryResult
    summary: SummaryResult
    tags: TagsResult
    total_processing_time_ms: int

class CategoryResult(BaseModel):
    """カテゴリ分析結果"""

    category: CategoryEnum
    confidence_score: float

class SummaryResult(BaseModel):
    """要約分析結果"""

    summary: str

class TagsResult(BaseModel):
    """タグ分析結果"""

    tags: List[str]
```

#### 使用例

```python
from src.ai.processor import AIProcessor

# AI プロセッサーの初期化
ai_processor = AIProcessor()

# テキスト分析
result = await ai_processor.process_text("機械学習について学習した")

# YAML 生成
generator = YAMLFrontmatterGenerator()
yaml_str = generator.create_comprehensive_frontmatter(
    title="学習記録",
    content_type="knowledge",
    ai_result=result,
    content="機械学習について学習した"
)
```

## 設定・カスタマイズ API

### フィールド順序のカスタマイズ

```python
# カスタム順序の定義
CUSTOM_FIELD_ORDER = [
    "title", "date", "type",
    "priority", "status", "progress",
    "summary", "tags",
    # ... その他のフィールド
]

# 生成器にカスタム順序を適用
generator = YAMLFrontmatterGenerator()
generator.FIELD_ORDER = CUSTOM_FIELD_ORDER
```

### データ型変換のカスタマイズ

```python
# カスタム数値フィールドの追加
generator.NUMERIC_FIELDS.add("custom_score")
generator.BOOLEAN_FIELDS.add("custom_flag")
generator.ARRAY_FIELDS.add("custom_list")
```

### テンプレートのカスタマイズ

```python
# カスタムテンプレートの定義
custom_template = {
    "created": "%Y 年%m 月%d 日 %H 時%M 分",  # 日本語形式
    "custom_field": "カスタム: {value}",  # プレフィックス付き
    "tags": "#{}",  # ハッシュタグ形式
}

# テンプレート適用
yaml_str = generator.generate_frontmatter(
    data,
    custom_template=custom_template
)
```

## 拡張 API

### カスタムフィールド生成器の追加

```python
class CustomYAMLGenerator(YAMLFrontmatterGenerator):
    """カスタム拡張した YAML 生成器"""

    def __init__(self):
        super().__init__()
        # カスタムフィールドを追加
        self.FIELD_ORDER.extend([
            "custom_priority",
            "custom_metadata",
            "business_unit"
        ])
        self.NUMERIC_FIELDS.add("custom_score")

    def _generate_custom_fields(self, content: str, context: dict) -> dict:
        """カスタムフィールドの生成ロジック"""
        custom_data = {}

        # ビジネスユニットの自動判定
        if "営業" in content or "sales" in content.lower():
            custom_data["business_unit"] = "sales"
        elif "開発" in content or "dev" in content.lower():
            custom_data["business_unit"] = "development"

        # カスタムスコアの計算
        if context.get("importance") == "high":
            custom_data["custom_score"] = 100
        else:
            custom_data["custom_score"] = 50

        return custom_data

    def create_business_frontmatter(self, title: str, content: str, **kwargs) -> str:
        """ビジネス特化フロントマター生成"""

        # 基本フロントマター生成
        base_data = {
            "title": title,
            "created": datetime.now(),
            "type": "business"
        }

        # カスタムフィールド追加
        context = kwargs.get("context", {})
        custom_fields = self._generate_custom_fields(content, context)
        base_data.update(custom_fields)

        return self.generate_frontmatter(base_data)
```

### プラグインシステム

```python
class FrontmatterPlugin:
    """フロントマタープラグインのベースクラス"""

    def process(self, generator: YAMLFrontmatterGenerator, data: dict) -> dict:
        """データ処理のフック"""
        return data

    def post_generate(self, yaml_content: str) -> str:
        """生成後処理のフック"""
        return yaml_content

class TimestampPlugin(FrontmatterPlugin):
    """タイムスタンププラグイン"""

    def process(self, generator: YAMLFrontmatterGenerator, data: dict) -> dict:
        """Unix タイムスタンプを追加"""
        if "created" in data:
            data["timestamp"] = int(data["created"].timestamp())
        return data

class HashtagPlugin(FrontmatterPlugin):
    """ハッシュタグプラグイン"""

    def post_generate(self, yaml_content: str) -> str:
        """タグをハッシュタグ形式に変換"""
        import re
        return re.sub(
            r'- (\w+)',
            r'- #\1',
            yaml_content
        )

# プラグインシステムの使用
generator = YAMLFrontmatterGenerator()
generator.add_plugin(TimestampPlugin())
generator.add_plugin(HashtagPlugin())
```

## デバッグ・監視 API

### ログ出力の制御

```python
import logging

# デバッグログの有効化
logging.getLogger("yaml_generator").setLevel(logging.DEBUG)

# 生成過程のトレース
generator = YAMLFrontmatterGenerator()
generator.enable_debug_trace = True

yaml_str = generator.create_comprehensive_frontmatter(
    title="デバッグテスト",
    content="テストコンテンツ"
)
# -> 詳細なデバッグ情報が出力される
```

### パフォーマンス測定

```python
from src.obsidian.template_system.yaml_generator import YAMLFrontmatterGenerator
import time

class PerformanceTracker:
    """パフォーマンス追跡クラス"""

    def __init__(self):
        self.metrics = {}

    def track_generation(self, func):
        """生成時間の追跡デコレータ"""
        def wrapper(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()

            self.metrics[func.__name__] = {
                "execution_time": end_time - start_time,
                "field_count": result.count('\n'),
                "character_count": len(result)
            }
            return result
        return wrapper

# 使用例
tracker = PerformanceTracker()
generator = YAMLFrontmatterGenerator()

# メソッドのトラッキング
generator.create_comprehensive_frontmatter = tracker.track_generation(
    generator.create_comprehensive_frontmatter
)

# パフォーマンス測定
yaml_str = generator.create_comprehensive_frontmatter(
    title="パフォーマンステスト",
    content="テストコンテンツ" * 100
)

print(tracker.metrics)
# -> {'create_comprehensive_frontmatter': {'execution_time': 0.023, 'field_count': 25, 'character_count': 1250}}
```

## テスト API

### ユニットテスト用のモック

```python
from unittest.mock import Mock
import pytest

@pytest.fixture
def mock_ai_result():
    """AI 結果のモック"""
    ai_result = Mock()
    ai_result.category = Mock()
    ai_result.category.category = Mock()
    ai_result.category.category.value = "knowledge"
    ai_result.category.confidence_score = 0.95

    ai_result.summary = Mock()
    ai_result.summary.summary = "テスト要約"

    ai_result.tags = Mock()
    ai_result.tags.tags = ["test", "mock", "example"]

    return ai_result

@pytest.fixture
def yaml_generator():
    """YAML 生成器のフィクスチャ"""
    return YAMLFrontmatterGenerator()

def test_comprehensive_generation(yaml_generator, mock_ai_result):
    """包括的生成のテスト"""
    result = yaml_generator.create_comprehensive_frontmatter(
        title="テストノート",
        content_type="knowledge",
        ai_result=mock_ai_result,
        content="テストコンテンツ"
    )

    assert "title: テストノート" in result
    assert "type: knowledge" in result
    assert "category: knowledge" in result
    assert "summary: テスト要約" in result
    assert "ai_confidence: 0.95" in result
```

### 統合テスト

```python
class IntegrationTest:
    """統合テストクラス"""

    @pytest.mark.asyncio
    async def test_full_pipeline(self):
        """完全なパイプラインテスト"""
        from src.ai.processor import AIProcessor

        # AI プロセッサーでテキスト分析
        ai_processor = AIProcessor()
        ai_result = await ai_processor.process_text(
            "機械学習について学習した。 Python の scikit-learn を使用。"
        )

        # YAML 生成
        generator = YAMLFrontmatterGenerator()
        yaml_str = generator.create_comprehensive_frontmatter(
            title="機械学習学習記録",
            content_type="knowledge",
            ai_result=ai_result,
            content="機械学習について学習した。 Python の scikit-learn を使用。"
        )

        # 検証
        assert yaml_str.startswith("---")
        assert yaml_str.endswith("---")
        assert "title:" in yaml_str
        assert "category:" in yaml_str
        assert "summary:" in yaml_str
        assert "tags:" in yaml_str
```

## メトリクス・分析 API

### 生成統計の収集

```python
class GenerationMetrics:
    """生成メトリクス収集"""

    def __init__(self):
        self.stats = {
            "total_generations": 0,
            "field_usage": {},
            "content_types": {},
            "ai_confidence_avg": 0.0
        }

    def record_generation(self, yaml_content: str, metadata: dict):
        """生成記録"""
        self.stats["total_generations"] += 1

        # フィールド使用頻度
        for line in yaml_content.split('\n'):
            if ':' in line:
                field_name = line.split(':')[0].strip()
                self.stats["field_usage"][field_name] = \
                    self.stats["field_usage"].get(field_name, 0) + 1

        # コンテンツタイプ統計
        content_type = metadata.get("type", "unknown")
        self.stats["content_types"][content_type] = \
            self.stats["content_types"].get(content_type, 0) + 1

    def get_usage_report(self) -> dict:
        """使用レポート生成"""
        return {
            "most_used_fields": sorted(
                self.stats["field_usage"].items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],
            "content_type_distribution": self.stats["content_types"],
            "total_generations": self.stats["total_generations"]
        }
```

## 高度な使用例

### バッチ処理

```python
async def batch_generate_frontmatter(messages: List[dict]) -> List[str]:
    """複数メッセージの一括フロントマター生成"""

    generator = YAMLFrontmatterGenerator()
    ai_processor = AIProcessor()
    results = []

    for message in messages:
        # AI 分析
        ai_result = await ai_processor.process_text(message["content"])

        # YAML 生成
        yaml_str = generator.create_comprehensive_frontmatter(
            title=message.get("title", message["content"][:30]),
            content_type=message.get("type", "memo"),
            ai_result=ai_result,
            content=message["content"],
            context=message.get("context", {})
        )

        results.append(yaml_str)

    return results
```

### ストリーミング処理

```python
async def stream_generate_frontmatter(message_stream):
    """ストリーミング フロントマター生成"""

    generator = YAMLFrontmatterGenerator()
    ai_processor = AIProcessor()

    async for message in message_stream:
        try:
            # AI 分析
            ai_result = await ai_processor.process_text(message["content"])

            # YAML 生成
            yaml_str = generator.create_comprehensive_frontmatter(
                title=message["content"][:30],
                ai_result=ai_result,
                content=message["content"]
            )

            yield {
                "message_id": message["id"],
                "yaml_frontmatter": yaml_str,
                "status": "success"
            }

        except Exception as e:
            yield {
                "message_id": message["id"],
                "error": str(e),
                "status": "error"
            }
```

---

この API ドキュメントは MindBridge YAML フロントマターシステムの完全なプログラマティック リファレンスです。
