"""
Advanced note analyzer with semantic search and AI-powered features
"""

import re
from datetime import datetime
from typing import Any, Union

from src.ai.mock_processor import MockAIProcessor
from src.ai.processor import AIProcessor
from src.ai.url_processor import URLContentExtractor
from src.ai.vector_store import SemanticSearchResult, VectorStore
from src.obsidian.file_manager import ObsidianFileManager
from src.utils.mixins import LoggerMixin

# Settings loaded lazily to avoid circular imports


class AdvancedNoteAnalyzer(LoggerMixin):
    """高度なノート分析システム"""

    def __init__(
        self,
        obsidian_file_manager: "ObsidianFileManager",
        ai_processor: Union["AIProcessor", "MockAIProcessor"],
    ):
        """
        初期化

        Args:
            obsidian_file_manager: Obsidian ファイルマネージャー
            ai_processor: AI 処理システム
        """
        self.file_manager = obsidian_file_manager
        self.ai_processor = ai_processor

        # コンポーネントの初期化
        self.vector_store = VectorStore(
            obsidian_file_manager=obsidian_file_manager, ai_processor=ai_processor
        )
        self.url_extractor = URLContentExtractor()

        # 設定
        self.max_related_notes = 10
        self.min_similarity_threshold = 0.3
        self.max_internal_links = 5

        self.logger.info("Advanced note analyzer initialized")

    async def analyze_note_content(
        self,
        content: str,
        title: str,
        file_path: str | None = None,
        include_url_processing: bool = True,
        include_related_notes: bool = True,
        discord_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        ノート内容の包括的な分析

        Args:
            content: ノート内容
            title: ノートタイトル
            file_path: ファイルパス（オプション）
            include_url_processing: URL 処理を含むかどうか
            include_related_notes: 関連ノート分析を含むかどうか
            discord_metadata: Discord由来のメタデータ（チャンネル情報など）

        Returns:
            分析結果
        """
        try:
            self.logger.info(
                "Starting comprehensive note analysis",
                title=title,
                content_length=len(content),
                file_path=file_path,
                has_discord_metadata=bool(discord_metadata),
            )

            analysis_results = {}

            # 0. Discord メタデータを活用した分類分析
            if discord_metadata:
                discord_analysis = await self._analyze_discord_context(
                    content, discord_metadata
                )
                analysis_results["discord_analysis"] = discord_analysis

            # 1. URL 内容処理と要約
            if include_url_processing:
                url_results = await self._process_urls_in_content(content)
                analysis_results["url_processing"] = url_results

                # URL 要約をコンテンツに統合
                if url_results.get("summaries"):
                    content = await self._integrate_url_summaries(
                        content, url_results["summaries"]
                    )

            # 2. 関連ノート分析
            related_notes = []
            if include_related_notes:
                related_notes = await self._find_related_notes(
                    content, exclude_file=file_path
                )
                analysis_results["related_notes"] = {
                    "results": [
                        {
                            "file_path": note.file_path,
                            "title": note.title,
                            "similarity_score": note.similarity_score,
                            "content_preview": note.content_preview,
                        }
                        for note in related_notes
                    ]
                }

            # 3. 内部リンク提案
            internal_links = []
            if related_notes:
                internal_links = await self._generate_internal_links(
                    content, related_notes
                )
                analysis_results["internal_links"] = {"suggestions": internal_links}

            # 4. コンテンツの最終統合
            enhanced_content = await self._enhance_content_with_links(
                content,
                internal_links,
                analysis_results.get("url_processing", {}),
                discord_metadata,
            )
            analysis_results["enhanced_content"] = {"content": enhanced_content}

            # 5. ベクトルストアにノートを追加（新規ノートの場合）
            if file_path and enhanced_content:
                await self._add_to_vector_store(file_path, title, enhanced_content)

            analysis_results.update(
                {
                    "original_content": {"content": content},
                    "title": {"value": title},
                    "file_path": {"path": file_path or ""},
                    "analyzed_at": {"timestamp": datetime.now().isoformat()},
                    "content_stats": self._get_content_stats(content),
                }
            )

            self.logger.info(
                "Note analysis completed",
                title=title,
                related_notes_count=len(related_notes),
                internal_links_count=len(internal_links),
                urls_processed=len(
                    analysis_results.get("url_processing", {}).get("processed_urls", [])
                ),
                has_discord_context=bool(discord_metadata),
            )

            return analysis_results

        except Exception as e:
            self.logger.error(
                "Failed to analyze note content",
                title=title,
                error=str(e),
                exc_info=True,
            )
            return {
                "error": str(e),
                "title": title,
                "file_path": file_path,
                "analyzed_at": datetime.now().isoformat(),
            }

    async def search_related_notes(
        self, query: str, limit: int = 10, min_similarity: float = 0.1
    ) -> list[dict[str, Any]]:
        """
        関連ノートを検索

        Args:
            query: 検索クエリ
            limit: 結果数制限
            min_similarity: 最小類似度

        Returns:
            検索結果
        """
        try:
            results = await self.vector_store.search_similar_notes(
                query_text=query, limit=limit, min_similarity=min_similarity
            )

            return [
                {
                    "file_path": result.file_path,
                    "title": result.title,
                    "similarity_score": result.similarity_score,
                    "content_preview": result.content_preview,
                    "metadata": result.metadata,
                }
                for result in results
            ]

        except Exception as e:
            self.logger.error("Failed to search related notes", error=str(e))
            return []

    async def rebuild_vector_index(self, force: bool = False) -> dict[str, Any]:
        """
        ベクトルインデックスを再構築

        Args:
            force: 強制再構築

        Returns:
            再構築結果
        """
        try:
            self.logger.info("Starting vector index rebuild", force=force)

            start_time = datetime.now()
            await self.vector_store.build_index(force_rebuild=force)
            end_time = datetime.now()

            duration = (end_time - start_time).total_seconds()
            stats = await self.vector_store.get_embedding_stats()

            result = {
                "success": True,
                "duration_seconds": duration,
                "stats": stats,
                "rebuilt_at": end_time.isoformat(),
            }

            self.logger.info(
                "Vector index rebuild completed",
                duration=duration,
                embeddings=stats.get("total_embeddings", 0),
            )

            return result

        except Exception as e:
            self.logger.error(
                "Failed to rebuild vector index", error=str(e), exc_info=True
            )
            return {
                "success": False,
                "error": str(e),
                "attempted_at": datetime.now().isoformat(),
            }

    async def _process_urls_in_content(self, content: str) -> dict[str, Any]:
        """コンテンツ内の URL を処理"""
        try:
            # URL を抽出・処理
            url_results = await self.url_extractor.process_urls_in_text(
                content, max_urls=3
            )

            if not url_results.get("processed_urls"):
                return url_results

            # 各 URL の内容を要約
            summaries = []
            for url_data in url_results["processed_urls"]:
                try:
                    summary = await self.ai_processor.summarize_url_content(
                        url_data["url"], url_data["content"]
                    )

                    if summary:
                        summaries.append(
                            {
                                "url": url_data["url"],
                                "title": url_data["title"],
                                "summary": summary,
                                "original_content_length": url_data["content_length"],
                            }
                        )

                except Exception as e:
                    self.logger.warning(
                        "Failed to summarize URL content",
                        url=url_data["url"],
                        error=str(e),
                    )

            url_results["summaries"] = summaries
            return url_results

        except Exception as e:
            self.logger.error("Failed to process URLs in content", error=str(e))
            return {"error": str(e)}

    async def _integrate_url_summaries(
        self, content: str, summaries: list[dict[str, Any]]
    ) -> str:
        """URL 要約をコンテンツに統合（有効な URL がない場合はスキップ）"""
        try:
            if not summaries:
                return content

            # 既存の URL 要約セクションをチェックして重複を避ける
            if "## 📎 URL 要約" in content:
                self.logger.debug(
                    "URL 要約セクションが既に存在するため、スキップします"
                )
                return content

            # 有効な要約のみをフィルタリング
            valid_summaries = []
            for summary_data in summaries:
                summary_text = summary_data.get("summary", "").strip()
                url = summary_data.get("url", "").strip()

                # 有効な URL かチェック（ Discord 無効リンクなどを除外）
                is_valid_url = (
                    url
                    and not url.endswith("/channels/")  # Discord 無効リンク
                    and "discord.com/channels/" not in url  # Discord 不完全リンク
                    and summary_text
                    and not summary_text.startswith(
                        "Discord の会話の要約が提供されていません"
                    )
                    and "URL へのアクセス権限がない" not in summary_text
                    and "箇条書き 3 点による要約を作成できません" not in summary_text
                    and "URL から情報を取得して要約することはできません"
                    not in summary_text
                    and "提供されたテキストからは" not in summary_text
                    and "不足しているため、正確な要約はできません" not in summary_text
                )

                if is_valid_url:
                    valid_summaries.append(summary_data)

            # 有効な要約がない場合はセクションを追加しない
            if not valid_summaries:
                self.logger.debug("有効な URL 要約がないため、セクションを追加しません")
                return content

            # コンテンツの末尾に URL 要約セクションを追加
            url_section_parts = ["\n\n## 📎 URL 要約\n"]

            for summary_data in valid_summaries:
                url_section_parts.append(
                    f"### {summary_data['title']}\n"
                    f"🔗 {summary_data['url']}\n\n"
                    f"{summary_data['summary']}\n"
                )

            return content + "".join(url_section_parts)

        except Exception as e:
            self.logger.warning("Failed to integrate URL summaries", error=str(e))
            return content

    async def _find_related_notes(
        self, content: str, exclude_file: str | None = None
    ) -> list[SemanticSearchResult]:
        """関連ノートを検索"""
        try:
            exclude_files = {exclude_file} if exclude_file else set()

            results = await self.vector_store.search_similar_notes(
                query_text=content,
                limit=self.max_related_notes,
                min_similarity=self.min_similarity_threshold,
                exclude_files=exclude_files,
            )

            return results

        except Exception as e:
            self.logger.error("Failed to find related notes", error=str(e))
            return []

    async def _generate_internal_links(
        self, content: str, related_notes: list[SemanticSearchResult]
    ) -> list[str]:
        """内部リンクを生成"""
        try:
            if not related_notes:
                return []

            # SemanticSearchResult を辞書形式に変換
            related_notes_dict = [
                {
                    "title": note.title,
                    "similarity_score": note.similarity_score,
                    "content_preview": note.content_preview,
                    "file_path": note.file_path,
                }
                for note in related_notes[: self.max_internal_links]
            ]

            links = await self.ai_processor.generate_internal_links(
                content, related_notes_dict
            )

            return links

        except Exception as e:
            self.logger.error("Failed to generate internal links", error=str(e))
            return []

    async def _enhance_content_with_links(
        self,
        content: str,
        internal_links: list[str],
        url_processing_results: dict[str, Any],
        discord_metadata: dict[str, Any] | None = None,
    ) -> str:
        """コンテンツにリンクを追加して強化"""
        try:
            enhanced_content = content

            # Discord メタデータからのコンテキスト情報を追加
            if discord_metadata:
                discord_section = await self._create_discord_metadata_section(
                    discord_metadata
                )
                if discord_section:
                    enhanced_content = discord_section + "\n\n" + enhanced_content

            # URL 要約が既に追加されているかチェック
            if url_processing_results.get("summaries"):
                url_summaries = url_processing_results["summaries"]
                enhanced_content = await self._integrate_url_summaries(
                    enhanced_content, url_summaries
                )

            # 内部リンクセクションを追加
            if internal_links:
                links_section = "\n\n## 🔗 関連ノート\n\n"
                links_section += "\n".join(internal_links)
                enhanced_content += links_section

            return enhanced_content

        except Exception as e:
            self.logger.warning("Failed to enhance content with links", error=str(e))
            return content

    async def _analyze_discord_context(
        self, content: str, discord_metadata: dict[str, Any]
    ) -> dict[str, Any]:
        """Discord コンテキストを分析してコンテンツ分類を強化"""
        try:
            # Discord メタデータから情報を抽出
            channel_name = discord_metadata.get("channel_name", "unknown")
            channel_category = discord_metadata.get("channel_category", "unknown")
            message_timestamp = discord_metadata.get("timestamp")
            user_id = discord_metadata.get("user_id")

            # コンテンツタイプの推定
            content_type = await self._infer_content_type_from_context(
                content, channel_name, channel_category
            )

            # 適切なフォルダパスの推定
            suggested_folder = await self._suggest_folder_from_context(
                content, content_type, channel_category
            )

            # タグの提案
            suggested_tags = await self._suggest_tags_from_context(
                content, channel_category, content_type
            )

            return {
                "content_type": content_type,
                "suggested_folder": suggested_folder,
                "suggested_tags": suggested_tags,
                "channel_context": {
                    "name": channel_name,
                    "category": channel_category,
                    "timestamp": message_timestamp,
                    "user_id": user_id,
                },
                "classification_confidence": await self._calculate_classification_confidence(
                    content, content_type, suggested_folder
                ),
            }

        except Exception as e:
            self.logger.error("Failed to analyze Discord context", error=str(e))
            return {"error": str(e)}

    async def _infer_content_type_from_context(
        self, content: str, channel_name: str, channel_category: str
    ) -> str:
        """チャンネル名とカテゴリからコンテンツタイプを推定"""
        # コンテンツの長さと特徴を分析
        content_lower = content.lower()

        # 1. Archive キーワード（最優先 - 完了・過去の判定）
        archive_keywords = [
            "完了した",
            "完成した",
            "終了した",
            "修了した",
            "過去の",
            "昨年の",
            "前の",
            "以前の",
            "アーカイブ",
            "履歴",
            "証明書",
            "契約書",
            "報告書",
            "最終",
        ]
        # 「記録」は現在進行形の場合Archive対象外
        has_current_record = any(
            indicator in content_lower
            for indicator in ["今日", "現在", "継続中", "目標"]
        )
        if not has_current_record and "記録" in content_lower:
            archive_keywords.append("記録")

        if any(keyword in content_lower for keyword in archive_keywords):
            return "archive"

        # 2. Learning キーワード（超高優先 - 学習コンテンツの確実な識別）
        # 「基本：」「について」などの学習特有表現を最優先
        learning_keywords = [
            "学習",
            "読書",
            "勉強",
            "research",
            "python",
            "機械学習",
            "教師あり",
            "非同期処理",
            "async",
            "await",
            "について学んだ",
            "使用して",
            "訓練する",
        ]
        # 学習コンテンツの強力な識別パターン
        strong_learning_patterns = [
            "基本：",
            "の基本",
            "について学んだ",
            "重要性について",
            "マーケティングの基本",
            "設定、価値提案、チャネル",
            "ターゲット設定、価値提案",
            "選択の重要性",
        ]
        has_strong_learning = any(
            pattern in content_lower for pattern in strong_learning_patterns
        )
        if has_strong_learning or any(
            keyword in content_lower for keyword in learning_keywords
        ):
            return "learning"

        # 3. Task キーワード（超高優先 - 期限付きタスクの確実な識別）
        # 「までに」「必要があります」などの期限・必要性表現を最優先
        urgent_task_patterns = [
            "までに",
            "必要があります",
            "しなければならない",
            "明日までに",
            "来週まで",
            "期限",
            "deadline",
        ]
        task_keywords = [
            "todo",
            "やること",
            "スケジュール",
            "準備",
            "作成",
            "連絡",
            "手続きを済ませる",
            "リストを作成する",
            "返信をする",
            "準備をしなければならない",
            "準備が必要",
            "連絡が必要",
        ]

        # 期限付きタスクは他のすべてのカテゴリより優先
        has_urgent_task = any(
            pattern in content_lower for pattern in urgent_task_patterns
        )
        if (
            has_urgent_task
            or channel_category == "productivity"
            or any(keyword in content_lower for keyword in task_keywords)
        ):
            return "task"

        # 4. Finance キーワード（高優先 - 金融関連）
        financial_keywords = [
            "円",
            "¥",
            "$",
            "支出",
            "収入",
            "購入",
            "支払い",
            "投資",
            "貯金",
            "家計簿",
            "食費",
            "交通費",
            "光熱費",
            "昼食",
            "コーヒー",
            "代",
        ]
        financial_context = any(
            keyword in content_lower for keyword in ["家計簿", "支出", "今日の支出"]
        )
        if (
            channel_category == "finance"
            or financial_context
            or any(keyword in content_lower for keyword in financial_keywords)
        ):
            # 「書籍」単体は除外、「書籍代」などの支出文脈のみFinance
            if "書籍" in content_lower and not any(
                expense in content_lower for expense in ["代", "支出", "円"]
            ):
                pass  # 次の判定に流す
            else:
                return "finance"

        # 5. Health キーワード（高優先 - 健康記録）
        health_keywords = [
            "体重",
            "血圧",
            "運動",
            "睡眠",
            "健康",
            "workout",
            "fitness",
            "ランニング",
            "km",
            "bpm",
            "食事制限",
            "継続中",
            "目覚め",
            "kg",
            "目標",
        ]
        health_context = any(
            keyword in content_lower
            for keyword in ["体重記録", "睡眠ログ", "ランニング"]
        )
        if (
            channel_category == "health"
            or health_context
            or any(keyword in content_lower for keyword in health_keywords)
        ):
            return "health"

        # 6. Ideas キーワード（創作・発想の判定）
        idea_keywords = [
            "アイデア",
            "ネタ",
            "着想",
            "思いつき",
            "考え",
            "発想",
            "創作",
            "企画案",
            "コンセプト",
            "構想",
            "案",
            "提案",
        ]
        if any(keyword in content_lower for keyword in idea_keywords):
            return "idea"

        # 7. Projects キーワード（仕事・開発の判定）
        project_keywords = [
            "プロジェクト",
            "案件",
            "開発",
            "制作",
            "進捗",
            "フェーズ",
            "統合",
            "実装",
            "事業",
            "企画",
            "計画",
            "業務",
            "クライアント",
            "顧客",
            "受注",
        ]
        if any(keyword in content_lower for keyword in project_keywords):
            return "project"

        # 8. Resources キーワード（参考資料の判定）
        resource_keywords = [
            "参考",
            "資料",
            "文献",
            "論文",
            "書籍",
            "本",
            "記事",
            "ドキュメント",
            "ウェブサイト",
            "URL",
            "リンク",
            "ベストプラクティス",
            "ガイド",
            "マニュアル",
            "https://",
            "http://",
        ]
        if any(keyword in content_lower for keyword in resource_keywords):
            return "resource"

        # 9. Daily キーワード（日常記録の判定）
        daily_keywords = [
            "今日",
            "昨日",
            "今朝",
            "今夜",
            "朝から",
            "夕方",
            "散歩",
            "天気",
            "友達",
            "家族",
            "映画",
            "料理",
            "振り返り",
            "日記",
            "出来事",
        ]
        if any(keyword in content_lower for keyword in daily_keywords):
            return "daily"

        # 10. デフォルト判定
        if len(content) < 100:
            return "quick_note"
        else:
            return "memo"

    async def _suggest_folder_from_context(
        self, content: str, content_type: str, channel_category: str
    ) -> str:
        """コンテキストに基づいて適切なフォルダを提案"""
        # コンテンツタイプに基づくフォルダマッピング（数値プレフィックス統一）
        type_folder_map = {
            # 新規カテゴリ
            "archive": "📦 30_Archive",
            "idea": "💡 03_Ideas",
            "project": "🚀 11_Projects",
            "resource": "📖 12_Resources",
            "daily": "📅 01_DailyNotes",
            # 既存カテゴリ（統一）
            "finance": "💰 20_Finance",
            "task": "✅ 02_Tasks",
            "health": "🏃 21_Health",
            "learning": "📚 10_Knowledge",
            "quick_note": "📥 00_Inbox",
            "memo": "📥 00_Inbox",
        }

        return type_folder_map.get(content_type, "📥 00_Inbox")

    async def _suggest_tags_from_context(
        self, content: str, channel_category: str, content_type: str
    ) -> list[str]:
        """コンテキストに基づいてタグを提案"""
        tags = []

        # コンテンツタイプベースのタグ
        if content_type == "finance":
            tags.append("#finance")
            if "支出" in content.lower() or "購入" in content.lower():
                tags.append("#expense")
            if "収入" in content.lower():
                tags.append("#income")
        elif content_type == "task":
            tags.append("#task")
            if "urgent" in content.lower() or "緊急" in content.lower():
                tags.append("#urgent")
        elif content_type == "health":
            tags.append("#health")
        elif content_type == "learning":
            tags.append("#learning")

        # 日付ベースのタグ（今月/今年）
        now = datetime.now()
        tags.append(f"#{now.strftime('%Y-%m')}")

        return tags

    async def _calculate_classification_confidence(
        self, content: str, content_type: str, suggested_folder: str
    ) -> float:
        """分類の信頼度を計算"""
        # 簡単な信頼度計算（実際にはもっと複雑なロジックを実装可能）
        confidence = 0.5  # ベース信頼度

        # コンテンツの長さに基づく調整
        if len(content) > 50:
            confidence += 0.2
        if len(content) > 200:
            confidence += 0.1

        # キーワードマッチに基づく調整
        content_lower = content.lower()
        type_keywords = {
            "finance": ["円", "¥", "支出", "収入", "購入"],
            "task": ["todo", "タスク", "完了", "期限"],
            "health": ["体重", "運動", "睡眠", "健康"],
            "learning": ["学習", "読書", "勉強"],
        }

        if content_type in type_keywords:
            matches = sum(
                1 for keyword in type_keywords[content_type] if keyword in content_lower
            )
            confidence += min(matches * 0.1, 0.3)

        return min(confidence, 1.0)

    async def _create_discord_metadata_section(
        self, discord_metadata: dict[str, Any]
    ) -> str | None:
        """Discord メタデータセクションを作成"""
        try:
            if not discord_metadata:
                return None

            channel_name = discord_metadata.get("channel_name")
            timestamp = discord_metadata.get("timestamp")

            if not any([channel_name, timestamp]):
                return None

            metadata_lines = ["## 📱 Discord Info"]

            if channel_name:
                metadata_lines.append(f"- **Channel**: #{channel_name}")
            if timestamp:
                # タイムスタンプをより読みやすい形式に変換
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M")
                    metadata_lines.append(f"- **Created**: {formatted_time}")
                except Exception:
                    metadata_lines.append(f"- **Created**: {timestamp}")

            return "\n".join(metadata_lines)

        except Exception as e:
            self.logger.warning(
                "Failed to create Discord metadata section", error=str(e)
            )
            return None

    async def _add_to_vector_store(
        self, file_path: str, title: str, content: str
    ) -> None:
        """ベクトルストアにノートを追加"""
        try:
            await self.vector_store.add_note_embedding(
                file_path=file_path, title=title, content=content
            )

        except Exception as e:
            self.logger.warning(
                "Failed to add note to vector store", file_path=file_path, error=str(e)
            )

    def _get_content_stats(self, content: str) -> dict[str, Any]:
        """コンテンツの統計情報を取得"""
        try:
            lines = content.split("\n")
            words = content.split()

            # 見出し数をカウント
            headers = re.findall(r"^#{1,6}\s+.+$", content, re.MULTILINE)

            # リンク数をカウント
            markdown_links = re.findall(r"\[([^\]]+)\]\([^)]+\)", content)
            wiki_links = re.findall(r"\[\[([^\]]+)\]\]", content)

            return {
                "character_count": len(content),
                "word_count": len(words),
                "line_count": len(lines),
                "header_count": len(headers),
                "markdown_link_count": len(markdown_links),
                "wiki_link_count": len(wiki_links),
                "total_link_count": len(markdown_links) + len(wiki_links),
            }

        except Exception as e:
            self.logger.warning("Failed to get content stats", error=str(e))
            return {}

    async def get_system_stats(self) -> dict[str, Any]:
        """システム統計情報を取得"""
        try:
            vector_stats = await self.vector_store.get_embedding_stats()

            return {
                "vector_store": vector_stats,
                "analyzer_config": {
                    "max_related_notes": self.max_related_notes,
                    "min_similarity_threshold": self.min_similarity_threshold,
                    "max_internal_links": self.max_internal_links,
                },
                "system_status": "operational",
                "last_updated": datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error("Failed to get system stats", error=str(e))
            return {"error": str(e)}
