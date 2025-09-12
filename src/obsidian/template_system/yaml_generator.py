"""YAML フロントマター生成器"""

from typing import Any


class YAMLFrontmatterGenerator:
    """YAML フロントマターを生成するクラス（拡張版）"""

    # Obsidian 特有のフィールド（特別な処理が必要）
    OBSIDIAN_SPECIAL_FIELDS = {
        # Core Obsidian フィールド
        "tags",
        "aliases",
        "cssclasses",
        # 公開・共有
        "publish",
        "permalink",
        # リンク・関連性
        "links",
        "related",
        "backlinks",
        # カンバン・プロジェクト管理
        "kanban-plugin",
        "board",
        "column",
        # テンプレート・自動化
        "template",
        "automated_tags",
    }

    # 推奨される順序（実用性重視で大幅拡張）
    FIELD_ORDER = [
        # === 基本メタデータ（必須情報）===
        "title",
        "created",
        "modified",
        "date",
        # === 分類・組織化 ===
        "type",
        "category",
        "status",
        "priority",
        "importance",
        "project",
        "area",
        "phase",
        "context",
        # === コンテンツメタデータ ===
        "summary",
        "description",
        "abstract",
        "excerpt",
        "word_count",
        "reading_time",
        "difficulty_level",
        # === Obsidian 特有フィールド ===
        "tags",
        "aliases",
        "cssclasses",
        "links",
        "related",
        "backlinks",
        # === タスク・進捗管理 ===
        "due_date",
        "start_date",
        "completion_date",
        "progress",
        "estimated_hours",
        "actual_hours",
        "assignee",
        "reviewer",
        # === 知識管理・学習 ===
        "source",
        "reference",
        "author",
        "publisher",
        "publication_date",
        "isbn",
        "doi",
        "url",
        "citations",
        "learning_stage",
        "knowledge_type",
        "evidence_strength",
        "confidence_level",
        # === 財務・ビジネス ===
        "amount",
        "currency",
        "budget",
        "cost_center",
        "expense_category",
        "invoice_number",
        "receipt",
        "tax_deductible",
        "business_purpose",
        # === 健康・ライフスタイル ===
        "health_metric",
        "activity_type",
        "duration",
        "intensity",
        "calories",
        "heart_rate",
        "mood",
        "energy_level",
        "sleep_quality",
        # === AI ・自動化メタデータ ===
        "ai_confidence",
        "ai_model",
        "ai_version",
        "ai_metadata",
        "auto_generated",
        "processing_date",
        "data_quality",
        # === バージョン管理・履歴 ===
        "version",
        "revision",
        "change_log",
        "last_reviewed",
        "review_date",
        "next_review",
        "archive_date",
        # === 地理・時間情報 ===
        "location",
        "timezone",
        "coordinates",
        "weather",
        "season",
        "event_date",
        "recurring",
        # === メディア・添付ファイル ===
        "attachments",
        "images",
        "audio_files",
        "video_files",
        "file_size",
        "file_format",
        "quality",
        "duration_media",
        # === コラボレーション ===
        "collaborators",
        "shared_with",
        "permissions",
        "feedback",
        "comments",
        "discussion_link",
        "meeting_notes",
        # === カスタムフィールド（プロジェクト固有）===
        "custom_field_1",
        "custom_field_2",
        "custom_field_3",
        "template_used",
        "automation_rules",
        "sync_status",
        # === 公開・共有設定 ===
        "publish",
        "permalink",
        "public",
        "featured",
        "pinned",
    ]

    def generate_frontmatter(
        self,
        frontmatter_dict: dict[str, Any],
        include_empty: bool = False,
        sort_fields: bool = False,
        custom_template: dict[str, str] | None = None,
    ) -> str:
        """
        辞書から YAML フロントマターを生成

        Args:
            frontmatter_dict: フロントマターの内容を含む辞書
            include_empty: 空の値を含めるかどうか
            sort_fields: フィールドをソートするかどうか
            custom_template: カスタムテンプレート設定

        Returns:
            YAML 形式のフロントマター文字列
        """
        if not frontmatter_dict:
            return ""

        # 空の値を除外（ include_empty が False の場合）
        if not include_empty:
            frontmatter_dict = {
                key: value
                for key, value in frontmatter_dict.items()
                if value is not None and value != "" and value != [] and value != {}
            }

        if not frontmatter_dict:
            return ""

        # 前処理：日付フォーマットや特殊な値の変換
        processed_dict = self._preprocess_values(frontmatter_dict, custom_template)

        # フィールドの順序を決定
        ordered_items = self._order_fields(processed_dict, sort_fields)

        # YAML 形式で出力
        yaml_lines = ["---"]

        for key, value in ordered_items:
            yaml_lines.append(self._format_yaml_field(key, value))

        yaml_lines.append("---")

        return "\n".join(yaml_lines)

    def _preprocess_values(
        self,
        frontmatter_dict: dict[str, Any],
        custom_template: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        値の前処理を行う（日付フォーマット、特殊な値の変換など）
        """
        from datetime import date, datetime

        processed: dict[str, Any] = {}

        for key, value in frontmatter_dict.items():
            # カスタムテンプレートの適用
            if custom_template and key in custom_template:
                template_format = custom_template[key]
                if isinstance(value, datetime | date):
                    processed[key] = value.strftime(template_format)
                else:
                    processed[key] = template_format.format(value=value)
                continue

            # 日付の自動フォーマット
            if isinstance(value, datetime):
                processed[key] = value.strftime("%Y-%m-%d %H:%M:%S")
            elif isinstance(value, date):
                processed[key] = value.strftime("%Y-%m-%d")
            # タグの正規化
            elif key == "tags" and isinstance(value, str):
                # 文字列の場合は配列に変換
                processed[key] = [tag.strip() for tag in value.split(",")]
            # エイリアスの正規化
            elif key == "aliases" and isinstance(value, str):
                processed[key] = [alias.strip() for alias in value.split(",")]
            # 数値型の自動処理
            elif key in [
                "word_count",
                "reading_time",
                "estimated_hours",
                "actual_hours",
                "amount",
                "calories",
            ]:
                if isinstance(value, str):
                    try:
                        # 整数として解析を試行
                        if key in ["word_count", "calories"]:
                            processed[key] = int(float(value))
                        else:
                            processed[key] = float(value)
                    except (ValueError, TypeError):
                        processed[key] = value
                else:
                    processed[key] = value
            # 論理値の正規化
            elif key in [
                "publish",
                "public",
                "featured",
                "pinned",
                "tax_deductible",
                "auto_generated",
            ]:
                if isinstance(value, str):
                    processed[key] = value.lower() in ["true", "yes", "1", "on"]
                else:
                    processed[key] = bool(value)
            # URL の正規化
            elif key in ["url", "permalink", "discussion_link"]:
                if isinstance(value, str) and value:
                    # HTTP/HTTPS がない場合は追加しない（相対パスの可能性）
                    processed[key] = value.strip()
                else:
                    processed[key] = value
            else:
                processed[key] = value

        return processed

    def _order_fields(
        self, frontmatter_dict: dict[str, Any], sort_fields: bool
    ) -> list[tuple[str, Any]]:
        """
        フィールドの順序を決定する
        """
        if sort_fields:
            return sorted(frontmatter_dict.items())

        # 推奨順序を使用してフィールドを並べ替え
        ordered_items = []
        remaining_items = dict(frontmatter_dict)

        # 推奨順序のフィールドを最初に追加
        for field in self.FIELD_ORDER:
            if field in remaining_items:
                ordered_items.append((field, remaining_items.pop(field)))

        # 残りのフィールドをアルファベット順で追加
        for key, value in sorted(remaining_items.items()):
            ordered_items.append((key, value))

        return ordered_items

    def create_comprehensive_frontmatter(
        self,
        title: str,
        content_type: str = "memo",
        ai_result=None,
        content: str = "",
        context: dict[str, Any] | None = None,
        **kwargs,
    ) -> str:
        """
        包括的で実用的なフロントマターを生成する高度なメソッド

        Args:
            title: ノートタイトル
            content_type: コンテンツタイプ（ memo, task, knowledge, project など）
            ai_result: AI 分析結果
            content: ノート本文（分析用）
            context: 追加コンテキスト情報
            **kwargs: その他のメタデータ

        Returns:
            包括的なフロントマター
        """
        import re
        from datetime import datetime

        frontmatter: dict[str, Any] = {
            "title": title,
            "created": datetime.now(),
            "type": content_type,
        }

        # コンテンツ分析による自動メタデータ生成
        if content:
            # 文字数とおおよその読了時間
            word_count = len(content.split())
            frontmatter["word_count"] = word_count
            frontmatter["reading_time"] = max(
                1, word_count // 200
            )  # 分あたり 200 語として計算

            # 難易度レベル（文章の複雑さに基づく簡易判定）
            avg_word_length = sum(len(word) for word in content.split()) / max(
                1, word_count
            )
            if avg_word_length > 6:
                frontmatter["difficulty_level"] = "advanced"
            elif avg_word_length > 4:
                frontmatter["difficulty_level"] = "intermediate"
            else:
                frontmatter["difficulty_level"] = "basic"

            # URL の自動抽出
            urls = re.findall(r"https?://[^\s]+", content)
            if urls:
                frontmatter["reference"] = urls[:3]  # 最大 3 つまで

            # 金額の自動抽出（財務関連の場合）
            amounts = re.findall(r"[¥$€£]\s?(\d+(?:,\d+)*(?:\.\d+)?)", content)
            if amounts:
                try:
                    frontmatter["amount"] = float(amounts[0].replace(",", ""))
                    frontmatter["currency"] = "JPY" if "¥" in content else "USD"
                except ValueError:
                    pass

        # AI 結果の統合
        if ai_result:
            ai_frontmatter = self._extract_comprehensive_ai_data(ai_result)
            frontmatter.update(ai_frontmatter)

        # コンテキスト情報の統合
        if context:
            # Discord 特有の情報
            if context.get("source") == "Discord":
                frontmatter["source"] = "Discord"
                if context.get("channel_name"):
                    frontmatter["context"] = f"Discord #{context['channel_name']}"
                if context.get("message_id"):
                    frontmatter["discord_message_id"] = context["message_id"]

            # 音声メモの情報
            if context.get("is_voice_memo", False):
                frontmatter["input_method"] = "voice"
                if context.get("transcription_confidence"):
                    frontmatter["transcription_confidence"] = context[
                        "transcription_confidence"
                    ]
                if context.get("audio_duration"):
                    frontmatter["duration"] = context["audio_duration"]

            # 位置情報
            if context.get("location"):
                frontmatter["location"] = context["location"]

            # 時間情報
            if context.get("timezone"):
                frontmatter["timezone"] = context["timezone"]

        # コンテンツタイプ別の特別な処理
        type_specific = self._generate_type_specific_metadata(
            content_type, content, ai_result
        )
        if type_specific:
            frontmatter.update(type_specific)

        # 追加のキーワード引数を統合
        frontmatter.update(kwargs)

        return self.generate_frontmatter(frontmatter)

    def _extract_comprehensive_ai_data(self, ai_result) -> dict[str, Any]:
        """AI 分析結果から包括的なメタデータを抽出"""
        ai_data = {}

        # 基本的な AI 情報
        if hasattr(ai_result, "category") and ai_result.category:
            # CategoryResult オブジェクトの場合、 category.category.value でアクセス
            if hasattr(ai_result.category, "category") and hasattr(
                ai_result.category.category, "value"
            ):
                category_value = ai_result.category.category.value
                ai_data["category"] = category_value.lower()
                ai_data["type"] = self._map_category_to_type(category_value)
            else:
                # 文字列の場合はそのまま使用
                category_value = str(ai_result.category).lower()
                ai_data["category"] = category_value
                ai_data["type"] = self._map_category_to_type(category_value)

        if hasattr(ai_result, "summary") and ai_result.summary:
            # SummaryResult オブジェクトの場合、 summary.summary でアクセス
            if hasattr(ai_result.summary, "summary"):
                ai_data["summary"] = ai_result.summary.summary
            else:
                ai_data["summary"] = str(ai_result.summary)

        if hasattr(ai_result, "tags") and ai_result.tags:
            # TagsResult オブジェクトの場合、 tags.tags でアクセス
            if hasattr(ai_result.tags, "tags"):
                ai_data["tags"] = ai_result.tags.tags
            else:
                ai_data["tags"] = ai_result.tags

        # 感情・ムード情報の取得
        if hasattr(ai_result, "sentiment") and ai_result.sentiment:
            ai_data["mood"] = ai_result.sentiment

        # エンティティ情報の取得
        if hasattr(ai_result, "entities") and ai_result.entities:
            ai_data["entities"] = ai_result.entities

        # 信頼度の取得 - 複数のパターンに対応
        confidence_score = None

        # パターン1: ai_result.category.confidence_score
        if (
            hasattr(ai_result, "category")
            and ai_result.category
            and hasattr(ai_result.category, "confidence_score")
        ):
            confidence_score = ai_result.category.confidence_score
        # パターン2: ai_result.confidence
        elif hasattr(ai_result, "confidence") and ai_result.confidence is not None:
            confidence_score = ai_result.confidence
        # パターン3: ai_result.confidence_score
        elif (
            hasattr(ai_result, "confidence_score")
            and ai_result.confidence_score is not None
        ):
            confidence_score = ai_result.confidence_score

        # 信頼度を設定
        if confidence_score is not None:
            ai_data["ai_confidence"] = round(float(confidence_score), 2)
            # 信頼度に基づくデータ品質
            if confidence_score >= 0.9:
                ai_data["data_quality"] = "high"
            elif confidence_score >= 0.7:
                ai_data["data_quality"] = "medium"
            else:
                ai_data["data_quality"] = "low"

        # AI結果から直接重要度を取得（テスト対応）
        if hasattr(ai_result, "importance") and ai_result.importance:
            ai_data["importance"] = str(ai_result.importance).lower()
        else:
            # 重要度・優先度の設定（カテゴリベースで推定）
            if "category" in ai_data:
                category = ai_data["category"]
                # カテゴリから重要度を推定
                if category in ["tasks", "finance", "health"]:
                    ai_data["importance"] = "high"
                    ai_data["priority"] = "high"
                elif category in ["knowledge", "projects"]:
                    ai_data["importance"] = "medium"
                    ai_data["priority"] = "normal"
                else:
                    ai_data["importance"] = "low"
                    ai_data["priority"] = "low"

        # 優先度は重要度から自動設定（まだ設定されていない場合）
        if "importance" in ai_data and "priority" not in ai_data:
            importance_to_priority = {
                "critical": "urgent",
                "high": "high",
                "medium": "normal",
                "low": "low",
            }
            ai_data["priority"] = importance_to_priority.get(
                ai_data["importance"], "low"
            )

        # AI モデル情報 - AI結果から取得、なければデフォルト値
        if hasattr(ai_result, "model_version") and ai_result.model_version:
            ai_data["ai_model"] = ai_result.model_version
        elif hasattr(ai_result, "model") and ai_result.model:
            ai_data["ai_model"] = ai_result.model
        else:
            ai_data["ai_model"] = "gemini-pro"

        # 分析日時（現在時刻を設定）
        from datetime import datetime

        ai_data["processing_date"] = datetime.now()

        return ai_data

    def _generate_type_specific_metadata(
        self, content_type: str, content: str = "", ai_result=None
    ) -> dict[str, Any]:
        """コンテンツタイプ別の特別なメタデータを生成"""
        metadata: dict[str, Any] = {}

        if content_type == "task":
            metadata["status"] = "pending"
            metadata["progress"] = 0
            # 締切日の自動抽出を試行
            import re

            date_patterns = [
                r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})",  # YYYY-MM-DD or YYYY/MM/DD
                r"(\d{1,2}[-/]\d{1,2}[-/]\d{4})",  # MM-DD-YYYY or MM/DD/YYYY
            ]
            for pattern in date_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    metadata["due_date"] = matches[0]
                    break

        elif content_type == "knowledge":
            metadata["knowledge_type"] = "factual"
            metadata["learning_stage"] = "new"
            if ai_result and hasattr(ai_result, "confidence"):
                if ai_result.confidence >= 0.9:
                    metadata["evidence_strength"] = "strong"
                elif ai_result.confidence >= 0.7:
                    metadata["evidence_strength"] = "moderate"
                else:
                    metadata["evidence_strength"] = "weak"

        elif content_type == "project":
            metadata["phase"] = "planning"
            metadata["status"] = "active"

        elif content_type == "finance":
            metadata["expense_category"] = "uncategorized"
            metadata["tax_deductible"] = False
            # 通貨の検出
            if "¥" in content:
                metadata["currency"] = "JPY"
            elif "$" in content:
                metadata["currency"] = "USD"
            elif "€" in content:
                metadata["currency"] = "EUR"

        elif content_type == "health":
            metadata["health_metric"] = "general"
            # 活動タイプの推定
            activity_keywords = {
                "running": ["run", "jog", "ランニング", "走"],
                "walking": ["walk", "ウォーキング", "歩"],
                "cycling": ["bike", "cycle", "サイクリング", "自転車"],
                "swimming": ["swim", "水泳", "泳"],
                "gym": ["gym", "workout", "ジム", "筋トレ"],
            }
            content_lower = content.lower()
            for activity, keywords in activity_keywords.items():
                if any(keyword in content_lower for keyword in keywords):
                    metadata["activity_type"] = activity
                    break

        elif content_type == "daily":
            from datetime import date

            metadata["date"] = date.today()
            metadata["template_used"] = "daily_template"
            metadata["automated_tags"] = ["daily", "journal"]

        return metadata

    def create_note_frontmatter(
        self,
        title: str,
        note_type: str = "memo",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        ノート用の標準的なフロントマターを生成する便利メソッド
        """
        from datetime import datetime

        frontmatter = {
            "title": title,
            "created": datetime.now(),
            "type": note_type,
        }

        if tags:
            frontmatter["tags"] = tags

        if metadata:
            frontmatter.update(metadata)

        return self.generate_frontmatter(frontmatter)

    def create_daily_note_frontmatter(self, date_obj=None) -> str:
        """
        デイリーノート用のフロントマターを生成する便利メソッド
        """
        from datetime import date, datetime

        if date_obj is None:
            date_obj = date.today()

        frontmatter = {
            "title": f"Daily Note - {date_obj.strftime('%Y-%m-%d')}",
            "type": "daily",
            "date": date_obj,
            "created": datetime.now(),
            "tags": ["daily", "journal"],
            "template_used": "daily_template",
            "automated_tags": ["daily", "journal"],
        }

        return self.generate_frontmatter(frontmatter)

    def create_ai_enhanced_frontmatter(
        self,
        title: str,
        ai_result=None,
        source: str = "Discord",
        additional_metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        AI 分析結果を統合した高度なフロントマターを生成

        Args:
            title: ノートのタイトル
            ai_result: AI 分析結果 (AIProcessingResult)
            source: データソース
            additional_metadata: 追加のメタデータ

        Returns:
            AI 分析を反映した YAML フロントマター
        """
        return self.create_comprehensive_frontmatter(
            title=title,
            ai_result=ai_result,
            context={"source": source},
            **(additional_metadata or {}),
        )

    def _map_category_to_type(self, category: str) -> str:
        """
        カテゴリから Obsidian ノートタイプにマッピング
        """
        category_lower = category.lower()
        mapping = {
            "tasks": "task",
            "ideas": "idea",
            "knowledge": "knowledge",
            "projects": "project",
            "finance": "finance",
            "health": "health",
            "dailynotes": "daily",
            "archive": "archive",
            "resources": "resource",
        }
        return mapping.get(category_lower, "memo")

    def _get_category_tag(self, category: str) -> str | None:
        """
        カテゴリに基づく推奨タグを取得
        """
        category_lower = category.lower()
        tag_mapping = {
            "tasks": "task",
            "ideas": "idea",
            "knowledge": "learning",
            "projects": "project",
            "finance": "money",
            "health": "health",
            "dailynotes": "daily",
            "archive": "archive",
            "resources": "reference",
        }
        return tag_mapping.get(category_lower)

    def create_obsidian_enhanced_frontmatter(
        self,
        title: str,
        content: str = "",
        vault_path: str | None = None,
        ai_result=None,
        **kwargs,
    ) -> str:
        """
        Obsidian 固有機能を活用した高度なフロントマターを生成

        Args:
            title: ノートタイトル
            content: ノート本文（バックリンク抽出用）
            vault_path: Obsidian ボルトパス（既存ノート検索用）
            ai_result: AI 分析結果
            **kwargs: 追加オプション

        Returns:
            Obsidian 最適化された YAML フロントマター
        """
        from datetime import datetime

        frontmatter = {
            "title": title,
            "created": datetime.now(),
        }

        # AI 結果の統合
        if ai_result:
            ai_frontmatter = self._extract_ai_frontmatter(ai_result)
            frontmatter.update(ai_frontmatter)

        # バックリンクの自動抽出
        if content:
            links = self._extract_wikilinks(content)
            if links:
                frontmatter["links"] = sorted(list(set(links)))

        # 既存ノートとの関連性分析
        if vault_path and content:
            related_notes = self._find_related_notes(content, vault_path)
            if related_notes:
                frontmatter["related"] = related_notes[:5]  # 上位 5 件

        # Obsidian 特有のメタデータ
        obsidian_meta = self._generate_obsidian_metadata(title, content, **kwargs)
        if obsidian_meta:
            frontmatter.update(obsidian_meta)

        # 追加オプションの統合
        frontmatter.update(kwargs)

        return self.generate_frontmatter(frontmatter)

    def _extract_ai_frontmatter(self, ai_result) -> dict[str, Any]:
        """AI 分析結果からフロントマター要素を抽出"""
        ai_data = {}

        if hasattr(ai_result, "category") and ai_result.category:
            # CategoryResult オブジェクトの場合、 category.category.value でアクセス
            if hasattr(ai_result.category, "category") and hasattr(
                ai_result.category.category, "value"
            ):
                category_value = ai_result.category.category.value
                ai_data["category"] = category_value.lower()
                ai_data["type"] = self._map_category_to_type(category_value)
            else:
                # 文字列の場合はそのまま使用
                category_value = str(ai_result.category).lower()
                ai_data["category"] = category_value
                ai_data["type"] = self._map_category_to_type(category_value)

        if hasattr(ai_result, "summary") and ai_result.summary:
            # SummaryResult オブジェクトの場合、 summary.summary でアクセス
            if hasattr(ai_result.summary, "summary"):
                ai_data["summary"] = ai_result.summary.summary
            else:
                ai_data["summary"] = str(ai_result.summary)

        if hasattr(ai_result, "tags") and ai_result.tags:
            # TagsResult オブジェクトの場合、 tags.tags でアクセス
            if hasattr(ai_result.tags, "tags"):
                ai_data["tags"] = ai_result.tags.tags
            else:
                ai_data["tags"] = ai_result.tags

        if hasattr(ai_result, "confidence") and ai_result.confidence is not None:
            ai_data["ai_confidence"] = round(ai_result.confidence, 2)

        return ai_data

    def _extract_wikilinks(self, content: str) -> list[str]:
        """
        コンテンツから Wikilink 形式のリンクを抽出
        [[Link]] や [[Link|Display]] 形式をサポート
        """
        import re

        # Wikilink パターン: [[ページ名]] または [[ページ名|表示名]]
        pattern = r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]"
        matches = re.findall(pattern, content)

        # リンクをクリーンアップ
        links = []
        for match in matches:
            clean_link = match.strip()
            if clean_link and clean_link not in links:
                links.append(clean_link)

        return links

    def _find_related_notes(self, content: str, vault_path: str) -> list[str]:
        """
        コンテンツの類似性に基づいて関連ノートを検索
        簡易的なキーワードベース検索を実装
        """
        import os

        if not os.path.exists(vault_path):
            return []

        # コンテンツからキーワードを抽出
        keywords = self._extract_keywords(content)
        if not keywords:
            return []

        related_notes = []

        try:
            # .md ファイルを検索
            for root, _dirs, files in os.walk(vault_path):
                for file in files:
                    if file.endswith(".md"):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, encoding="utf-8") as f:
                                file_content = f.read()

                            # キーワードマッチング
                            matches = sum(
                                1
                                for keyword in keywords
                                if keyword.lower() in file_content.lower()
                            )
                            if matches >= 2:  # 2 つ以上のキーワードがマッチ
                                note_name = os.path.splitext(file)[0]
                                related_notes.append((note_name, matches))

                        except (UnicodeDecodeError, PermissionError):
                            continue
        except Exception:
            return []

        # マッチ数でソートし、ノート名のみ返す
        related_notes.sort(key=lambda x: x[1], reverse=True)
        return [note[0] for note in related_notes[:5]]

    def _extract_keywords(self, content: str, min_length: int = 3) -> list[str]:
        """コンテンツから重要なキーワードを抽出"""
        import re
        from collections import Counter

        # 日本語と英語の単語を分けて処理
        keywords = []

        # 英語の単語を抽出（小文字に変換）
        english_words = re.findall(r"\b[a-zA-Z]+\b", content.lower())
        keywords.extend([word for word in english_words if len(word) >= min_length])

        # 日本語の単語を抽出（カタカナ、ひらがな、漢字）
        japanese_pattern = r"[ぁ-んァ-ヶー一-龯]+"
        japanese_words = re.findall(japanese_pattern, content)
        keywords.extend([word for word in japanese_words if len(word) >= min_length])

        # ストップワード（簡易版）
        stopwords = {
            "the",
            "is",
            "at",
            "which",
            "on",
            "and",
            "or",
            "but",
            "if",
            "then",
            "with",
            "for",
            "from",
            "about",
            "が",
            "の",
            "を",
            "に",
            "は",
            "で",
            "と",
            "から",
            "まで",
            "より",
            "です",
            "である",
            "します",
            "して",
            "した",
            "する",
            "ます",
            "ました",
            "について",
        }

        # フィルタリング
        filtered_keywords = [
            word
            for word in keywords
            if len(word) >= min_length and word not in stopwords
        ]

        # 重複を除去し、頻度順で上位を選択
        word_freq = Counter(filtered_keywords)
        return [word for word, count in word_freq.most_common(10)]

    def _generate_obsidian_metadata(
        self, title: str, content: str, **kwargs
    ) -> dict[str, Any]:
        """Obsidian 特有のメタデータを生成"""
        import re

        metadata: dict[str, Any] = {}

        # CSS クラスの設定（コンテンツ長に基づく）
        if content:
            content_length = len(content)
            if content_length > 2000:
                metadata["cssclasses"] = ["long-form"]
            elif content_length < 200:
                metadata["cssclasses"] = ["short-note"]

        # 公開設定（オプション）
        if kwargs.get("auto_publish", False):
            metadata["publish"] = True

        # パーマリンク（タイトルベース）
        if kwargs.get("generate_permalink", False):
            permalink = re.sub(r"[^\w\s-]", "", title.lower())
            permalink = re.sub(r"[-\s]+", "-", permalink).strip("-")
            if permalink:
                metadata["permalink"] = f"/{permalink}"

        return metadata

    def _format_yaml_field(self, key: str, value: Any, indent: int = 0) -> str:
        """
        単一の YAML フィールドをフォーマット

        Args:
            key: フィールド名
            value: 値
            indent: インデント レベル

        Returns:
            フォーマットされた YAML フィールド文字列
        """
        indent_str = "  " * indent

        if isinstance(value, list):
            if not value:
                return f"{indent_str}{key}: []"

            # Obsidian 特有のフィールドの特別処理
            if key in self.OBSIDIAN_SPECIAL_FIELDS:
                return self._format_obsidian_list_field(key, value, indent)

            lines = [f"{indent_str}{key}:"]
            for item in value:
                if isinstance(item, str | int | float | bool):
                    lines.append(f"{indent_str}  - {self._format_yaml_value(item)}")
                else:
                    lines.append(f"{indent_str}  - {item}")
            return "\n".join(lines)

        elif isinstance(value, dict):
            if not value:
                return f"{indent_str}{key}: {{}}"

            lines = [f"{indent_str}{key}:"]
            for sub_key, sub_value in value.items():
                lines.append(self._format_yaml_field(sub_key, sub_value, indent + 1))
            return "\n".join(lines)

        else:
            formatted_value = self._format_yaml_value(value)
            return f"{indent_str}{key}: {formatted_value}"

    def _format_obsidian_list_field(
        self, key: str, value: list, indent: int = 0
    ) -> str:
        """
        Obsidian 特有のリストフィールドをフォーマット
        """
        indent_str = "  " * indent

        # タグの場合は階層タグをサポート
        if key == "tags":
            formatted_tags = []
            for tag in value:
                # 階層タグの処理（#を含む場合）
                if isinstance(tag, str):
                    clean_tag = tag.lstrip("#").strip()
                    if clean_tag:
                        formatted_tags.append(clean_tag)

            if not formatted_tags:
                return f"{indent_str}{key}: []"

            lines = [f"{indent_str}{key}:"]
            for tag in formatted_tags:
                lines.append(f"{indent_str}  - {tag}")
            return "\n".join(lines)

        # その他の特殊フィールドは通常の配列として処理
        lines = [f"{indent_str}{key}:"]
        for item in value:
            lines.append(f"{indent_str}  - {self._format_yaml_value(item)}")
        return "\n".join(lines)

    def _format_yaml_value(self, value: Any) -> str:
        """
        YAML 値を適切な形式でフォーマット

        Args:
            value: フォーマットする値

        Returns:
            フォーマットされた値の文字列
        """
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, str):
            # 空文字列の場合
            if value == "":
                return '""'

            # 日付形式の判定（YYYY-MM-DD HH:MM:SS など）
            import re

            date_pattern = r"^\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2}(:\d{2})?)?$"
            if re.match(date_pattern, value.strip()):
                # 日付形式の場合はクォートなしで出力
                return value

            # 特殊文字や改行を含む文字列は引用符で囲む
            needs_quotes = (
                "\n" in value
                or ":" in value
                or value.startswith(("#", "-", "[", "{"))
                or value.strip() != value
                or value in ("true", "false", "null", "yes", "no", "on", "off")
                # 数値のような文字列も引用符で囲む
                or self._looks_like_number(value)
            )

            if needs_quotes:
                # 改行を含む場合はリテラル形式を使用
                if "\n" in value:
                    lines = value.split("\n")
                    return "|\n" + "\n".join(f"  {line}" for line in lines)
                else:
                    return f'"{value}"'
            else:
                return value
        else:
            return str(value)

    def _looks_like_number(self, value: str) -> bool:
        """文字列が数値のように見えるかチェック"""
        if not value:
            return False
        try:
            float(value)
            return True
        except ValueError:
            return False
