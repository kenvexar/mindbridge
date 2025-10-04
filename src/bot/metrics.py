"""System metrics and monitoring functionality for Discord bot"""

from datetime import datetime
from typing import Any

from src.utils.mixins import LoggerMixin


class SystemMetrics(LoggerMixin):
    """システムメトリクス収集とパフォーマンス監視"""

    def __init__(self) -> None:
        self.metrics: dict[str, Any] = {
            "total_messages_processed": 0,
            "successful_ai_requests": 0,
            "failed_ai_requests": 0,
            "api_usage_minutes": 0.0,
            "obsidian_files_created": 0,
            "errors_last_hour": 0,
            "warnings_last_hour": 0,
            "system_start_time": datetime.now(),
        }
        self.hourly_stats: dict[str, Any] = {}
        self.error_history: list[Any] = []
        self.performance_history: list[Any] = []

    def increment_message_count(self) -> None:
        """処理メッセージ数をインクリメント"""
        self.metrics["total_messages_processed"] += 1

    def increment_ai_success(self) -> None:
        """AI 成功カウントをインクリメント"""
        self.metrics["successful_ai_requests"] += 1

    def increment_ai_failure(self) -> None:
        """AI 失敗カウントをインクリメント"""
        self.metrics["failed_ai_requests"] += 1

    def add_api_usage(self, minutes: float) -> None:
        """API 使用時間を追加"""
        self.metrics["api_usage_minutes"] += minutes

    def increment_obsidian_files(self) -> None:
        """Obsidian ファイル作成数をインクリメント"""
        self.metrics["obsidian_files_created"] += 1

    def add_error(self, error_info: dict[str, Any]) -> None:
        """エラー情報を追加"""
        self.error_history.append(
            {
                "timestamp": datetime.now(),
                "error": error_info,
            }
        )
        self.metrics["errors_last_hour"] += 1

        # Keep only last 100 errors
        if len(self.error_history) > 100:
            self.error_history.pop(0)

    def add_performance_data(self, operation: str, duration: float) -> None:
        """パフォーマンスデータを追加"""
        self.performance_history.append(
            {
                "timestamp": datetime.now(),
                "operation": operation,
                "duration": duration,
            }
        )

        # Keep only last 1000 performance records
        if len(self.performance_history) > 1000:
            self.performance_history.pop(0)

    def record_message_processed(self) -> None:
        """処理メッセージ数をインクリメント"""
        self.increment_message_count()

    def record_ai_request(self, success: bool, processing_time_ms: int) -> None:
        """AI リクエストを記録"""
        if success:
            self.increment_ai_success()
        else:
            self.increment_ai_failure()
        self.add_performance_data("ai_request", processing_time_ms / 1000.0)

    def record_file_created(self) -> None:
        """ファイル作成を記録"""
        self.increment_obsidian_files()

    def get_system_health_status(self) -> dict[str, Any]:
        """システムヘルス状況を取得"""
        total_requests = (
            self.metrics["successful_ai_requests"] + self.metrics["failed_ai_requests"]
        )
        ai_success_rate = (
            self.metrics["successful_ai_requests"] / max(1, total_requests)
        ) * 100

        return {
            "total_messages_processed": self.metrics["total_messages_processed"],
            "ai_success_rate": ai_success_rate,
            "files_created": self.metrics["obsidian_files_created"],
            "performance_score": 100.0 - (self.metrics["errors_last_hour"] * 10),
            "uptime_hours": (
                (datetime.now() - self.metrics["system_start_time"]).total_seconds()
                / 3600
            ),
        }

    def get_metrics_summary(self) -> dict[str, Any]:
        """メトリクス要約を取得"""
        uptime = datetime.now() - self.metrics["system_start_time"]

        avg_performance = 0.0
        if self.performance_history:
            total_duration = sum(p["duration"] for p in self.performance_history)
            avg_performance = total_duration / len(self.performance_history)

        return {
            **self.metrics,
            "uptime_seconds": uptime.total_seconds(),
            "uptime_formatted": str(uptime),
            "avg_operation_duration": avg_performance,
            "error_rate": (
                self.metrics["failed_ai_requests"]
                / max(1, self.metrics["total_messages_processed"])
            )
            * 100,
        }

    def reset_hourly_stats(self) -> None:
        """時間毎の統計をリセット"""
        self.metrics["errors_last_hour"] = 0
        self.metrics["warnings_last_hour"] = 0
        self.hourly_stats = {}


class APIUsageMonitor(LoggerMixin):
    """API 使用量監視と制限管理"""

    def __init__(self) -> None:
        self.daily_requests: dict[str, int] = {}
        self.hourly_requests: dict[str, int] = {}
        self.last_reset_day = datetime.now().day
        self.last_reset_hour = datetime.now().hour

        # API limits
        self.daily_limits = {
            "gemini": 1500,  # Free tier limit
            "speech": 60,  # 60 minutes per month
        }

        self.hourly_limits = {
            "gemini": 15,  # Rate limit
            "speech": 2,  # Conservative hourly limit
        }

    def record_api_usage(self, api_name: str) -> bool:
        """API 使用を記録し、制限チェック"""
        self._check_and_reset_counters()

        # Check limits before incrementing
        if not self._check_limits(api_name):
            return False

        self.daily_requests[api_name] = self.daily_requests.get(api_name, 0) + 1
        self.hourly_requests[api_name] = self.hourly_requests.get(api_name, 0) + 1

        return True

    def _check_limits(self, api_name: str) -> bool:
        """API 制限をチェック"""
        daily_count = self.daily_requests.get(api_name, 0)
        hourly_count = self.hourly_requests.get(api_name, 0)

        if daily_count >= self.daily_limits.get(api_name, 999999):
            self.logger.warning(f"Daily limit exceeded for {api_name}")
            return False

        if hourly_count >= self.hourly_limits.get(api_name, 999999):
            self.logger.warning(f"Hourly limit exceeded for {api_name}")
            return False

        return True

    def _check_and_reset_counters(self) -> None:
        """カウンタの日時リセットをチェック"""
        now = datetime.now()

        if now.day != self.last_reset_day:
            self.daily_requests = {}
            self.last_reset_day = now.day
            self.logger.info("Daily API counters reset")

        if now.hour != self.last_reset_hour:
            self.hourly_requests = {}
            self.last_reset_hour = now.hour
            self.logger.info("Hourly API counters reset")

    def get_usage_status(self) -> dict[str, Any]:
        """API 使用状況を取得"""
        self._check_and_reset_counters()

        status: dict[str, dict[str, int]] = {
            "daily_usage": {},
            "hourly_usage": {},
            "daily_remaining": {},
            "hourly_remaining": {},
        }

        for api_name in ["gemini", "speech"]:
            daily_used = self.daily_requests.get(api_name, 0)
            hourly_used = self.hourly_requests.get(api_name, 0)

            status["daily_usage"][api_name] = daily_used
            status["hourly_usage"][api_name] = hourly_used
            status["daily_remaining"][api_name] = max(
                0, self.daily_limits[api_name] - daily_used
            )
            status["hourly_remaining"][api_name] = max(
                0, self.hourly_limits[api_name] - hourly_used
            )

        return status

    def is_api_available(self, api_name: str) -> bool:
        """API が使用可能かチェック"""
        return self._check_limits(api_name)

    def track_gemini_usage(
        self, request_count: int = 1, success: bool | None = None
    ) -> None:
        """Gemini API 使用量を追跡"""
        normalized = max(1, request_count)
        if normalized > 10:
            # トークン数など大きな値が渡された場合は 1 リクエストとして扱う
            normalized = 1

        for _ in range(normalized):
            self.record_api_usage("gemini")

    def track_speech_usage(self, minutes_used: float) -> None:
        """Speech API 使用量を追跡"""
        # Convert minutes to request count for tracking
        requests = max(1, int(minutes_used))
        for _ in range(requests):
            self.record_api_usage("speech")

    def get_usage_dashboard(self) -> dict[str, Any]:
        """使用量ダッシュボード データを取得"""
        status = self.get_usage_status()
        return {
            **status,
            "limits": {
                "daily": self.daily_limits,
                "hourly": self.hourly_limits,
            },
            "availability": {
                api: self.is_api_available(api) for api in ["gemini", "speech"]
            },
        }

    def export_usage_report(self, format_type: str = "json") -> dict[str, Any]:
        """使用量レポートをエクスポート"""
        dashboard = self.get_usage_dashboard()
        return {
            "report_type": "api_usage",
            "format": format_type,
            "timestamp": datetime.now().isoformat(),
            "data": dashboard,
        }
