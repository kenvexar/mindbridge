"""
GitHub-based Obsidian vault synchronization system
"""

import asyncio
import os
import subprocess  # nosec: B404 - subprocess used safely for git operations with validation
from datetime import datetime
from pathlib import Path
from typing import Any, cast

from src.config import get_settings
from src.utils.mixins import LoggerMixin


class GitHubSyncError(Exception):
    """GitHub 同期エラー"""

    pass


class GitHubObsidianSync(LoggerMixin):
    """GitHub を使用した Obsidian vault の永続化システム"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.vault_path = self.settings.obsidian_vault_path
        provider_raw = cast(
            str,
            os.getenv("GIT_PROVIDER")
            or getattr(self.settings, "git_provider", None)
            or "github",
        )
        self.git_provider = provider_raw.lower()
        self.token_env_var = "GIT_REMOTE_TOKEN"
        self.github_token = self._resolve_git_token()
        self.github_repo_url = self.settings.obsidian_backup_repo or os.getenv(
            "OBSIDIAN_BACKUP_REPO"
        )
        self.github_branch = self.settings.obsidian_backup_branch or os.getenv(
            "OBSIDIAN_BACKUP_BRANCH", "main"
        )

        # Git 設定
        self.git_user_name = self.settings.git_user_name or os.getenv(
            "GIT_USER_NAME", "ObsidianBot"
        )
        self.git_user_email = self.settings.git_user_email or os.getenv(
            "GIT_USER_EMAIL", "bot@example.com"
        )

        self._validate_configuration()

    def _resolve_git_token(self) -> str | None:
        """プロバイダに応じたトークンを解決する。

        優先順位: 設定ファイルの `github_token` → `GIT_REMOTE_TOKEN`
        → プロバイダ別の環境変数（GitLab: `GITLAB_TOKEN`, GitHub: `GITHUB_TOKEN`）。
        """

        gitlab_token = getattr(self.settings, "gitlab_token", None)
        if self.git_provider.startswith("gitlab") and gitlab_token is not None:
            # テストが期待する環境変数名に合わせて保持
            self.token_env_var = "GITLAB_TOKEN"
            return str(gitlab_token.get_secret_value())

        github_token = self.settings.github_token
        if github_token is not None:
            # GitHub トークンを設定から取得した場合も環境変数名を明示
            self.token_env_var = "GITHUB_TOKEN"
            return str(github_token.get_secret_value())

        env_order = ["GIT_REMOTE_TOKEN"]
        if self.git_provider.startswith("gitlab"):
            env_order.append("GITLAB_TOKEN")
        env_order.append("GITHUB_TOKEN")

        for key in env_order:
            value = os.getenv(key)
            if value:
                # ヘルパー内で参照する環境変数名を保持
                self.token_env_var = key
                return value

        return None

    def _validate_configuration(self) -> None:
        """設定の検証"""
        if not self.github_token:
            self.logger.warning("Git token not set, remote sync disabled")
            return

        if not self.github_repo_url:
            self.logger.warning("OBSIDIAN_BACKUP_REPO not set, remote sync disabled")
            return

        self.logger.info(
            "Git sync configuration validated",
            git_provider=self.git_provider,
            repo=self.github_repo_url,
        )

    @property
    def is_configured(self) -> bool:
        """GitHub 同期が設定されているかチェック"""
        return bool(self.github_token and self.github_repo_url)

    async def setup_git_repository(self) -> bool:
        """Git リポジトリの初期化"""
        if not self.is_configured:
            self.logger.warning("GitHub sync not configured")
            return False

        try:
            # Vault ディレクトリが存在しない場合は作成
            self.vault_path.mkdir(parents=True, exist_ok=True)

            # Git リポジトリの初期化
            if not (self.vault_path / ".git").exists():
                try:
                    await self._run_git_command(["init"])
                    self.logger.info("Git repository initialized")
                except Exception as e:
                    self.logger.warning(f"Git init failed: {e}")
                    return False

            # リモートリポジトリの設定（エラーがあっても継続）
            try:
                await self._setup_remote_repository()
            except Exception as e:
                self.logger.warning(f"Remote setup failed, but continuing: {e}")

            # Git ユーザー設定
            try:
                await self._configure_git_user()
            except Exception as e:
                self.logger.warning(f"Git user config failed: {e}")

            # .gitignore の設定
            try:
                await self._setup_gitignore()
            except Exception as e:
                self.logger.warning(f"Gitignore setup failed: {e}")

            self.logger.info("Git repository setup completed (with possible warnings)")
            return True

        except Exception as e:
            self.logger.error(f"Failed to setup Git repository: {e}")
            return False

    async def _setup_remote_repository(self) -> None:
        """リモートリポジトリの設定

        リモート URL には認証トークンを含めず、
        `git -c credential.helper=...` で指定したヘルパー経由で
        トークン（`GIT_REMOTE_TOKEN` など）を安全に供給する。
        """
        try:
            # Git リポジトリが初期化されているかチェック
            if not (self.vault_path / ".git").exists():
                self.logger.warning(
                    "Git repository not initialized, skipping remote setup"
                )
                return

            # 既存のリモートをチェック（エラーを抑制）
            result = await self._run_git_command(
                ["remote", "get-url", "origin"], check=False
            )

            if result.returncode != 0:
                # リモートが存在しない場合は追加
                try:
                    repo_url = self._get_authenticated_repo_url()
                    await self._run_git_command(
                        ["remote", "add", "origin", repo_url],
                        check=False,
                    )
                    self.logger.info("Remote repository added")
                except Exception as e:
                    self.logger.warning(f"Failed to add remote: {e}")
                    # リモート追加失敗は非致命的エラーとして継続
            else:
                # 既存のリモートを更新
                try:
                    repo_url = self._get_authenticated_repo_url()
                    await self._run_git_command(
                        ["remote", "set-url", "origin", repo_url],
                        check=False,
                    )
                    self.logger.info("Remote repository URL updated")
                except Exception as e:
                    self.logger.warning(f"Failed to update remote: {e}")
                    # リモート更新失敗も非致命的エラーとして継続

        except Exception as e:
            self.logger.warning(f"Remote repository setup encountered issues: {e}")
            # 致命的でないエラーとして処理を継続

    async def _configure_git_user(self) -> None:
        """Git ユーザー設定"""
        await self._run_git_command(["config", "user.name", self.git_user_name])
        await self._run_git_command(["config", "user.email", self.git_user_email])
        self.logger.debug("Git user configuration set")

    def _build_credential_helper(self) -> str:
        """Return the credential helper script that reads the selected token at runtime."""
        username = (
            "oauth2" if self.git_provider.startswith("gitlab") else "x-access-token"
        )
        return (
            "!f() { echo username="
            f"{username}; echo password=${self.token_env_var}; }}; f"
        )

    async def _setup_gitignore(self) -> None:
        """.gitignore の設定"""
        gitignore_path = self.vault_path / ".gitignore"
        if not gitignore_path.exists():
            gitignore_content = """
# Obsidian workspace files
.obsidian/workspace*
.obsidian/hotkeys.json
.obsidian/core-plugins-migration.json

# System files
.DS_Store
Thumbs.db

# Temporary files
*.tmp
*.temp
*~
""".strip()
            gitignore_path.write_text(gitignore_content, encoding="utf-8")
            self.logger.info("Created .gitignore file")

    def _get_authenticated_repo_url(self) -> str:
        """Return repository URL without embedding secrets.

        認証情報は `_build_credential_helper` がトークンを差し込むため、
        ここではプレーンな HTTPS URL のみを扱う。
        """
        if self.github_repo_url is None:
            raise GitHubSyncError("Remote repository URL is not configured")

        if not self.github_repo_url.startswith("https://"):
            self.logger.warning(
                "Non-HTTPS repository URL detected; consider using HTTPS for security"
            )
        else:
            self.logger.debug("Using repository URL without embedding token")
        return self.github_repo_url

    async def sync_to_github(self, commit_message: str | None = None) -> bool:
        """Obsidian vault を GitHub に同期"""
        if not self.is_configured:
            self.logger.warning("GitHub sync not configured, skipping sync")
            return False

        try:
            # 変更があるかチェック
            if not await self._has_changes():
                self.logger.debug("No changes to sync")
                return True

            # ステージング
            await self._run_git_command(["add", "."])

            # コミット
            message = commit_message or f"Auto-sync: {datetime.now().isoformat()}"
            await self._run_git_command(["commit", "-m", message])

            # プッシュ（初回プッシュに対応）
            await self._push_with_retry()

            self.logger.info("Successfully synced vault to GitHub")
            return True

        except Exception as e:
            self.logger.error(f"Failed to sync to GitHub: {e}")
            return False

    async def _push_with_retry(self) -> None:
        """初回プッシュに対応したプッシュ処理"""
        try:
            # 設定されたブランチを強制的に使用（現在のブランチに依存しない）
            target_branch = self.github_branch  # 常に設定されたブランチ（ main ）を使用

            # 現在のブランチを確認（デバッグ用）
            branch_result = await self._run_git_command(
                ["branch", "--show-current"], capture_output=True, check=False
            )
            current_branch = (
                branch_result.stdout.strip()
                if branch_result.returncode == 0
                else "none"
            )

            self.logger.info(
                f"Current branch: {current_branch}, Target branch: {target_branch}"
            )

            # 目標ブランチが現在のブランチと異なる場合は切り替え
            if current_branch != target_branch:
                # ブランチが存在するかチェック
                branch_exists = await self._run_git_command(
                    ["branch", "--list", target_branch],
                    capture_output=True,
                    check=False,
                )

                if branch_exists.stdout.strip():
                    # ブランチが存在する場合は切り替え
                    await self._run_git_command(["checkout", target_branch])
                    self.logger.info(f"Switched to existing branch: {target_branch}")
                else:
                    # ブランチが存在しない場合は作成して切り替え
                    await self._run_git_command(["checkout", "-b", target_branch])
                    self.logger.info(
                        f"Created and switched to new branch: {target_branch}"
                    )

            # 最初に通常のプッシュを試行
            push_result = await self._run_git_command(
                ["push", "origin", target_branch], check=False, capture_output=True
            )

            if push_result.returncode == 0:
                self.logger.info(f"Push successful to {target_branch}")
                return

            stderr_lower = push_result.stderr.lower()

            # リモートに新しいコミットがある場合は pull --rebase を試行
            if "fetch first" in stderr_lower or "non-fast-forward" in stderr_lower:
                self.logger.info(
                    f"Remote ahead detected, rebasing before push to {target_branch}"
                )
                # 進行中のリベースが残っている場合に備えて abort を試みる
                await self._run_git_command(
                    ["rebase", "--abort"], check=False, capture_output=True
                )
                pull_result = await self._run_git_command(
                    ["pull", "--rebase", "origin", target_branch],
                    check=False,
                    capture_output=True,
                )

                if pull_result.returncode != 0:
                    # リベースが失敗した場合は必ず abort しておく
                    await self._run_git_command(
                        ["rebase", "--abort"], check=False, capture_output=True
                    )
                    raise GitHubSyncError(
                        f"Pull before push failed: {pull_result.stderr}"
                    )

                retry_result = await self._run_git_command(
                    ["push", "origin", target_branch],
                    check=False,
                    capture_output=True,
                )

                if retry_result.returncode == 0:
                    self.logger.info(f"Push successful after rebase to {target_branch}")
                    return

                raise GitHubSyncError(
                    f"Push failed after rebase to {target_branch}: {retry_result.stderr}"
                )

            # 初回プッシュの場合は upstream を設定してリトライ
            if (
                "does not match any" in push_result.stderr
                or "no upstream branch" in push_result.stderr
            ):
                self.logger.info(
                    f"Attempting first push with upstream setup to {target_branch}"
                )
                await self._run_git_command(["push", "-u", "origin", target_branch])
                self.logger.info(f"First push successful to {target_branch}")
                return

            # その他のエラーは再発生させる
            raise GitHubSyncError(
                f"Push failed to {target_branch}: {push_result.stderr}"
            )

        except Exception as e:
            self.logger.error(f"Push failed: {e}")
            raise

    async def sync_from_github(self) -> bool:
        """GitHub から Obsidian vault を同期"""
        if not self.is_configured:
            self.logger.warning("GitHub sync not configured, skipping sync")
            return False

        try:
            # リポジトリが存在するかチェック
            if not (self.vault_path / ".git").exists():
                # 初回クローン
                return await self._clone_repository()

            # 既存リポジトリの場合はプル
            await self._run_git_command(["fetch", "origin"])
            await self._run_git_command(
                ["reset", "--hard", f"origin/{self.github_branch}"]
            )

            self.logger.info("Successfully synced vault from GitHub")
            return True

        except Exception as e:
            self.logger.error(f"Failed to sync from GitHub: {e}")
            return False

    async def _clone_repository(self) -> bool:
        """リポジトリをクローン"""
        try:
            # 既存のディレクトリを削除（空でない場合）
            if self.vault_path.exists():
                import shutil

                from ...utils.logger import secure_file_operation

                # セキュリティチェック
                if not secure_file_operation("delete", self.vault_path, Path.home()):
                    raise GitHubSyncError("Unsafe path operation blocked")

                shutil.rmtree(self.vault_path)

            # 親ディレクトリを作成
            self.vault_path.parent.mkdir(parents=True, exist_ok=True)

            # クローン
            repo_url = self._get_authenticated_repo_url()
            process = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                repo_url,
                str(self.vault_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.vault_path.parent,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise GitHubSyncError(f"Clone failed: {stderr.decode()}")

            self.logger.info("Repository cloned successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to clone repository: {e}")
            return False

    async def _has_changes(self) -> bool:
        """変更があるかチェック"""
        try:
            result = await self._run_git_command(
                ["status", "--porcelain"], capture_output=True
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    async def _run_git_command(
        self, args: list[str], capture_output: bool = False, check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """Git コマンドを実行（credential helper を通じたトークン供給）。"""
        # Vault パスが存在しない場合は作成
        if not self.vault_path.exists():
            self.vault_path.mkdir(parents=True, exist_ok=True)
            self.logger.debug(f"Created vault directory: {self.vault_path}")

        cmd = ["git", "-C", str(self.vault_path)]

        if self.github_token:
            helper = self._build_credential_helper()
            cmd += ["-c", f"credential.helper={helper}"]

        cmd += args

        # 環境変数をコピー（シンプルな実装）
        env = os.environ.copy()
        if self.github_token:
            env[self.token_env_var] = self.github_token
            env.setdefault("GIT_TERMINAL_PROMPT", "0")

        try:
            if capture_output:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                    cwd=self.vault_path.parent
                    if not self.vault_path.exists()
                    else None,
                )
                stdout, stderr = await process.communicate()

                result = subprocess.CompletedProcess(
                    cmd, process.returncode or 0, stdout.decode(), stderr.decode()
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    env=env,
                    cwd=self.vault_path.parent
                    if not self.vault_path.exists()
                    else None,
                )
                returncode = await process.wait()

                result = subprocess.CompletedProcess(cmd, returncode or 0, "", "")

            if check and result.returncode != 0:
                # エラーメッセージから認証情報を除去
                safe_stderr = result.stderr
                if self.github_token:
                    safe_stderr = safe_stderr.replace(
                        str(self.github_token), "[REDACTED]"
                    )
                raise GitHubSyncError(
                    f"Git command failed: {' '.join(cmd[:3])}...\n{safe_stderr}"
                )

            return result

        except Exception as e:
            # エラーログから認証情報を除去
            safe_cmd = cmd[:3] + ["..."] if len(cmd) > 3 else cmd
            self.logger.error(f"Git command failed: {' '.join(safe_cmd)}, error: {e}")
            raise

    async def get_sync_status(self) -> dict[str, Any]:
        """同期ステータスを取得"""
        if not self.is_configured:
            return {"configured": False, "status": "GitHub sync not configured"}

        try:
            has_changes = await self._has_changes()

            # 最新コミット情報を取得
            result = await self._run_git_command(
                ["log", "-1", "--format=%H|%s|%ci"], capture_output=True
            )

            commit_info = (
                result.stdout.strip().split("|")
                if result.stdout.strip()
                else ["", "", ""]
            )

            return {
                "configured": True,
                "has_changes": has_changes,
                "last_commit_hash": commit_info[0],
                "last_commit_message": commit_info[1],
                "last_commit_date": commit_info[2],
                "repository_url": self.github_repo_url,
                "branch": self.github_branch,
            }

        except Exception as e:
            return {"configured": True, "status": f"Error getting sync status: {e}"}

    async def force_reset_from_github(self) -> bool:
        """GitHub からの強制リセット"""
        if not self.is_configured:
            self.logger.warning("GitHub sync not configured")
            return False

        try:
            self.logger.warning(
                "Performing force reset from GitHub - local changes will be lost"
            )

            # ローカルの変更を破棄
            await self._run_git_command(["reset", "--hard", "HEAD"])
            await self._run_git_command(["clean", "-fd"])

            # リモートから強制プル
            await self._run_git_command(["fetch", "origin"])
            await self._run_git_command(
                ["reset", "--hard", f"origin/{self.github_branch}"]
            )

            self.logger.info("Force reset from GitHub completed")
            return True

        except Exception as e:
            self.logger.error(f"Force reset failed: {e}")
            return False
