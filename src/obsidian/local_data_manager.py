"""
ローカルデータ管理システム
デプロイ環境での Obsidian Vault データの永続化と管理
"""

import asyncio
import json
import shutil
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles

from src.obsidian.models import LocalDataIndex
from src.utils.mixins import LoggerMixin


class LocalDataManager(LoggerMixin):
    """ローカルデータ管理システム"""

    def __init__(self, vault_path: Path, backup_path: Path | None = None):
        """
        初期化

        Args:
            vault_path: Obsidian vault のパス
            backup_path: バックアップ保存先（デフォルトは vault_path/backups ）
        """
        self.vault_path = vault_path
        self.backup_path = backup_path or vault_path / "backups"
        self.data_index = LocalDataIndex(vault_path)

        # ローカルデータ管理用ディレクトリ
        self.local_data_dir = vault_path / ".local_data"
        self.snapshots_dir = self.local_data_dir / "snapshots"
        self.exports_dir = self.local_data_dir / "exports"

        # 設定ファイル
        self.config_file = self.local_data_dir / "config.json"
        self.sync_log_file = self.local_data_dir / "sync_log.json"

        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """必要なディレクトリを作成"""
        for directory in [
            self.backup_path,
            self.local_data_dir,
            self.snapshots_dir,
            self.exports_dir,
        ]:
            directory.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> bool:
        """ローカルデータ管理システムを初期化"""
        try:
            # インデックスの初期化
            await self.rebuild_index()

            # 初期設定の作成
            await self._create_initial_config()

            # 初期スナップショットの作成
            snapshot_path = await self.create_snapshot("initial_setup")

            self.logger.info(
                "Local data manager initialized",
                vault_path=str(self.vault_path),
                snapshot_path=str(snapshot_path) if snapshot_path else None,
            )

            return True

        except Exception as e:
            self.logger.error(
                "Failed to initialize local data manager",
                error=str(e),
                exc_info=True,
            )
            return False

    async def _create_initial_config(self) -> None:
        """初期設定ファイルを作成"""
        if not self.config_file.exists():
            config = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "auto_backup_enabled": True,
                "backup_retention_days": 30,
                "snapshot_retention_count": 50,
                "compression_enabled": True,
                "sync_intervals": {
                    "full_backup": "daily",
                    "incremental_sync": "hourly",
                    "index_rebuild": "weekly",
                },
            }

            async with aiofiles.open(self.config_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(config, ensure_ascii=False, indent=2))

    async def rebuild_index(self) -> bool:
        """インデックスを完全に再構築"""
        try:
            self.logger.info("Starting index rebuild")

            # 既存インデックスをクリア
            self.data_index.notes_index.clear()
            self.data_index.tags_index.clear()
            self.data_index.links_index.clear()
            self.data_index.content_index.clear()

            # すべての Markdown ファイルを処理
            processed_count = 0
            for md_file in self.vault_path.rglob("*.md"):
                # システムファイルとテンプレートを除外
                relative_path = md_file.relative_to(self.vault_path)
                if any(part.startswith(".") for part in relative_path.parts):
                    continue
                if "templates" in str(relative_path).lower():
                    continue

                # ノートを読み込み、インデックスに追加
                try:
                    # 簡易的なノート情報を抽出
                    stat = md_file.stat()
                    async with aiofiles.open(md_file, encoding="utf-8") as f:
                        content = await f.read()

                    # フロントマターとコンテンツを分離
                    frontmatter, main_content = self._parse_frontmatter(content)

                    # インデックスに追加
                    file_key = str(relative_path)
                    self.data_index.notes_index[file_key] = {
                        "title": frontmatter.get("title", md_file.stem),
                        "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        "modified_at": datetime.fromtimestamp(
                            stat.st_mtime
                        ).isoformat(),
                        "status": frontmatter.get("status", "active"),
                        "category": frontmatter.get("ai_category"),
                        "file_size": len(content.encode()),
                        "word_count": len(main_content.split()),
                        "ai_processed": frontmatter.get("ai_processed", False),
                        "ai_summary": frontmatter.get("ai_summary"),
                    }

                    # タグインデックス
                    tags = frontmatter.get("ai_tags", []) + frontmatter.get("tags", [])
                    for tag in tags:
                        clean_tag = tag.lstrip("#")
                        if clean_tag not in self.data_index.tags_index:
                            self.data_index.tags_index[clean_tag] = set()
                        self.data_index.tags_index[clean_tag].add(file_key)

                    # コンテンツインデックス
                    words = main_content.lower().split()
                    self.data_index.content_index[file_key] = list(set(words))

                    processed_count += 1

                except Exception as e:
                    self.logger.warning(
                        "Failed to process file for indexing",
                        file_path=str(md_file),
                        error=str(e),
                    )

            # インデックスを保存
            success = self.data_index.save_indexes()

            self.logger.info(
                "Index rebuild completed",
                processed_files=processed_count,
                success=success,
            )

            return success

        except Exception as e:
            self.logger.error(
                "Failed to rebuild index",
                error=str(e),
                exc_info=True,
            )
            return False

    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """フロントマターとコンテンツを分離"""
        import yaml

        if not content.startswith("---\n"):
            return {}, content

        try:
            parts = content.split("---\n", 2)
            if len(parts) >= 3:
                frontmatter_data = yaml.safe_load(parts[1]) or {}
                main_content = parts[2]
                return frontmatter_data, main_content
        except yaml.YAMLError:
            pass

        return {}, content

    async def create_snapshot(self, name: str | None = None) -> Path | None:
        """
        Vault の現在の状態のスナップショットを作成

        Args:
            name: スナップショット名（省略時は自動生成）

        Returns:
            作成されたスナップショットファイルのパス
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_name = name or f"snapshot_{timestamp}"
            snapshot_file = self.snapshots_dir / f"{snapshot_name}.tar.gz"

            # スナップショット作成
            with tarfile.open(snapshot_file, "w:gz") as tar:
                # Vault ディレクトリを追加（隠しファイルも含む）
                tar.add(
                    self.vault_path,
                    arcname="vault",
                    filter=self._tar_filter,
                )

                # インデックスファイルも追加
                if self.data_index.index_file.exists():
                    tar.add(
                        self.data_index.index_file,
                        arcname="vault/.obsidian_local_index.json",
                    )

            # メタデータを記録
            metadata = {
                "name": snapshot_name,
                "created_at": datetime.now().isoformat(),
                "vault_path": str(self.vault_path),
                "file_size": snapshot_file.stat().st_size,
                "notes_count": len(self.data_index.notes_index),
            }

            metadata_file = self.snapshots_dir / f"{snapshot_name}.meta.json"
            async with aiofiles.open(metadata_file, "w", encoding="utf-8") as f:
                await f.write(json.dumps(metadata, ensure_ascii=False, indent=2))

            self.logger.info(
                "Snapshot created",
                snapshot_name=snapshot_name,
                file_size_mb=snapshot_file.stat().st_size / (1024 * 1024),
                notes_count=metadata["notes_count"],
            )

            # 古いスナップショットの削除
            await self._cleanup_old_snapshots()

            return snapshot_file

        except Exception as e:
            self.logger.error(
                "Failed to create snapshot",
                name=name,
                error=str(e),
                exc_info=True,
            )
            return None

    def _tar_filter(self, tarinfo):
        """tar ファイル作成時のフィルター"""
        # バックアップディレクトリと一時ファイルを除外
        if any(
            exclude in tarinfo.name
            for exclude in [
                "backups/",
                ".local_data/",
                "__pycache__/",
                ".git/",
                ".DS_Store",
                "Thumbs.db",
                ".tmp",
            ]
        ):
            return None
        return tarinfo

    async def restore_snapshot(
        self, snapshot_file: Path, restore_path: Path | None = None
    ) -> bool:
        """
        スナップショットから Vault を復元

        Args:
            snapshot_file: 復元するスナップショットファイル
            restore_path: 復元先パス（省略時は元の vault_path ）

        Returns:
            復元の成功可否
        """
        try:
            target_path = restore_path or self.vault_path

            # バックアップを作成
            backup_name = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backup_snapshot = await self.create_snapshot(backup_name)

            # 既存の Vault をバックアップ
            if target_path.exists():
                temp_backup = (
                    target_path.parent
                    / f"{target_path.name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                shutil.move(str(target_path), str(temp_backup))

            # スナップショットを展開
            with tarfile.open(snapshot_file, "r:gz") as tar:
                tar.extractall(target_path.parent)

                # vault ディレクトリをリネーム
                extracted_vault = target_path.parent / "vault"
                if extracted_vault.exists():
                    shutil.move(str(extracted_vault), str(target_path))

            # インデックスを再構築
            await self.rebuild_index()

            self.logger.info(
                "Snapshot restored successfully",
                snapshot_file=str(snapshot_file),
                target_path=str(target_path),
                backup_snapshot=str(backup_snapshot) if backup_snapshot else None,
            )

            return True

        except Exception as e:
            self.logger.error(
                "Failed to restore snapshot",
                snapshot_file=str(snapshot_file),
                error=str(e),
                exc_info=True,
            )
            return False

    async def export_vault_data(self, format: str = "json") -> Path | None:
        """
        Vault データを指定形式でエクスポート

        Args:
            format: エクスポート形式（ json, csv, md ）

        Returns:
            エクスポートファイルのパス
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if format == "json":
                export_file = self.exports_dir / f"vault_export_{timestamp}.json"

                # JSON 形式でエクスポート
                export_data = {
                    "metadata": {
                        "exported_at": datetime.now().isoformat(),
                        "vault_path": str(self.vault_path),
                        "total_notes": len(self.data_index.notes_index),
                    },
                    "notes": self.data_index.notes_index,
                    "tags": {k: list(v) for k, v in self.data_index.tags_index.items()},
                    "statistics": self.data_index.get_stats(),
                }

                async with aiofiles.open(export_file, "w", encoding="utf-8") as f:
                    await f.write(json.dumps(export_data, ensure_ascii=False, indent=2))

            elif format == "zip":
                export_file = self.exports_dir / f"vault_export_{timestamp}.zip"

                # ZIP 形式でエクスポート
                with zipfile.ZipFile(export_file, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for md_file in self.vault_path.rglob("*.md"):
                        if not any(
                            part.startswith(".")
                            for part in md_file.relative_to(self.vault_path).parts
                        ):
                            arcname = str(md_file.relative_to(self.vault_path))
                            zipf.write(md_file, arcname)

                    # インデックスファイルも追加
                    if self.data_index.index_file.exists():
                        zipf.write(self.data_index.index_file, "index.json")

            else:
                raise ValueError(f"Unsupported export format: {format}")

            self.logger.info(
                "Vault data exported",
                format=format,
                export_file=str(export_file),
                file_size_mb=export_file.stat().st_size / (1024 * 1024),
            )

            return export_file

        except Exception as e:
            self.logger.error(
                "Failed to export vault data",
                format=format,
                error=str(e),
                exc_info=True,
            )
            return None

    async def sync_with_remote(
        self, remote_path: Path, direction: str = "both"
    ) -> bool:
        """
        リモートロケーションとの同期

        Args:
            remote_path: リモート同期先
            direction: 同期方向（"upload", "download", "both"）

        Returns:
            同期の成功可否
        """
        try:
            sync_log: dict[str, Any] = {
                "started_at": datetime.now().isoformat(),
                "direction": direction,
                "remote_path": str(remote_path),
                "files_synced": 0,
                "errors": [],
            }

            if direction in ["upload", "both"]:
                # アップロード: ローカル → リモート
                await self._sync_to_remote(remote_path, sync_log)

            if direction in ["download", "both"]:
                # ダウンロード: リモート → ローカル
                await self._sync_from_remote(remote_path, sync_log)

            # 同期後にインデックスを再構築
            await self.rebuild_index()

            # 同期ログを保存
            sync_log["completed_at"] = datetime.now().isoformat()
            sync_log["success"] = len(sync_log.get("errors", [])) == 0

            async with aiofiles.open(self.sync_log_file, "a", encoding="utf-8") as f:
                await f.write(json.dumps(sync_log, ensure_ascii=False) + "\n")

            self.logger.info(
                "Sync completed",
                direction=direction,
                files_synced=sync_log.get("files_synced", 0),
                errors_count=len(sync_log.get("errors", [])),
            )

            return bool(sync_log.get("success", False))

        except Exception as e:
            self.logger.error(
                "Failed to sync with remote",
                remote_path=str(remote_path),
                direction=direction,
                error=str(e),
                exc_info=True,
            )
            return False

    async def _sync_to_remote(self, remote_path: Path, sync_log: dict) -> None:
        """ローカルからリモートへの同期"""
        remote_path.mkdir(parents=True, exist_ok=True)

        for md_file in self.vault_path.rglob("*.md"):
            try:
                relative_path = md_file.relative_to(self.vault_path)
                remote_file = remote_path / relative_path

                # ディレクトリを作成
                remote_file.parent.mkdir(parents=True, exist_ok=True)

                # ファイルをコピー
                await asyncio.to_thread(shutil.copy2, md_file, remote_file)
                sync_log["files_synced"] += 1

            except Exception as e:
                error_msg = f"Failed to sync {md_file}: {str(e)}"
                sync_log["errors"].append(error_msg)
                self.logger.warning(error_msg)

    async def _sync_from_remote(self, remote_path: Path, sync_log: dict) -> None:
        """リモートからローカルへの同期"""
        if not remote_path.exists():
            return

        for remote_file in remote_path.rglob("*.md"):
            try:
                relative_path = remote_file.relative_to(remote_path)
                local_file = self.vault_path / relative_path

                # ディレクトリを作成
                local_file.parent.mkdir(parents=True, exist_ok=True)

                # ファイルをコピー（新しいもののみ）
                if (
                    not local_file.exists()
                    or remote_file.stat().st_mtime > local_file.stat().st_mtime
                ):
                    await asyncio.to_thread(shutil.copy2, remote_file, local_file)
                    sync_log["files_synced"] += 1

            except Exception as e:
                error_msg = f"Failed to sync {remote_file}: {str(e)}"
                sync_log["errors"].append(error_msg)
                self.logger.warning(error_msg)

    async def _cleanup_old_snapshots(self) -> None:
        """古いスナップショットを削除"""
        try:
            # 設定から保持数を取得
            config = await self._load_config()
            retention_count = config.get("snapshot_retention_count", 50)

            # スナップショットファイルをリストアップ
            snapshots = []
            for file in self.snapshots_dir.glob("*.tar.gz"):
                if file.is_file():
                    snapshots.append((file.stat().st_mtime, file))

            # 作成日時でソート（新しい順）
            snapshots.sort(key=lambda x: x[0], reverse=True)

            # 古いスナップショットを削除
            for _, file in snapshots[retention_count:]:
                file.unlink()
                # メタデータファイルも削除
                meta_file = file.with_suffix(".meta.json")
                if meta_file.exists():
                    meta_file.unlink()

                self.logger.debug("Old snapshot deleted", file=str(file))

        except Exception as e:
            self.logger.warning("Failed to cleanup old snapshots", error=str(e))

    async def _load_config(self) -> dict:
        """設定ファイルを読み込み"""
        try:
            if self.config_file.exists():
                async with aiofiles.open(self.config_file, encoding="utf-8") as f:
                    content = await f.read()
                    return json.loads(content)
        except Exception:
            pass

        return {}

    async def get_local_stats(self) -> dict:
        """ローカルデータ管理の統計情報を取得"""
        try:
            # スナップショット情報
            snapshots = list(self.snapshots_dir.glob("*.tar.gz"))
            total_snapshot_size = sum(f.stat().st_size for f in snapshots)

            # エクスポート情報
            exports = list(self.exports_dir.glob("*"))
            total_export_size = sum(f.stat().st_size for f in exports if f.is_file())

            # インデックス統計
            index_stats = self.data_index.get_stats()

            return {
                "local_data_directory": str(self.local_data_dir),
                "snapshots": {
                    "count": len(snapshots),
                    "total_size_mb": total_snapshot_size / (1024 * 1024),
                    "latest": max((f.stat().st_mtime for f in snapshots), default=0),
                },
                "exports": {
                    "count": len(exports),
                    "total_size_mb": total_export_size / (1024 * 1024),
                },
                "index": index_stats,
                "vault_path": str(self.vault_path),
                "backup_path": str(self.backup_path),
            }

        except Exception as e:
            self.logger.error("Failed to get local stats", error=str(e), exc_info=True)
            return {}
