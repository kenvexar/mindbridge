# ⚡ コマンドリファレンス

MindBridgeで利用可能な全コマンドの完全リファレンスです。

## 📋 目次

1. [コマンドの基本](#コマンドの基本)
2. [基本コマンド](#基本コマンド)
3. [Obsidian管理コマンド](#obsidian管理コマンド)
4. [AI処理コマンド](#ai処理コマンド)
5. [金融管理コマンド](#金融管理コマンド)
6. [タスク管理コマンド](#タスク管理コマンド)
7. [システム管理コマンド](#システム管理コマンド)
8. [テンプレート管理コマンド](#テンプレート管理コマンド)
9. [健康データコマンド](#健康データコマンド)
10. [トラブルシューティングコマンド](#トラブルシューティングコマンド)

## 🎯 コマンドの基本

### コマンド実行方法

1. **スラッシュコマンド**: `/` で始まるコマンド
2. **実行場所**: 設定されたコマンドチャンネル（推奨）または任意のチャンネル
3. **権限**: ボットが参加しているサーバーのメンバーのみ実行可能

### パラメータの種類

| 記号 | 意味 |
|------|------|
| `[required]` | 必須パラメータ |
| `(optional)` | オプションパラメータ |
| `"text"` | 文字列入力 |
| `123` | 数値入力 |
| `true/false` | ブール値 |

## ⚙️ 基本コマンド

### `/help`
ヘルプ情報とコマンド一覧を表示します。

**パラメータ:**
- `category` (optional): コマンドカテゴリ
  - `basic` - 基本コマンド
  - `obsidian` - Obsidian管理
  - `ai` - AI機能
  - `finance` - 金融管理
  - `tasks` - タスク管理
  - `system` - システム管理

**使用例:**
```
/help
/help category:obsidian
```

**応答例:**
```
📚 MindBridge コマンドヘルプ

🔧 基本コマンド:
• /ping - 接続テスト
• /status - システム状態確認
• /help - このヘルプ表示

📝 Obsidian管理:
• /search_notes - ノート検索
• /vault_stats - ボルト統計
...
```

### `/ping`
ボットの応答性とDiscord接続をテストします。

**パラメータ:** なし

**使用例:**
```
/ping
```

**応答例:**
```
🏓 Pong!
レスポンス時間: 245ms
Discord WebSocket レイテンシ: 87ms
ボット稼働時間: 2日 14時間 32分
```

### `/status`
システム全体の動作状況を確認します。

**パラメータ:** なし

**使用例:**
```
/status
```

**応答例:**
```
🟢 MindBridge - システム状態

📊 基本情報:
• 状態: 正常稼働中
• 稼働時間: 2日 14時間 32分
• バージョン: 1.0.0
• 環境: production

🤖 Discord接続:
• 接続状態: ✅ 正常
• レイテンシ: 87ms
• サーバー数: 1
• チャンネル数: 12

🧠 AI処理:
• 今日の処理数: 45/1500 (日次制限)
• 平均処理時間: 1.23秒
• キャッシュヒット率: 78%

💾 Obsidian:
• ボルト状態: ✅ アクセス可能
• 今日作成したファイル数: 12
• 総ファイル数: 234

⚡ システムリソース:
• CPU使用率: 12%
• メモリ使用率: 35%
• ディスク使用率: 45%
```

## 📚 Obsidian管理コマンド

### `/search_notes`
Obsidianボルト内のノートを検索します。

**パラメータ:**
- `query` [required]: 検索クエリ
- `folder` (optional): 検索対象フォルダ
- `limit` (optional): 結果上限数 (デフォルト: 10, 最大: 50)
- `include_content` (optional): 内容も含めて検索 (デフォルト: false)

**使用例:**
```
/search_notes query:"プロジェクト"
/search_notes query:"Python AI" folder:"05_Resources"
/search_notes query:"タスク" limit:5 include_content:true
```

**応答例:**
```
🔍 検索結果: "プロジェクト" (3件)

📄 **新しいプロジェクト計画.md**
📁 01_Projects/
🕒 作成日: 2025-08-15
📝 プロジェクトの初期企画について話し合った...

📄 **プロジェクト進捗報告.md**
📁 01_Projects/
🕒 作成日: 2025-08-10
📝 フロントエンド実装が遅れている...

📄 **プロジェクト振り返り.md**
📁 04_Archive/
🕒 作成日: 2025-08-05
📝 前回のプロジェクトから学んだこと...
```

### `/vault_stats`
Obsidianボルトの統計情報を表示します。

**パラメータ:** なし

**使用例:**
```
/vault_stats
```

**応答例:**
```
📊 Obsidian Vault 統計情報

📁 フォルダ別ノート数:
• 00_Inbox: 15 ファイル
• 01_Projects: 23 ファイル
• 02_DailyNotes: 95 ファイル
• 03_Ideas: 31 ファイル
• 05_Resources: 45 ファイル
• 06_Finance: 18 ファイル
• 07_Tasks: 12 ファイル

📈 最近の活動:
• 今日: 5 ファイル作成
• 今週: 28 ファイル作成
• 今月: 87 ファイル作成

💾 ストレージ:
• 総ファイル数: 239 ファイル
• 総サイズ: 12.3 MB
• 平均ファイルサイズ: 52.8 KB

🏷️ 人気タグ:
• #project (23)
• #idea (18)
• #learning (15)
• #finance (12)
• #health (8)
```

### `/daily_note`
指定日のデイリーノートを作成・表示します。

**パラメータ:**
- `action` [required]: 実行アクション
  - `show` - ノートを表示
  - `create` - 新規作成
  - `update` - 内容を追加
- `date` (optional): 対象日付 (YYYY-MM-DD形式、デフォルト: 今日)
- `content` (optional): 追加する内容 (update時)

**使用例:**
```
/daily_note action:show
/daily_note action:create date:"2025-08-17"
/daily_note action:update content:"重要な会議があった"
```

**応答例:**
```
📅 デイリーノート: 2025-08-17

✅ ノートが見つかりました

📝 **今日のハイライト:**
• プロジェクト進捗会議
• 新機能の設計レビュー
• ドキュメント整理

🎯 **完了したタスク:**
• [x] 要件定義書のレビュー
• [x] コードレビューの実施

💭 **メモ:**
• React Server Componentsについて調査
• 来週のスプリント計画を検討

📊 **今日の統計:**
• 処理したメッセージ: 8件
• 作成したファイル: 3件
• AI分析回数: 12回

[ノートを開く](obsidian://open?vault=MyVault&file=02_DailyNotes%2F2025%2F08-August%2F2025-08-17.md)
```

## 🧠 AI処理コマンド

### `/process`
テキストを手動でAI処理します。

**パラメータ:**
- `text` [required]: 処理したいテキスト
- `save_to_obsidian` (optional): Obsidianに保存するか (デフォルト: true)
- `processing_type` (optional): 処理タイプ
  - `standard` - 標準分析
  - `summary` - 要約重視
  - `detailed` - 詳細分析

**使用例:**
```
/process text:"今日のミーティングで新機能の設計について議論した"
/process text:"長い記事の内容..." processing_type:summary save_to_obsidian:false
```

**応答例:**
```
🧠 AI処理結果

📝 **要約:**
ミーティングで新機能の設計について議論し、技術的な課題と解決策を検討した

🏷️ **タグ:**
#meeting #design #feature-planning #development

📂 **カテゴリ:** Projects

🔗 **抽出されたキーワード:**
• 新機能設計
• 技術的課題
• 解決策検討

✅ **Obsidianに保存:** 01_Projects/meeting-feature-design.md

⏱️ **処理時間:** 1.23秒
```

### `/summarize`
長文テキストの要約を生成します。

**パラメータ:**
- `text` [required]: 要約したいテキスト
- `max_length` (optional): 最大要約長 (文字数、デフォルト: 200)
- `style` (optional): 要約スタイル
  - `bullet` - 箇条書き
  - `paragraph` - 段落形式
  - `keywords` - キーワード抽出

**使用例:**
```
/summarize text:"長い記事の内容..." max_length:150
/summarize text:"会議議事録..." style:bullet
```

**応答例:**
```
📄 要約生成結果

💡 **要約 (bullet形式):**
• 新しいAI技術により、自然言語処理の精度が大幅に向上
• 従来の手法と比較して30%の性能改善を実現
• 実用化に向けた課題として、計算リソースの最適化が必要
• 今後6ヶ月以内に商用展開を予定

📊 **統計:**
• 元テキスト: 1,250文字
• 要約: 143文字 (89%圧縮)
• 処理時間: 0.8秒

🎯 **キーポイント:**
AI技術進歩、性能改善、実用化課題、商用展開計画
```

### `/analyze_url`
URL内容を分析・要約します。

**パラメータ:**
- `url` [required]: 分析したいURL
- `save_summary` (optional): 要約をObsidianに保存 (デフォルト: true)
- `analysis_depth` (optional): 分析の深度
  - `quick` - 基本情報のみ
  - `standard` - 標準分析
  - `deep` - 詳細分析

**使用例:**
```
/analyze_url url:"https://example.com/article"
/analyze_url url:"https://tech-blog.com/post" analysis_depth:deep
```

**応答例:**
```
🌐 URL分析結果

📰 **記事情報:**
• タイトル: "2025年のAI技術トレンド"
• 著者: 田中太郎
• 公開日: 2025-08-15
• 推定読了時間: 8分

📝 **要約:**
2025年のAI技術における主要なトレンドとして、生成AI、マルチモーダルAI、エッジAIの3つの分野で大きな進展が期待される。特に生成AIの実用化が加速し、様々な業界での活用が進む見込み。

🏷️ **抽出タグ:**
#ai #technology #trends #2025 #article

🔗 **関連キーワード:**
生成AI、マルチモーダル、エッジコンピューティング、機械学習

✅ **保存先:** 05_Resources/ai-trends-2025.md

⚡ **処理時間:** 2.1秒
```

## 💰 金融管理コマンド

### `/add_expense`
支出を記録します。

**パラメータ:**
- `amount` [required]: 金額 (数値)
- `description` [required]: 支出の説明
- `category` (optional): カテゴリ
- `date` (optional): 日付 (YYYY-MM-DD形式、デフォルト: 今日)
- `payment_method` (optional): 支払い方法
- `tags` (optional): 追加タグ (カンマ区切り)

**使用例:**
```
/add_expense amount:1200 description:"ランチ" category:"食費"
/add_expense amount:3500 description:"技術書購入" category:"教育" payment_method:"クレジットカード"
```

**応答例:**
```
💰 支出を記録しました

📊 **記録詳細:**
• 金額: ¥1,200
• 内容: ランチ
• カテゴリ: 食費
• 日付: 2025-08-17
• 支払い方法: 現金

📈 **今月の統計:**
• 食費合計: ¥23,400 / ¥30,000 (予算)
• 今日の支出: ¥3,200
• 今月の支出: ¥87,650

✅ **保存先:** 06_Finance/2025-08-expenses.md
```

### `/expense_report`
支出レポートを生成します。

**パラメータ:**
- `period` [required]: 期間
  - `daily` - 今日
  - `weekly` - 今週
  - `monthly` - 今月
  - `yearly` - 今年
- `category` (optional): 特定カテゴリのみ
- `chart` (optional): グラフ表示 (デフォルト: true)

**使用例:**
```
/expense_report period:monthly
/expense_report period:weekly category:"食費"
```

**応答例:**
```
📊 支出レポート: 2025年8月

💰 **総支出:** ¥87,650

📁 **カテゴリ別支出:**
• 食費: ¥28,400 (32.4%) [予算内]
• 交通費: ¥15,200 (17.3%) [予算内]
• 教育: ¥12,800 (14.6%) [予算内]
• エンタメ: ¥8,950 (10.2%) [予算内]
• その他: ¥22,300 (25.4%)

📈 **トレンド:**
• 前月比: +5.2% (¥4,340増)
• 日平均: ¥5,165
• 予算達成率: 87.7%

⚠️ **注意点:**
• エンタメ費が予算の90%に到達
• 今月残り¥12,350まで予算内

📋 **詳細レポート:** 06_Finance/2025-08-monthly-report.md
```

### `/add_subscription`
定期購入サービスを登録します。

**パラメータ:**
- `name` [required]: サービス名
- `amount` [required]: 月額料金
- `billing_date` [required]: 請求日 (1-31)
- `category` (optional): カテゴリ
- `description` (optional): 説明
- `auto_renew` (optional): 自動更新 (デフォルト: true)

**使用例:**
```
/add_subscription name:"Netflix" amount:1980 billing_date:15 category:"エンタメ"
/add_subscription name:"Adobe CC" amount:6480 billing_date:1 category:"ツール"
```

**応答例:**
```
🔄 サブスクリプションを登録しました

📝 **サービス詳細:**
• サービス名: Netflix
• 月額料金: ¥1,980
• 請求日: 毎月15日
• カテゴリ: エンタメ
• 自動更新: ON

📊 **更新された統計:**
• 月額合計: ¥18,460
• 登録サービス数: 8件
• 次回請求: Netflix (8/15, ¥1,980)

⏰ **今後の請求予定:**
• 8/15: Netflix (¥1,980)
• 8/20: Spotify (¥980)
• 9/1: Adobe CC (¥6,480)

✅ **保存先:** 06_Finance/subscriptions.md
```

## ✅ タスク管理コマンド

### `/add_task`
新しいタスクを作成します。

**パラメータ:**
- `title` [required]: タスクタイトル
- `description` (optional): タスク詳細
- `due_date` (optional): 期限 (YYYY-MM-DD形式)
- `priority` (optional): 優先度
  - `low` - 低
  - `medium` - 中 (デフォルト)
  - `high` - 高
  - `urgent` - 緊急
- `project` (optional): プロジェクト名
- `tags` (optional): タグ (カンマ区切り)

**使用例:**
```
/add_task title:"要件定義書の作成" due_date:"2025-08-20" priority:high
/add_task title:"コードレビュー" description:"新機能のPRをレビュー" project:"WebApp"
```

**応答例:**
```
✅ タスクを作成しました

📋 **タスク詳細:**
• ID: #T-001
• タイトル: 要件定義書の作成
• 期限: 2025-08-20 (3日後)
• 優先度: 🔴 高
• 状態: 未着手
• プロジェクト: WebApp

⏰ **リマインダー:**
• 期限1日前にアラート設定済み

📊 **プロジェクト統計:**
• WebApp: 5件 (未着手: 3件, 進行中: 2件)
• 全体: 12件のアクティブタスク

✅ **保存先:** 07_Tasks/task-T001-requirements.md
```

### `/list_tasks`
タスクリストを表示します。

**パラメータ:**
- `status` (optional): 状態でフィルタ
  - `pending` - 未着手
  - `in_progress` - 進行中
  - `completed` - 完了
  - `all` - 全て (デフォルト)
- `project` (optional): プロジェクトでフィルタ
- `priority` (optional): 優先度でフィルタ
- `due_soon` (optional): 期限が近いもののみ (デフォルト: false)

**使用例:**
```
/list_tasks status:pending
/list_tasks project:"WebApp" priority:high
/list_tasks due_soon:true
```

**応答例:**
```
📋 タスクリスト (未着手: 5件)

🔴 **高優先度:**
• #T-001: 要件定義書の作成 (期限: 8/20)
• #T-003: セキュリティ監査 (期限: 8/22)

🟡 **中優先度:**
• #T-005: UIデザインレビュー (期限: 8/25)
• #T-007: ドキュメント更新 (期限: なし)

🟢 **低優先度:**
• #T-009: リファクタリング検討 (期限: なし)

⚠️ **期限が近いタスク:**
• #T-001: あと3日
• #T-003: あと5日

📊 **統計:**
• 今日期限: 0件
• 今週期限: 2件
• 期限超過: 0件
```

### `/complete_task`
タスクを完了します。

**パラメータ:**
- `task_id` [required]: タスクID (#T-001 形式)
- `notes` (optional): 完了メモ
- `time_spent` (optional): 所要時間 (分)

**使用例:**
```
/complete_task task_id:"T-001" notes:"無事に完了。次はレビュー依頼"
/complete_task task_id:"T-003" time_spent:120
```

**応答例:**
```
🎉 タスクを完了しました！

✅ **完了タスク:**
• #T-001: 要件定義書の作成
• 完了日時: 2025-08-17 14:30
• 所要時間: 3時間 (推定: 4時間)
• メモ: 無事に完了。次はレビュー依頼

📈 **生産性統計:**
• 今日完了: 3件
• 今週完了: 12件
• 平均完了時間: 2.5時間

🎯 **次のタスク:**
• #T-003: セキュリティ監査 (高優先度, 期限: 8/22)

✅ **更新:** 07_Tasks/task-T001-requirements.md
```

## 🔧 システム管理コマンド

### `/backup_vault`
Obsidianボルトのバックアップを作成します。

**パラメータ:**
- `include_media` (optional): メディアファイルも含める (デフォルト: true)
- `compression` (optional): 圧縮レベル (1-9、デフォルト: 6)

**使用例:**
```
/backup_vault
/backup_vault include_media:false compression:9
```

**応答例:**
```
💾 バックアップを作成中...

✅ **バックアップ完了**

📦 **バックアップ詳細:**
• ファイル名: vault-backup-20250817-143052.zip
• サイズ: 15.2 MB (圧縮率: 67%)
• ファイル数: 239件
• 所要時間: 8.3秒

📁 **含まれる内容:**
• Markdownファイル: 234件
• 画像ファイル: 12件
• 音声ファイル: 3件
• その他: 5件

💾 **保存場所:** /app/backups/

📊 **バックアップ履歴:**
• 今日: 1回目
• 今週: 3回目
• 保持期間: 30日間
```

### `/system_metrics`
詳細なシステムメトリクスを表示します。

**パラメータ:** なし

**使用例:**
```
/system_metrics
```

**応答例:**
```
📊 システムメトリクス (詳細)

🖥️ **システムリソース:**
• CPU使用率: 12% (2コア)
• メモリ使用率: 35% (1.4GB / 4GB)
• ディスク使用率: 45% (9GB / 20GB)
• ネットワーク: 125KB/s (上り), 67KB/s (下り)

🤖 **Discord接続:**
• WebSocketレイテンシ: 87ms
• 再接続回数: 0回 (今日)
• 処理中リクエスト: 2件
• キューイング中: 0件

🧠 **AI処理統計:**
• 今日の処理数: 45/1500 (3%)
• 平均レスポンス時間: 1.23秒
• 成功率: 98.2%
• キャッシュヒット率: 78%

💾 **Obsidian操作:**
• 今日のファイル作成: 12件
• 平均ファイルサイズ: 52KB
• 保存成功率: 100%
• 検索クエリ数: 8回

⚡ **パフォーマンス (過去1時間):**
• 最速処理: 0.45秒
• 最遅処理: 3.21秒
• エラー数: 0件
• 警告数: 2件
```

### `/cache_info`
AIキャッシュの状態を確認します。

**パラメータ:** なし

**使用例:**
```
/cache_info
```

**応答例:**
```
🧠 AIキャッシュ状態

📊 **キャッシュ統計:**
• ヒット率: 78.3% (157/200件)
• サイズ: 23.4MB / 100MB (23%)
• エントリ数: 157件 / 1000件
• 平均ヒット時間: 12ms

⏰ **時間別ヒット率:**
• 過去1時間: 85%
• 過去6時間: 82%
• 過去24時間: 78%

🔄 **キャッシュ内容:**
• AI分析結果: 134件
• URL要約: 18件
• 翻訳結果: 5件

🗑️ **クリーンアップ:**
• 最終クリーンアップ: 2時間前
• 期限切れエントリ: 3件
• 自動クリーンアップ: 有効

💡 **推奨アクション:**
現在のキャッシュ状態は良好です。
```

## 📄 テンプレート管理コマンド

### `/list_templates`
利用可能なテンプレート一覧を表示します。

**パラメータ:** なし

**使用例:**
```
/list_templates
```

**応答例:**
```
📄 利用可能なテンプレート

📝 **標準テンプレート:**
• `daily_note` - デイリーノート用
• `meeting_note` - 会議議事録用
• `idea_note` - アイデアメモ用
• `task_note` - タスク詳細用
• `project_note` - プロジェクト管理用

💰 **金融テンプレート:**
• `expense_record` - 支出記録用
• `budget_plan` - 予算計画用
• `financial_review` - 財務レビュー用

📚 **学習テンプレート:**
• `learning_note` - 学習記録用
• `book_review` - 読書感想用
• `research_note` - 調査メモ用

🎯 **使用方法:**
`/create_from_template template_name:"daily_note" title:"タイトル"`

📁 **テンプレート場所:** 99_Meta/Templates/
```

### `/create_from_template`
テンプレートからノートを作成します。

**パラメータ:**
- `template_name` [required]: テンプレート名
- `title` [required]: ノートタイトル
- `variables` (optional): テンプレート変数 (JSON形式)

**使用例:**
```
/create_from_template template_name:"meeting_note" title:"週次進捗会議"
/create_from_template template_name:"project_note" title:"新機能開発" variables:'{"due_date":"2025-09-01","priority":"high"}'
```

**応答例:**
```
📄 テンプレートからノートを作成しました

✅ **作成されたノート:**
• タイトル: 週次進捗会議
• テンプレート: meeting_note
• 保存先: 01_Projects/weekly-progress-meeting.md

📝 **適用された変数:**
• date: 2025-08-17
• time: 14:30
• attendees: (未設定)
• agenda: (未設定)

🔗 **ノートリンク:**
[Obsidianで開く](obsidian://open?vault=MyVault&file=01_Projects%2Fweekly-progress-meeting.md)

💡 **次のステップ:**
Obsidianでノートを開いて、会議の詳細を記入してください。
```

## 🏃‍♂️ 健康データコマンド

### `/garmin_sync`
Garmin Connect からデータを同期します。

**パラメータ:**
- `date` (optional): 同期する日付 (YYYY-MM-DD、デフォルト: 昨日)
- `data_type` (optional): データタイプ
  - `all` - 全データ (デフォルト)
  - `activities` - アクティビティのみ
  - `sleep` - 睡眠データのみ
  - `health` - 健康指標のみ

**使用例:**
```
/garmin_sync
/garmin_sync date:"2025-08-15" data_type:activities
```

**応答例:**
```
🏃‍♂️ Garmin データ同期完了

📊 **同期されたデータ (2025-08-16):**

🏃 **アクティビティ:**
• ランニング: 5.2km, 28分, 平均心拍数 145bpm
• ウォーキング: 8,432歩

😴 **睡眠:**
• 就寝: 23:15
• 起床: 06:45
• 睡眠時間: 7時間30分
• 深い睡眠: 1時間45分 (23%)

💓 **健康指標:**
• 安静時心拍数: 58bpm
• ストレスレベル: 25 (低)
• Body Battery: 85/100

✅ **保存先:** 08_Health/2025-08-16-garmin-data.md

📈 **今週の傾向:**
• 平均歩数: 7,845歩 (目標: 8,000歩)
• 運動日数: 4/7日
• 平均睡眠: 7時間12分
```

### `/health_report`
健康データのレポートを生成します。

**パラメータ:**
- `period` [required]: 期間
  - `weekly` - 今週
  - `monthly` - 今月
  - `quarterly` - 四半期
- `focus` (optional): 焦点
  - `fitness` - フィットネス
  - `sleep` - 睡眠
  - `heart` - 心拍
  - `all` - 全体 (デフォルト)

**使用例:**
```
/health_report period:weekly
/health_report period:monthly focus:sleep
```

## 🔍 トラブルシューティングコマンド

### `/debug_info`
デバッグ情報を表示します。

**パラメータ:** なし

**使用例:**
```
/debug_info
```

**応答例:**
```
🔍 デバッグ情報

⚙️ **設定状態:**
• 環境: production
• ログレベル: INFO
• モックモード: 無効
• Secret Manager: 有効

🔗 **接続状態:**
• Discord: ✅ 接続済み
• Gemini API: ✅ 正常
• Google Speech: ✅ 正常
• Obsidian Vault: ✅ アクセス可能

📊 **チャンネル設定:**
• INBOX: 設定済み (123...678)
• VOICE: 設定済み (234...789)
• TASKS: 設定済み (345...890)
• その他: 8チャンネル設定済み

🐛 **最近のエラー:**
• エラー数 (過去1時間): 0件
• 警告数 (過去1時間): 2件
• 最新エラー: なし

🔧 **システム情報:**
• Python: 3.13.0
• discord.py: 2.3.2
• uv: 0.1.32
• 稼働時間: 2日14時間32分
```

### `/test_features`
主要機能のテストを実行します。

**パラメータ:**
- `feature` (optional): テストする機能
  - `ai` - AI処理
  - `obsidian` - Obsidian統合
  - `discord` - Discord接続
  - `all` - 全機能 (デフォルト)

**使用例:**
```
/test_features
/test_features feature:ai
```

**応答例:**
```
🧪 機能テスト実行中...

✅ **Discord接続テスト:**
• WebSocket: 正常 (87ms)
• コマンド応答: 正常
• 権限: 正常

✅ **AI処理テスト:**
• Gemini API接続: 正常
• テスト分析: 正常 (1.23s)
• キャッシュ: 正常

✅ **Obsidian統合テスト:**
• ボルトアクセス: 正常
• ファイル作成: 正常
• 検索機能: 正常

❌ **音声処理テスト:**
• Speech API: エラー (認証失敗)
• 推奨対応: Google Cloud認証を確認

📊 **テスト結果:**
• 成功: 3/4 機能
• 失敗: 1/4 機能
• 総実行時間: 5.7秒

💡 **推奨アクション:**
音声処理の認証設定を確認してください。
```

---

このコマンドリファレンスを参考に、MindBridgeの豊富な機能を活用してください。各コマンドには詳細なヘルプも用意されているので、`/help` コマンドと組み合わせてご利用ください。
