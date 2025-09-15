"""
Access logging and security monitoring for MindBridge
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

import aiofiles

from src.utils.mixins import LoggerMixin


class SecurityEventType(Enum):
    """Types of security events to track"""

    LOGIN_ATTEMPT = "login_attempt"
    SECRET_ACCESS = "secret_access"  # nosec: B105
    CONFIG_CHANGE = "config_change"
    COMMAND_EXECUTION = "command_execution"
    FILE_ACCESS = "file_access"
    API_CALL = "api_call"
    ERROR_EVENT = "error_event"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


class SecurityEvent:
    """Security event data structure"""

    def __init__(
        self,
        event_type: SecurityEventType,
        user_id: str | None = None,
        channel_id: str | None = None,
        action: str = "",
        details: dict[str, Any] | None = None,
        success: bool = True,
        ip_address: str | None = None,
    ):
        self.timestamp = datetime.now()
        self.event_type = event_type
        self.user_id = user_id
        self.channel_id = channel_id
        self.action = action
        self.details = details or {}
        self.success = success
        self.ip_address = ip_address
        self.session_id = self._generate_session_id()

    def _generate_session_id(self) -> str:
        """Generate a simple session identifier"""
        return (
            f"{self.user_id or 'anonymous'}_{self.timestamp.strftime('%Y%m%d_%H%M%S')}"
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for logging （機密情報マスキング付き）"""
        # 機密情報のマスキング
        filtered_details = (
            self._mask_sensitive_data(self.details) if self.details else {}
        )

        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "user_id": self.user_id,
            "channel_id": self.channel_id,
            "action": self.action,
            "details": filtered_details,
            "success": self.success,
            "ip_address": self.ip_address,
            "session_id": self.session_id,
        }

    def _mask_sensitive_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """機密情報をマスキング（個人使用向け）"""
        SENSITIVE_KEYS = {
            "password",
            "token",
            "secret",
            "api_key",
            "authorization",
            "cookie",
            "session",
            "credential",
            "private_key",
            "discord_token",
            "gemini_key",
            "github_token",
        }

        filtered_data = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
                # 機密情報はマスク
                if isinstance(value, str) and len(value) > 4:
                    filtered_data[key] = f"{value[:2]}...{value[-2:]}"
                else:
                    filtered_data[key] = "[MASKED]"
            else:
                filtered_data[key] = value

        return filtered_data


class AccessLogger(LoggerMixin):
    """Security access logger with threat detection capabilities"""

    def __init__(self, log_file: Path | None = None):
        self.log_file = log_file or Path("logs/security_access.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # In-memory tracking for real-time analysis
        self.recent_events: list[SecurityEvent] = []  # Last 1000 events
        self.failed_attempts: defaultdict[str, list[datetime]] = defaultdict(
            list
        )  # Track failed attempts by user
        self.rate_limits: defaultdict[str, list[datetime]] = defaultdict(
            list
        )  # Track rate limiting by user
        self.suspicious_patterns: list[SecurityEvent] = []

        # Configuration （個人使用向けに大幅簡素化）
        self.max_recent_events = 100  # 個人使用では 100 イベントで十分
        self.failed_attempt_threshold = 20  # 個人使用では緩和
        self.failed_attempt_window = timedelta(hours=1)  # 個人使用では長めに設定
        self.rate_limit_threshold = 200  # 個人使用では高めに設定
        self.rate_limit_window = timedelta(minutes=30)  # 個人使用では長めに設定

    async def log_event(self, event: SecurityEvent) -> None:
        """Log a security event"""
        # Add to recent events
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events.pop(0)

        # Track failed attempts
        if not event.success and event.user_id:
            self.failed_attempts[event.user_id].append(event.timestamp)
            self._cleanup_old_attempts(event.user_id)

        # Track rate limiting
        if event.user_id:
            self.rate_limits[event.user_id].append(event.timestamp)
            self._cleanup_old_rate_limits(event.user_id)

        # Check for suspicious activity
        await self._analyze_suspicious_activity(event)

        # Write to log file
        await self._write_to_file(event)

        # Log to application logger
        self.logger.info(
            "Security event recorded",
            event_type=event.event_type.value,
            user_id=event.user_id,
            action=event.action,
            success=event.success,
        )

    async def _write_to_file(self, event: SecurityEvent) -> None:
        """Write event to log file in JSONL format"""
        try:
            async with aiofiles.open(self.log_file, "a") as f:
                await f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write security log: {e}")

    def _cleanup_old_attempts(self, user_id: str) -> None:
        """Remove old failed attempts outside the window"""
        cutoff_time = datetime.now() - self.failed_attempt_window
        self.failed_attempts[user_id] = [
            ts for ts in self.failed_attempts[user_id] if ts > cutoff_time
        ]

    def _cleanup_old_rate_limits(self, user_id: str) -> None:
        """Remove old rate limit entries outside the window"""
        cutoff_time = datetime.now() - self.rate_limit_window
        self.rate_limits[user_id] = [
            ts for ts in self.rate_limits[user_id] if ts > cutoff_time
        ]

    async def _analyze_suspicious_activity(self, event: SecurityEvent) -> None:
        """Analyze event for suspicious patterns"""
        if not event.user_id:
            return

        # Check for excessive failed attempts
        failed_count = len(self.failed_attempts.get(event.user_id, []))
        if failed_count >= self.failed_attempt_threshold:
            await self._flag_suspicious_activity(
                event.user_id,
                f"Excessive failed attempts: {failed_count}",
                {
                    "failed_attempts": failed_count,
                    "threshold": self.failed_attempt_threshold,
                },
            )

        # Check for rate limit violations
        rate_count = len(self.rate_limits.get(event.user_id, []))
        if rate_count >= self.rate_limit_threshold:
            await self._flag_suspicious_activity(
                event.user_id,
                f"Rate limit exceeded: {rate_count} requests",
                {"request_count": rate_count, "threshold": self.rate_limit_threshold},
            )

        # Check for unusual command patterns
        if event.event_type == SecurityEventType.COMMAND_EXECUTION:
            await self._analyze_command_patterns(event)

    async def _flag_suspicious_activity(
        self, user_id: str, description: str, details: dict[str, Any]
    ) -> None:
        """Flag and log suspicious activity"""
        suspicious_event = SecurityEvent(
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            action=description,
            details=details,
            success=False,
        )

        self.suspicious_patterns.append(suspicious_event)

        self.logger.warning(
            "Suspicious activity detected",
            user_id=user_id,
            description=description,
            details=details,
        )

    async def _analyze_command_patterns(self, event: SecurityEvent) -> None:
        """Analyze command execution patterns for anomalies"""
        if not event.user_id:
            return

        # Get recent commands from this user
        recent_commands = [
            e
            for e in self.recent_events[-20:]  # Last 20 events
            if (
                e.user_id == event.user_id
                and e.event_type == SecurityEventType.COMMAND_EXECUTION
                and e.timestamp > datetime.now() - timedelta(minutes=5)
            )
        ]

        # 個人使用では rapid command execution は正常なので閾値を大幅に緩和
        if len(recent_commands) >= 50:
            await self._flag_suspicious_activity(
                event.user_id,
                "Excessive command execution detected",
                {"command_count": len(recent_commands), "time_window": "5 minutes"},
            )

    async def get_security_report(self, hours: int = 24) -> dict[str, Any]:
        """Generate security activity report"""
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # Filter events within time window
        recent_events = [e for e in self.recent_events if e.timestamp > cutoff_time]

        # Aggregate statistics
        event_types: defaultdict[str, int] = defaultdict(int)
        user_activity: defaultdict[str, int] = defaultdict(int)
        failed_events = 0

        for event in recent_events:
            event_types[event.event_type.value] += 1
            if event.user_id:
                user_activity[event.user_id] += 1
            if not event.success:
                failed_events += 1

        # Get recent suspicious activities
        recent_suspicious = [
            e for e in self.suspicious_patterns if e.timestamp > cutoff_time
        ]

        return {
            "report_period_hours": hours,
            "total_events": len(recent_events),
            "failed_events": failed_events,
            "success_rate": (len(recent_events) - failed_events)
            / max(1, len(recent_events))
            * 100,
            "event_types": dict(event_types),
            "most_active_users": dict(
                sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "suspicious_activities": len(recent_suspicious),
            "suspicious_events": [e.to_dict() for e in recent_suspicious],
            "generated_at": datetime.now().isoformat(),
        }

    def is_user_suspicious(self, user_id: str) -> bool:
        """Check if a user has suspicious activity flags"""
        # Check for recent failed attempts
        if len(self.failed_attempts.get(user_id, [])) >= self.failed_attempt_threshold:
            return True

        # Check for recent suspicious events
        recent_suspicious = [
            e
            for e in self.suspicious_patterns
            if (
                e.user_id == user_id
                and e.timestamp > datetime.now() - timedelta(hours=1)
            )
        ]

        return len(recent_suspicious) > 0

    async def cleanup_old_logs(self, days: int = 30) -> None:
        """Clean up old log entries"""
        if not self.log_file.exists():
            return

        cutoff_time = datetime.now() - timedelta(days=days)
        temp_file = self.log_file.with_suffix(".tmp")

        try:
            async with (
                aiofiles.open(self.log_file) as infile,
                aiofiles.open(temp_file, "w") as outfile,
            ):
                async for line in infile:
                    try:
                        event_data = json.loads(line.strip())
                        event_time = datetime.fromisoformat(event_data["timestamp"])

                        if event_time > cutoff_time:
                            await outfile.write(line)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        # Keep malformed lines for manual review
                        await outfile.write(line)

            # Replace original file
            temp_file.replace(self.log_file)
            self.logger.info(f"Cleaned up security logs older than {days} days")

        except Exception as e:
            self.logger.error(f"Failed to cleanup old logs: {e}")
            if temp_file.exists():
                temp_file.unlink()


# Global access logger instance
_access_logger = None


def get_access_logger() -> AccessLogger:
    """Get the global access logger instance"""
    global _access_logger
    if _access_logger is None:
        _access_logger = AccessLogger()
    return _access_logger


async def log_security_event(
    event_type: SecurityEventType,
    user_id: str | None = None,
    channel_id: str | None = None,
    action: str = "",
    details: dict[str, Any] | None = None,
    success: bool = True,
) -> None:
    """Convenience function to log a security event"""
    logger = get_access_logger()
    event = SecurityEvent(
        event_type=event_type,
        user_id=user_id,
        channel_id=channel_id,
        action=action,
        details=details,
        success=success,
    )
    await logger.log_event(event)
