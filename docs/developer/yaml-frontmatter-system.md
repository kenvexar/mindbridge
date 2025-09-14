# MindBridge 包括的 YAML フロントマターシステム

## 概要

MindBridge の包括的 YAML フロントマターシステムは、 Discord から投稿されたメッセージを構造化された Obsidian ノートに変換する際に、 60 以上の包括的なメタデータフィールドを自動生成する高度なシステムです。

## システムの特徴

- **完全自動化**: ユーザーの手動入力なしで包括的なメタデータを生成
- **AI 統合**: Google Gemini を使用した高度なコンテンツ分析
- **適応的フィールド**: コンテンツタイプに応じて最適なフィールドを選択
- **多言語対応**: 日本語・英語混在コンテンツに対応
- **型安全性**: Pydantic による厳密なデータバリデーション

## アーキテクチャ

```
Discord メッセージ
       ↓
AI 処理 (Gemini)
       ↓
コンテンツ分析
       ↓
YAML ジェネレーター
       ↓
包括的フロントマター
       ↓
Obsidian ノート
```

### コアコンポーネント

1. **YAMLFrontmatterGenerator** (`src/obsidian/template_system/yaml_generator.py`)
   - メインの生成エンジン
   - 60+ フィールドの定義と順序管理
   - 自動データ型変換

2. **AIProcessor** (`src/ai/processor.py`)
   - Gemini API との統合
   - CategoryResult, SummaryResult, TagsResult の生成

3. **MessageHandler** (`src/bot/handlers.py`)
   - Discord メッセージの処理
   - YAML 生成器との連携

## フィールドカテゴリ詳細解説

### 1. 基本情報フィールド（ Core Fields ）

すべてのノートで必須となる基本的なメタデータです。

```yaml
title: "ノートのタイトル"
created: 2025-01-15T10:30:00+09:00
modified: 2025-01-15T10:30:00+09:00
date: 2025-01-15
type: "memo"
```

| フィールド | 型 | 説明 | 生成方法 |
|----------|---|------|---------|
| `title` | string | ノートのタイトル | メッセージの最初の 30 文字から生成 |
| `created` | datetime | 作成日時（ JST ） | Discord メッセージのタイムスタンプ |
| `modified` | datetime | 最終更新日時 | 初回は created と同じ |
| `date` | date | 日付（検索・フィルタ用） | created の日付部分 |
| `type` | string | コンテンツタイプ | AI 分析 + 手動指定 |

**使用例**:
```yaml
title: "機械学習プロジェクトのタスク整理"
created: 2025-01-15T14:30:00+09:00
modified: 2025-01-15T14:30:00+09:00
date: 2025-01-15
type: "task"
```

### 2. AI 統合メタデータ（ AI 統合）

Google Gemini による分析結果を構造化して保存します。

```yaml
category: "knowledge"
summary: "機械学習の基本概念について学習した内容"
ai_confidence: 0.95
ai_model: "gemini-pro"
data_quality: "high"
processing_date: 2025-01-15T14:30:00+09:00
```

| フィールド | 型 | 説明 | 生成ロジック |
|----------|---|------|-------------|
| `category` | string | AI によるカテゴリ分類 | CategoryResult.category.category.value |
| `summary` | string | 内容の要約 | SummaryResult.summary.summary |
| `ai_confidence` | float | 分類の信頼度 (0-1) | CategoryResult.confidence_score |
| `ai_model` | string | 使用 AI モデル | 固定値："gemini-pro" |
| `data_quality` | string | データ品質評価 | 信頼度に基づく自動判定 |
| `processing_date` | datetime | AI 処理実行日時 | 現在時刻 |

**信頼度による品質判定**:
- `ai_confidence >= 0.9` → `data_quality: "high"`
- `ai_confidence >= 0.7` → `data_quality: "medium"`
- `ai_confidence < 0.7` → `data_quality: "low"`

### 3. コンテンツ分析メタデータ（ Content Analytics ）

テキスト内容を自動分析して生成されるメタデータです。

```yaml
word_count: 1500
reading_time: 7
difficulty_level: "advanced"
language: "ja"
source: "Discord"
```

| フィールド | 型 | 計算方法 |
|----------|---|---------|
| `word_count` | integer | `len(content.split())` |
| `reading_time` | integer | `max(1, word_count // 200)` 分 |
| `difficulty_level` | string | 平均単語長による判定 |
| `language` | string | 主要言語の検出 |
| `source` | string | 固定値："Discord" |

**難易度判定アルゴリズム**:
```python
avg_word_length = sum(len(word) for word in content.split()) / word_count
if avg_word_length > 6:
    difficulty_level = "advanced"
elif avg_word_length > 4:
    difficulty_level = "intermediate"
else:
    difficulty_level = "basic"
```

### 4. 自動パターン認識（ Pattern Recognition ）

正規表現と AI 分析を組み合わせてコンテンツから情報を抽出します。

#### 金額の自動抽出
```python
amounts = re.findall(r'[¥$€£]\s?(\d+(?:,\d+)*(?:\.\d+)?)', content)
```

**例**:
- "ランチ代¥1,200 を支払った" → `amount: 1200.0, currency: "JPY"`
- "予算$500 で計画" → `amount: 500.0, currency: "USD"`

#### 日付の自動抽出
```python
dates = re.findall(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', content)
```

**例**:
- "2024-12-25 までに完了" → `due_date: 2024-12-25`
- "来月 15 日が締切" → 相対日付の計算

#### 活動タイプの検出
```python
activities = {
    "running": ["ランニング", "走", "ジョギング"],
    "meeting": ["会議", "ミーティング", "打ち合わせ"],
    "study": ["学習", "勉強", "研修"]
}
```

### 5. コンテンツタイプ別適応フィールド

`content_type` に応じて異なるフィールドセットを自動追加します。

#### タスクタイプ
```yaml
type: "task"
status: "pending"
progress: 0
estimated_hours: null
due_date: null
priority: "normal"
```

#### ファイナンスタイプ
```yaml
type: "finance"
amount: 1200.0
currency: "JPY"
expense_category: "uncategorized"
tax_deductible: false
business_purpose: null
```

#### ヘルスタイプ
```yaml
type: "health"
activity_type: "general"
duration: null
calories: null
mood: null
energy_level: null
```

#### 知識タイプ
```yaml
type: "knowledge"
subject: null
learning_stage: null
mastery_level: null
review_date: null
skill_level: null
```

### 6. 関係性・参照管理（関係性管理）

Obsidian の機能を最大限活用するための関係性メタデータです。

```yaml
tags: ["learning", "python", "ai"]
aliases: ["ML 学習", "機械学習基礎"]
links: ["重要なドキュメント", "プロジェクト管理"]
related_notes: []
parent: null
children: []
```

#### タグの生成ロジック
1. **AI 生成タグ**: `TagsResult.tags.tags` から取得
2. **自動タグ**: コンテンツタイプ、カテゴリから生成
3. **コンテキストタグ**: Discord チャンネル、日付から生成

#### Wikilink の抽出
```python
wikilink_pattern = r'\[\[([^\]]+)\]\]'
links = re.findall(wikilink_pattern, content)
```

**例**: "この[[重要なドキュメント]]を参照" → `links: ["重要なドキュメント"]`

### 7. 時系列・スケジュール管理

プロジェクト管理とスケジューリングのためのフィールドです。

```yaml
due_date: 2025-02-15
estimated_hours: 8.0
progress: 25
milestone: "beta-release"
review_date: 2025-01-30
next_review: 2025-02-30
```

#### 期限の自動抽出パターン
- "〜までに" → `due_date`
- "来週" → 相対日付計算
- "月末" → 月末日の計算
- "Q1" → 四半期末日

### 8. 協働・権限管理

チーム作業とアクセス制御のためのフィールドです。

```yaml
collaborators: ["alice", "bob"]
assignee: "project-manager"
team: "development"
permissions: "shared"
shared_with: ["team-alpha"]
confidential: false
```

### 9. バージョン管理・履歴

文書のライフサイクル管理のためのトラッキングです。

```yaml
version: "1.0"
revision: 1
change_log: "初回作成"
last_reviewed: null
archive_date: null
status: "active"
```

### 10. 表示・ UI 制御

Obsidian での表示とレンダリングを制御するフィールドです。

```yaml
cssclasses: ["project-note", "high-priority"]
template_used: "project_template"
permalink: "/projects/mindbridge-v2"
publish: false
featured: false
```

## 技術実装詳細

### データ型自動変換システム

YAMLFrontmatterGenerator は文字列データを適切な型に自動変換します。

```python
def _convert_value(self, key: str, value: Any) -> Any:
    """値を適切なデータ型に変換"""
    if key in self.NUMERIC_FIELDS:
        return self._to_numeric(value)
    elif key in self.BOOLEAN_FIELDS:
        return self._to_boolean(value)
    elif key in self.ARRAY_FIELDS:
        return self._to_array(value)
    elif key in self.DATE_FIELDS:
        return self._to_datetime(value)
    return value
```

#### 数値変換
```python
def _to_numeric(self, value: Any) -> float:
    if isinstance(value, str):
        # カンマを削除して数値変換
        clean_value = value.replace(',', '').replace('¥', '').replace('$', '')
        return float(clean_value)
    return float(value)
```

#### 論理値変換
```python
def _to_boolean(self, value: Any) -> bool:
    if isinstance(value, str):
        return value.lower() in ["true", "yes", "1", "on", "はい"]
    return bool(value)
```

#### 配列変換
```python
def _to_array(self, value: Any) -> list:
    if isinstance(value, str):
        # カンマ区切りの文字列を配列に変換
        return [item.strip() for item in value.split(',')]
    return list(value) if not isinstance(value, list) else value
```

### AI 結果オブジェクトの処理

複雑なネストされた Pydantic オブジェクトを適切に処理します。

```python
def _extract_comprehensive_ai_data(self, ai_result) -> dict[str, Any]:
    """AI 結果から包括的なメタデータを抽出"""
    ai_data = {}

    # CategoryResult の処理
    if hasattr(ai_result, 'category') and ai_result.category:
        if hasattr(ai_result.category, 'category') and hasattr(ai_result.category.category, 'value'):
            category_value = ai_result.category.category.value
            ai_data["category"] = category_value.lower()
        else:
            ai_data["category"] = str(ai_result.category).lower()

    # SummaryResult の処理
    if hasattr(ai_result, 'summary') and ai_result.summary:
        if hasattr(ai_result.summary, 'summary'):
            ai_data["summary"] = ai_result.summary.summary
        else:
            ai_data["summary"] = str(ai_result.summary)

    # TagsResult の処理
    if hasattr(ai_result, 'tags') and ai_result.tags:
        if hasattr(ai_result.tags, 'tags'):
            ai_data["tags"] = ai_result.tags.tags
        else:
            ai_data["tags"] = ai_result.tags

    return ai_data
```

### フィールド順序管理

YAML の可読性を向上させるため、フィールドの出力順序を制御します。

```python
FIELD_ORDER = [
    # 基本情報（最優先）
    "title", "created", "modified", "date", "type",

    # 分類・組織化
    "category", "status", "priority", "importance",

    # コンテンツメタデータ
    "summary", "description", "word_count", "reading_time",

    # AI 関連
    "ai_confidence", "ai_model", "data_quality",

    # ... 60+ fields in total
]
```

## 使用例とベストプラクティス

### 1. 学習ノートの例

**入力**: "Python の機械学習ライブラリ scikit-learn について学習。回帰分析とクラス分類の基本的な使い方を理解した。次回は深層学習について調べる予定。"

**生成される YAML**:
```yaml
---
title: "Python の機械学習ライブラリ scikit-learn"
created: 2025-01-15T14:30:00+09:00
modified: 2025-01-15T14:30:00+09:00
date: 2025-01-15
type: "knowledge"
category: "learning"
summary: "scikit-learn の回帰分析とクラス分類の基本的な使い方を学習"
word_count: 45
reading_time: 1
difficulty_level: "intermediate"
language: "ja"
source: "Discord"
subject: "machine-learning"
learning_stage: "intermediate"
tags: ["python", "scikit-learn", "machine-learning", "regression", "classification"]
ai_confidence: 0.92
ai_model: "gemini-pro"
data_quality: "high"
processing_date: 2025-01-15T14:30:00+09:00
next_review: 2025-01-22
status: "active"
auto_generated: true
---
```

### 2. タスク管理の例

**入力**: "プロジェクトの進捗レポートを来週金曜日までに作成する。推定作業時間は 4 時間程度。優先度高。"

**生成される YAML**:
```yaml
---
title: "プロジェクトの進捗レポートを来週金曜日まで"
created: 2025-01-15T14:30:00+09:00
modified: 2025-01-15T14:30:00+09:00
date: 2025-01-15
type: "task"
category: "tasks"
summary: "プロジェクトの進捗レポート作成タスク"
due_date: 2025-01-24
estimated_hours: 4.0
progress: 0
priority: "high"
importance: "high"
status: "pending"
tags: ["task", "report", "project"]
word_count: 25
reading_time: 1
difficulty_level: "basic"
ai_confidence: 0.89
data_quality: "high"
auto_generated: true
---
```

### 3. 財務記録の例

**入力**: "チームランチ代¥3,200 を経費として支払い。領収書あり。税控除対象。"

**生成される YAML**:
```yaml
---
title: "チームランチ代¥3,200 を経費として支払い"
created: 2025-01-15T14:30:00+09:00
modified: 2025-01-15T14:30:00+09:00
date: 2025-01-15
type: "finance"
category: "finance"
summary: "チームランチの経費支払い記録"
amount: 3200.0
currency: "JPY"
expense_category: "meals"
tax_deductible: true
business_purpose: "チームランチ"
receipt: true
tags: ["expense", "meals", "tax-deductible"]
word_count: 15
reading_time: 1
ai_confidence: 0.94
data_quality: "high"
auto_generated: true
---
```

### 4. 健康記録の例

**入力**: "朝 5km ランニング完了。 30 分で走破。天気良好で気分最高！心拍数平均 150bpm 。"

**生成される YAML**:
```yaml
---
title: "朝 5km ランニング完了"
created: 2025-01-15T07:30:00+09:00
modified: 2025-01-15T07:30:00+09:00
date: 2025-01-15
type: "health"
category: "health"
summary: "朝のランニング記録"
activity_type: "running"
duration: 30
distance: 5.0
heart_rate: 150
mood: "positive"
energy_level: "high"
weather: "good"
tags: ["running", "exercise", "morning"]
word_count: 18
reading_time: 1
ai_confidence: 0.96
data_quality: "high"
auto_generated: true
---
```

## デバッグとトラブルシューティング

### よくある問題と解決策

#### 1. CategoryResult AttributeError
**エラー**: `'CategoryResult' object has no attribute 'lower'`

**原因**: AI 結果オブジェクトのネストされた属性への不適切なアクセス

**解決策**:
```python
# 間違い
ai_data["category"] = ai_result.category.lower()

# 正しい
if hasattr(ai_result.category, 'category') and hasattr(ai_result.category.category, 'value'):
    category_value = ai_result.category.category.value
    ai_data["category"] = category_value.lower()
```

#### 2. Tags Join TypeError
**エラー**: `sequence item 0: expected str instance, tuple found`

**原因**: TagsResult にタプルが含まれている場合の文字列結合エラー

**解決策**:
```python
# 間違い
tags_str = ", ".join(ai_result.tags)

# 正しい
if isinstance(tags_list, (list, tuple)):
    tags_str = ", ".join(str(tag) for tag in tags_list)
```

#### 3. Docker 同期問題
**症状**: コード変更が反映されない

**解決策**:
```bash
# コンテナを完全に再構築
docker compose down
docker compose up --build -d
```

### ログモニタリング

開発時の動作確認のためのログ出力例：

```json
{
  "event": "⭐ SUCCESS: Enhanced YAML frontmatter note created",
  "file_path": "11_Projects/2025-01-15-sample-note.md",
  "category": "knowledge",
  "has_ai_analysis": true,
  "ai_confidence": 0.92,
  "data_quality": "high",
  "timestamp": "2025-01-15T14:30:00+09:00"
}
```

## テストスイート

包括的なテストケースで品質を保証しています。

### テストカテゴリ

1. **基本機能テスト** (`test_comprehensive_frontmatter_generation`)
2. **コンテンツタイプ別テスト** (`test_content_type_specific_metadata`)
3. **データ型変換テスト** (`test_automatic_data_type_conversion`)
4. **Obsidian 統合テスト** (`test_obsidian_enhanced_frontmatter`)
5. **AI 統合テスト** (`test_ai_analysis_integration`)
6. **エッジケーステスト** (`test_edge_cases_and_error_handling`)

### テスト実行方法

```bash
# 全テスト実行
uv run pytest tests/unit/test_enhanced_yaml_generator.py

# 特定テスト実行
uv run pytest tests/unit/test_enhanced_yaml_generator.py::TestEnhancedYAMLFrontmatterGenerator::test_comprehensive_frontmatter_generation -v

# カバレッジ付きテスト
uv run pytest tests/unit/test_enhanced_yaml_generator.py --cov=src/obsidian/template_system/yaml_generator
```

## パフォーマンス最適化

### メモリ使用量の最適化

- フィールド順序の事前定義によるソート処理の削減
- 不要なフィールドの動的除外
- 大きなオブジェクトの早期ガベージコレクション

### 処理速度の向上

- 正規表現の事前コンパイル
- AI 結果の効率的なキャッシュ
- 条件分岐の最適化

```python
# 正規表現の事前コンパイル
AMOUNT_PATTERN = re.compile(r'[¥$€£]\s?(\d+(?:,\d+)*(?:\.\d+)?)')
DATE_PATTERN = re.compile(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})')
```

## 将来の拡張計画

### 予定されている機能追加

1. **カスタムフィールド定義**
   - ユーザー定義フィールドの動的追加
   - フィールドテンプレートの保存・再利用

2. **多言語フィールド対応**
   - 英語・中国語・韓国語フィールド名
   - ローカライゼーション機能

3. **高度なパターン認識**
   - 機械学習による自動分類精度向上
   - コンテキスト理解の向上

4. **外部サービス統合**
   - Google Calendar 連携
   - Slack 統合
   - Notion API 連携

### アーキテクチャの改善

- プラグイン システムによる機能拡張
- 設定ファイルによる動的フィールド定義
- GraphQL API による柔軟なデータアクセス

## コントリビューション ガイド

### 新しいフィールドの追加方法

1. **フィールド定義の追加**
```python
# yaml_generator.py の FIELD_ORDER に追加
FIELD_ORDER = [
    # ... existing fields
    "new_field_name",
]

# 適切なフィールドタイプに分類
BOOLEAN_FIELDS = {"publish", "featured", "new_boolean_field"}
```

2. **生成ロジックの実装**
```python
def _generate_new_field_logic(self, content: str, context: dict) -> Any:
    """新フィールドの生成ロジック"""
    # 実装内容
    pass
```

3. **テストケースの追加**
```python
def test_new_field_generation(self):
    """新フィールドのテスト"""
    result = self.generator.create_comprehensive_frontmatter(
        title="テスト",
        content="テスト内容"
    )
    assert "new_field_name:" in result
```

### コーディングガイドライン

- **型ヒント**: 全ての関数に適切な型ヒントを付加
- **ドキュメント**: docstring による詳細な説明
- **エラーハンドリング**: 適切な例外処理
- **ログ出力**: デバッグ用の構造化ログ

## 関連資料

### 技術仕様書
- [Obsidian YAML Frontmatter 仕様](https://help.obsidian.md/Editing+and+formatting/Properties)
- [Google Gemini API ドキュメント](https://ai.google.dev/docs)
- [Discord.py API リファレンス](https://discordpy.readthedocs.io/)

### 実装詳細
- `src/obsidian/template_system/yaml_generator.py` - メインジェネレーター
- `src/bot/handlers.py` - Discord 統合部分
- `tests/unit/test_enhanced_yaml_generator.py` - テストスイート

---

このドキュメントは MindBridge v2.0 の包括的 YAML フロントマターシステムの完全な技術仕様書です。システムの理解と拡張のために定期的に更新されます。
