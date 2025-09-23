"""
Lifelog handling functionality for Discord messages
"""

from typing import Any

import discord

from src.utils.mixins import LoggerMixin


class LifelogHandler(LoggerMixin):
    """ライフログ処理専用ハンドラー"""

    def __init__(
        self,
        lifelog_manager=None,
        lifelog_analyzer=None,
        lifelog_message_handler=None,
        lifelog_commands=None,
    ):
        self.lifelog_manager = lifelog_manager
        self.lifelog_analyzer = lifelog_analyzer
        self.lifelog_message_handler = lifelog_message_handler
        self.lifelog_commands = lifelog_commands

    async def handle_lifelog_auto_detection(
        self,
        message_data: dict[str, Any],
        channel_info: Any,
        original_message: discord.Message | None = None,
    ) -> None:
        """ライフログ自動検出処理"""
        if not self.lifelog_message_handler or not original_message:
            return

        try:
            # メッセージ内容を取得
            metadata = message_data.get("metadata", {})
            content_info = metadata.get("content", {})
            final_content = ""

            # 音声転写結果も含めた最終コンテンツを取得
            if "raw_content" in content_info:
                final_content = content_info["raw_content"]
            elif original_message.content:
                final_content = original_message.content

            # 音声データがある場合は転写結果も考慮
            audio_data = content_info.get("audio_transcription_data")
            if audio_data and audio_data.get("transcript"):
                if final_content:
                    final_content += f"\n\n 音声転写: {audio_data['transcript']}"
                else:
                    final_content = audio_data["transcript"]

            if not final_content or len(final_content.strip()) < 10:
                return

            # ライフログエントリーを自動分析・生成
            lifelog_entry = (
                await self.lifelog_message_handler.analyze_message_for_lifelog(
                    final_content, str(original_message.author.id)
                )
            )

            if lifelog_entry and self.lifelog_manager:
                # ライフログエントリーを保存
                entry_id = await self.lifelog_manager.add_entry(lifelog_entry)

                # Obsidian ノートを生成
                await self.create_lifelog_obsidian_note(
                    lifelog_entry, message_data, channel_info
                )

                self.logger.info(
                    "ライフログエントリーを自動生成しました",
                    entry_id=entry_id,
                    category=lifelog_entry.category,
                    type=lifelog_entry.type,
                    title=lifelog_entry.title,
                )

                # Discord に通知（オプション）
                if hasattr(original_message, "add_reaction"):
                    try:
                        await original_message.add_reaction(
                            "📝"
                        )  # ライフログ記録を示すリアクション
                    except Exception as e:
                        self.logger.debug(
                            "Failed to add reaction", error=str(e)
                        )  # リアクション追加は必須ではない

        except Exception as e:
            self.logger.warning("ライフログ自動検出でエラー", error=str(e))

    async def create_lifelog_obsidian_note(
        self,
        lifelog_entry: Any,
        message_data: dict[str, Any],
        channel_info: Any,
    ) -> dict[str, Any]:
        """ライフログ Obsidian ノート作成"""
        try:
            from pathlib import Path

            # カテゴリに基づいてフォルダを決定
            folder_map = {
                "health": "21_Health",
                "work": "11_Projects",
                "learning": "10_Knowledge",
                "finance": "20_Finance",
                "mood": "01_DailyNotes",
                "routine": "01_DailyNotes",
                "reflection": "01_DailyNotes",
                "goal": "02_Tasks",
                "relationship": "01_DailyNotes",
                "entertainment": "01_DailyNotes",
            }

            folder = folder_map.get(str(lifelog_entry.category).lower(), "00_Inbox")

            # ファイル名を生成
            timestamp = lifelog_entry.timestamp.strftime("%Y%m%d_%H%M")
            safe_title = "".join(
                c for c in lifelog_entry.title if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            safe_title = safe_title[:50] if len(safe_title) > 50 else safe_title
            filename = f"lifelog_{timestamp}_{safe_title}.md"

            # ノート内容を生成
            note_content = f"""# {lifelog_entry.title}

## 📅 基本情報
- **日時**: {lifelog_entry.timestamp.strftime("%Y-%m-%d %H:%M")}
- **カテゴリ**: {lifelog_entry.category}
- **タイプ**: {lifelog_entry.type}

## 📝 内容
{lifelog_entry.content}

## 🏷️ タグ
#{lifelog_entry.category} #lifelog

---
*自動生成されたライフログエントリー*
"""

            # ファイルパス
            file_path = f"{folder}/{filename}"

            # ローカルファイルに保存（簡略化）
            try:
                import aiofiles

                vault_path = Path("/app/vault")
                local_folder = vault_path / folder
                local_folder.mkdir(parents=True, exist_ok=True)
                local_file_path = local_folder / filename

                async with aiofiles.open(local_file_path, "w", encoding="utf-8") as f:
                    await f.write(note_content)

                self.logger.info(
                    "ライフログ Obsidian ノートを作成しました",
                    file_path=file_path,
                    category=lifelog_entry.category,
                )

                return {"status": "success", "file_path": file_path}

            except Exception:
                return {"status": "error", "error": "ファイル保存に失敗"}

        except Exception as e:
            self.logger.error("ライフログ Obsidian ノート作成でエラー", error=str(e))
            return {"status": "error", "error": str(e)}

    async def handle_system_message(
        self,
        message_data: dict[str, Any],
        channel_info: Any,
        original_message: discord.Message | None = None,
    ) -> None:
        """システムメッセージ処理"""
        self.logger.info(
            "Handling system message",
            channel_name=channel_info.name if channel_info else "unknown",
        )

        # Process system-related messages
        try:
            content = message_data.get("content", "").strip()

            # Detect bot commands (starting with / or !)
            if content.startswith(("//", "!!")):
                command = content.split()[0] if content.split() else ""
                self.logger.info("Bot command detected", command=command)
                # Add command tag for future processing
                if "metadata" not in message_data:
                    message_data["metadata"] = {}
                if "tags" not in message_data["metadata"]:
                    message_data["metadata"]["tags"] = []
                message_data["metadata"]["tags"].append("command")

            # Detect configuration updates
            config_keywords = ["config", "setting", "configure", "設定", "環境設定"]
            if any(keyword in content.lower() for keyword in config_keywords):
                self.logger.info("Configuration-related content detected")
                # Add config tag for future processing
                if "metadata" not in message_data:
                    message_data["metadata"] = {}
                if "tags" not in message_data["metadata"]:
                    message_data["metadata"]["tags"] = []
                message_data["metadata"]["tags"].append("config")

            # Log system notifications for monitoring
            if (
                content and len(content) > 10
            ):  # Avoid logging empty or very short messages
                self.logger.debug("System message logged", content_length=len(content))

        except Exception as e:
            self.logger.error("Error processing system message", error=str(e))

    def is_lifelog_candidate(self, message_content: str) -> bool:
        """メッセージがライフログ候補かどうかを判定"""
        # 簡単な判定ロジック（実際の実装は移動予定）
        lifelog_keywords = [
            "食べた",
            "飲んだ",
            "寝た",
            "起きた",
            "運動",
            "勉強",
            "仕事",
            "買い物",
            "映画",
            "読書",
            "散歩",
            "会議",
            "電話",
        ]
        return any(keyword in message_content for keyword in lifelog_keywords)
