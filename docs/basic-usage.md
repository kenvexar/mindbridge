# 基本的な使用方法

Discord でメッセージを送るだけで、MindBridge が Obsidian ノートを生成し、必要に応じて統計や外部連携を実行します。このドキュメントでは利用時の挙動と主要コマンドをまとめます。

## Discord からの入力

### テキストメッセージ
- `#memo` など監視対象チャンネルへ投稿すると、`MessageProcessor` がメタデータを抽出し、`AIProcessor` が要約・タグ・カテゴリを推定します。
- AI が付与したタグは `ai_tags` として、手動タグは `tags` として YAML に保存されます。
- メッセージ内のメンションやコードブロックも解析され、ノート本文に整形されます。

### URL を含むメッセージ
- `url_processor` がリンク先を取得し、タイトル・メタデータ・要約をノート末尾に追記します。
- 同じ URL はハッシュ化して重複保存を防ぎます。

### ファイル添付
- 画像・ドキュメントは `80_Attachments/` 以下に保存され、ノート本文へ埋め込みリンクを追加します。
- 添付ファイルのメタデータ（拡張子・サイズ・スレッド情報など）も YAML に記録されます。

### 音声ファイル
- MP3 / WAV / FLAC / OGG / M4A / WEBM に対応。
- Google Cloud Speech-to-Text が利用可能な場合は自動で文字起こしし、要約を生成。
- 認証情報が無い場合はファイルを保存して「未処理」ステータスでノート化し、再処理待ちにします。

## ノート生成と自動処理
- `TemplateEngine` が YAML フロントマターと本文レイアウトを組み立てます。フィールド詳細は `docs/yaml-front-matter.md` を参照。
- `DailyNoteIntegration` が日次サマリーに統合し、統計値（件数やカテゴリ別カウント）を更新します。
- `AdvancedNoteAnalyzer` が既存ノートとの類似度を計算し、関連ノートセクションを生成する設定も可能です。
- ライフログ候補と判断したメッセージは `LifelogHandler` が自動ハイライトを追加します。
- GitHub バックアップが有効な場合、起動時/終了時に Vault を push/pull します。

## Slash コマンド一覧

**基本操作**
- `/help` – 利用可能なコマンドの概要を表示。
- `/status` – Bot の接続状態・監視チャンネル・起動時刻を確認。
- `/search query:<キーワード> limit:<件数>` – Obsidian ノート全文検索（最大 50 件）。
- `/random` – ランダムなノートのプレビューを表示。

**設定関連**
- `/show [setting]` – 設定値を参照（現在は検出チャンネルの一覧などを返答）。
- `/set setting:<キー> value:<値>` – 設定値の更新リクエスト（安全な範囲で適用）。
- `/history` – 設定変更履歴（履歴が無い場合はガイドメッセージを返す）。

**統計ダッシュボード**
- `/bot` – 稼働時間、レイテンシー、メモリ使用量、参加サーバー数を表示。
- `/obsidian` – Vault のノート数、今日日数、平均サイズ、更新日時など。
- `/finance` – 家計データの集計とカテゴリ別ハイライト。
- `/tasks` – タスク全体の完了率、期限切れ数、平均完了日数など。

**家計管理**
- `/finance_help` – 家計機能で利用できるコマンドのヘルプ。
- `/expense_add` – 支出を追加（カテゴリ・メモ対応）。
- `/income_add` – 収入を追加。
- `/expense_list` – 直近の支出やフィルタ済み支出を一覧表示。
- `/subscription_add` – 定期購入を登録し、金額や頻度を保存。
- `/subscription_list` – 登録済み定期購入を一覧表示。
- `/finance_summary` – 月次/年次サマリーとアクティブ契約の統計。

**タスク管理**
- `/task_add` – 優先度・期限・タグ付きのタスクを作成。
- `/task_update` – 進捗率とメモを更新。
- `/task_done` – タスクを完了ステータスに変更。
- `/task_list` – アクティブ/完了タスクをフィルタ表示。
- `/schedule_add` – 繰り返しタスクやリマインダーを登録。
- `/task_stats` – タスクの完了率や平均作業時間を集計。

**外部連携・ライフログ**
- `/integration_status` – 登録済み連携の状態と直近同期結果。
- `/system_status` – Bot、Integration Manager、Scheduler の状態まとめ。
- `/manual_sync integration:<名前> force:<bool>` – 指定連携の即時同期。
- `/integration_config` – 各連携の設定を確認・保存。
- `/scheduler_status` – 自動同期スケジューラのジョブ状況。
- `/lifelog_stats` – ライフログのカテゴリ別統計と最近のエントリ。
- `/calendar_auth` – Google Calendar OAuth URL を発行。
- `/calendar_token code:<認証コード>` – OAuth で取得したコードを登録。
- `/calendar_test` – Calendar 連携の接続テスト。
- `/garmin_today` – Garmin の本日アクティビティとメトリクスを表示。
- `/garmin_sleep` – ガーミン睡眠データの詳細レポート。

> Slash コマンドはギルド専用同期です。Bot を再起動した直後は反映まで数秒〜数十秒かかる場合があります。

## Prefix コマンド（ライフログ）
`LifelogCommands` はプレフィックス `!` を利用したテキストコマンドを提供します。

- `!log <category> <content>` – ライフログエントリを追加。気分や場所などを含む自然文を解析します。
- `!mood <1-5> [description]` – 当日の気分スコアを記録。
- `!habit <create|done|list|status> ...` – 習慣トラッキングの追加・完了チェック。
- `!goal <create|update|list|status> ...` – 目標管理と進捗更新。

Prefix コマンドは Bot の接頭辞設定に依存するため、ギルド側でブロックされていないことを確認してください。

## 補足
- コマンドの応答が遅い場合は `/system_status` で Integration Manager / Scheduler の状態を確認するか、ログ (`logs/`) を参照してください。
- チャンネルを追加・変更する場合は `ChannelConfig`（`src/bot/channel_config.py`）の設定を更新し、Bot を再起動します。
