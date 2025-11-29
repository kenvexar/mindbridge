# 基本的な使い方

Discord に投稿するだけでノート化されます。ここでは挙動の概要と主要コマンドだけをコンパクトにまとめます。

## 入力すると何が起きるか
1. 監視チャンネルの投稿を `MessageProcessor` が整形（メンション・コードブロック・URL・添付の整理）。
2. `AIProcessor` / `AdvancedNoteAnalyzer` が要約・タグ・カテゴリ分類を実施。
3. `TemplateEngine` が YAML フロントマター付き Markdown を組み立て、`ObsidianFileManager` が Vault に保存。
4. `DailyNoteIntegration` が日次ノートへ統計や関連リンクを反映。

## 投稿の種類ごとの動き
- **テキストのみ**: 要約・タグ付けし、メンションやコードを整形して本文に残す。
- **URL を含む投稿**: `url_processor` がタイトル/メタ情報/要約を取得して末尾に追記し、重複 URL はハッシュで抑止。
- **ファイル添付**: `80_Attachments/` に保存し、本文へ埋め込みリンクを追加。拡張子やサイズなども YAML に記録。
- **音声ファイル**: Google Speech-to-Text が設定されていれば文字起こし＋要約を追加。未設定ならファイルだけ保存し `pending` と記録。

## Slash コマンド（抜粋）
- `/status` — 接続状態・監視チャンネル・起動時刻
- `/help` — 利用可能コマンドの一覧
- `/search query:<語> limit:<件>` — Vault 全文検索
- `/random` — ランダムなノートのプレビュー
- `/bot` / `/obsidian` — ランタイムと Vault の統計

**設定系**
- `/integration_status` — 外部連携の状態
- `/manual_sync integration:<name>` — 即時同期
- `/integration_config` — 連携設定の参照・保存
- `/scheduler_status` — スケジューラのジョブ状況

**タスク/家計**
- `/task_add`, `/task_list`, `/task_done`, `/task_progress`
- `/finance_help`, `/expense_add`, `/income_add`, `/subscription_add`, `/finance_summary`

**カレンダー/ガーミン**
- `/calendar_auth`, `/calendar_token`, `/calendar_test`
- `/garmin_today`, `/garmin_sleep`

> Slash コマンドはギルド専用同期です。Bot 再起動直後は反映まで数秒〜数十秒かかることがあります。

## Prefix コマンド（ライフログ）
`!` プレフィックスで呼び出すテキストコマンドです。
- `!log <category> <content>` — ライフログ追加（自然文を解析）
- `!mood <1-5> [メモ]` — 気分スコア
- `!habit <create|done|list|status> ...` — 習慣管理
- `!goal <create|update|list|status> ...` — 目標管理

## 困ったときの確認ポイント
- 応答が遅い: `/system_status` で Integration Manager / Scheduler の状態を確認。
- チャンネルを変えたい: `src/bot/channel_config.py` を編集後、再起動。
- 外部 API を呼びたくない: `.env` に `ENABLE_MOCK_MODE=true` と各 `MOCK_*_ENABLED` を設定。
