"""Note creation and Obsidian integration handler."""

import re
from typing import Any

from src.utils.mixins import LoggerMixin


class NoteHandler(LoggerMixin):
    """ノート作成と Obsidian 連携専用ハンドラー"""

    def __init__(
        self,
        obsidian_manager=None,
        note_template=None,
        daily_integration=None,
        template_engine=None,
        note_analyzer=None,
    ):
        self.obsidian_manager = obsidian_manager
        self.note_template = note_template
        self.daily_integration = daily_integration
        self.template_engine = template_engine
        self.note_analyzer = note_analyzer

    async def handle_obsidian_note_creation(
        self,
        message_data: dict[str, Any],
        channel_info: Any,
        ai_result: Any,
        original_message: Any = None,
    ) -> dict[str, Any]:
        """Obsidian ノート作成処理"""
        try:
            import base64
            import os
            from datetime import datetime, timedelta, timezone
            from pathlib import Path

            import aiofiles
            import aiohttp

            from src.obsidian.template_system.yaml_generator import (
                YAMLFrontmatterGenerator,
            )

            # 日本時間で統一処理
            jst = timezone(timedelta(hours=9))
            now_jst = datetime.now(jst)
            timestamp = now_jst.strftime("%Y-%m-%d-%H%M%S")

            # メッセージ内容を取得
            raw_content = (
                message_data.get("metadata", {})
                .get("content", {})
                .get("raw_content", "新しいメモ")
            )

            # Integrate audio data if available (centralized management)
            content_info = message_data.get("metadata", {}).get("content", {})
            audio_data = content_info.get("audio_transcription_data")

            if audio_data and "🎤 音声文字起こし" not in raw_content:
                # Add audio section
                audio_section = (
                    f"\n\n## 🎤 音声文字起こし\n\n{audio_data['transcript']}"
                )
                if audio_data.get("confidence", 0) > 0.0:
                    audio_section += f"\n\n**信頼度**: {audio_data['confidence']:.2f} ({audio_data['confidence_level']})"
                if audio_data.get("fallback_used"):
                    audio_section += f"\n\n**注意**: {audio_data['fallback_reason']}"
                    if audio_data.get("saved_file_path"):
                        audio_section += (
                            f"\n**保存先**: `{audio_data['saved_file_path']}`"
                        )

                raw_content += audio_section

            # Inline duplicate removal (reliable operation)
            content = raw_content
            audio_marker = "## 🎤 音声文字起こし"
            audio_count_before = content.count(audio_marker)

            if audio_count_before > 1:
                # シンプルな文字列置換アプローチ
                lines = content.split("\n")
                result_lines = []
                audio_section_encountered = False
                skip_mode = False

                for line in lines:
                    if line.strip() == audio_marker.strip():
                        if not audio_section_encountered:
                            # First audio section - keep
                            audio_section_encountered = True
                            result_lines.append(line)
                        else:
                            # Duplicate audio section - start skipping
                            skip_mode = True
                            continue
                    elif line.startswith("##") and skip_mode:
                        # 新しいセクションが始まったらスキップ終了
                        skip_mode = False
                        result_lines.append(line)
                    elif not skip_mode:
                        # スキップモードでない場合は追加
                        result_lines.append(line)

                content = "\n".join(result_lines)

            title_preview = self._generate_title_preview(content, audio_data)

            # AI 分析に基づくカテゴリ決定（シンプル化）
            category = "memo"
            category_folder = "00_Inbox"
            if ai_result and ai_result.category:
                cat_val = ai_result.category.category.value
                if "task" in cat_val.lower() or "タスク" in cat_val:
                    category = "task"
                    category_folder = "02_Tasks"
                elif (
                    "finance" in cat_val.lower()
                    or "金融" in cat_val
                    or "お金" in cat_val
                ):
                    category = "finance"
                    category_folder = "20_Finance"
                elif "health" in cat_val.lower() or "健康" in cat_val:
                    category = "health"
                    category_folder = "21_Health"
                elif "idea" in cat_val.lower() or "アイデア" in cat_val:
                    category = "idea"
                    category_folder = "03_Ideas"
                elif (
                    "knowledge" in cat_val.lower()
                    or "学習" in cat_val
                    or "知識" in cat_val
                ):
                    category = "knowledge"
                    category_folder = "10_Knowledge"
                elif "project" in cat_val.lower() or "プロジェクト" in cat_val:
                    category = "project"
                    category_folder = "11_Projects"

            # 安全なファイル名生成
            safe_title = "".join(
                c for c in title_preview if c.isalnum() or c in "-_あ-んア-ン一-龯"
            )[:40]
            filename = f"{timestamp}-{safe_title}.md"
            file_path = f"{category_folder}/{filename}"

            # Use comprehensive YAML frontmatter generator
            yaml_generator = YAMLFrontmatterGenerator()

            # Discord コンテキスト情報の準備
            discord_context = {
                "source": "Discord",
                "channel_name": message_data.get("channel_name", "unknown"),
                "message_id": message_data.get("message_id"),
                "user_id": message_data.get("author_id"),
                "timestamp": now_jst,
            }

            # 音声メモの場合の追加情報
            if message_data.get("attachments"):
                for attachment in message_data["attachments"]:
                    if attachment.get("content_type", "").startswith("audio/"):
                        discord_context["is_voice_memo"] = True
                        discord_context["audio_duration"] = attachment.get(
                            "duration", 0
                        )
                        discord_context["input_method"] = "voice"
                        break

            # Generate comprehensive frontmatter
            yaml_frontmatter = yaml_generator.create_comprehensive_frontmatter(
                title=title_preview,
                content_type=category,
                ai_result=ai_result,
                content=content,
                context=discord_context,
                # 追加のメタデータ
                vault_section=category_folder,
                processing_timestamp=now_jst,
                auto_generated=True,
                data_quality="high" if ai_result else "medium",
            )

            # Generate comprehensive YAML frontmatter markdown content
            markdown_parts = [
                yaml_frontmatter,
                "",  # フロントマター後の空行
                f"# {title_preview}",
                "",
                "## 📝 内容",
                "",
                content,
            ]

            # AI 分析結果がある場合は追加情報を含める
            if ai_result:
                markdown_parts.extend(["", "---", "", "## AI 分析情報", ""])

                if ai_result.category:
                    confidence = getattr(ai_result.category, "confidence_score", 0)
                    markdown_parts.append(
                        f"- **カテゴリ**: {ai_result.category.category.value} ({confidence:.0%})"
                    )

                if ai_result.summary:
                    markdown_parts.extend(
                        [
                            f"- **要約**: {ai_result.summary.summary}",
                        ]
                    )

                if hasattr(ai_result, "tags") and ai_result.tags:
                    # TagsResult オブジェクトの場合、 tags.tags でアクセス
                    if hasattr(ai_result.tags, "tags"):
                        tags_list: list[str] = ai_result.tags.tags
                    else:
                        # TagResult の場合は適切に変換
                        if hasattr(ai_result.tags, "__iter__") and not isinstance(
                            ai_result.tags, str
                        ):
                            # TagResult の iteration を安全に処理
                            try:
                                tags_list = [str(tag) for tag in ai_result.tags]
                            except (TypeError, AttributeError):
                                tags_list = [str(ai_result.tags)]
                        else:
                            tags_list = [str(ai_result.tags)]

                    # タグリストを文字列に変換（各要素を文字列として処理）
                    if isinstance(tags_list, list | tuple):
                        tags_str = ", ".join(str(tag) for tag in tags_list)
                    else:
                        tags_str = str(tags_list)

                    markdown_parts.append(f"- **推奨タグ**: {tags_str}")

            # 最終的なクリーンなマークダウン
            clean_markdown = "\n".join(markdown_parts)

            # GitHub API 失敗フラグ
            github_success = False

            # STEP 1: Try GitHub API
            github_token = os.getenv("GITHUB_TOKEN")
            github_repo = "kenvexar/obsidian-vault-test"  # テストリポジトリに修正

            if github_token and github_repo:
                try:
                    # GitHub API に直接送信
                    headers = {
                        "Authorization": f"token {github_token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "MindBridge-Bot",
                    }

                    url = f"https://api.github.com/repos/{github_repo}/contents/{file_path}"

                    payload = {
                        "message": f"Enhanced YAML: {title_preview}",
                        "content": base64.b64encode(
                            clean_markdown.encode("utf-8")
                        ).decode("utf-8"),
                        "branch": "main",
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.put(
                            url, headers=headers, json=payload
                        ) as response:
                            if response.status == 201:
                                github_success = True
                            else:
                                pass  # Fall back to local

                except Exception as e:
                    self.logger.debug(
                        "GitHub upload failed, falling back to local", error=str(e)
                    )

            # STEP 2: Local file creation fallback
            local_file_created = False
            if not github_success:
                try:
                    # ローカル vault パスの設定
                    vault_path = Path("/app/vault")

                    local_folder = vault_path / category_folder

                    # フォルダが存在しない場合は作成
                    local_folder.mkdir(parents=True, exist_ok=True)

                    local_file_path = local_folder / filename

                    # ローカルファイルに保存
                    async with aiofiles.open(
                        local_file_path, "w", encoding="utf-8"
                    ) as f:
                        await f.write(clean_markdown)

                    local_file_created = True

                except Exception as e:
                    self.logger.warning(
                        "Failed to create local note file", error=str(e)
                    )

            # STEP 3: GitHub sync (only if local file was created)
            if local_file_created:
                try:
                    from src.obsidian.github_sync import GitHubObsidianSync

                    # Create GitHub sync instance
                    sync_client = GitHubObsidianSync()

                    # Check configuration
                    if sync_client.is_configured:
                        # Execute auto sync
                        await sync_client.sync_to_github(
                            commit_message=f"Auto-sync Enhanced YAML: {title_preview}"
                        )

                except Exception as e:
                    self.logger.debug(
                        "GitHub sync failed but note is saved locally", error=str(e)
                    )

            return {
                "status": "success",
                "file_path": file_path,
                "github_success": github_success,
                "local_success": local_file_created,
            }

        except Exception as e:
            return {"status": "error", "error": str(e)}

    @staticmethod
    def _generate_title_preview(content: str, audio_data: dict[str, Any] | None) -> str:
        """ノートタイトルとなるプレビュー文字列を生成"""
        if audio_data and audio_data.get("transcript"):
            title_source = audio_data["transcript"].strip()
        else:
            title_source = content.replace("\n", " ").strip()

        title_source = re.sub(r"^[#\s*]+", "", title_source)
        title_source = re.sub(r"[#*]+$", "", title_source)
        title_source = re.sub(r"#{1,6}\s*", "", title_source)
        title_source = re.sub(r"🎤\s*音声文字起こし\s*", "", title_source)
        title_source = re.sub(r"音声文字起こし\s*", "", title_source)
        title_source = re.sub(r"\s{2,}", " ", title_source).strip()

        if not title_source:
            return "音声メモ"

        sentence_candidates = re.split(r"[。！？?!]", title_source, maxsplit=1)
        primary_sentence = sentence_candidates[0].strip() if sentence_candidates else ""
        title_preview = primary_sentence or title_source
        return title_preview[:30]

    async def organize_note_by_ai_category(
        self, note_path: str, ai_category: str, ai_result: Any
    ) -> None:
        """AI カテゴリによるノート整理"""
        if not ai_result or not ai_result.category:
            self.logger.debug(
                "No AI category found, keeping note in current location",
                note_path=note_path,
            )
            return

        try:
            from src.obsidian.models import FolderMapping

            # AI 分類結果から目標フォルダを決定
            category = ai_result.category.category
            subcategory = getattr(ai_result.category, "subcategory", None)

            target_folder = FolderMapping.get_folder_for_category(category, subcategory)

            # 現在のフォルダパスを確認
            if self.obsidian_manager is None:
                self.logger.warning("Obsidian manager not available for organization")
                return

            # ファイル移動を実行
            # 実際の移動処理は obsidian_manager に委譲
            await self.obsidian_manager.organize_note_by_category(
                note_path, target_folder, ai_result
            )

            self.logger.info(
                "Note organized by AI category",
                note_path=note_path,
                target_folder=target_folder.value
                if hasattr(target_folder, "value")
                else str(target_folder),
                category=category,
                subcategory=subcategory,
                confidence=ai_result.category.confidence_score,
            )

        except Exception as e:
            self.logger.error(
                "Failed to organize note by AI category",
                note_path=note_path,
                category=category if "category" in locals() else "unknown",
                error=str(e),
                exc_info=True,
            )

    async def handle_daily_note_integration(
        self, message_data: dict[str, Any], ai_result: Any
    ) -> None:
        """デイリーノート統合処理"""
        try:
            from src.config import get_settings

            settings = get_settings()

            # channel_info が message_data に含まれている場合の処理
            channel_info = message_data.get("channel_info")
            if not channel_info:
                return

            channel_id = channel_info.id

            # Activity Log チャンネルの処理
            if (
                self.daily_integration
                and hasattr(settings, "channel_activity_log")
                and settings.channel_activity_log
                and channel_id == settings.channel_activity_log
            ):
                success = await self.daily_integration.add_activity_log_entry(
                    message_data
                )
                if success:
                    self.logger.info("Activity log entry added to daily note")
                else:
                    self.logger.warning("Failed to add activity log entry")

            # Daily Tasks チャンネルの処理
            elif (
                self.daily_integration
                and hasattr(settings, "channel_daily_tasks")
                and settings.channel_daily_tasks
                and channel_id == settings.channel_daily_tasks
            ):
                success = await self.daily_integration.add_daily_task_entry(
                    message_data
                )
                if success:
                    self.logger.info("Daily task entry added to daily note")
                else:
                    self.logger.warning("Failed to add daily task entry")

        except Exception as e:
            self.logger.error(
                "Error in daily note integration",
                channel_name=message_data.get("channel_name", "unknown"),
                error=str(e),
                exc_info=True,
            )

    async def handle_github_direct_sync(
        self, note_path: str, channel_info: Any
    ) -> None:
        """GitHub 直接同期処理"""
        try:
            from src.obsidian.github_direct import GitHubDirectClient

            # GitHub Direct Client を初期化
            github_client = GitHubDirectClient()

            self.logger.debug(
                "GitHubDirectClient initialized",
                is_configured=github_client.is_configured,
                has_token=bool(github_client.github_token),
                has_repo_url=bool(github_client.github_repo_url),
                owner=github_client.owner,
                repo=github_client.repo,
            )

            if not github_client.is_configured:
                self.logger.warning(
                    "GitHub direct sync not configured - file saved locally only"
                )
                return

            # ローカルファイルから内容を読み取り
            from pathlib import Path

            import aiofiles

            local_path = Path(note_path)
            if not local_path.exists():
                self.logger.warning("Local note file not found", note_path=note_path)
                return

            async with aiofiles.open(local_path, encoding="utf-8") as f:
                content = await f.read()

            # GitHub にアップロード
            result = await github_client.create_or_update_file(
                file_path=note_path,
                content=content,
                commit_message=f"Auto-sync: {local_path.stem} from Discord",
            )

            if result:
                self.logger.info(
                    "GitHub direct sync completed successfully",
                    file_path=note_path,
                    commit_sha=result.get("content", {}).get("sha"),
                )
            else:
                self.logger.warning(
                    "GitHub direct sync failed",
                    file_path=note_path,
                    reason="create_or_update_file returned None",
                )

        except ImportError:
            self.logger.warning(
                "GitHubDirectClient not available - falling back to traditional sync"
            )
        except Exception as github_error:
            self.logger.error(
                "GitHub direct sync failed with error",
                file_path=note_path,
                error=str(github_error),
                exc_info=True,
            )

    def generate_ai_based_title(self, text_content: str) -> str:
        """AI 基盤のタイトル生成"""
        # 簡略化された実装 - 実際には AI 結果を使用
        if len(text_content) > 30:
            return f"📝 {text_content[:30]}..."
        return f"📝 {text_content}"

    def generate_text_based_title(self, text_content: str) -> str:
        """テキスト基盤のタイトル生成"""
        if text_content and len(text_content) > 10:
            # 最初の 30 文字を使用してタイトル生成
            clean_text = text_content.strip()[:30]
            return f"📝 {clean_text}"
        return "📝 テキストメモ"

    def get_fallback_title(self, channel_name: str) -> str:
        """フォールバックタイトル生成"""
        return f"📝 メモ - #{channel_name}"

    def generate_activity_log_title(self, text_content: str) -> str:
        """活動ログタイトル生成"""
        try:
            # テキストから意味のあるタイトルを生成
            if text_content and len(text_content.strip()) > 5:
                # 最初の行または 30 文字を使用
                first_line = text_content.split("\n")[0].strip()
                if len(first_line) > 30:
                    first_line = first_line[:30] + "..."
                return f"📝 {first_line}"

            return "📝 活動ログ"

        except Exception:
            return "📝 活動ログ"
