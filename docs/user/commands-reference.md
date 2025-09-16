# コマンドリファレンス

MindBridge の全コマンドの完全リファレンス。

## 目次

1. [コマンドの基本](#コマンドの基本)
2. [基本コマンド](#基本コマンド)
3. [Obsidian 管理](#obsidian-管理)
4. [AI 処理](#ai-処理)
5. [家計管理](#家計管理)
6. [タスク管理](#タスク管理)
7. [システム管理](#システム管理)
8. [健康データ](#健康データ)
9. [トラブルシューティング](#トラブルシューティング)

## コマンドの基本

### 実行方法

1. **スラッシュコマンド**: `/` で始まる
2. **場所**: `#commands` チャンネルで使用（推奨）
3. **権限**: ボットが存在するサーバーの全メンバーが利用可能

### パラメータータイプ

| 記号 | 意味 |
|--------|---------|
| `[必須]` | 必須パラメータ |
| `(オプション)` | オプションパラメータ |
| `"テキスト"` | 文字列入力 |
| `123` | 数値入力 |
| `true/false` | ブール値 |

## 基本コマンド

### `/help`
ボットのヘルプ情報を表示。

**パラメータ:**
- `command` (オプション): 特定のコマンドのヘルプ

**例:**
```
/help
/help command:search
```

**レスポンス:**
MindBridge の主要機能とコマンド一覧を表示。メモ管理、タスク管理、家計管理、統計・分析、設定、検索の各カテゴリに分類されたコマンドリストが表示されます。


### `/status`
ボットの現在のステータスを表示。

**パラメータ:** なし

**例:**
```
/status
```

**レスポンス:**
- ボット状態（稼働中/停止中）
- 接続状態（ Discord 接続、レイテンシ）
- サーバー数、チャンネル設定状況
- 各種サービスの状態（ Obsidian 、 AI 処理、音声認識）

## 検索・閲覧

### `/search`
Obsidian ボルト内のノートを検索。

**パラメータ:**
- `query` [必須]: 検索キーワード
- `limit` (オプション): 検索結果の最大表示数 (デフォルト: 10)

**例:**
```
/search query:"プロジェクト"
/search query:"python ai" limit:5
```

**レスポンス:**
指定されたキーワードでノートを検索し、一致した結果をタイトル、プレビュー、作成日付と共に表示します。

### `/random`
ランダムなノートを表示。

**パラメータ:** なし

**例:**
```
/random
```

**レスポンス:**
Obsidian ボルトからランダムに選択されたノートの詳細（タイトル、プレビュー、タグ、作成日、ファイルパス）を表示します。

## 統計・分析

### `/stats bot`
ボットの統計情報を表示。

**パラメータ:** なし

**例:**
```
/stats bot
```

**レスポンス:**
- 稼働時間、バージョン情報
- Python のバージョン
- 処理されたメッセージ数などのボット統計

### `/stats obsidian`
Obsidian ボルトの統計を表示。

**パラメータ:** なし

**例:**
```
/stats obsidian
```

**レスポンス:**
- 総ファイル数、フォルダ別統計
- 最近のアクティビティ
- 人気タグランキングなどのボルト統計

### `/stats finance`
家計管理の統計を表示。

**パラメータ:** なし

**例:**
```
/stats finance
```

**レスポンス:**
- 月間・年間支出統計
- カテゴリ別支出内訳
- 予算達成率などの財務統計

### `/stats task`
タスク管理の統計を表示。

**パラメータ:** なし

**例:**
```
/stats task
```

**レスポンス:**
- タスク完了率、進捗状況
- プロジェクト別統計
- 生産性分析などのタスク統計

## 家計管理

### `/finance_help`
家計管理コマンドのヘルプを表示。

**パラメータ:** なし

**例:**
```
/finance_help
```

**レスポンス:**
家計管理機能の説明と利用可能なコマンド一覧を表示します。

### `/expense_add`
支出を記録。

**パラメータ:**
- `amount` [必須]: 支出金額
- `description` [必須]: 支出の説明
- `category` (オプション): 支出カテゴリ（ food/transportation/entertainment/utilities/healthcare/education/shopping/other ）
- `notes` (オプション): メモ

**例:**
```
/expense_add amount:1500 description:"ランチ" category:"food"
/expense_add amount:3000 description:"電車代" category:"transportation" notes:"定期券購入"
```

**レスポンス:**
支出記録の確認と詳細情報（金額、カテゴリ、日付、 ID ）を表示。 Obsidian ノートに自動保存。

### `/income_add`
収入を記録。

**パラメータ:**
- `amount` [必須]: 収入金額
- `description` [必須]: 収入の説明
- `notes` (オプション): メモ

**例:**
```
/income_add amount:50000 description:"給与"
/income_add amount:5000 description:"副業収入" notes:"フリーランス"
```

**レスポンス:**
収入記録の確認と詳細情報を表示。 Obsidian ノートに自動保存。

### `/expense_list`
支出履歴を表示。

**パラメータ:**
- `category` (オプション): カテゴリでフィルタ
- `days` (オプション): 過去何日分を表示するか（デフォルト: 30 ）

**例:**
```
/expense_list
/expense_list category:"food" days:7
```

**レスポンス:**
指定期間の支出履歴と合計金額を表示。最大 10 件まで表示。

### `/subscription_add`
定期購入を追加。

**パラメータ:**
- `name` [必須]: サービス名
- `amount` [必須]: 金額
- `frequency` [必須]: 支払い頻度（ weekly/monthly/quarterly/yearly ）
- `start_date` (オプション): 開始日（ YYYY-MM-DD 形式）
- `category` (オプション): カテゴリ

**例:**
```
/subscription_add name:"Netflix" amount:1490 frequency:"monthly"
/subscription_add name:"Adobe CC" amount:6248 frequency:"monthly" category:"ソフトウェア"
```

**レスポンス:**
定期購入の詳細と次回支払日、月額換算金額を表示。 Obsidian ノート作成。

### `/subscription_list`
定期購入一覧を表示。

**パラメータ:**
- `active_only` (オプション): アクティブな定期購入のみ表示（デフォルト: true ）

**例:**
```
/subscription_list
/subscription_list active_only:false
```

**レスポンス:**
定期購入の一覧と月額合計、支払い期限の警告を表示。

### `/finance_summary`
家計サマリーを表示。

**パラメータ:**
- `days` (オプション): 過去何日分を表示するか（デフォルト: 30 ）

**例:**
```
/finance_summary
/finance_summary days:90
```

**レスポンス:**
収支概要、定期購入合計、支出カテゴリ上位 3 位、今後の支払い予定を表示。

## タスク管理

### `/task_help`
タスク管理コマンドのヘルプを表示。

**パラメータ:** なし

**例:**
```
/task_help
```

**レスポンス:**
タスク管理機能の説明と利用可能なコマンド一覧を表示します。

### `/task_add`
新しいタスクを作成。

**パラメータ:**
- `title` [必須]: タスクのタイトル
- `description` (オプション): タスクの詳細説明
- `priority` (オプション): 優先度（ low/medium/high/urgent ）
- `due_date` (オプション): 期限日（ YYYY-MM-DD 形式）
- `estimated_hours` (オプション): 予想作業時間
- `project` (オプション): プロジェクト名
- `tags` (オプション): タグ（カンマ区切り）

**例:**
```
/task_add title:"資料作成"
/task_add title:"プレゼン準備" priority:"high" due_date:"2025-01-20" estimated_hours:3
/task_add title:"コードレビュー" project:"WebApp" tags:"開発,レビュー"
```

**レスポンス:**
作成されたタスクの詳細（ ID 、優先度、期限、プロジェクト）を表示。 Obsidian ノート自動生成。

### `/task_list`
タスク一覧を表示。

**パラメータ:**
- `status` (オプション): ステータスでフィルタ（ todo/in_progress/waiting/done ）
- `priority` (オプション): 優先度でフィルタ（ low/medium/high/urgent ）
- `project` (オプション): プロジェクトでフィルタ
- `active_only` (オプション): アクティブなタスクのみ表示（デフォルト: true ）
- `limit` (オプション): 表示件数の上限（デフォルト: 10 ）

**例:**
```
/task_list
/task_list status:"in_progress" priority:"high"
/task_list project:"WebApp" limit:5
```

**レスポンス:**
条件に一致するタスクを優先度順で表示。進捗、期限の警告、プロジェクト情報を含む。

### `/task_done`
タスクを完了としてマーク。

**パラメータ:**
- `task_id` [必須]: 完了するタスクの ID （先頭 8 文字でも可）
- `actual_hours` (オプション): 実際の作業時間
- `notes` (オプション): 完了時のメモ

**例:**
```
/task_done task_id:"abc12345"
/task_done task_id:"abc12345" actual_hours:2.5 notes:"予想より早く完了"
```

**レスポンス:**
完了したタスクの詳細、実績時間と予想時間の比較、作業期間を表示。

### `/task_progress`
タスクの進捗を更新。

**パラメータ:**
- `task_id` [必須]: 更新するタスクの ID （先頭 8 文字でも可）
- `progress` [必須]: 進捗パーセンテージ（ 0-100 ）
- `notes` (オプション): 進捗更新時のメモ

**例:**
```
/task_progress task_id:"abc12345" progress:50
/task_progress task_id:"abc12345" progress:75 notes:"API の実装完了"
```

**レスポンス:**
更新された進捗率、ステータス、進捗バーの視覚表示。

### `/task_delete`
タスクを削除。

**パラメータ:**
- `task_id` [必須]: 削除するタスクの ID （先頭 8 文字でも可）
- `confirm` [必須]: 削除確認のため「 DELETE 」と入力

**例:**
```
/task_delete task_id:"abc12345" confirm:"DELETE"
```

**レスポンス:**
削除されたタスクの情報を表示。サブタスクがある場合は削除不可。

## 設定・外部連携

### `/config show`
現在の設定を表示。

**パラメータ:** なし

**例:**
```
/config show
```

**レスポンス:**
統合コマンドは実装中です。各サービスとの連携機能は開発中です。

### `/integration status`
外部サービス連携の状態を確認。

**パラメータ:** なし

**例:**
```
/integration status
```

**レスポンス:**
Garmin Connect 、 Google Calendar などの外部サービス連携状況を表示します。

---

## メモ機能について

MindBridge の主要機能である **自動メモ処理** は、 Discord チャンネルへの投稿により利用します：

### `#memo` チャンネル
- テキストメッセージの AI 分析・分類・ Obsidian 保存
- URL の自動解析と要約
- 画像・ファイル添付の処理

### `#voice` チャンネル
- 音声ファイルの自動文字起こし（ Google Cloud Speech-to-Text ）
- 音声メモの AI 分析・構造化
- 複数音声フォーマット対応（ MP3, WAV, FLAC, OGG, M4A, WEBM ）

### AI 分析機能
- 自動カテゴリ分類（タスク、アイデア、プロジェクト、健康、財務など）
- タグ抽出とメタデータ生成
- YAML フロントマター付き Markdown ノート生成
- 適切な Obsidian フォルダへの自動保存

このコマンドリファレンスに記載されているコマンドと合わせて、 MindBridge の機能を最大限に活用してください。
