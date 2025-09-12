# 📚 YAML フロントマター フィールドリファレンス

## クイックリファレンス

全 60+フィールドの完全な一覧表です。

## 🏷️ フィールド分類

### A. 基本情報（基本フィールド） - 必須

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `title` | string | "機械学習の基礎" | ノートのタイトル |
| `created` | datetime | 2025-01-15T14:30:00+09:00 | 作成日時（ JST ） |
| `modified` | datetime | 2025-01-15T14:30:00+09:00 | 最終更新日時 |
| `date` | date | 2025-01-15 | 日付（検索用） |
| `type` | string | "knowledge" | コンテンツタイプ |

### B. 分類・組織化（分類）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `category` | string | "learning" | AI による分類 |
| `status` | string | "active" | ワークフロー状態 |
| `priority` | string | "high" | 優先度 |
| `importance` | string | "critical" | 重要度 |
| `difficulty_level` | string | "advanced" | 難易度レベル |
| `urgency` | string | "normal" | 緊急度 |

### C. AI 統合メタデータ（ AI 統合）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `summary` | string | "機械学習の概要" | AI 生成要約 |
| `ai_confidence` | float | 0.95 | AI 判定信頼度 |
| `ai_model` | string | "gemini-pro" | 使用 AI モデル |
| `ai_version` | string | "1.5" | AI モデルバージョン |
| `data_quality` | string | "high" | データ品質評価 |
| `processing_date` | datetime | 2025-01-15T14:30:00+09:00 | AI 処理日時 |
| `ai_metadata` | object | {...} | AI 追加情報 |

### D. コンテンツ分析（コンテンツ解析）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `word_count` | integer | 1500 | 単語数 |
| `reading_time` | integer | 7 | 推定読了時間（分） |
| `language` | string | "ja" | 主要言語 |
| `character_count` | integer | 3000 | 文字数 |
| `sentence_count` | integer | 25 | 文数 |
| `paragraph_count` | integer | 5 | 段落数 |

### E. タスク管理（ Task Management ）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `due_date` | date | 2025-02-15 | 期限日 |
| `progress` | integer | 50 | 進捗率（ 0-100 ） |
| `estimated_hours` | float | 4.5 | 推定作業時間 |
| `actual_hours` | float | 5.0 | 実作業時間 |
| `completed_date` | date | 2025-01-20 | 完了日 |
| `assignee` | string | "alice" | 担当者 |
| `milestone` | string | "beta-release" | マイルストーン |

### F. 学習・知識管理（ Knowledge Management ）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `subject` | string | "machine-learning" | 学習分野 |
| `learning_stage` | string | "intermediate" | 学習段階 |
| `mastery_level` | integer | 75 | 習得度（ 0-100 ） |
| `review_date` | date | 2025-02-15 | 復習予定日 |
| `next_review` | date | 2025-03-01 | 次回復習日 |
| `skill_level` | string | "expert" | 技能レベル |
| `certification` | string | "AWS-SA" | 関連資格 |

### G. 財務・ビジネス（ Finance & Business ）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `amount` | float | 1200.0 | 金額 |
| `currency` | string | "JPY" | 通貨 |
| `budget` | float | 5000.0 | 予算 |
| `cost_center` | string | "marketing" | コストセンター |
| `expense_category` | string | "meals" | 経費分類 |
| `invoice_number` | string | "INV-2024-001" | 請求書番号 |
| `receipt` | boolean | true | 領収書の有無 |
| `tax_deductible` | boolean | true | 税控除可能 |
| `business_purpose` | string | "会議用ランチ" | 事業目的 |

### H. 健康・ライフスタイル（健康・ライフスタイル）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `health_metric` | string | "exercise" | 健康指標 |
| `activity_type` | string | "running" | 活動タイプ |
| `duration` | integer | 30 | 時間（分） |
| `intensity` | string | "high" | 強度 |
| `calories` | integer | 500 | 消費カロリー |
| `heart_rate` | integer | 150 | 心拍数 |
| `mood` | string | "positive" | 気分 |
| `energy_level` | string | "high" | エネルギーレベル |
| `sleep_quality` | string | "good" | 睡眠の質 |
| `distance` | float | 5.0 | 距離（ km ） |
| `weight` | float | 70.5 | 体重（ kg ） |

### I. 関係性・参照（関係性・参照）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `tags` | array | ["python", "ai"] | タグ一覧 |
| `aliases` | array | ["ML", "機械学習"] | 別名 |
| `links` | array | ["重要文書"] | Wikilink |
| `reference` | array | ["https://..."] | 参考 URL |
| `related_notes` | array | ["note123"] | 関連ノート |
| `parent` | string | "project-alpha" | 親ノート |
| `children` | array | ["task1", "task2"] | 子ノート |
| `dependencies` | array | ["req1", "req2"] | 依存関係 |

### J. 地理・時間情報（地理・時間情報）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `location` | string | "東京都渋谷区" | 場所 |
| `timezone` | string | "Asia/Tokyo" | タイムゾーン |
| `coordinates` | array | [35.6762, 139.6503] | GPS 座標 |
| `weather` | string | "sunny" | 天気 |
| `temperature` | float | 22.5 | 気温（℃） |
| `season` | string | "spring" | 季節 |

### K. バージョン管理・履歴（バージョン管理・履歴）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `version` | string | "1.2" | バージョン |
| `revision` | integer | 5 | 改訂回数 |
| `change_log` | string | "タグを追加" | 変更履歴 |
| `last_reviewed` | date | 2025-01-10 | 最終レビュー |
| `review_date` | date | 2025-02-10 | レビュー予定 |
| `archive_date` | date | null | アーカイブ日 |
| `deprecated` | boolean | false | 廃止フラグ |

### L. コラボレーション（協同作業）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `collaborators` | array | ["alice", "bob"] | 協力者 |
| `team` | string | "development" | チーム |
| `project` | string | "mindbridge-v2" | プロジェクト |
| `shared_with` | array | ["team-alpha"] | 共有相手 |
| `permissions` | string | "read-write" | 権限 |
| `access_level` | string | "team" | アクセスレベル |
| `confidential` | boolean | false | 機密フラグ |

### M. 表示・ UI 制御（表示・ UI 制御）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `cssclasses` | array | ["important"] | CSS クラス |
| `template_used` | string | "daily" | テンプレート |
| `permalink` | string | "/notes/ml-basics" | パーマリンク |
| `publish` | boolean | false | 公開フラグ |
| `featured` | boolean | false | 注目フラグ |
| `banner` | string | "banner.jpg" | バナー画像 |
| `icon` | string | "🧠" | アイコン |

### N. メタデータ・システム（メタデータ・システム）

| フィールド | 型 | 例 | 説明 |
|----------|---|---|------|
| `source` | string | "Discord" | 情報源 |
| `source_id` | string | "msg_123456" | ソース ID |
| `auto_generated` | boolean | true | 自動生成フラグ |
| `checksum` | string | "sha256:abc..." | チェックサム |
| `encoding` | string | "utf-8" | 文字エンコード |
| `format_version` | string | "2.0" | フォーマット版 |

## 🔧 フィールドタイプ定義

### データ型マッピング

```python
# 数値フィールド
NUMERIC_FIELDS = {
    "word_count", "reading_time", "progress", "estimated_hours",
    "actual_hours", "amount", "budget", "calories", "heart_rate",
    "duration", "mastery_level", "revision", "temperature",
    "distance", "weight"
}

# 論理値フィールド
BOOLEAN_FIELDS = {
    "publish", "featured", "tax_deductible", "receipt",
    "confidential", "auto_generated", "deprecated"
}

# 配列フィールド
ARRAY_FIELDS = {
    "tags", "aliases", "links", "reference", "related_notes",
    "children", "dependencies", "collaborators", "shared_with",
    "cssclasses", "coordinates"
}

# 日時フィールド
DATETIME_FIELDS = {
    "created", "modified", "processing_date", "last_reviewed"
}

# 日付フィールド
DATE_FIELDS = {
    "date", "due_date", "completed_date", "review_date",
    "next_review", "archive_date"
}
```

### 制約値（列挙値）

```python
# 優先度
PRIORITY_VALUES = ["low", "normal", "high", "urgent"]

# 重要度
IMPORTANCE_VALUES = ["low", "medium", "high", "critical"]

# 状態
STATUS_VALUES = ["draft", "active", "completed", "archived", "cancelled"]

# 難易度
DIFFICULTY_VALUES = ["basic", "intermediate", "advanced", "expert"]

# データ品質
QUALITY_VALUES = ["low", "medium", "high", "excellent"]

# 言語コード
LANGUAGE_VALUES = ["ja", "en", "zh", "ko", "fr", "de", "es"]

# 通貨
CURRENCY_VALUES = ["JPY", "USD", "EUR", "GBP", "CNY", "KRW"]

# 活動タイプ
ACTIVITY_VALUES = [
    "running", "walking", "cycling", "swimming", "yoga",
    "meeting", "study", "work", "rest", "travel"
]

# 気分
MOOD_VALUES = ["very-negative", "negative", "neutral", "positive", "very-positive"]

# エネルギーレベル
ENERGY_VALUES = ["very-low", "low", "normal", "high", "very-high"]
```

## 🎯 コンテンツタイプ別フィールドセット

### タスクタイプ
```yaml
# 必須フィールド
type: "task"
status: "pending"
progress: 0

# 推奨フィールド
due_date: null
estimated_hours: null
priority: "normal"
assignee: null
milestone: null
```

### 知識タイプ
```yaml
# 必須フィールド
type: "knowledge"
subject: null

# 推奨フィールド
learning_stage: null
mastery_level: null
review_date: null
skill_level: null
difficulty_level: "intermediate"
```

### 金融タイプ
```yaml
# 必須フィールド
type: "finance"
amount: null
currency: "JPY"

# 推奨フィールド
expense_category: "uncategorized"
tax_deductible: false
business_purpose: null
receipt: false
```

### 健康タイプ
```yaml
# 必須フィールド
type: "health"
activity_type: "general"

# 推奨フィールド
duration: null
calories: null
mood: null
energy_level: null
intensity: null
```

### プロジェクトタイプ
```yaml
# 必須フィールド
type: "project"
status: "active"

# 推奨フィールド
progress: 0
milestone: null
team: null
collaborators: []
priority: "normal"
```

### メモタイプ
```yaml
# 必須フィールド
type: "memo"

# 推奨フィールド
mood: null
location: null
weather: null
tags: []
```

## 🤖 自動生成ルール

### 1. AI 分析による生成

```python
# CategoryResult から
category: ai_result.category.category.value.lower()
ai_confidence: ai_result.category.confidence_score
data_quality: "high" if confidence >= 0.9 else "medium"

# SummaryResult から
summary: ai_result.summary.summary

# TagsResult から
tags: ai_result.tags.tags
```

### 2. パターン認識による生成

```python
# 金額抽出
r'[¥$€£]\s?(\d+(?:,\d+)*(?:\.\d+)?)'
# → amount, currency

# 日付抽出
r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})'
# → due_date

# 時間抽出
r'(\d+)\s*時間'
# → estimated_hours

# 活動抽出
activities = {
    "running": ["ランニング", "走", "ジョギング"],
    "meeting": ["会議", "ミーティング", "打ち合わせ"]
}
# → activity_type
```

### 3. コンテンツ分析による生成

```python
# 文字数・単語数
word_count: len(content.split())
character_count: len(content)

# 読了時間（ 200 語/分）
reading_time: max(1, word_count // 200)

# 難易度（平均単語長）
avg_length = sum(len(word) for word in words) / len(words)
difficulty_level: "advanced" if avg_length > 6 else "intermediate"

# 言語検出
language: detect_language(content)
```

## 🔍 フィールド検索・フィルタリング

### Obsidian でのクエリ例

```markdown
# 高優先度のタスク
```query
path:"" AND priority:"high" AND type:"task"
```

# AI 信頼度の高い知識ノート
```query
path:"" AND ai_confidence:>0.9 AND type:"knowledge"
```

# 今月の財務記録
```query
path:"" AND type:"finance" AND date:>2025-01-01
```

# 復習が必要な学習ノート
```query
path:"" AND review_date:<2025-01-20 AND type:"knowledge"
```
```

### Dataview での集計例

```javascript
// 月別支出合計
TABLE SUM(rows.amount) AS "合計支出"
FROM ""
WHERE type = "finance"
GROUP BY dateformat(date, "yyyy-MM") AS "月"
SORT "月" DESC

// プロジェクト進捗一覧
TABLE progress, due_date, assignee
FROM ""
WHERE type = "project" AND status = "active"
SORT progress ASC

// 健康データサマリー
TABLE activity_type, duration, calories
FROM ""
WHERE type = "health" AND date > date(today) - dur(7 days)
SORT date DESC
```

## 📋 フィールド拡張ガイド

### 新フィールド追加手順

1. **フィールド定義**
```python
# FIELD_ORDER に追加
"new_field_name"

# 適切なタイプセットに分類
BOOLEAN_FIELDS.add("new_boolean_field")
```

2. **生成ロジック実装**
```python
def _generate_new_field(self, content: str) -> Any:
    # 生成ロジック
    pass
```

3. **テスト追加**
```python
def test_new_field_generation(self):
    result = self.generator.create_comprehensive_frontmatter(
        title="Test", content="Test content"
    )
    assert "new_field_name:" in result
```

### カスタムフィールドのベストプラクティス

- **命名規則**: snake_case を使用
- **型の一貫性**: 同じ概念には同じデータ型を使用
- **デフォルト値**: null または意味のあるデフォルト値を設定
- **バリデーション**: 制約がある場合は明示的に定義

---

このリファレンスは MindBridge YAML フロントマターシステムの全フィールドの完全な仕様書です。
