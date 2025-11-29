# YAML フロントマターガイド

Obsidian ノートの先頭に付与されるメタデータの仕様です。スキーマは `src/obsidian/models.py` の `NoteFrontmatter` が定義します。

## いつ付くか
- Discord の投稿/添付/音声を処理したとき
- Garmin / Calendar など外部連携で日次ノートやレポートを生成したとき
- `DailyNoteIntegration` やタスク・家計モジュールがサマリーを更新したとき

`TemplateEngine` が Pydantic モデルを YAML にシリアライズし、Markdown 本文と合わせて書き出します。

## 主なフィールド
| グループ | フィールド | 型 | 役割 |
| --- | --- | --- | --- |
| Discord | `discord_message_id`, `discord_channel`, `discord_author`, `discord_timestamp`, `discord_guild` | `int/str` | 投稿元の情報 |
| AI | `ai_processed`, `ai_processing_time`, `ai_summary`, `ai_tags`, `ai_category`, `ai_subcategory`, `ai_confidence` | 各種 | 要約・分類結果 |
| ノート管理 | `created`, `modified`, `status`, `obsidian_folder`, `source_type`, `vault_hierarchy`, `organization_level` | `str` 等 | 保存場所や状態 |
| タグ/表示 | `tags`, `aliases`, `cssclass` | `list[str]` / `str` | 手動タグ・エイリアス・表示用クラス |
| 統計 | `total_messages`, `processed_messages`, `ai_processing_time_total`, `categories` | `int/dict` | 日次集計などに利用 |

> `ai_tags` には自動で `#` が付与されます。手動タグは `tags` に `#` なしで入れてください。

## 生成例
```yaml
---
discord_message_id: 1234567890
discord_channel: memo
discord_author: user#1234
discord_timestamp: 2025-03-21T10:15:32+09:00
ai_processed: true
ai_summary: >-
  6時間30分の睡眠。深い睡眠が不足しているため、就寝前のストレッチを推奨。
ai_tags:
  - "#健康ログ"
  - "#睡眠"
ai_category: health
created: 2025-03-21T10:15:32+09:00
status: active
obsidian_folder: 21_Health/sleep
source_type: discord_message
tags: [health, sleep]
---
```

## カスタマイズのコツ
- フォルダは `VaultFolder` Enum から選ぶと階層が揃います。
- 新しいメタデータが欲しいときは `NoteFrontmatter` にフィールドを追加し、テンプレートとシリアライザも更新してください。
- 日時はタイムゾーン付き ISO 形式を推奨。欠けると UTC 扱いになる場合があります。
- Obsidian 上で手動編集する場合はリストや数値を文字列化しないよう注意。

関連コード: `src/obsidian/models.py`, `src/obsidian/template_system/`, `src/bot/handlers/note_handler.py`。
