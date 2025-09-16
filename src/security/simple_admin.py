"""
Simple admin authentication for personal use.
個人使用向けのシンプルな管理者権限システム
"""

import os
from collections.abc import Callable
from typing import Any

import discord
import structlog

logger = structlog.get_logger(__name__)


class SimpleAdminAuth:
    """個人使用向けシンプル管理者権限システム"""

    def __init__(self) -> None:
        # 環境変数から自分のユーザー ID を取得（オプション）
        owner_id_str = os.getenv("DISCORD_OWNER_ID", "")
        self.owner_id: int | None = int(owner_id_str) if owner_id_str.strip() else None

        logger.info(
            "SimpleAdminAuth initialized",
            has_owner_id=self.owner_id is not None,
            owner_id_masked=f"...{str(self.owner_id)[-4:]}" if self.owner_id else None,
        )

    def is_admin(self, user: discord.User | discord.Member) -> bool:
        """ユーザーが管理者かどうかを判定"""
        # 環境変数でオーナー ID が設定されている場合はそれをチェック
        if self.owner_id and user.id == self.owner_id:
            return True

        # Discord サーバーの管理者権限をチェック（サーバー内の場合）
        if hasattr(user, "guild_permissions") and user.guild_permissions.administrator:
            return True

        return False

    async def check_admin_command(self, interaction: discord.Interaction) -> bool:
        """管理者コマンドの権限チェック"""
        if not self.is_admin(interaction.user):
            await interaction.response.send_message(
                "🔒 このコマンドは管理者のみ実行できます。", ephemeral=True
            )

            # セキュリティログ
            logger.warning(
                "Unauthorized admin command attempt",
                user_id=interaction.user.id,
                username=str(interaction.user),
                command=getattr(interaction.command, "name", "unknown"),
            )
            return False

        # 成功ログ
        logger.info(
            "Admin command authorized",
            user_id=interaction.user.id,
            command=getattr(interaction.command, "name", "unknown"),
        )
        return True


# グローバルインスタンス
_simple_admin = None


def get_simple_admin() -> SimpleAdminAuth:
    """SimpleAdminAuth のシングルトンインスタンスを取得"""
    global _simple_admin
    if _simple_admin is None:
        _simple_admin = SimpleAdminAuth()
    return _simple_admin


def admin_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """管理者権限が必要なコマンドのデコレータ（個人使用向け）"""

    async def wrapper(
        self: Any, interaction: discord.Interaction, *args: Any, **kwargs: Any
    ) -> Any:
        admin_auth = get_simple_admin()

        if not await admin_auth.check_admin_command(interaction):
            return

        # 認証成功時は元の関数を実行
        return await func(self, interaction, *args, **kwargs)

    return wrapper
