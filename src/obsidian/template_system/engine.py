"""Main template engine combining all template system components"""

from datetime import datetime
from pathlib import Path
from typing import Any

from .base import GeneratedNote
from .generator import NoteGenerator
from .loader import TemplateLoader
from .processor import TemplateProcessor
from .validator import TemplateValidator


class TemplateEngine:
    """統合テンプレートエンジン - すべての機能を統合"""

    def __init__(self, vault_path: str | Path):
        self.vault_path = Path(vault_path)
        self.template_loader = TemplateLoader(self.vault_path)
        self.template_processor = TemplateProcessor()
        self.note_generator = NoteGenerator(self.template_processor)
        self.validator = TemplateValidator()

    @property
    def template_path(self) -> Path:
        """Template directory path for backward compatibility"""
        return self.template_loader.template_path

    async def generate_note_from_content(
        self,
        template_name: str,
        content: str,
        author: str = "unknown",
        channel: str = "general",
        timestamp: datetime | None = None,
        additional_context: dict[str, Any] | None = None,
    ) -> GeneratedNote:
        """コンテンツからノートを生成"""
        if timestamp is None:
            timestamp = datetime.now()

        # 基本コンテキストを作成
        base_context = await self.create_template_context(
            content=content, author=author, channel=channel, timestamp=timestamp
        )

        # 追加コンテキストがある場合は統合
        if additional_context:
            # 追加コンテキストの値で基本コンテキストを更新
            base_context.update(additional_context)
            # タイムスタンプが datetime オブジェクトの場合は ISO 形式に変換
            if isinstance(base_context.get("timestamp"), datetime):
                base_context["timestamp"] = base_context["timestamp"].isoformat()

        template = await self.template_loader.load_template(template_name)
        return await self.note_generator.generate_message_note(
            template, content, author, channel, timestamp, base_context
        )

    async def generate_daily_note(
        self,
        template_name: str = "daily_note",
        date: datetime | None = None,
        tasks: list[Any] | None = None,
    ) -> GeneratedNote:
        """デイリーノートを生成"""
        if date is None:
            date = datetime.now()

        template = await self.template_loader.load_template(template_name)
        return await self.note_generator.generate_daily_note(template, date, tasks)

    async def create_template_context(
        self,
        content: str | None = None,
        author: str | None = None,
        channel: str | None = None,
        timestamp: datetime | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        title: str | None = None,
        summary: str | None = None,
        mood: str | None = None,
        weather: str | None = None,
        location: str | None = None,
        additional_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """テンプレートコンテキストを作成"""
        if timestamp is None:
            timestamp = datetime.now()

        context = {
            "content": content or "",
            "author": author or "unknown",
            "channel": channel or "general",
            "category": category or "general",
            "tags": tags or [],
            "title": title or "",
            "summary": summary or "",
            "mood": mood or "",
            "weather": weather or "",
            "location": location or "",
            "timestamp": timestamp.isoformat(),
            "date": timestamp.strftime("%Y-%m-%d"),
            "time": timestamp.strftime("%H:%M:%S"),
            "year": timestamp.year,
            "month": timestamp.month,
            "day": timestamp.day,
            "hour": timestamp.hour,
            "minute": timestamp.minute,
            "weekday": timestamp.strftime("%A"),
            "weekday_jp": self._get_japanese_weekday(timestamp),
            "month_name": timestamp.strftime("%B"),
            "month_name_jp": self._get_japanese_month(timestamp),
            "week_number": timestamp.isocalendar()[1],
            "day_of_year": timestamp.timetuple().tm_yday,
            "vault_path": str(self.vault_path),
            "current_date": timestamp.strftime("%Y-%m-%d"),
        }

        if additional_metadata:
            context.update(additional_metadata)

        return context

    async def _create_fallback_note(
        self, content: str, timestamp: datetime
    ) -> GeneratedNote:
        """フォールバックノートを作成"""
        fallback_template = f"""---
created: {timestamp.isoformat()}
tags: [memo, fallback]
---

# メモ

{content}
"""
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_memo.md"
        return GeneratedNote(
            filename=filename, content=fallback_template, frontmatter=None
        )

    async def render_template(
        self, template_name_or_content: str, context: dict[str, Any]
    ) -> tuple[str, Any]:
        """テンプレートをレンダリング (名前または直接コンテンツ)"""
        # Backward compatibility: if content looks like template content (contains {{), render directly
        if "{{" in template_name_or_content:
            return await self.template_processor.render_template(
                template_name_or_content, context
            )
        else:
            # Template name - load from file
            template = await self.template_loader.load_template(
                template_name_or_content
            )
            return await self.template_processor.render_template(template, context)

    async def compile_template(self, template: str, context: dict[str, Any]) -> str:
        """Legacy API: compile template and return content only"""
        compiled_content, _ = await self.template_processor.render_template(
            template, context
        )
        return compiled_content

    async def render_template_content_only(
        self, template_name_or_content: str, context: dict[str, Any]
    ) -> str:
        """Backward compatibility: return content only for tests"""
        compiled_content, _ = await self.render_template(
            template_name_or_content, context
        )
        return compiled_content

    async def validate_template(
        self, template_name_or_content: str, context: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """テンプレートを検証 (名前または直接コンテンツ)"""
        # Backward compatibility: if content looks like template content, validate directly
        if "{{" in template_name_or_content:
            return await self.validator.validate_template(
                template_name_or_content, context
            )
        else:
            # Template name - load from file
            template = await self.template_loader.load_template(
                template_name_or_content
            )
            return await self.validator.validate_template(template, context)

    async def list_available_templates(self) -> list[str]:
        """利用可能なテンプレート一覧を取得"""
        template_dir = self.template_loader.template_path
        if not template_dir.exists():
            return []

        templates = []
        for file in template_dir.glob("*.md"):
            templates.append(file.stem)

        return sorted(templates)

    def _format_value(self, value: Any) -> str:
        """Format value for template rendering - backward compatibility method"""
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        return str(value)

    def ensure_template_directory(self) -> bool:
        """Ensure template directory exists - backward compatibility"""
        self.template_loader.template_path.mkdir(parents=True, exist_ok=True)
        return self.template_loader.template_path.exists()

    @property
    def cached_templates(self) -> dict[str, str]:
        """Access to cached templates - backward compatibility"""
        return self.template_loader.cached_templates

    def _parse_template_content(
        self, template: str
    ) -> tuple[dict[str, Any] | None, str]:
        """Parse template content into frontmatter and body - backward compatibility"""
        import re

        frontmatter_match = re.match(
            r"^---\s*\n(.*?)\n---\s*\n(.*)$", template, re.DOTALL
        )

        if frontmatter_match:
            frontmatter_content = frontmatter_match.group(1)
            body_content = frontmatter_match.group(2)
            # Enhanced YAML-like parsing to handle multiline lists
            frontmatter = {}
            current_key = None
            for line in frontmatter_content.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if ":" in line and not line.startswith("-"):
                    key, value = line.split(":", 1)
                    current_key = key.strip()
                    value = value.strip()
                    if value:
                        frontmatter[current_key] = value
                    else:
                        # Multiline value starts (like YAML lists)
                        frontmatter[current_key] = ""
                elif line.startswith("-") and current_key:
                    # YAML list item
                    list_item = line[1:].strip()
                    if frontmatter[current_key] == "":
                        frontmatter[current_key] = list_item
                    else:
                        frontmatter[current_key] += f", {list_item}"
            return frontmatter, body_content
        else:
            return None, template

    async def load_template(self, template_name: str) -> str:
        """テンプレートを読み込み"""
        return await self.template_loader.load_template(template_name)

    async def create_default_templates(self) -> bool:
        """デフォルトテンプレートを作成"""
        template_dir = self.template_loader.template_path
        template_dir.mkdir(parents=True, exist_ok=True)

        default_templates = {
            "base_note": """---
created: {{ timestamp }}
type: {{ type | default:"note" }}
tags: {{ tags | join:", " | default:"note" }}
---

# {{ title | default:"ノート" }}

{{ content }}
""",
            "daily_note": """---
created: {{ timestamp }}
date: {{ date }}
weekday: {{ weekday_jp }}
tags: [daily, {{ year }}, {{ month_name_jp }}]
---

# {{ date_full }}（{{ weekday_jp }}）

## 今日のタスク

{{ if tasks }}
{{ each task in tasks }}
- [ ] {{ task }}
{{ endeach }}
{{ else }}
- [ ] 新しいタスクを追加
{{ endif }}

## 今日の振り返り

### 良かったこと


### 改善点


### 明日への課題


## メモ


---
*作成日時: {{ timestamp }}*
""",
            "idea_note": """---
created: {{ timestamp }}
type: idea
tags: [idea, {{ category | default:"general" }}]
---

# 💡 {{ title | default:"アイデア" }}

## 概要
{{ content }}

## 詳細


## 関連リンク


## アクション項目
- [ ]
""",
            "meeting_note": """---
created: {{ timestamp }}
type: meeting
attendees: {{ attendees | join:", " }}
tags: [meeting, {{ project | default:"general" }}]
---

# 📝 {{ title | default:"会議メモ" }}

**日時:** {{ date }} {{ time }}
**参加者:** {{ attendees | join:", " }}

## アジェンダ
{{ agenda | default:"" }}

## 議事録
{{ content }}

## アクション項目
{{ if action_items }}
{{ each item in action_items }}
- [ ] {{ item }}
{{ endeach }}
{{ else }}
- [ ]
{{ endif }}
""",
            "task_note": """---
created: {{ timestamp }}
type: task
priority: {{ priority | default:"medium" }}
status: {{ status | default:"todo" }}
tags: [task, {{ category | default:"general" }}]
---

# ✅ {{ title | default:"タスク" }}

## 説明
{{ content }}

## 優先度
{{ priority | default:"medium" }}

## ステータス
{{ status | default:"todo" }}

{{ if due_date }}
## 期限
{{ due_date }}
{{ endif }}

## 進捗メモ
""",
            "voice_memo": """---
created: {{ timestamp }}
type: voice_memo
duration: {{ duration | default:"" }}
tags: [voice, memo, {{ category | default:"general" }}]
---

# 🎤 {{ title | default:"音声メモ" }}

**録音日時:** {{ date }} {{ time }}
{{ if duration }}**長さ:** {{ duration }}{{ endif }}

## 内容
{{ content }}

{{ if transcript }}
## 文字起こし
{{ transcript }}
{{ endif }}
""",
            "project_note": """---
created: {{ timestamp }}
type: project
status: {{ status | default:"active" }}
tags: [project, {{ category | default:"work" }}]
---

# 🚀 {{ title | default:"プロジェクト" }}

## 概要
{{ content }}

## 目標
{{ if goals }}
{{ each goal in goals }}
- {{ goal }}
{{ endeach }}
{{ else }}
-
{{ endif }}

## 進捗
{{ if progress }}
{{ progress }}
{{ else }}
開始前
{{ endif }}

## 次のステップ
- [ ]
""",
            "media_note": """---
created: {{ timestamp }}
type: media
media_type: {{ media_type | default:"unknown" }}
source: {{ source | default:"" }}
tags: [media, {{ category | default:"reference" }}]
---

# 📎 {{ title | default:"メディアメモ" }}

{{ if source }}**ソース:** {{ source }}{{ endif }}
**タイプ:** {{ media_type | default:"unknown" }}

## 内容
{{ content }}

{{ if notes }}
## メモ
{{ notes }}
{{ endif }}
""",
            "high_confidence": """---
created: {{ timestamp }}
confidence: high
reviewed: false
tags: [high_confidence, {{ category | default:"general" }}]
---

# ✨ {{ title | default:"高信頼度メモ" }}

{{ content }}

---
*AI 信頼度: 高*
""",
            "review_required": """---
created: {{ timestamp }}
confidence: low
reviewed: false
requires_review: true
tags: [review_required, {{ category | default:"general" }}]
---

# ⚠️ {{ title | default:"要確認メモ" }}

{{ content }}

---
*要確認: このメモは人間による確認が必要です*
""",
        }

        created_count = 0
        for template_name, template_content in default_templates.items():
            template_file = template_dir / f"{template_name}.md"
            if not template_file.exists():
                with open(template_file, "w", encoding="utf-8") as f:
                    f.write(template_content)
                created_count += 1

        return created_count > 0

    async def generate_note_from_template(
        self, template_name: str, context: dict[str, Any]
    ) -> GeneratedNote:
        """テンプレートからノートを生成"""
        template = await self.template_loader.load_template(template_name)

        is_valid, errors = await self.validator.validate_template(template, context)
        if not is_valid:
            timestamp = datetime.now()
            fallback_content = context.get("content", "エラーのためフォールバック")
            return await self._create_fallback_note(fallback_content, timestamp)

        compiled_content, frontmatter = await self.template_processor.render_template(
            template, context
        )

        # Generate filename based on context
        timestamp = datetime.fromisoformat(
            context.get("timestamp", datetime.now().isoformat())
        )
        author = context.get("author", "unknown")
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{author}.md"

        return GeneratedNote(
            filename=filename, content=compiled_content, frontmatter=frontmatter
        )

    def _get_japanese_weekday(self, date: datetime) -> str:
        """日本語の曜日を取得"""
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        return weekdays[date.weekday()]

    def _get_japanese_month(self, date: datetime) -> str:
        """日本語の月名を取得"""
        return f"{date.month}月"
