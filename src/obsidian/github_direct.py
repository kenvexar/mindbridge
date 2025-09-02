"""
GitHub API を使用した直接ファイル操作
Cloud Run 環境での読み取り専用ファイルシステム問題を解決
"""

from datetime import datetime
from typing import Any

import structlog

from ..config.settings import get_settings


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
            if self.github_repo_url.startswith("https://github.com/"):
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
        """カテゴリ enum を Obsidian フォルダー名にマッピング"""
        try:
            if hasattr(category, "value"):
                # ProcessingCategory enum の場合
                category_value = category.value.lower()
            else:
                # 文字列の場合
                category_value = str(category).lower()

            # カテゴリマッピング
            folder_mapping = {
                "金融": "Finance",
                "仕事": "Work",
                "学習": "Learning",
                "プロジェクト": "Projects",
                "生活": "Life",
                "アイデア": "Ideas",
                "タスク": "Tasks",
                "健康": "Health",
                "その他": "Memos",
                "finance": "Finance",
                "work": "Work",
                "learning": "Learning",
                "project": "Projects",
                "life": "Life",
                "idea": "Ideas",
                "tasks": "Tasks",
                "health": "Health",
                "other": "Memos",
            }

            return folder_mapping.get(category_value, "Memos")

        except Exception as e:
            self.logger.warning(
                "Failed to map category to folder", category=str(category), error=str(e)
            )
            return "Memos"

    @property
    def is_configured(self) -> bool:
        """GitHub 直接書き込みが設定されているかチェック"""
        return bool(self.github_token and self.owner and self.repo)

    async def create_or_update_file(
        self, file_path: str, content: str, commit_message: str, branch: str = "main"
    ) -> dict[str, Any] | None:
        """GitHub API を使用してファイルを作成または更新"""
        if not self.is_configured:
            self.logger.warning("GitHub direct client not configured")
            return None

        try:
            # MCP GitHub ツールを使用してファイルを作成/更新
            from ..utils.mcp_client import get_mcp_client

            github_client = get_mcp_client("github")
            if not github_client:
                self.logger.error("GitHub MCP client not available")
                return None

            # 既存ファイルをチェックして SHA を取得
            sha = None
            try:
                existing_file = await github_client.get_file_contents(
                    owner=self.owner, repo=self.repo, path=file_path, branch=branch
                )
                if existing_file:
                    sha = existing_file.get("sha")
            except Exception:
                # ファイルが存在しない場合は新規作成
                pass

            # ファイル作成/更新
            result = await github_client.create_or_update_file(
                owner=self.owner,
                repo=self.repo,
                path=file_path,
                content=content,
                message=commit_message,
                branch=branch,
                sha=sha,
            )

            self.logger.info(
                "Successfully created/updated file via GitHub API",
                file_path=file_path,
                commit_sha=result.get("commit", {}).get("sha"),
            )
            return result

        except Exception as e:
            self.logger.error(
                "Failed to create/update file via GitHub API",
                file_path=file_path,
                error=str(e),
                exc_info=True,
            )
            return None

    async def create_note_from_discord(
        self, note_data: dict[str, Any], category: str = "Memos"
    ) -> dict[str, Any] | None:
        """Discord メッセージから Obsidian ノートを直接 GitHub に作成"""
        try:
            # ファイル名生成
            timestamp = datetime.now().strftime("%Y-%m-%d-%H%M%S")
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
        content_parts.append(
            f"- **作成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
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

        # フッター
        content_parts.append("---")
        content_parts.append("*Created by Discord-Obsidian Memo Bot*")

        return "\n".join(content_parts)
