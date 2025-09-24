"""
AI 処理統合システム
"""

import asyncio
import hashlib
import time
from datetime import datetime, timedelta
from typing import Any

from src.ai.gemini_client import GeminiAPIError, GeminiClient
from src.ai.models import (
    AIModelConfig,
    AIProcessingResult,
    ProcessingCache,
    ProcessingRequest,
    ProcessingSettings,
    ProcessingStats,
)
from src.utils.lru_cache import MemoryOptimizedCache
from src.utils.memory_manager import get_memory_manager
from src.utils.mixins import LoggerMixin


class AIProcessor(LoggerMixin):
    """AI 処理統合システム"""

    def __init__(
        self,
        model_config: AIModelConfig | None = None,
        settings: ProcessingSettings | None = None,
    ):
        """
        AI 処理システムの初期化

        Args:
            model_config: AI モデル設定
            settings: 処理設定
        """
        self.settings = settings or ProcessingSettings()
        self.model_config = model_config or AIModelConfig()
        self.gemini_client = GeminiClient(self.model_config)

        # キャッシュとステータス管理（ LRU Cache に変更）
        self._cache = MemoryOptimizedCache(
            max_size=getattr(self.settings, "max_cache_entries", 500),
            ttl_hours=self.settings.cache_duration_hours,
        )
        self.stats = ProcessingStats()
        self._processing_queue: list[ProcessingRequest] = []
        self._is_processing = False

        # メモリマネージャーに登録
        memory_manager = get_memory_manager()
        memory_manager.register_component(self)

        self.logger.info(
            "AI Processor initialized",
            cache_duration=self.settings.cache_duration_hours,
            model=self.model_config.model_name,
            min_text_length=self.settings.min_text_length,
            max_text_length=self.settings.max_text_length,
            enable_summary=self.settings.enable_summary,
            enable_tags=self.settings.enable_tags,
            enable_categorization=self.settings.enable_categorization,
        )

    def _generate_content_hash(self, text: str) -> str:
        """テキストのハッシュ値を生成"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def _is_text_processable(self, text: str) -> bool:
        """テキストが処理可能かチェック（互換性のため残す）"""
        result = self._check_text_processability(text)
        return result["is_processable"]

    def _check_text_processability(self, text: str) -> dict[str, Any]:
        """テキストが処理可能かチェック（詳細情報付き）"""
        text_length = len(text.strip())
        stripped_text = text.strip()

        min_length = max(1, getattr(self.settings, "min_text_length", 3))
        max_length = getattr(self.settings, "max_text_length", 8000)

        self.logger.debug(
            "Checking text processability",
            text_length=text_length,
            min_length=min_length,
            max_length=max_length,
            text_preview=stripped_text[:100] + "..."
            if len(stripped_text) > 100
            else stripped_text,
        )

        # 空文字チェック
        if not stripped_text:
            return {"is_processable": False, "reason": "empty text"}

        # 長さチェック - 強制的に 3 を使用
        if text_length < min_length:
            self.logger.warning(
                "❌ Text too short for processing",
                length=text_length,
                min_length=min_length,
            )
            return {
                "is_processable": False,
                "reason": f"too short ({text_length} < {min_length})",
            }

        if text_length > max_length:
            self.logger.warning(
                "Text too long for processing",
                length=text_length,
                max_length=max_length,
            )
            return {
                "is_processable": False,
                "reason": f"too long ({text_length} > {max_length})",
            }

        # 無効文字チェック (Control characters など)
        if any(ord(c) < 32 and c not in "\t\n\r" for c in stripped_text):
            return {
                "is_processable": False,
                "reason": "contains invalid control characters",
            }

        return {"is_processable": True, "reason": "valid"}

    def _get_from_cache(self, content_hash: str) -> AIProcessingResult | None:
        """キャッシュから結果を取得（ LRU 最適化）"""
        cache_entry = self._cache.get(content_hash)

        if cache_entry is None:
            return None

        # アクセス情報更新
        cache_entry.access()

        # キャッシュヒット
        result = cache_entry.result
        result.cache_hit = True

        self.logger.debug(
            "Cache hit",
            content_hash=content_hash,
            access_count=cache_entry.access_count,
        )

        return result

    def _save_to_cache(self, content_hash: str, result: AIProcessingResult) -> None:
        """結果をキャッシュに保存（ LRU 最適化）"""
        expires_at = datetime.now() + timedelta(
            hours=self.settings.cache_duration_hours
        )

        cache_entry = ProcessingCache(
            content_hash=content_hash,
            result=result,
            created_at=datetime.now(),
            expires_at=expires_at,
        )

        self._cache.put(content_hash, cache_entry)

        self.logger.debug(
            "Result cached",
            content_hash=content_hash,
            expires_at=expires_at.isoformat(),
            cache_size=self._cache.size(),
        )

    def _clean_expired_cache(self) -> int:
        """期限切れキャッシュを削除（ LRU 最適化）"""
        # LRU キャッシュの期限切れクリーンアップを実行
        expired_count = self._cache.cleanup_expired()

        if expired_count > 0:
            self.logger.info(f"Cleaned {expired_count} expired cache entries")

        return expired_count

    async def cleanup_expired(self) -> int:
        """メモリマネージャーから呼び出される清理メソッド"""
        return self._clean_expired_cache()

    async def process_text(
        self, text: str, message_id: int, force_reprocess: bool = False
    ) -> AIProcessingResult:
        """
        テキストの AI 処理を実行

        Args:
            text: 処理対象のテキスト
            message_id: メッセージ ID
            force_reprocess: 強制再処理フラグ

        Returns:
            AI 処理結果
        """
        start_time = time.time()

        # テキストの前処理
        cleaned_text = text.strip()
        content_hash = self._generate_content_hash(cleaned_text)

        # 処理可能性チェック - より詳細なエラーハンドリング
        processable_result = self._check_text_processability(cleaned_text)
        if not processable_result["is_processable"]:
            self.logger.warning(
                "Text not processable",
                message_id=message_id,
                reason=processable_result["reason"],
                text_length=len(cleaned_text),
            )
            return AIProcessingResult(
                message_id=message_id,
                processed_at=datetime.now(),
                total_processing_time_ms=int((time.time() - start_time) * 1000),
                errors=[f"Text is not processable: {processable_result['reason']}"],
            )

        # キャッシュチェック
        if not force_reprocess:
            cached_result = self._get_from_cache(content_hash)
            if cached_result:
                # メッセージ ID を更新
                cached_result.message_id = message_id
                cached_result.processed_at = datetime.now()

                # 統計更新
                self.stats.update_stats(cached_result)

                return cached_result

        # AI 処理実行
        errors = []
        warnings: list[str] = []
        summary = None
        tags = None
        category = None

        try:
            self.logger.info(
                "Starting AI processing",
                message_id=message_id,
                text_length=len(cleaned_text),
                content_hash=content_hash,
            )

            # 並列 AI 処理
            if (
                self.settings.enable_summary
                or self.settings.enable_tags
                or self.settings.enable_categorization
            ):
                summary_result, tags_result, category_result = await asyncio.wait_for(
                    self.gemini_client.process_all(cleaned_text),
                    timeout=self.settings.timeout_seconds,
                )

                # 結果の割り当て
                if self.settings.enable_summary:
                    summary = summary_result
                if self.settings.enable_tags:
                    tags = tags_result
                if self.settings.enable_categorization:
                    category = category_result

        except TimeoutError:
            error_msg = (
                f"Processing timeout after {self.settings.timeout_seconds} seconds"
            )
            errors.append(error_msg)
            self.logger.error(error_msg, message_id=message_id)

        except GeminiAPIError as e:
            error_msg = f"Gemini API error: {str(e)}"
            errors.append(error_msg)
            self.logger.error(
                error_msg,
                message_id=message_id,
                error_code=getattr(e, "error_code", None),
            )

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            errors.append(error_msg)
            self.logger.error(error_msg, message_id=message_id, exc_info=True)

        # 結果作成
        total_time = int((time.time() - start_time) * 1000)

        result = AIProcessingResult(
            message_id=message_id,
            processed_at=datetime.now(),
            summary=summary,
            tags=tags,
            category=category,
            total_processing_time_ms=total_time,
            cache_hit=False,
            errors=errors,
            warnings=warnings,
        )

        # 成功した場合はキャッシュに保存
        if not errors:
            self._save_to_cache(content_hash, result)

        # 統計更新
        self.stats.update_stats(result)

        self.logger.info(
            "AI processing completed",
            message_id=message_id,
            total_time_ms=total_time,
            has_errors=bool(errors),
            cached=False,
        )

        return result

    async def process_batch(
        self,
        requests: list[ProcessingRequest],
        max_concurrent: int = 3,
        batch_size: int = 5,
    ) -> list[AIProcessingResult]:
        """
        バッチ処理（並列化最適化）

        Args:
            requests: 処理リクエストのリスト
            max_concurrent: 最大同時実行数
            batch_size: バッチサイズ

        Returns:
            処理結果のリスト
        """
        self.logger.info(
            "Starting optimized batch processing",
            total_requests=len(requests),
            max_concurrent=max_concurrent,
            batch_size=batch_size,
        )

        # 優先度でソート
        sorted_requests = sorted(
            requests, key=lambda r: (r.priority.value, r.requested_at), reverse=True
        )

        # セマフォアで同時実行数を制限
        semaphore = asyncio.Semaphore(max_concurrent)
        results = []

        async def process_single_request(
            request: ProcessingRequest,
        ) -> AIProcessingResult:
            """1 つのリクエストを処理"""
            async with semaphore:
                try:
                    return await self.process_text(
                        text=request.text_content,
                        message_id=request.message_id,
                        force_reprocess=request.force_reprocess,
                    )
                except Exception as e:
                    self.logger.error(
                        "Batch processing item failed",
                        message_id=request.message_id,
                        error=str(e),
                    )
                    # エラー結果を作成
                    return AIProcessingResult(
                        message_id=request.message_id,
                        processed_at=datetime.now(),
                        total_processing_time_ms=0,
                        errors=[f"Batch processing failed: {str(e)}"],
                    )

        # チャンク分割で並列処理
        for i in range(0, len(sorted_requests), batch_size):
            chunk = sorted_requests[i : i + batch_size]

            self.logger.debug(
                f"Processing chunk {i // batch_size + 1}",
                chunk_size=len(chunk),
                total_chunks=(len(sorted_requests) + batch_size - 1) // batch_size,
            )

            # チャンクを並列処理
            chunk_tasks = [
                asyncio.create_task(process_single_request(request))
                for request in chunk
            ]

            # 結果を収集
            chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)

            # 例外処理
            for j, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    error_result = AIProcessingResult(
                        message_id=chunk[j].message_id,
                        processed_at=datetime.now(),
                        total_processing_time_ms=0,
                        errors=[f"Async processing failed: {str(result)}"],
                    )
                    results.append(error_result)
                elif isinstance(result, AIProcessingResult):
                    results.append(result)
                else:
                    # 予期しない型の場合はエラーとして扱う
                    error_result = AIProcessingResult(
                        message_id=chunk[j].message_id,
                        processed_at=datetime.now(),
                        total_processing_time_ms=0,
                        errors=[f"Unexpected result type: {type(result)}"],
                    )
                    results.append(error_result)

        self.logger.info(
            "Optimized batch processing completed",
            total_results=len(results),
            success_count=sum(1 for r in results if not r.errors),
            error_count=sum(1 for r in results if r.errors),
        )
        return results

    def add_to_queue(self, request: ProcessingRequest) -> None:
        """処理キューに追加"""
        self._processing_queue.append(request)
        self.logger.debug(
            "Request added to queue",
            message_id=request.message_id,
            queue_size=len(self._processing_queue),
        )

    async def process_queue(self) -> list[AIProcessingResult]:
        """キューの処理"""
        if self._is_processing or not self._processing_queue:
            return []

        self._is_processing = True

        try:
            # キューをコピーしてクリア
            requests_to_process = self._processing_queue.copy()
            self._processing_queue.clear()

            # バッチ処理実行
            results = await self.process_batch(requests_to_process)

            return results

        finally:
            self._is_processing = False

    def get_stats(self) -> ProcessingStats:
        """処理統計を取得"""
        # 期限切れキャッシュをクリーンアップ
        self._clean_expired_cache()

        return self.stats

    def get_cache_info(self) -> dict[str, Any]:
        """キャッシュ情報を取得（ LRU 最適化）"""
        self._clean_expired_cache()

        # LRU キャッシュの統計情報を取得
        cache_stats = self._cache.get_performance_stats()

        return {
            "total_entries": cache_stats["size"],
            "max_entries": cache_stats["max_size"],
            "usage_ratio": cache_stats["usage_ratio"],
            "cache_hits": cache_stats["hits"],
            "cache_misses": cache_stats["misses"],
            "cache_hit_rate": cache_stats["hit_ratio"],
            "is_full": cache_stats["is_full"],
            "ttl_hours": cache_stats["ttl_seconds"] / 3600
            if cache_stats["ttl_seconds"]
            else None,
        }

    def clear_cache(self) -> int:
        """キャッシュをクリア（ LRU 最適化）"""
        cleared_count = self._cache.size()
        self._cache.clear()
        self._cache.reset_stats()  # パフォーマンス統計もリセット
        self.logger.info(f"Cache cleared: {cleared_count} entries removed")
        return cleared_count

    async def generate_embeddings(self, text: str) -> list[float] | None:
        """
        テキストの埋め込みベクトルを生成

        Args:
            text: 対象テキスト

        Returns:
            埋め込みベクトル（失敗時は None ）
        """
        try:
            self.logger.debug("Generating embeddings", text_length=len(text))

            # Gemini クライアントで埋め込み生成
            if hasattr(self.gemini_client, "generate_embeddings"):
                embedding = await self.gemini_client.generate_embeddings(text)
                if embedding and isinstance(embedding, list):
                    return list(embedding)

            # フォールバック: 簡単なハッシュベースのダミー埋め込み
            text_hash = hashlib.sha256(text.encode()).hexdigest()
            embedding = [
                float(int(text_hash[i : i + 2], 16)) / 255.0 for i in range(0, 32, 2)
            ]

            self.logger.warning("Using fallback embedding generation")
            return embedding

        except Exception as e:
            self.logger.error("Failed to generate embeddings", error=str(e))
            return None

    async def summarize_url_content(self, url: str, content: str) -> str | None:
        """
        URL 内容を要約

        Args:
            url: 対象 URL
            content: ウェブページの内容

        Returns:
            要約テキスト（失敗時は None ）
        """
        try:
            self.logger.debug(
                "Summarizing URL content", url=url, content_length=len(content)
            )

            # プロンプト作成
            prompt = f"""以下のウェブページの内容を日本語で簡潔に要約してください：

URL: {url}

内容:
{content[:2000]}...  # 最初の 2000 文字のみ

要約は以下の形式で：
- 主要なポイントを 3-5 行で
- 重要なキーワードを含める
- 読みやすい文章で"""

            summary = await self.gemini_client.generate_summary(prompt)

            if summary:
                self.logger.debug("URL content summarized successfully", url=url)
                return summary.summary.strip()

            return None

        except Exception as e:
            self.logger.error("Failed to summarize URL content", url=url, error=str(e))
            return None

    async def generate_internal_links(
        self, content: str, related_notes: list[dict[str, Any]]
    ) -> list[str]:
        """
        内部リンクを生成

        Args:
            content: 新規ノートの内容
            related_notes: 関連ノートのリスト

        Returns:
            内部リンクのリスト
        """
        try:
            self.logger.debug(
                "Generating internal links",
                content_length=len(content),
                related_notes_count=len(related_notes),
            )

            if not related_notes:
                return []

            # 関連ノート情報を整理
            note_info = []
            for note in related_notes[:10]:  # 上位 10 件まで
                title = note.get("title", "Untitled")
                similarity = note.get("similarity_score", 0.0)
                preview = note.get("content_preview", "")[:100]

                note_info.append(f"- {title} (類似度: {similarity:.2f}): {preview}")

            # プロンプト作成
            prompt = f"""以下の新しいノートの内容に基づいて、関連する既存のノートへの内部リンクを提案してください：

新しいノートの内容:
{content[:1000]}...

関連する既存のノート:
{chr(10).join(note_info)}

以下の条件で内部リンクを提案してください：
1. 最も関連性の高い 3-5 個のノートを選択
2. [[ノート名]]の形式でリンクを作成
3. 簡潔な説明を付ける
4. 関連性が低いものは除外

出力形式:
- [[ノート名 1]] - 説明
- [[ノート名 2]] - 説明"""

            response = await self.gemini_client.generate_summary(prompt)

            if not response:
                return []

            # レスポンスからリンクを抽出
            links = []
            response_text = (
                response.summary if hasattr(response, "summary") else str(response)
            )
            for line in response_text.split("\n"):
                if "[[" in line and "]]" in line:
                    links.append(line.strip())

            self.logger.debug("Internal links generated", links_count=len(links))
            return links

        except Exception as e:
            self.logger.error("Failed to generate internal links", error=str(e))
            return []

    async def health_check(self) -> dict[str, Any]:
        """ヘルスチェック"""
        try:
            # シンプルなテストリクエスト
            test_text = "Hello, this is a test message for health check."
            start_time = time.time()

            await self.gemini_client.generate_summary(test_text)

            response_time = int((time.time() - start_time) * 1000)

            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "model": self.model_config.model_name,
                "cache_entries": len(self._cache),
                "queue_size": len(self._processing_queue),
                "total_requests": self.stats.total_requests,
                "success_rate": self.stats.successful_requests
                / max(self.stats.total_requests, 1),
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model_config.model_name,
            }
