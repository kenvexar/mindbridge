"""Basic bot commands (help, status, search)."""

from datetime import datetime
from typing import Any

import discord
import structlog
from discord import app_commands
from discord.ext import commands

from src.bot.mixins.command_base import CommandMixin
from src.security.simple_admin import admin_required

logger = structlog.get_logger(__name__)


class BasicCommands(commands.Cog, CommandMixin):
    """Basic bot commands like help, status, and search."""

    def __init__(self, bot: discord.Client):
        self.bot = bot

    @app_commands.command(name="help", description="ボットのヘルプ情報を表示")
    @app_commands.describe(
        command="特定のコマンドのヘルプ（省略時は全体ヘルプ）",
    )
    async def help_command(
        self, interaction: discord.Interaction, command: str | None = None
    ) -> None:
        """Display help information."""
        try:
            await self.defer_if_needed(interaction)

            if command:
                # Show help for specific command
                await self._show_command_help(interaction, command)
            else:
                # Show general help
                await self._show_general_help(interaction)

        except Exception as e:
            logger.error("Failed to show help", error=str(e))
            await self.send_error_response(
                interaction, "ヘルプ情報の表示に失敗しました。", followup=True
            )

    @app_commands.command(name="status", description="ボットの現在のステータスを表示")
    async def status_command(self, interaction: discord.Interaction) -> None:
        """Display bot status."""
        response_sent = False
        fallback_channel = False
        try:
            try:
                await self.defer_if_needed(interaction)
            except discord.NotFound as error:
                # Interaction が期限切れの場合はチャンネルへの直接送信にフォールバック
                logger.warning("Interaction expired before defer", error=str(error))
                fallback_channel = True
            except discord.HTTPException as error:
                if getattr(error, "code", None) == 40060:
                    # 他ハンドラがすでに ack 済みの場合はフォローアップ送信に切り替える
                    logger.warning("Interaction already acknowledged", error=str(error))
                else:
                    raise

            # Get basic status information
            status_info = await self._get_status_info()

            fields = [
                ("ボット状態", "🟢 稼働中", True),
                (
                    "接続状態",
                    "🟢 接続済み" if self.bot.is_ready() else "🔴 切断中",
                    True,
                ),
                ("レイテンシー", f"{self.bot.latency * 1000:.0f}ms", True),
                ("サーバー数", str(len(self.bot.guilds)), True),
                ("チャンネル設定", status_info.get("channel_status", "未確認"), True),
                ("最終起動", status_info.get("last_startup", "不明"), True),
            ]

            # Add service status
            service_status = await self._check_service_status()
            for service, status in service_status.items():
                fields.append((f"{service} サービス", status, True))

            if fallback_channel:
                channel = getattr(interaction, "channel", None)
                if channel is None:
                    raise RuntimeError("Interaction channel not available")

                embed = discord.Embed(
                    title="✅ ボットステータス",
                    color=discord.Color.blue(),
                    timestamp=datetime.now(),
                )
                for name, value, inline in fields:
                    embed.add_field(name=name, value=value, inline=inline)

                await channel.send(embed=embed)
                response_sent = True
                return

            await self.send_success_response(
                interaction,
                "ボットステータス",
                fields=fields,
                color=discord.Color.blue(),
                followup=True,
            )
            response_sent = True

        except Exception as e:
            logger.error("Failed to get status", error=str(e))
            if not response_sent:
                await self.send_error_response(
                    interaction, "ステータス情報の取得に失敗しました。", followup=True
                )

    @app_commands.command(name="search", description="Obsidian ノートを検索")
    @app_commands.describe(
        query="検索キーワード",
        limit="検索結果の最大表示数",
    )
    @admin_required
    async def search_command(
        self,
        interaction: discord.Interaction,
        query: str,
        limit: int = 10,
    ) -> None:
        """Search Obsidian notes."""
        try:
            await self.defer_if_needed(interaction)

            if not query.strip():
                await self.send_error_response(
                    interaction, "検索キーワードを入力してください。", followup=True
                )
                return

            if limit <= 0 or limit > 50:
                limit = 10

            # Perform search
            search_results = await self._search_notes(query, limit)

            if not search_results:
                await self.send_error_response(
                    interaction,
                    f"'{query}' に一致するノートが見つかりませんでした。",
                    followup=True,
                )
                return

            # Format results
            result_text = self._format_search_results(search_results, query)

            embed = discord.Embed(
                title=f"🔍 検索結果: '{query}'",
                description=result_text,
                color=discord.Color.blue(),
                timestamp=datetime.now(),
            )

            embed.set_footer(text=f"{len(search_results)}件の結果を表示")

            await interaction.followup.send(embed=embed)

            logger.info(
                "Search performed",
                user_id=interaction.user.id,
                query=query,
                results_count=len(search_results),
            )

        except Exception as e:
            logger.error("Failed to search notes", error=str(e))
            await self.send_error_response(
                interaction, "検索の実行に失敗しました。", followup=True
            )

    @app_commands.command(name="random", description="ランダムなノートを表示")
    @admin_required
    async def random_note_command(self, interaction: discord.Interaction) -> None:
        """Display a random note."""
        try:
            await self.defer_if_needed(interaction)

            # Get random note
            random_note = await self._get_random_note()

            if not random_note:
                await self.send_error_response(
                    interaction, "ランダムノートを取得できませんでした。", followup=True
                )
                return

            # Format note display
            embed = discord.Embed(
                title=f"🎲 ランダムノート: {random_note['title']}",
                description=random_note.get("preview", "プレビューなし"),
                color=discord.Color.gold(),
                timestamp=datetime.now(),
            )

            if random_note.get("tags"):
                embed.add_field(
                    name="タグ", value=", ".join(random_note["tags"]), inline=False
                )

            if random_note.get("created_date"):
                embed.add_field(
                    name="作成日", value=random_note["created_date"], inline=True
                )

            if random_note.get("file_path"):
                embed.add_field(
                    name="パス", value=random_note["file_path"], inline=True
                )

            await interaction.followup.send(embed=embed)

            logger.info(
                "Random note displayed",
                user_id=interaction.user.id,
                note_title=random_note.get("title", "Unknown"),
            )

        except Exception as e:
            logger.error("Failed to get random note", error=str(e))
            await self.send_error_response(
                interaction, "ランダムノートの取得に失敗しました。", followup=True
            )

    async def _show_general_help(self, interaction: discord.Interaction) -> None:
        """Show general help information."""
        help_text = """
## 🤖 MindBridge

このボットは Discord と Obsidian を連携し、 AI を活用したメモ管理を提供します。

### 📝 主な機能

**メモ管理**
- `#memo` チャンネルでのメッセージ自動保存
- `#voice` チャンネルでの音声メモ処理
- AI による自動分類と要約

**タスク管理**
- `/task add` - 新しいタスクを追加
- `/task list` - タスク一覧を表示
- `/task done` - タスクを完了

**家計管理**
- `/expense add` - 支出を記録
- `/sub add` - 定期購入を追加
- `/budget set` - 予算を設定

**統計・分析**
- `/stats bot` - ボット統計
- `/stats obsidian` - Vault 統計
- `/stats finance` - 家計統計

### 🔧 設定
- `/config show` - 現在の設定表示
- `/config set` - 設定変更

### 🔍 検索
- `/search` - ノート検索
- `/random` - ランダムノート表示

詳細は各コマンドで `/help <コマンド名>` を実行してください。
"""

        embed = discord.Embed(
            title="📚 ボットヘルプ",
            description=help_text.strip(),
            color=discord.Color.blue(),
        )

        await interaction.followup.send(embed=embed)

    async def _show_command_help(
        self, interaction: discord.Interaction, command: str
    ) -> None:
        """Show help for specific command."""
        # This would show detailed help for specific commands
        # For now, show a placeholder
        await self.send_error_response(
            interaction, f"コマンド '{command}' のヘルプは準備中です。", followup=True
        )

    async def _get_status_info(self) -> dict[str, Any]:
        """Get basic status information."""
        return {
            "channel_status": "設定済み",  # This would check actual channel config
            "last_startup": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    async def _check_service_status(self) -> dict[str, str]:
        """Check status of various services."""
        status = {}

        try:
            # Obsidian FileManager チェック
            from src.config.settings import Settings
            from src.obsidian.file_manager import ObsidianFileManager

            settings = Settings()
            file_manager = ObsidianFileManager(settings.obsidian_vault_path)

            # ボルトパスの存在確認
            if file_manager.vault_path.exists():
                status["Obsidian"] = "🟢 利用可能"
            else:
                status["Obsidian"] = "🔴 ボルトパスが見つかりません"

        except Exception as e:
            status["Obsidian"] = f"🔴 エラー: {str(e)[:50]}"

        try:
            # AI 処理システムチェック
            from src.config.settings import get_settings

            settings = get_settings()
            # SecretStr の場合は.get_secret_value() を使用
            api_key = (
                settings.gemini_api_key.get_secret_value()
                if settings.gemini_api_key
                else ""
            )
            if api_key and api_key.strip():
                status["AI 処理"] = "🟢 利用可能"
            else:
                status["AI 処理"] = "🔴 API キーが設定されていません"

        except Exception as e:
            status["AI 処理"] = f"🔴 エラー: {str(e)[:50]}"

        try:
            # 音声認識システムチェック
            import os

            google_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if google_creds and os.path.exists(google_creds):
                status["音声認識"] = "🟢 利用可能"
            else:
                status["音声認識"] = "🔴 認証情報が設定されていません"

        except Exception as e:
            status["音声認識"] = f"🔴 エラー: {str(e)[:50]}"

        return status

    async def _search_notes(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Search notes in Obsidian vault."""
        try:
            from src.config.settings import Settings
            from src.obsidian.file_manager import ObsidianFileManager

            settings = Settings()
            file_manager = ObsidianFileManager(settings.obsidian_vault_path)

            # 検索実行
            search_results = await file_manager.search_notes(query, limit=limit)

            if not search_results:
                return []

            # 結果をフォーマット
            formatted_results = []
            for result in search_results:
                # ファイルパスからタイトルを抽出
                file_path = result.get("path", "")
                title = (
                    file_path.replace(".md", "").split("/")[-1] if file_path else "無題"
                )

                # プレビューテキストを作成
                content = result.get("content", "")
                preview = content[:200].replace("\n", " ").strip() if content else ""

                # メタデータを取得
                metadata = result.get("metadata", {})

                formatted_result = {
                    "title": title,
                    "preview": preview,
                    "file_path": file_path,
                    "score": result.get("score", 0),
                    "tags": metadata.get("tags", [])
                    if isinstance(metadata.get("tags"), list)
                    else [],
                    "created_date": metadata.get("created", ""),
                }

                formatted_results.append(formatted_result)

            return formatted_results

        except Exception as e:
            logger.error("検索処理でエラー", error=str(e))
            return []

    def _format_search_results(self, results: list[dict[str, Any]], query: str) -> str:
        """Format search results for display."""
        if not results:
            return "検索結果がありません。"

        formatted_results = []
        for i, result in enumerate(results, 1):
            title = result.get("title", "無題")
            preview = result.get("preview", "").strip()
            if len(preview) > 100:
                preview = preview[:100] + "..."

            formatted_results.append(f"{i}. **{title}**\n{preview}\n")

        return "\n".join(formatted_results)

    async def _get_random_note(self) -> dict[str, Any] | None:
        """Get a random note from the vault."""
        try:
            import random

            import aiofiles

            from src.config.settings import Settings
            from src.obsidian.file_manager import ObsidianFileManager

            settings = Settings()
            file_manager = ObsidianFileManager(settings.obsidian_vault_path)

            # ボルト内の全マークダウンファイルを取得
            vault_path = file_manager.vault_path
            if not vault_path.exists():
                logger.warning("ボルトパスが存在しません", path=str(vault_path))
                return None

            # .md ファイルをすべて検索
            md_files = list(vault_path.rglob("*.md"))

            # システムファイルやテンプレートを除外
            filtered_files = []
            for file_path in md_files:
                relative_path_obj = file_path.relative_to(vault_path)

                # 除外パターン
                exclude_patterns = [
                    ".obsidian/",
                    "templates/",
                    "Template",
                    ".trash/",
                    "_archive/",
                ]

                should_exclude = any(
                    pattern in str(relative_path_obj) for pattern in exclude_patterns
                )

                if not should_exclude and file_path.is_file():
                    filtered_files.append(file_path)

            if not filtered_files:
                logger.info("ランダム表示用のノートが見つかりません")
                return None

            # ランダムにファイルを選択
            random_file = random.choice(filtered_files)  # nosec B311

            try:
                # ファイル内容を読み取り
                async with aiofiles.open(random_file, encoding="utf-8") as f:
                    content = await f.read()

                # タイトルを抽出（ファイル名から）
                title = random_file.stem

                # プレビューテキストを作成（最初の 300 文字）
                preview = content[:300].replace("\n", " ").strip() if content else ""

                # メタデータ抽出（簡易版）
                tags = []
                created_date = ""

                # タグを抽出（#で始まる単語）
                import re

                tag_matches = re.findall(r"#(\w+)", content)
                tags = list(set(tag_matches))  # 重複除去

                # 作成日を推定（ファイル作成日時）
                try:
                    import os

                    created_timestamp = os.path.getctime(random_file)
                    from datetime import datetime

                    created_date = datetime.fromtimestamp(created_timestamp).strftime(
                        "%Y-%m-%d"
                    )
                except Exception:
                    created_date = "不明"

                # 相対パスを作成（文字列として）
                relative_path_str = str(random_file.relative_to(vault_path))

                return {
                    "title": title,
                    "preview": preview,
                    "file_path": relative_path_str,
                    "tags": tags[:5],  # 最大 5 個まで
                    "created_date": created_date,
                    "content_length": len(content),
                }

            except Exception as e:
                logger.error(
                    "ファイル読み取りでエラー", file_path=str(random_file), error=str(e)
                )
                return None

        except Exception as e:
            logger.error("ランダムノート取得でエラー", error=str(e))
            return None
