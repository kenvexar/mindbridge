# YAML フロントマターガイド

## 概要

MindBridge では Discord で受信したメッセージや外部連携データを Obsidian ノートへ書き出す際、YAML フロントマターを最初に配置してメタデータを管理します。`---` で囲まれた領域にノートの属性・処理状況・格納先フォルダなどを記述し、後続の自動整理・検索・統計に活用します。

## 自動生成されるタイミング

- Discord メッセージを取り込んでノート化する際（テキスト／音声／添付の各パス）
- 外部サービス連携（Garmin 等）から生成したノートを保存する際
- Daily Note やタスク集計ノートなど、テンプレートエンジンが Markdown を生成する際

これらのケースでは `src/obsidian/models.py` の `NoteFrontmatter` モデルが中心となり、`src/obsidian/core/file_operations.py` が YAML 形式へシリアライズします。

## 主なフィールド

### Discord 由来のメタデータ
- `discord_message_id` (int): 元メッセージの ID。
- `discord_channel` (str): 投稿チャンネル名。
- `discord_author` (str) / `discord_author_id` (int): 投稿者情報。
- `discord_timestamp` (str): ISO8601 形式の送信時刻。
- `discord_guild` (str): サーバー名。

### AI 処理結果
- `ai_processed` (bool): Gemini などの AI 処理が完了したか。
- `ai_processing_time` (int): ミリ秒単位の処理時間。
- `ai_summary` (str): AI が生成した要約。
- `ai_tags` (list[str]): `#` 付きで正規化された AI 推奨タグ。
- `ai_category` / `ai_subcategory` (str): 自動分類結果。
- `ai_confidence` (float): 分類・要約に対する信頼度。

### Obsidian 管理情報
- `created` / `modified` (str): ISO8601（タイムゾーン付）の作成・更新時刻。空欄の場合は自動で現在時刻に補完されます。
- `status` (str): `active` / `archived` / `draft` / `template` のいずれか。`NoteStatus` Enum を参照してください。
- `obsidian_folder` (str): ノートを配置する Vault 内フォルダ。`VaultFolder` Enum の値を利用すると整理が揃います。
- `source_type` (str): 生成元の識別子（既定値は `discord_message`）。
- `vault_hierarchy` / `organization_level` (str): 階層構造やワークフロー管理用の追加メタデータ。

### タグ・表示に関する情報
- `tags` (list[str]): 手動タグ。保存時に `#` を除去し、Obsidian 側で `#タグ` として扱いやすい形式に整形します。
- `aliases` (list[str]): Obsidian のエイリアス機能に渡されます。
- `cssclass` (str): Obsidian のカスタム CSS 用クラス。既定は `discord-note`。

### 統計フィールド（主に Daily Note 用）
- `total_messages` / `processed_messages` (int): 日次処理の集計値。
- `ai_processing_time_total` (int): 当日の AI 処理合計時間（ミリ秒）。
- `categories` (dict[str, int]): カテゴリ別件数。
- 専用の統計フィールドを使いたい場合は、`NoteFrontmatter` へフィールドを追加してからテンプレート側で値を設定してください。

### 音声文字起こしノートのフィールド例

- `type` (str): ノートの種別。ワークフローやビューごとの振り分けに利用します。
- `category` (str): 件名の分類。タスクやメモなど用途別の集計・検索に役立ちます。
- `status` (str): 進行状況。`pending` などの値でダッシュボード上のフィルタリングに使用します。
- `priority` (str): 優先度レベル。`low` / `medium` / `high` などで処理順を判断できます。
- `importance` (str): 重要度。優先度と組み合わせてリストのソートに活用します。
- `context` (str): 発生場所やチャネルのメモ。`Discord #channel` の形式で残すと出典が明確になります。
- `summary` (str): 要約文。音声起点の内容でも主要ポイントをすぐ把握できます。複数行の場合は YAML のブロック表記 (`|` や `>-`) が自動適用されます。
- `word_count` (int): 本文の語数。読了時間やボリューム指標に使えます。
- `reading_time` (int): 想定読了時間（分）。ビューでの負荷見積りに便利です。
- `difficulty_level` (str): 内容の難易度。レビュー担当をアサインするときの補助情報になります。
- `tags` (list[str]): 手動タグ。音声などの性質をキーワードで絞り込む際に使用します。
- `progress` (int | float): タスクの進捗率。`0` は未着手、100 で完了など運用に合わせた値を保存します。
- `source` (str): 情報の取得元。`Discord` や `Garmin` など、後からデータ経路を追跡しやすくなります。
- `ai_confidence` (float): AI 推論の信頼度。数値が低い場合は手動確認の優先度を上げる判断材料になります。
- `ai_model` (str): 利用したモデル名。`gemini-pro` などを記録することで再現性を担保できます。
- `auto_generated` (bool): AI やバッチ処理で生成されたかを示すフラグ。手動入力と区別する際に参照します。
- `processing_date` (str): 処理日付。バッチ処理スケジュールとの突き合わせに使います。
- `data_quality` (str): データ品質評価。`high` や `low` などで検証対象を絞り込めます。
- `input_method` (str): 入力手段。`voice` や `text` など、取り込み経路の分析に便利です。
- `processing_timestamp` (str): 実際に処理が完了したタイムスタンプ。タイムゾーンを含む ISO8601 形式 (`2025-10-04T20:47:20+09:00` など) で記録すると後段処理が安定します。
- `vault_section` (str): Obsidian Vault 内の保存フォルダ。`02_Tasks` などのセクション名で整理されます。



## YAML レイアウト例

```yaml
---
discord_message_id: DISCORD_MESSAGE_ID_PLACEHOLDER
discord_channel: memo
discord_author: user#1234
discord_author_id: DISCORD_AUTHOR_ID_PLACEHOLDER
discord_timestamp: 2024-05-20T07:32:11+09:00
discord_guild: MindBridge Lab
ai_processed: true
ai_processing_time: 842
ai_summary: >-
  6時間30分の睡眠。深い睡眠が不足気味なため、就寝前のストレッチを推奨。
ai_tags: [#健康ログ, #睡眠]
ai_category: health
ai_subcategory: sleep
ai_confidence: 0.82
created: 2024-05-20T07:32:11+09:00
modified: 2024-05-20T07:34:02+09:00
status: active
obsidian_folder: 21_Health/sleep
source_type: discord_message
vault_hierarchy: health/sleep/daily
organization_level: personal
tags: [health, sleep]
aliases: []
cssclass: discord-note
---

# TEST: 朝の睡眠ログ

本文...
```

> `ai_summary` のような複数行テキストは YAML の `>-` ブロック表記に自動変換されます。リストは `[value1, value2]` の形式で格納され、空リストの場合はフィールドごと出力されません。

## 編集・カスタマイズのベストプラクティス

- `---` で囲む構造を崩さないでください。先頭・末尾の区切りが欠けると後段のパーサーが失敗します。
- 時刻フィールドは `2024-05-20T07:34:02+09:00` のように ISO8601 で記述します。秒以下やタイムゾーンが欠けると正しく解釈できない場合があります。
- `tags` は `#` を付けずに記述し、AI 生成タグとの重複を避けると整理しやすくなります。`ai_tags` は自動的に `#` 付きへ正規化されるため手で書く場合も同じ形式を維持してください。
- `obsidian_folder` は `src/obsidian/models.py` の `VaultFolder` に定義された値を使うとフォルダ構造が崩れません。存在しないフォルダを指定すると新規フォルダとして作成されますが、運用ポリシーに沿っているか確認してください。
- `status` の値は Enum に合わせて小文字で揃えます。新しいステータスを導入する際はコード側でも Enum を更新する必要があります。
- 追加のカスタムメタデータを永続化したい場合は `NoteFrontmatter` モデルへフィールドを定義してください。モデルに存在しないキーは読み込み時に破棄されます。
- 手動編集した Markdown を MindBridge に再インポートするときは、リストや数値が文字列になっていないか（`"123"` など）を確認してください。型が合わない場合は自動変換で `None` になることがあります。

## トラブルシューティング

- フロントマターの解析エラーは `logs/` 以下に出力され、`Failed to parse YAML frontmatter` などのメッセージで確認できます。
- フィールド欠落によりノートが INBOX に移動する場合は、`obsidian_folder` が空のまま生成されていないか確認してください。
- YAML の整形崩れが疑われるときは `uv run pytest tests/unit/test_yaml_generator.py` を実行し、テンプレート生成に問題がないか確認できます。

このドキュメントは YAML フロントマターを手動調整する際のリファレンスとして活用してください。
