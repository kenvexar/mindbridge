# YAML フロントマターガイド

MindBridge が Obsidian ノートを生成するとき、先頭に YAML フロントマターを付与してメタデータを管理します。`src/obsidian/models.py` の `NoteFrontmatter` モデルがスキーマを定義しており、テンプレートや外部連携でも共通して利用されます。

---

## 1. 生成タイミング

- Discord メッセージ（テキスト / 添付 / 音声）を処理してノートを作成する場合
- Garmin / Google Calendar など外部連携で日次ノートやレポートを生成する場合
- `DailyNoteIntegration` やタスク・家計モジュールがサマリーを更新する場合

`TemplateEngine` は `NoteFrontmatter` を Pydantic モデルとして受け取り、YAML 文字列へシリアライズします。

---

## 2. フィールド一覧

| グループ | フィールド | 型 | 説明 |
| --- | --- | --- | --- |
| Discord メタデータ | `discord_message_id` | `int | null` | 元メッセージ ID |
|  | `discord_channel` | `str | null` | チャンネル名 |
|  | `discord_author` / `discord_author_id` | `str | int | null` | 投稿者表示名 / ID |
|  | `discord_timestamp` | `str | null` | ISO8601 形式の投稿時刻 |
|  | `discord_guild` | `str | null` | サーバー名 |
| AI 情報 | `ai_processed` | `bool` | AI 処理が完了したか（既定: `false`） |
|  | `ai_processing_time` | `int | null` | AI 処理時間（ミリ秒） |
|  | `ai_summary` | `str | null` | Gemini による要約 |
|  | `ai_tags` | `list[str]` | `#` 付きタグ（自動で `#` を付与） |
|  | `ai_category` / `ai_subcategory` | `str | null` | カテゴリ/サブカテゴリ |
|  | `ai_confidence` | `float | null` | 分類信頼度 |
| ノート管理 | `created` / `modified` | `str` | ISO8601 日時。未指定の場合は現在時刻で初期化。 |
|  | `status` | `NoteStatus` | `active`, `archived`, `draft`, `template` |
|  | `obsidian_folder` | `str` | 保存先フォルダ。`VaultFolder` Enum を参照。 |
|  | `source_type` | `str` | 生成元（例: `discord_message`, `garmin_sync`） |
|  | `vault_hierarchy` / `organization_level` | `str | null` | 任意の階層ラベル |
| タグ/表示 | `tags` | `list[str]` | 手動タグ (`#` なしで記録し、Obsidian 側で `#` 表示) |
|  | `aliases` | `list[str]` | Obsidian のエイリアス |
|  | `cssclass` | `str | null` | Obsidian のカスタム CSS クラス（既定: `discord-note`） |
| 統計 | `total_messages` | `int | null` | 日次処理のメッセージ数など |
|  | `processed_messages` | `int | null` | 処理済みメッセージ数 |
|  | `ai_processing_time_total` | `int | null` | 当日の AI 処理累計（ミリ秒） |
|  | `categories` | `dict[str, int] | null` | カテゴリ別件数 |

> **メモ**: Pydantic のバリデータにより、`created` / `modified` に `datetime` オブジェクトを渡しても自動で ISO8601 文字列に変換されます。

---

## 3. 生成例

```yaml
---
discord_message_id: DISCORD_MESSAGE_ID_PLACEHOLDER
discord_channel: memo
discord_author: user#1234
discord_author_id: DISCORD_AUTHOR_ID_PLACEHOLDER
discord_timestamp: 2025-03-21T10:15:32+09:00
discord_guild: MindBridge Lab
ai_processed: true
ai_processing_time: 842
ai_summary: >-
  6時間30分の睡眠。深い睡眠が不足しているため、就寝前のストレッチを推奨。
ai_tags:
  - "#健康ログ"
  - "#睡眠"
ai_category: health
ai_subcategory: sleep
ai_confidence: 0.82
created: 2025-03-21T10:15:32+09:00
modified: 2025-03-21T10:16:10+09:00
status: active
obsidian_folder: 21_Health/sleep
source_type: discord_message
vault_hierarchy: health/sleep/daily
organization_level: personal
tags:
  - health
  - sleep
aliases: []
cssclass: discord-note
total_messages: 12
processed_messages: 12
ai_processing_time_total: 5320
categories:
  sleep: 8
  exercise: 2
  nutrition: 2
---
```

本文はテンプレートで定義されます。`TemplateEngine` の既定レイアウトは以下のように組み立てられます。

```markdown
# {title}

{content}
```

テンプレートは `vault/90_Meta/Templates/` に保存したカスタムファイルに差し替え可能です。

---

## 4. カスタマイズのベストプラクティス

- **フォルダ管理**: `obsidian_folder` は `VaultFolder` Enum（`src/obsidian/models.py`）から選ぶと構成が統一されます。
- **タグ整合性**: 手動タグは `tags`（`#` なし）、AI タグは `ai_tags`（自動で `#` 付与）。重複を避けるため両方を確認してください。
- **ステータス遷移**: `status` を更新する場合は Enum (`NoteStatus`) を変更し、フィルタビューに活用します。
- **追加フィールド**: 新しいメタデータが必要な場合は `NoteFrontmatter` モデルへフィールドを追加し、テンプレートとシリアライザを更新します。未定義のキーは読み込み時に破棄されます。
- **タイムゾーン**: 日時は `datetime.isoformat()`（タイムゾーン付き）で記録することを推奨します。タイムゾーンが欠けると解析時に UTC と解釈される可能性があります。
- **手動編集時の注意**: Obsidian 上で YAML を編集しても構いませんが、リストや数値を文字列化しないようにしてください（例: `tags: ["task", "daily"]`）。

---

## 5. 関連モジュール

- `src/obsidian/models.py` – `NoteFrontmatter`, `VaultFolder`, `NoteStatus` の定義。
- `src/obsidian/template_system/` – テンプレート管理と YAML シリアライズ。
- `src/bot/handlers/note_handler.py` – Discord メッセージからフロントマターを構築するロジック。
- `docs/basic-usage.md` – ノート生成時に含まれる情報の概要。

フロントマターを適切に保守することで、Vault 内の自動整理・検索・可視化が安定します。新しいフィールドを導入した際は必ずこのドキュメントと関連モジュールを更新してください。
