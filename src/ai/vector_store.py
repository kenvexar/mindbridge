"""
Vector store and semantic search system for Obsidian notes
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles

from src.utils.mixins import LoggerMixin

try:
    from src.config import get_settings
    from src.obsidian import ObsidianFileManager
except ImportError:
    # Mock for standalone testing
    class MockSettings:
        import tempfile

        obsidian_vault_path = tempfile.gettempdir() + "/vault"

    settings = MockSettings()

    class MockObsidianFileManager:
        async def search_notes(self, **kwargs: Any) -> list[Any]:
            return []

    class MockAIProcessor:
        async def generate_embeddings(self, text: str) -> list[float]:
            # 簡単なハッシュベースのダミー埋め込み
            hash_obj = hashlib.md5(text.encode(), usedforsecurity=False)
            return [
                float(int(hash_obj.hexdigest()[i : i + 2], 16)) / 255.0
                for i in range(0, 32, 2)
            ]


import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class NoteEmbedding:
    """ノートの埋め込みデータ"""

    def __init__(
        self,
        file_path: str,
        title: str,
        content_hash: str,
        embedding: list[float],
        created_at: datetime,
        updated_at: datetime,
        metadata: dict[str, Any] | None = None,
    ):
        self.file_path = file_path
        self.title = title
        self.content_hash = content_hash
        self.embedding = embedding
        self.created_at = created_at
        self.updated_at = updated_at
        self.metadata = metadata or {}

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return {
            "file_path": self.file_path,
            "title": self.title,
            "content_hash": self.content_hash,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NoteEmbedding":
        """辞書から復元"""
        return cls(
            file_path=data["file_path"],
            title=data["title"],
            content_hash=data["content_hash"],
            embedding=data["embedding"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            metadata=data.get("metadata", {}),
        )


class SemanticSearchResult:
    """セマンティック検索結果"""

    def __init__(
        self,
        file_path: str,
        title: str,
        similarity_score: float,
        content_preview: str = "",
        metadata: dict[str, Any] | None = None,
    ):
        self.file_path = file_path
        self.title = title
        self.similarity_score = similarity_score
        self.content_preview = content_preview
        self.metadata = metadata or {}


class VectorStore(LoggerMixin):
    """ベクトルストアとセマンティック検索システム"""

    def __init__(
        self,
        obsidian_file_manager: "ObsidianFileManager",
        ai_processor: Any | None = None,
    ):
        """
        初期化

        Args:
            obsidian_file_manager: Obsidian ファイルマネージャー
            ai_processor: AI 処理システム（埋め込み生成用）
        """
        self.file_manager = obsidian_file_manager or MockObsidianFileManager()
        self.ai_processor = ai_processor or MockAIProcessor()

        # ベクトルストレージ
        self.embeddings: dict[str, NoteEmbedding] = {}

        # TF-IDF バックアップ検索用
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000, stop_words="english", ngram_range=(1, 2)
        )
        self.tfidf_matrix = None
        self.file_paths_index: list[str] = []

        # 設定
        settings = get_settings()
        self.index_file_path = Path(settings.obsidian_vault_path) / ".vector_index.json"
        self.min_content_length = 10  # 最小コンテンツ長
        self.embedding_dimension = 16  # ダミー埋め込み次元数

        self.logger.info("Vector store initialized")

    async def build_index(self, force_rebuild: bool = False) -> None:
        """
        ベクトルインデックスを構築

        Args:
            force_rebuild: 強制的に再構築するかどうか
        """
        try:
            self.logger.info("Building vector index", force_rebuild=force_rebuild)

            # 既存インデックスの読み込み
            if not force_rebuild:
                await self._load_existing_index()

            # Vault の全ファイルを取得
            vault_files = await self._get_all_vault_files()

            # 新規・更新ファイルの処理
            updated_count = 0
            for file_path in vault_files:
                if await self._should_update_embedding(file_path):
                    await self._process_file_for_embedding(file_path)
                    updated_count += 1

            # 削除されたファイルのクリーンアップ
            await self._cleanup_deleted_files(vault_files)

            # TF-IDF マトリックスの更新
            await self._update_tfidf_index()

            # インデックスの保存
            await self._save_index()

            self.logger.info(
                "Vector index build completed",
                total_embeddings=len(self.embeddings),
                updated_files=updated_count,
            )

        except Exception as e:
            self.logger.error(
                "Failed to build vector index", error=str(e), exc_info=True
            )
            raise

    async def search_similar_notes(
        self,
        query_text: str,
        limit: int = 10,
        min_similarity: float = 0.1,
        exclude_files: set[str] | None = None,
    ) -> list[SemanticSearchResult]:
        """
        セマンティック検索を実行

        Args:
            query_text: 検索クエリ
            limit: 結果数制限
            min_similarity: 最小類似度
            exclude_files: 除外するファイルパス

        Returns:
            検索結果リスト
        """
        try:
            self.logger.debug("Searching similar notes", query=query_text[:50])

            exclude_files = exclude_files or set()

            # クエリの埋め込みを生成
            query_embedding = await self._generate_embedding(query_text)

            if not query_embedding:
                # フォールバック: TF-IDF 検索
                return await self._fallback_tfidf_search(
                    query_text, limit, exclude_files
                )

            # 類似度を計算
            similarities = []
            for file_path, note_embedding in self.embeddings.items():
                if file_path in exclude_files:
                    continue

                similarity = self._calculate_cosine_similarity(
                    query_embedding, note_embedding.embedding
                )

                if similarity >= min_similarity:
                    similarities.append((file_path, note_embedding, similarity))

            # 類似度順でソート
            similarities.sort(key=lambda x: x[2], reverse=True)

            # 検索結果を構築
            results = []
            for file_path, note_embedding, similarity in similarities[:limit]:
                # コンテンツプレビューを取得
                content_preview = await self._get_content_preview(file_path)

                result = SemanticSearchResult(
                    file_path=file_path,
                    title=note_embedding.title,
                    similarity_score=similarity,
                    content_preview=content_preview,
                    metadata=note_embedding.metadata,
                )
                results.append(result)

            self.logger.debug(
                "Search completed", query=query_text[:50], results_count=len(results)
            )

            return results

        except Exception as e:
            self.logger.error(
                "Failed to search similar notes", error=str(e), exc_info=True
            )
            # フォールバックとして TF-IDF 検索
            return await self._fallback_tfidf_search(
                query_text, limit, exclude_files or set()
            )

    async def add_note_embedding(
        self,
        file_path: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        新規ノートの埋め込みを追加

        Args:
            file_path: ファイルパス
            title: ノートタイトル
            content: ノート内容
            metadata: メタデータ

        Returns:
            成功フラグ
        """
        try:
            self.logger.debug("Adding note embedding", file_path=file_path)

            if len(content) < self.min_content_length:
                self.logger.debug("Content too short, skipping", file_path=file_path)
                return False

            # 埋め込み生成
            embedding = await self._generate_embedding(content)
            if not embedding:
                self.logger.warning("Failed to generate embedding", file_path=file_path)
                return False

            # コンテンツハッシュを計算
            content_hash = hashlib.md5(
                content.encode(), usedforsecurity=False
            ).hexdigest()

            # 埋め込みデータを作成
            now = datetime.now()
            note_embedding = NoteEmbedding(
                file_path=file_path,
                title=title,
                content_hash=content_hash,
                embedding=embedding,
                created_at=now,
                updated_at=now,
                metadata=metadata or {},
            )

            # ストレージに保存
            self.embeddings[file_path] = note_embedding

            # インデックスを保存
            await self._save_index()

            self.logger.debug("Note embedding added successfully", file_path=file_path)
            return True

        except Exception as e:
            self.logger.error(
                "Failed to add note embedding",
                file_path=file_path,
                error=str(e),
                exc_info=True,
            )
            return False

    async def remove_note_embedding(self, file_path: str) -> bool:
        """
        ノート埋め込みを削除

        Args:
            file_path: ファイルパス

        Returns:
            成功フラグ
        """
        try:
            if file_path in self.embeddings:
                del self.embeddings[file_path]
                await self._save_index()
                self.logger.debug("Note embedding removed", file_path=file_path)
                return True
            return False

        except Exception as e:
            self.logger.error(
                "Failed to remove note embedding", file_path=file_path, error=str(e)
            )
            return False

    async def get_embedding_stats(self) -> dict[str, Any]:
        """埋め込み統計情報を取得"""
        try:
            if not self.embeddings:
                return {
                    "total_embeddings": 0,
                    "last_updated": None,
                    "index_file_exists": self.index_file_path.exists(),
                }

            last_updated = max(emb.updated_at for emb in self.embeddings.values())

            return {
                "total_embeddings": len(self.embeddings),
                "last_updated": last_updated.isoformat(),
                "index_file_exists": self.index_file_path.exists(),
                "embedding_dimension": self.embedding_dimension,
                "vault_path": str(settings.obsidian_vault_path),
            }

        except Exception as e:
            self.logger.error("Failed to get embedding stats", error=str(e))
            return {"error": str(e)}

    async def _load_existing_index(self) -> None:
        """既存インデックスを読み込み"""
        try:
            if not self.index_file_path.exists():
                self.logger.debug("Index file does not exist, starting fresh")
                return

            async with aiofiles.open(self.index_file_path, encoding="utf-8") as f:
                data = await f.read()
                index_data = json.loads(data)

            # 埋め込みデータを復元
            for item in index_data.get("embeddings", []):
                embedding = NoteEmbedding.from_dict(item)
                self.embeddings[embedding.file_path] = embedding

            self.logger.info(
                "Existing index loaded", embeddings_count=len(self.embeddings)
            )

        except Exception as e:
            self.logger.warning(
                "Failed to load existing index, starting fresh", error=str(e)
            )
            self.embeddings = {}

    async def _save_index(self) -> None:
        """インデックスを保存"""
        try:
            index_data = {
                "embeddings": [emb.to_dict() for emb in self.embeddings.values()],
                "created_at": datetime.now().isoformat(),
                "version": "1.0",
            }

            # バックアップを作成
            if self.index_file_path.exists():
                backup_path = Path(str(self.index_file_path) + ".backup")
                self.index_file_path.rename(backup_path)

            async with aiofiles.open(self.index_file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(index_data, indent=2, ensure_ascii=False))

            self.logger.debug("Index saved successfully")

        except Exception as e:
            self.logger.error("Failed to save index", error=str(e), exc_info=True)
            raise

    async def _get_all_vault_files(self) -> list[str]:
        """Vault 内の全マークダウンファイルを取得"""
        try:
            settings = get_settings()
            vault_path = Path(settings.obsidian_vault_path)
            if not vault_path.exists():
                return []

            files = []
            for file_path in vault_path.rglob("*.md"):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(vault_path))
                    files.append(relative_path)

            return files

        except Exception as e:
            self.logger.error("Failed to get vault files", error=str(e))
            return []

    async def _should_update_embedding(self, file_path: str) -> bool:
        """埋め込みを更新すべきかチェック"""
        try:
            # 既存の埋め込みがなければ更新が必要
            if file_path not in self.embeddings:
                return True

            # ファイルの内容ハッシュをチェック
            settings = get_settings()
            full_path = Path(settings.obsidian_vault_path) / file_path
            if not full_path.exists():
                return False

            async with aiofiles.open(full_path, encoding="utf-8") as f:
                content = await f.read()

            current_hash = hashlib.md5(
                content.encode(), usedforsecurity=False
            ).hexdigest()
            stored_hash = self.embeddings[file_path].content_hash

            return current_hash != stored_hash

        except Exception as e:
            self.logger.warning(
                "Error checking if embedding should update",
                file_path=file_path,
                error=str(e),
            )
            return True  # エラー時は更新する

    async def _process_file_for_embedding(self, file_path: str) -> None:
        """ファイルを処理して埋め込みを生成"""
        try:
            settings = get_settings()
            full_path = Path(settings.obsidian_vault_path) / file_path
            if not full_path.exists():
                return

            # ファイル内容を読み込み
            async with aiofiles.open(full_path, encoding="utf-8") as f:
                content = await f.read()

            if len(content) < self.min_content_length:
                return

            # タイトルを抽出（ファイル名から）
            title = full_path.stem

            # メタデータを抽出（ YAML フロントマターがあれば）
            metadata = {}
            if content.startswith("---"):
                try:
                    import yaml

                    frontmatter_end = content.find("---", 3)
                    if frontmatter_end > 0:
                        frontmatter = content[3:frontmatter_end]
                        metadata = yaml.safe_load(frontmatter)
                        content = content[frontmatter_end + 3 :].strip()
                except Exception as e:
                    # YAML parsing failed, keep original content
                    self.logger.debug("Failed to parse YAML frontmatter", error=str(e))

            # 埋め込み生成
            embedding = await self._generate_embedding(content)
            if not embedding:
                return

            # コンテンツハッシュ
            content_hash = hashlib.md5(
                content.encode(), usedforsecurity=False
            ).hexdigest()

            # 埋め込みデータを作成・保存
            now = datetime.now()
            note_embedding = NoteEmbedding(
                file_path=file_path,
                title=title,
                content_hash=content_hash,
                embedding=embedding,
                created_at=now,
                updated_at=now,
                metadata=metadata,
            )

            self.embeddings[file_path] = note_embedding

            self.logger.debug(
                "File processed for embedding", file_path=file_path, title=title
            )

        except Exception as e:
            self.logger.error(
                "Failed to process file for embedding",
                file_path=file_path,
                error=str(e),
            )

    async def _cleanup_deleted_files(self, current_files: list[str]) -> None:
        """削除されたファイルの埋め込みをクリーンアップ"""
        current_files_set = set(current_files)
        deleted_files = [
            file_path
            for file_path in self.embeddings
            if file_path not in current_files_set
        ]

        for file_path in deleted_files:
            del self.embeddings[file_path]
            self.logger.debug("Removed embedding for deleted file", file_path=file_path)

        if deleted_files:
            self.logger.info("Cleaned up deleted files", count=len(deleted_files))

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """テキストの埋め込みを生成"""
        try:
            # Gemini API を使用
            if hasattr(self.ai_processor, "generate_embeddings"):
                return await self.ai_processor.generate_embeddings(text)

            # フォールバック: ダミー埋め込み
            return await self.ai_processor.generate_embeddings(text)

        except Exception as e:
            self.logger.warning("Failed to generate embedding", error=str(e))
            return None

    def _calculate_cosine_similarity(
        self, embedding1: list[float], embedding2: list[float]
    ) -> float:
        """コサイン類似度を計算"""
        try:
            vec1 = np.array(embedding1).reshape(1, -1)
            vec2 = np.array(embedding2).reshape(1, -1)

            similarity = cosine_similarity(vec1, vec2)[0][0]
            return float(similarity)

        except Exception as e:
            self.logger.warning("Failed to calculate cosine similarity", error=str(e))
            return 0.0

    async def _update_tfidf_index(self) -> None:
        """TF-IDF インデックスを更新（フォールバック検索用）"""
        try:
            if not self.embeddings:
                return

            documents = []
            self.file_paths_index = []

            for file_path, _embedding in self.embeddings.items():
                # ファイルの内容を読み込み（簡易版）
                try:
                    settings = get_settings()
                    full_path = Path(settings.obsidian_vault_path) / file_path
                    if full_path.exists():
                        async with aiofiles.open(full_path, encoding="utf-8") as f:
                            content = await f.read()

                        # YAML フロントマターを除去
                        if content.startswith("---"):
                            frontmatter_end = content.find("---", 3)
                            if frontmatter_end > 0:
                                content = content[frontmatter_end + 3 :].strip()

                        documents.append(content)
                        self.file_paths_index.append(file_path)
                except Exception as e:
                    # File read error, skip this file
                    self.logger.debug(
                        "Failed to read file for TF-IDF",
                        file_path=file_path,
                        error=str(e),
                    )
                    continue

            if documents:
                self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(documents)

        except Exception as e:
            self.logger.warning("Failed to update TF-IDF index", error=str(e))

    async def _fallback_tfidf_search(
        self, query_text: str, limit: int, exclude_files: set[str]
    ) -> list[SemanticSearchResult]:
        """TF-IDF フォールバック検索"""
        try:
            if self.tfidf_matrix is None or not self.file_paths_index:
                return []

            # クエリをベクトル化
            query_vector = self.tfidf_vectorizer.transform([query_text])

            # 類似度を計算
            similarities = cosine_similarity(query_vector, self.tfidf_matrix).flatten()

            # 結果を構築
            results = []
            for idx, similarity in enumerate(similarities):
                if similarity < 0.01:  # 最小閾値
                    continue

                file_path = self.file_paths_index[idx]
                if file_path in exclude_files:
                    continue

                embedding = self.embeddings.get(file_path)
                if not embedding:
                    continue

                content_preview = await self._get_content_preview(file_path)

                result = SemanticSearchResult(
                    file_path=file_path,
                    title=embedding.title,
                    similarity_score=float(similarity),
                    content_preview=content_preview,
                    metadata=embedding.metadata,
                )
                results.append(result)

            # 類似度順でソート
            results.sort(key=lambda x: x.similarity_score, reverse=True)
            return results[:limit]

        except Exception as e:
            self.logger.error("TF-IDF fallback search failed", error=str(e))
            return []

    async def _get_content_preview(self, file_path: str, max_length: int = 200) -> str:
        """ファイルのコンテンツプレビューを取得"""
        try:
            settings = get_settings()
            full_path = Path(settings.obsidian_vault_path) / file_path
            if not full_path.exists():
                return ""

            async with aiofiles.open(full_path, encoding="utf-8") as f:
                content = await f.read()

            # YAML フロントマターを除去
            if content.startswith("---"):
                frontmatter_end = content.find("---", 3)
                if frontmatter_end > 0:
                    content = content[frontmatter_end + 3 :].strip()

            # プレビュー用に短縮
            if len(content) > max_length:
                content = content[:max_length] + "..."

            return content

        except Exception as e:
            self.logger.warning(
                "Failed to get content preview", file_path=file_path, error=str(e)
            )
            return ""
