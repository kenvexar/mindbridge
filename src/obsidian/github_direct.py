"""
GitHub API を使用した直接ファイル操作
Cloud Run 環境での読み取り専用ファイルシステム問題を解決
"""

from datetime import datetime
from typing import Any

import structlog

from src.config import get_settings


class GitHubDirectClient:
    """GitHub API を使用した直接ファイル操作クライアント"""

    def __init__(self) -> None:
        self.logger = structlog.get_logger("GitHubDirectClient")
        self.settings = get_settings()

        # GitHub 設定を環境変数から取得
        import os

        self.github_token = os.getenv("GITHUB_TOKEN")
        self.github_repo_url = os.getenv("OBSIDIAN_BACKUP_REPO")

        # リポジトリ情報を解析
        self.owner: str | None = None
        self.repo: str | None = None
        if self.github_repo_url:
            self._parse_repo_url()

    def _parse_repo_url(self) -> None:
        """GitHub リポジトリ URL からオーナーとリポジトリ名を抽出"""
        try:
            if self.github_repo_url and self.github_repo_url.startswith(
                "https://github.com/"
            ):
                repo_path = self.github_repo_url.replace("https://github.com/", "")
                if repo_path.endswith(".git"):
                    repo_path = repo_path[:-4]
                parts = repo_path.split("/")
                if len(parts) == 2:
                    self.owner, self.repo = parts
                    self.logger.info(
                        "Parsed GitHub repository info",
                        owner=self.owner,
                        repo=self.repo,
                    )
        except Exception as e:
            self.logger.error("Failed to parse GitHub repository URL", error=str(e))

    def get_category_folder(self, category) -> str:
        """カテゴリ enum を Obsidian フォルダー名にマッピング（新構成対応）"""
        try:
            from src.obsidian.models import FolderMapping, VaultFolder

            if hasattr(category, "value"):
                # ProcessingCategory enum の場合
                category_value = category.value.lower()
            else:
                # 文字列の場合
                category_value = str(category).lower()

            # FolderMappingクラスを使用して統一的にマッピング
            vault_folder = FolderMapping.get_folder_for_category(category_value)
            return vault_folder.value

        except Exception as e:
            self.logger.warning(
                "Failed to map category to folder", category=str(category), error=str(e)
            )
            # フォールバックとして VaultFolder.INBOX を使用
            from src.obsidian.models import VaultFolder

            return VaultFolder.INBOX.value

    @property
    def is_configured(self) -> bool:
        """GitHub 直接書き込みが設定されているかチェック"""
        return bool(self.github_token and self.owner and self.repo)

    async def create_or_update_file(
        self, file_path: str, content: str, commit_message: str, branch: str = "main"
    ) -> dict[str, Any] | None:
        """GitHub API を使用してファイルを作成または更新"""
        try:
            import base64

            import aiohttp

            # 🔧 FIX: 最終段階で自動生成メッセージを確実に除去
            clean_content = self._remove_bot_attribution_messages(content)

            # Base64 エンコード
            encoded_content = base64.b64encode(clean_content.encode("utf-8")).decode(
                "utf-8"
            )

            # API エンドポイント
            api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}/contents/{file_path}"

            # 既存ファイルのSHAを取得を試行
            existing_sha = None  # 新規作成として処理

            # リクエストペイロード
            payload = {
                "message": commit_message,
                "content": encoded_content,
                "branch": branch,
            }

            if existing_sha:
                payload["sha"] = existing_sha

            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "Discord-Obsidian-Memo-Bot/1.0",
            }

            self.logger.info(
                "Creating/updating GitHub file",
                file_path=file_path,
                content_length=len(clean_content),
                existing_sha=bool(existing_sha),
                commit_message=commit_message,
            )

            async with aiohttp.ClientSession() as session:
                async with session.put(
                    api_url, headers=headers, json=payload
                ) as response:
                    response_text = await response.text()

                    if response.status in [200, 201]:
                        result = await response.json()
                        self.logger.info(
                            "✅ File successfully synced to GitHub",
                            file_path=file_path,
                            status=response.status,
                            sha=result.get("content", {}).get("sha", "unknown"),
                        )
                        return result
                    else:
                        self.logger.error(
                            "❌ GitHub sync failed",
                            file_path=file_path,
                            status=response.status,
                            response_text=response_text,
                            payload_keys=list(payload.keys()),
                            existing_sha=existing_sha,
                        )
                        return None

        except Exception as e:
            self.logger.error(
                "❌ Exception during GitHub sync",
                file_path=file_path,
                error=str(e),
                exc_info=True,
            )
            return None

    def _remove_bot_attribution_messages(self, content: str) -> str:
        """自動生成メッセージを除去する"""
        import re

        # 日本語と英語の自動生成メッセージを削除
        patterns_to_remove = [
            r"\*Created by Discord-Obsidian Memo Bot\*[。\s]*",
            r"^---\s*\*Created by Discord-Obsidian Memo Bot\*\s*$",
            r"^\*Created by Discord-Obsidian Memo Bot\*\s*$",
            r".*Discord-Obsidian.*Memo.*Bot.*自動生成.*",
            r".*自動生成.*Discord-Obsidian.*Memo.*Bot.*",
        ]

        for pattern in patterns_to_remove:
            content = re.sub(pattern, "", content, flags=re.MULTILINE | re.IGNORECASE)

        # 空行の連続を整理
        content = re.sub(r"\n\s*\n\s*\n", "\n\n", content)
        content = content.strip()

        return content

    async def create_note_from_discord(
        self, note_data: dict[str, Any], category: str = "Memos"
    ) -> dict[str, Any] | None:
        """Discord メッセージから Obsidian ノートを直接 GitHub に作成"""
        try:
            # 日本時間でファイル名生成
            from datetime import timedelta, timezone

            jst = timezone(timedelta(hours=9))
            timestamp = datetime.now(jst).strftime("%Y-%m-%d-%H%M%S")
            title = note_data.get("title", "untitled").replace(" ", "-")
            safe_title = "".join(c for c in title if c.isalnum() or c in "-_")[:50]
            filename = f"{timestamp}-{safe_title}.md"

            # カテゴリフォルダーとファイルパス
            file_path = f"{category}/{filename}"

            # Markdown コンテンツ生成
            content = self._generate_markdown_content(note_data, category)

            # コミットメッセージ
            commit_message = (
                f"Auto-sync: {note_data.get('title', 'New note')} from Discord"
            )

            # GitHub にファイル作成
            result = await self.create_or_update_file(
                file_path=file_path, content=content, commit_message=commit_message
            )

            if result:
                self.logger.info(
                    "Successfully created Obsidian note via GitHub API",
                    file_path=file_path,
                    category=category,
                    title=note_data.get("title"),
                )
                return {
                    "file_path": file_path,
                    "github_result": result,
                    "content": content,
                }

            return None

        except Exception as e:
            self.logger.error(
                "Failed to create Obsidian note via GitHub API",
                error=str(e),
                exc_info=True,
            )
            return None

    def _generate_markdown_content(
        self, note_data: dict[str, Any], category: str
    ) -> str:
        """Obsidian ノート用の Markdown コンテンツを生成"""
        content_parts = []

        # タイトル
        title = note_data.get("title", "Untitled Note")
        content_parts.append(f"# {title}")
        content_parts.append("")

        # メタデータセクション
        content_parts.append("## メタデータ")

        # 日本時間で作成日時を表示
        from datetime import timedelta, timezone

        jst = timezone(timedelta(hours=9))
        jst_time = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")

        content_parts.append(f"- **作成日時**: {jst_time}")
        content_parts.append(f"- **カテゴリ**: {category}")
        content_parts.append("- **ソース**: Discord (#memo チャンネル)")

        # AI 分析結果があれば追加
        ai_analysis = note_data.get("ai_analysis", {})
        if ai_analysis:
            if ai_analysis.get("category"):
                content_parts.append(f"- **AI分類**: {ai_analysis['category']}")
            if ai_analysis.get("confidence"):
                content_parts.append(f"- **信頼度**: {ai_analysis['confidence']:.2%}")

        content_parts.append("")

        # メインコンテンツ
        content_parts.append("## 内容")
        content_parts.append("")
        main_content = note_data.get("content", "")
        content_parts.append(main_content)
        content_parts.append("")

        # AI による洞察があれば追加
        insights = ai_analysis.get("insights", [])
        if insights:
            content_parts.append("## AI 洞察")
            for insight in insights:
                content_parts.append(f"- {insight}")
            content_parts.append("")

        # キーワード・タグ
        keywords = ai_analysis.get("keywords", [])
        tags = note_data.get("tags", [])
        all_tags = list(set(keywords + tags))
        if all_tags:
            tag_line = " ".join(f"#{tag}" for tag in all_tags)
            content_parts.append(f"**タグ**: {tag_line}")
            content_parts.append("")

        return "\n".join(content_parts)
