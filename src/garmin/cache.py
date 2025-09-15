"""
Garmin health data caching system
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.garmin.models import HealthData
from src.utils.mixins import LoggerMixin


class GarminDataCache(LoggerMixin):
    """Garmin 健康データのキャッシュシステム"""

    def __init__(self, cache_dir: Path, max_age_hours: float = 24.0) -> None:
        """
        初期化処理

        Args:
            cache_dir: キャッシュディレクトリ
            max_age_hours: キャッシュの最大保持時間（時間）
        """
        self.cache_dir = Path(cache_dir)
        self.max_age_hours = max_age_hours
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(
            "Garmin data cache initialized",
            cache_dir=str(self.cache_dir),
            max_age_hours=max_age_hours,
        )

    def _get_cache_file_path(self, target_date: date) -> Path:
        """指定日付のキャッシュファイルパスを取得"""
        filename = f"health_data_{target_date.isoformat()}.json"
        return self.cache_dir / filename

    def save_health_data(self, health_data: HealthData) -> bool:
        """健康データをキャッシュに保存"""
        try:
            cache_file = self._get_cache_file_path(health_data.date)

            # キャッシュメタデータを更新
            health_data.is_cached_data = False  # 最新データとしてマーク
            health_data.cache_age_hours = 0.0

            with open(cache_file, "w", encoding="utf-8") as f:
                # Convert HealthData to dict for JSON serialization
                health_data_dict = health_data.model_dump()
                # Handle date/datetime serialization
                health_data_dict["date"] = health_data.date.isoformat()
                if health_data.retrieved_at:
                    health_data_dict["retrieved_at"] = (
                        health_data.retrieved_at.isoformat()
                    )
                json.dump(health_data_dict, f, ensure_ascii=False, indent=2)

            self.logger.info(
                "Health data cached successfully",
                date=health_data.date.isoformat(),
                cache_file=str(cache_file),
            )
            return True

        except Exception as e:
            self.logger.error(
                "Failed to cache health data",
                date=health_data.date.isoformat(),
                error=str(e),
                exc_info=True,
            )
            return False

    def load_health_data(
        self, target_date: date, allow_stale: bool = True
    ) -> HealthData | None:
        """キャッシュから健康データを読み込み"""
        try:
            cache_file = self._get_cache_file_path(target_date)

            if not cache_file.exists():
                self.logger.debug("Cache file not found", date=target_date.isoformat())
                return None

            # ファイルの更新時刻を確認
            file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            age_hours = (datetime.now() - file_mtime).total_seconds() / 3600

            # 古すぎるキャッシュの処理
            if not allow_stale and age_hours > self.max_age_hours:
                self.logger.debug(
                    "Cache file too old",
                    date=target_date.isoformat(),
                    age_hours=age_hours,
                    max_age_hours=self.max_age_hours,
                )
                return None

            # キャッシュデータの読み込み
            with open(cache_file, encoding="utf-8") as f:
                health_data_dict = json.load(f)
                # Convert date strings back to date objects
                health_data_dict["date"] = datetime.fromisoformat(
                    health_data_dict["date"]
                ).date()
                if health_data_dict.get("retrieved_at"):
                    health_data_dict["retrieved_at"] = datetime.fromisoformat(
                        health_data_dict["retrieved_at"]
                    )
                health_data = HealthData(**health_data_dict)

            # キャッシュメタデータを更新
            health_data.is_cached_data = True
            health_data.cache_age_hours = age_hours
            health_data.retrieved_at = file_mtime

            self.logger.info(
                "Health data loaded from cache",
                date=target_date.isoformat(),
                age_hours=age_hours,
                is_stale=age_hours > self.max_age_hours,
            )

            return health_data

        except Exception as e:
            self.logger.error(
                "Failed to load cached health data",
                date=target_date.isoformat(),
                error=str(e),
                exc_info=True,
            )
            return None

    def is_cache_valid(self, target_date: date) -> bool:
        """指定日付のキャッシュが有効かどうかを確認"""
        cache_file = self._get_cache_file_path(target_date)

        if not cache_file.exists():
            return False

        try:
            file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            age_hours = (datetime.now() - file_mtime).total_seconds() / 3600
            return age_hours <= self.max_age_hours

        except Exception as e:
            self.logger.warning(
                "Failed to check cache validity",
                date=target_date.isoformat(),
                error=str(e),
            )
            return False

    def cleanup_old_cache(self, days_to_keep: int = 7) -> int:
        """古いキャッシュファイルを削除"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            deleted_count = 0

            for cache_file in self.cache_dir.glob("health_data_*.pkl"):
                try:
                    file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    if file_mtime < cutoff_date:
                        cache_file.unlink()
                        deleted_count += 1

                except Exception as e:
                    self.logger.warning(
                        "Failed to delete old cache file",
                        file=str(cache_file),
                        error=str(e),
                    )
                    continue

            if deleted_count > 0:
                self.logger.info(
                    "Cleaned up old cache files",
                    deleted_count=deleted_count,
                    days_to_keep=days_to_keep,
                )

            return deleted_count

        except Exception as e:
            self.logger.error(
                "Failed to cleanup old cache", error=str(e), exc_info=True
            )
            return 0

    def get_cache_stats(self) -> dict[str, Any]:
        """キャッシュの統計情報を取得"""
        try:
            cache_files = list(self.cache_dir.glob("health_data_*.pkl"))
            total_files = len(cache_files)

            if total_files == 0:
                return {
                    "total_files": 0,
                    "total_size_mb": 0.0,
                    "oldest_cache": None,
                    "newest_cache": None,
                }

            # ファイルサイズの計算
            total_size = sum(f.stat().st_size for f in cache_files)
            total_size_mb = total_size / (1024 * 1024)

            # 最新・最古のキャッシュファイル
            file_times = [
                (f, datetime.fromtimestamp(f.stat().st_mtime)) for f in cache_files
            ]
            file_times.sort(key=lambda x: x[1])

            oldest_cache = file_times[0][1].isoformat() if file_times else None
            newest_cache = file_times[-1][1].isoformat() if file_times else None

            return {
                "total_files": total_files,
                "total_size_mb": round(total_size_mb, 2),
                "oldest_cache": oldest_cache,
                "newest_cache": newest_cache,
                "cache_dir": str(self.cache_dir),
            }

        except Exception as e:
            self.logger.error("Failed to get cache stats", error=str(e), exc_info=True)
            return {
                "total_files": 0,
                "total_size_mb": 0.0,
                "oldest_cache": None,
                "newest_cache": None,
                "error": str(e),
            }
