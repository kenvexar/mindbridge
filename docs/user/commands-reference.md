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

## 🎯 コマンドの基本

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

## ⚙️ 基本コマンド

### `/help`
ヘルプ情報とコマンド一覧を表示。

**パラメータ:**
- `category` (オプション): コマンドカテゴリ
  - `basic` - 基本コマンド
  - `obsidian` - Obsidian 管理
  - `ai` - AI 機能
  - `finance` - 家計管理
  - `tasks` - タスク管理
  - `system` - システム管理

**例:**
```
/help
/help category:obsidian
```

**サンプルレスポンス:**
```
📚 MindBridge コマンドヘルプ

🔧 基本コマンド:
• /status - システム状態確認
• /help - このヘルプを表示

📝 Obsidian 管理:
• /search - ノート検索
• /obsidian - ボルト統計
...
```


### `/status`
システム全体の運用状態を確認。

**パラメータ:** なし

**例:**
```
/status
```

**サンプルレスポンス:**
```
🟢 MindBridge - システム状態

📊 基本情報:
• 状態: 正常動作中
• 稼働時間: 2 日 14 時間 32 分
• バージョン: 1.0.0
• 環境: 本番

🤖 Discord 接続:
• 接続: ✅ 正常
• レイテンシ: 87ms
• サーバー: 1
• 検出されたチャンネル: 3

🧠 AI 処理:
• 今日の処理: 45/1500 (日次制限)
• 平均処理時間: 1.23 秒
• キャッシュヒット率: 78%

💾 Obsidian:
• ボルト状態: ✅ アクセス可能
• 今日作成されたファイル: 12
• 総ファイル数: 234

⚡ システムリソース:
• CPU 使用率: 12%
• メモリ使用率: 35%
• ディスク使用率: 45%
```

## 📚 Obsidian 管理

### `/search_notes`
Obsidian ボルト内のノートを検索。

**パラメータ:**
- `query` [必須]: 検索クエリ
- `folder` (オプション): 検索対象フォルダ
- `limit` (オプション): 結果件数制限 (デフォルト: 10 、最大: 50)
- `include_content` (オプション): 検索にコンテンツを含める (デフォルト: false)

**例:**
```
/search_notes query:"プロジェクト"
/search_notes query:"python ai" folder:"10_Knowledge"
/search_notes query:"タスク" limit:5 include_content:true
```

**サンプルレスポンス:**
```
🔍 検索結果: "プロジェクト" (3 件)

📄 **新プロジェクト計画.md**
📁 11_Projects/
🕒 作成日: 2025-01-15
📝 初期プロジェクト計画について話し合い...

📄 **プロジェクト進捗レポート.md**
📁 11_Projects/
🕒 作成日: 2025-01-10
📝 フロントエンド実装が遅れている...

📄 **プロジェクト振り返り.md**
📁 30_Archive/
🕒 作成日: 2025-01-05
📝 前回プロジェクトから学んだ教訓...
```

### `/vault_stats`
Obsidian ボルトの統計を表示。

**パラメータ:** なし

**例:**
```
/vault_stats
```

**サンプルレスポンス:**
```
📊 Obsidian ボルト統計

📁 フォルダ別ノート:
• 00_Inbox: 15 ファイル
• 01_DailyNotes: 95 ファイル
• 02_Tasks: 12 ファイル
• 03_Ideas: 31 ファイル
• 10_Knowledge: 45 ファイル
• 11_Projects: 23 ファイル
• 20_Finance: 18 ファイル
• 21_Health: 8 ファイル

📈 最近のアクティビティ:
• 今日: 5 ファイル作成
• 今週: 28 ファイル作成
• 今月: 87 ファイル作成

💾 ストレージ:
• 総ファイル数: 239 ファイル
• 総サイズ: 12.3 MB
• 平均ファイルサイズ: 52.8 KB

🏷️ 人気のタグ:
• #project (23)
• #idea (18)
• #learning (15)
• #finance (12)
• #health (8)
```

### `/daily_note`
日記ノートの作成または表示。

**パラメータ:**
- `action` [必須]: 実行するアクション
  - `show` - ノートを表示
  - `create` - 新規ノート作成
  - `update` - コンテンツを追加
- `date` (オプション): 対象日付 (YYYY-MM-DD 形式、デフォルト: 今日)
- `content` (オプション): 追加するコンテンツ (update アクション用)

**例:**
```
/daily_note action:show
/daily_note action:create date:"2025-01-17"
/daily_note action:update content:"Important meeting today"
```

## 🧠 AI 処理

### `/process`
AI を使ってテキストを手動処理。

**パラメータ:**
- `text` [必須]: 処理するテキスト
- `save_to_obsidian` (オプション): Obsidian に保存 (デフォルト: true)
- `processing_type` (オプション): 処理タイプ
  - `standard` - 標準分析
  - `summary` - 要約重視
  - `detailed` - 詳細分析

**例:
```
/process text:"Discussed new feature design in today's meeting"
/process text:"Long article content..." processing_type:summary save_to_obsidian:false
```

**サンプルレスポンス:**
```
🧠 AI 処理結果

📝 **要約:**
会議で新機能設計について議論し、技術的課題と解決策を検討

🏷️ **タグ:**
#meeting #design #feature-planning #development

📂 **カテゴリ:** Projects

🔗 **抽出されたキーワード:**
• 機能設計
• 技術的課題
• 解決策議論

✅ **Obsidian に保存:** 11_Projects/meeting-feature-design.md

⏱️ **処理時間:** 1.23s
```

### `/summarize`
長文テキストの要約を生成。

**パラメータ:**
- `text` [必須]: 要約するテキスト
- `max_length` (オプション): 要約の最大長 (文字数、デフォルト: 200)
- `style` (オプション): 要約スタイル
  - `bullet` - 箇条書き
  - `paragraph` - 段落形式
  - `keywords` - キーワード抽出

**例:**
```
/summarize text:"Long article content..." max_length:150
/summarize text:"Meeting minutes..." style:bullet
```

### `/analyze_url`
URL コンテンツの分析と要約。

**パラメータ:**
- `url` [必須]: 分析する URL
- `save_summary` (オプション): 要約を Obsidian に保存 (デフォルト: true)
- `analysis_depth` (オプション): 分析の深さ
  - `quick` - 基本情報のみ
  - `standard` - 標準分析
  - `deep` - 詳細分析

**例:**
```
/analyze_url url:"https://example.com/article"
/analyze_url url:"https://tech-blog.com/post" analysis_depth:deep
```

## 💰 家計管理

### `/add_expense`
支出を記録。

**パラメータ:**
- `amount` [必須]: 金額 (数値)
- `description` [必須]: 支出の説明
- `category` (オプション): カテゴリ
- `date` (オプション): 日付 (YYYY-MM-DD 形式、デフォルト: 今日)
- `payment_method` (オプション): 支払い方法
- `tags` (オプション): 追加のタグ (カンマ区切り)

**例:**
```
/add_expense amount:1200 description:"lunch" category:"food"
/add_expense amount:3500 description:"tech book" category:"education" payment_method:"credit card"
```

**サンプルレスポンス:**
```
💰 支出を記録しました

📊 **記録詳細:**
• 金額: ¥1,200
• 説明: 昼食
• カテゴリ: 食費
• 日付: 2025-01-17
• 支払い方法: 現金

📈 **月次統計:**
• 食費合計: ¥23,400 / ¥30,000 (予算)
• 今日の支出: ¥3,200
• 月間支出: ¥87,650

✅ **保存先:** 20_Finance/2025-01-expenses.md
```

### `/expense_report`
支出レポートを生成。

**パラメータ:**
- `period` [必須]: 期間
  - `daily` - 今日
  - `weekly` - 今週
  - `monthly` - 今月
  - `yearly` - 今年
- `category` (オプション): 特定のカテゴリのみ
- `chart` (オプション): チャートを表示 (デフォルト: true)

**例:**
```
/expense_report period:monthly
/expense_report period:weekly category:"food"
```

### `/add_subscription`
サブスクリプションサービスを登録。

**パラメータ:**
- `name` [必須]: サービス名
- `amount` [必須]: 月額料金
- `billing_date` [必須]: 請求日 (1-31)
- `category` (オプション): カテゴリ
- `description` (オプション): 説明
- `auto_renew` (オプション): 自動更新 (デフォルト: true)

**例:**
```
/add_subscription name:"Netflix" amount:1980 billing_date:15 category:"entertainment"
/add_subscription name:"Adobe CC" amount:6480 billing_date:1 category:"tools"
```

## ✅ タスク管理

### `/add_task`
新しいタスクを作成。

**パラメータ:**
- `title` [必須]: タスクタイトル
- `description` (オプション): タスク詳細
- `due_date` (オプション): 期限日 (YYYY-MM-DD 形式)
- `priority` (オプション): 優先度
  - `low` - 低
  - `medium` - 中 (デフォルト)
  - `high` - 高
  - `urgent` - 緊急
- `project` (オプション): プロジェクト名
- `tags` (オプション): タグ (カンマ区切り)

**例:**
```
/add_task title:"Create requirements document" due_date:"2025-01-20" priority:high
/add_task title:"Code review" description:"Review new feature PR" project:"WebApp"
```

**サンプルレスポンス:**
```
✅ タスクを作成しました

📋 **タスク詳細:**
• ID: #T-001
• タイトル: 要件定義書作成
• 期限: 2025-01-20 (3 日後)
• 優先度: 🔴 高
• ステータス: 待機中
• プロジェクト: WebApp

⏰ **リマインダー:**
• 期限の 1 日前にアラート設定

📊 **プロジェクト統計:**
• WebApp: 5 タスク (待機: 3, 進行中: 2)
• 合計: 12 アクティブタスク

✅ **保存先:** 02_Tasks/task-T001-requirements.md
```

### `/list_tasks`
タスク一覧を表示。

**パラメータ:**
- `status` (オプション): ステータスでフィルタ
  - `pending` - 待機中
  - `in_progress` - 進行中
  - `completed` - 完了
  - `all` - 全て (デフォルト)
- `project` (オプション): プロジェクトでフィルタ
- `priority` (オプション): 優先度でフィルタ
- `due_soon` (オプション): 期限が近いもののみ (デフォルト: false)

**例:**
```
/list_tasks status:pending
/list_tasks project:"WebApp" priority:high
/list_tasks due_soon:true
```

### `/complete_task`
タスクを完了としてマーク。

**パラメータ:**
- `task_id` [必須]: タスク ID (#T-001 形式)
- `notes` (オプション): 完了メモ
- `time_spent` (オプション): 所要時間 (分)

**例:**
```
/complete_task task_id:"T-001" notes:"Successfully completed. Next: request review"
/complete_task task_id:"T-003" time_spent:120
```

## 🔧 システム管理

### `/backup_vault`
Obsidian ボルトのバックアップを作成。

**パラメータ:**
- `include_media` (オプション): メディアファイルを含める (デフォルト: true)
- `compression` (オプション): 圧縮レベル (1-9 、デフォルト: 6)

**例:**
```
/backup_vault
/backup_vault include_media:false compression:9
```

### `/system_metrics`
詳細なシステムメトリクスを表示。

**パラメータ:** なし

**例:
```
/system_metrics
```

**サンプルレスポンス:**
```
📊 システムメトリクス (詳細)

🖥️ **システムリソース:**
• CPU 使用率: 12% (2 コア)
• メモリ使用率: 35% (1.4GB / 4GB)
• ディスク使用率: 45% (9GB / 20GB)
• ネットワーク: 125KB/s (アップ), 67KB/s (ダウン)

🤖 **Discord 接続:**
• WebSocket レイテンシ: 87ms
• 今日の再接続回数: 0
• 処理中のリクエスト: 2
• キューされたリクエスト: 0

🧠 **AI 処理:**
• 今日の処理: 45/1500 (3%)
• 平均応答時間: 1.23s
• 成功率: 98.2%
• キャッシュヒット率: 78%

💾 **Obsidian 操作:**
• 今日作成されたファイル: 12
• 平均ファイルサイズ: 52KB
• 保存成功率: 100%
• 検索クエリ: 8
```

### `/cache_info`
AI キャッシュの状態を確認。

**パラメータ:** なし

**例:
```
/cache_info
```

## 🏃 健康データ

### `/garmin_sync`
Garmin Connect からデータを同期。

**パラメータ:**
- `date` (オプション): 同期する日付 (YYYY-MM-DD 、デフォルト: 昨日)
- `data_type` (オプション): データタイプ
  - `all` - 全データ (デフォルト)
  - `activities` - アクティビティのみ
  - `sleep` - 睡眠データのみ
  - `health` - 健康指標のみ

**例:**
```
/garmin_sync
/garmin_sync date:"2025-01-15" data_type:activities
```

**サンプルレスポンス:**
```
🏃 Garmin データ同期完了

📊 **同期されたデータ (2025-01-16):**

🏃 **アクティビティ:**
• ランニング: 5.2km, 28 分, 平均心拍数 145bpm
• ウォーキング: 8,432 歩

😴 **睡眠:**
• 就寝時間: 23:15
• 起床時間: 06:45
• 睡眠時間: 7 時間 30 分
• 深い睡眠: 1 時間 45 分 (23%)

💓 **健康指標:**
• 安静時心拍数: 58bpm
• ストレスレベル: 25 (低)
• Body Battery: 85/100

✅ **保存先:** 21_Health/2025-01-16-garmin-data.md

📈 **週次トレンド:**
• 平均歩数: 7,845 (目標: 8,000)
• 運動日: 4/7
• 平均睡眠: 7 時間 12 分
```

### `/health_report`
健康データレポートを生成。

**パラメータ:**
- `period` [必須]: 期間
  - `weekly` - 今週
  - `monthly` - 今月
  - `quarterly` - 四半期
- `focus` (オプション): 焦点領域
  - `fitness` - フィットネス
  - `sleep` - 睡眠
  - `heart` - 心拍数
  - `all` - 全体 (デフォルト)

**例:
```
/health_report period:weekly
/health_report period:monthly focus:sleep
```

## 🔍 トラブルシューティング

### `/debug_info`
デバッグ情報を表示。

**パラメータ:** なし

**例:
```
/debug_info
```

**サンプルレスポンス:**
```
🔍 デバッグ情報

⚙️ **設定:**
• 環境: 本番
• ログレベル: INFO
• モックモード: 無効
• Secret Manager: 有効

🔗 **接続状態:**
• Discord: ✅ 接続済み
• Gemini API: ✅ 正常
• Google Speech: ✅ 正常
• Obsidian Vault: ✅ アクセス可能

📊 **チャンネル設定:**
• memo: 設定済み (123...678)
• notifications: 設定済み (234...789)
• commands: 設定済み (345...890)

🐛 **最近のエラー:**
• エラー (過去 1 時間): 0
• 警告 (過去 1 時間): 2
• 最新エラー: なし

🔧 **システム情報:**
• Python: 3.13.0
• discord.py: 2.3.2
• uv: 0.1.32
• 稼働時間: 2 日 14 時間 32 分
```

### `/test_features`
主要機能をテスト。

**パラメータ:**
- `feature` (オプション): テストする機能
  - `ai` - AI 処理
  - `obsidian` - Obsidian 統合
  - `discord` - Discord 接続
  - `all` - 全機能 (デフォルト)

**例:
```
/test_features
/test_features feature:ai
```

**サンプルレスポンス:**
```
🧪 機能テスト実行中...

✅ **Discord 接続テスト:**
• WebSocket: 正常 (87ms)
• コマンド応答: 正常
• 権限: 正常

✅ **AI 処理テスト:**
• Gemini API 接続: 正常
• テスト分析: 正常 (1.23s)
• キャッシュ: 正常

✅ **Obsidian 統合テスト:**
• ボルトアクセス: 正常
• ファイル作成: 正常
• 検索機能: 正常

❌ **音声処理テスト:**
• Speech API: エラー (認証失敗)
• 推奨アクション: Google Cloud 認証を確認

📊 **テスト結果:**
• 成功: 3/4 機能
• 失敗: 1/4 機能
• 総実行時間: 5.7 秒

💡 **推奨アクション:**
音声処理の認証設定を確認してください。
```

---

このコマンドリファレンスを使用して MindBridge の機能を最大限に活用してください。各コマンドは `/help` コマンドで詳細なヘルプも利用できます。
