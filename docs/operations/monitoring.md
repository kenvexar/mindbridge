# 📊 監視・ログ管理ガイド

MindBridge の包括的な監視、ログ管理、アラート設定について説明します。

## 📋 目次

1. [監視戦略](#監視戦略)
2. [ログ管理](#ログ管理)
3. [メトリクス収集](#メトリクス収集)
4. [アラート設定](#アラート設定)
5. [ダッシュボード設定](#ダッシュボード設定)
6. [パフォーマンス監視](#パフォーマンス監視)
7. [セキュリティ監視](#セキュリティ監視)
8. [トラブルシューティング支援](#トラブルシューティング支援)

## 🎯 監視戦略

### 監視の 4 つの黄金信号

1. **レイテンシ（ Latency ）**: 応答時間
2. **トラフィック（ Traffic ）**: リクエスト数
3. **エラー（ Errors ）**: エラー率
4. **サチュレーション（ Saturation ）**: リソース使用率

### 監視階層

```
┌─────────────────────────────────────────┐
│           Application Layer             │
│  • Discord Bot Status                   │
│  • AI 処理メトリクス                  │
│  • Obsidian File Operations            │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│            Service Layer                │
│  • API 応答時間                       │
│  • External Service Health             │
│  • Database Operations                 │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Infrastructure Layer           │
│  • CPU 、メモリ、ディスク使用量        │
│  • Network I/O                         │
│  • Container Health                    │
└─────────────────────────────────────────┘
```

## 📝 ログ管理

### ログレベル設定

```python
# src/utils/logger.py
import structlog
import logging
from enum import Enum

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# 構造化ログの設定
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### ログ出力例

**正常処理:**
```json
{
  "timestamp": "2025-08-17T10:30:15.123Z",
  "level": "info",
  "event": "message_processed",
  "user_id": "123456789012345678",
  "channel_id": "987654321098765432",
  "processing_time": 1.234,
  "ai_tokens_used": 150,
  "obsidian_file": "00_Inbox/2025-08-17-user-memo.md"
}
```

**エラー処理:**
```json
{
  "timestamp": "2025-08-17T10:31:20.456Z",
  "level": "error",
  "event": "ai_processing_failed",
  "error": "APIError",
  "error_message": "Rate limit exceeded",
  "user_id": "123456789012345678",
  "retry_count": 2,
  "max_retries": 3,
  "stack_trace": "..."
}
```

### Google Cloud Logging 設定

```yaml
# logging.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: logging-config
data:
  log_config.json: |
    {
      "version": 1,
      "disable_existing_loggers": false,
      "formatters": {
        "json": {
          "format": "%(asctime) s %(name) s %(levelname) s %(message) s",
          "class": "pythonjsonlogger.jsonlogger.JsonFormatter"
        }
      },
      "handlers": {
        "console": {
          "class": "logging.StreamHandler",
          "level": "INFO",
          "formatter": "json",
          "stream": "ext://sys.stdout"
        },
        "file": {
          "class": "logging.handlers.RotatingFileHandler",
          "level": "DEBUG",
          "formatter": "json",
          "filename": "/app/logs/bot.log",
          "maxBytes": 10485760,
          "backupCount": 5
        }
      },
      "loggers": {
        "discord": {
          "level": "WARNING"
        },
        "src": {
          "level": "DEBUG"
        }
      },
      "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
      }
    }
```

### ログ集約設定

```bash
# Google Cloud Logging エージェント設定
# /etc/google-fluentd/config.d/discord-bot.conf
<source>
  @type tail
  path /app/logs/bot.log
  pos_file /var/lib/google-fluentd/pos/discord-bot.log.pos
  tag discord.bot
  format json
  time_key timestamp
  time_format %Y-%m-%dT%H:%M:%S.%L%z
</source>

<filter discord.bot>
  @type record_transformer
  <record>
    service_name mindbridge
    environment ${ENV}
  </record>
</filter>

<match discord.bot>
  @type google_cloud
  project_id YOUR_PROJECT_ID
  zone YOUR_ZONE
  vm_id YOUR_VM_ID
  vm_name YOUR_VM_NAME
</match>
```

## 📈 メトリクス収集

### カスタムメトリクス定義

```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
from functools import wraps

# カウンター
MESSAGES_PROCESSED = Counter(
    'discord_messages_processed_total',
    'Total number of processed Discord messages',
    ['channel', 'status']
)

AI_REQUESTS = Counter(
    'ai_requests_total',
    'Total number of AI API requests',
    ['api', 'status']
)

OBSIDIAN_FILES_CREATED = Counter(
    'obsidian_files_created_total',
    'Total number of Obsidian files created',
    ['folder']
)

# ヒストグラム
PROCESSING_TIME = Histogram(
    'message_processing_duration_seconds',
    'Time spent processing messages',
    ['operation']
)

AI_RESPONSE_TIME = Histogram(
    'ai_response_duration_seconds',
    'AI API response time',
    ['api']
)

# ゲージ
ACTIVE_CONNECTIONS = Gauge(
    'discord_active_connections',
    'Number of active Discord connections'
)

MEMORY_USAGE = Gauge(
    'process_memory_usage_bytes',
    'Process memory usage in bytes'
)

# デコレーター
def track_processing_time(operation: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                PROCESSING_TIME.labels(operation=operation).observe(
                    time.time() - start_time
                )
                return result
            except Exception as e:
                PROCESSING_TIME.labels(operation=f"{operation}_error").observe(
                    time.time() - start_time
                )
                raise
        return wrapper
    return decorator

# 使用例
@track_processing_time("ai_analysis")
async def analyze_message(self, content: str):
    # AI 分析処理
    pass
```

### システムメトリクス

```python
# src/monitoring/system_metrics.py
import psutil
import asyncio
from typing import Dict, Any

class SystemMetrics:
    def __init__(self):
        self.process = psutil.Process()

    async def get_metrics(self) -> Dict[str, Any]:
        """システムメトリクスを取得."""
        cpu_percent = self.process.cpu_percent()
        memory_info = self.process.memory_info()
        disk_usage = psutil.disk_usage('/')

        return {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "rss": memory_info.rss,
                "vms": memory_info.vms,
                "percent": self.process.memory_percent(),
                "available": psutil.virtual_memory().available
            },
            "disk": {
                "total": disk_usage.total,
                "used": disk_usage.used,
                "free": disk_usage.free,
                "percent": disk_usage.percent
            },
            "network": {
                "connections": len(self.process.connections())
            }
        }

    async def update_prometheus_metrics(self):
        """Prometheus メトリクスを更新."""
        metrics = await self.get_metrics()

        MEMORY_USAGE.set(metrics["memory"]["rss"])
        ACTIVE_CONNECTIONS.set(metrics["network"]["connections"])
```

### Discord 特有メトリクス

```python
# src/monitoring/discord_metrics.py
class DiscordMetrics:
    def __init__(self, bot_client):
        self.bot = bot_client

    async def collect_discord_metrics(self):
        """Discord 関連メトリクスを収集."""
        if self.bot.is_ready():
            guild_count = len(self.bot.guilds)
            user_count = sum(guild.member_count for guild in self.bot.guilds)
            channel_count = sum(len(guild.channels) for guild in self.bot.guilds)

            # WebSocket latency
            latency = round(self.bot.latency * 1000, 2)

            return {
                "guilds": guild_count,
                "users": user_count,
                "channels": channel_count,
                "latency_ms": latency,
                "shards": len(self.bot.shards) if self.bot.shards else 1
            }
        return {}
```

## 🚨 アラート設定

### Cloud Monitoring アラートポリシー

```yaml
# alert-policies.yaml
displayName: "Discord Bot Critical Alerts"
conditions:
  # エラー率アラート
  - displayName: "High Error Rate"
    conditionThreshold:
      filter: |
        resource.type="cloud_run_revision"
        resource.labels.service_name="mindbridge"
        severity>=ERROR
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 10
      duration: 300s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_RATE
          crossSeriesReducer: REDUCE_SUM

  # レスポンス時間アラート
  - displayName: "High Response Time"
    conditionThreshold:
      filter: |
        metric.type="run.googleapis.com/request_latencies"
        resource.labels.service_name="mindbridge"
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 5000  # 5 秒
      duration: 180s
      aggregations:
        - alignmentPeriod: 60s
          perSeriesAligner: ALIGN_PERCENTILE_95

  # メモリ使用率アラート
  - displayName: "High Memory Usage"
    conditionThreshold:
      filter: |
        metric.type="run.googleapis.com/container/memory/utilizations"
        resource.labels.service_name="mindbridge"
      comparison: COMPARISON_GREATER_THAN
      thresholdValue: 0.8  # 80%
      duration: 300s

# 通知設定
notificationChannels:
  - projects/PROJECT_ID/notificationChannels/EMAIL_CHANNEL
  - projects/PROJECT_ID/notificationChannels/DISCORD_WEBHOOK

alertStrategy:
  autoClose: 604800s  # 7 日後に自動クローズ

documentation:
  content: |
    Discord Obsidian Memo Bot のクリティカルアラート

    トラブルシューティング:
    1. Cloud Run ログを確認
    2. /status コマンドで Bot 状態確認
    3. 必要に応じてサービス再起動
  mimeType: text/markdown
```

### Discord Webhook アラート

```python
# src/monitoring/alerts.py
import aiohttp
import json
from datetime import datetime
from typing import Dict, Any

class DiscordAlerts:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_alert(
        self,
        level: str,
        title: str,
        description: str,
        fields: Dict[str, Any] = None
    ):
        """Discord にアラートを送信."""

        color_map = {
            "critical": 0xFF0000,  # 赤
            "warning": 0xFFA500,   # オレンジ
            "info": 0x00FF00,      # 緑
            "resolved": 0x0080FF   # 青
        }

        embed = {
            "title": f"🚨 {title}",
            "description": description,
            "color": color_map.get(level, 0x808080),
            "timestamp": datetime.utcnow().isoformat(),
            "fields": []
        }

        if fields:
            for key, value in fields.items():
                embed["fields"].append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })

        payload = {
            "embeds": [embed],
            "username": "Monitoring Bot"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status != 204:
                    logger.error(
                        "Failed to send Discord alert",
                        status=response.status,
                        response=await response.text()
                    )

# 使用例
alerts = DiscordAlerts(webhook_url)

await alerts.send_alert(
    level="critical",
    title="High Error Rate Detected",
    description="Error rate exceeded 10% in the last 5 minutes",
    fields={
        "Error Count": 15,
        "Total Requests": 120,
        "Service": "mindbridge",
        "Region": "asia-northeast1"
    }
)
```

## 📊 ダッシュボード設定

### Grafana ダッシュボード設定

```json
{
  "dashboard": {
    "title": "Discord Obsidian Memo Bot",
    "panels": [
      {
        "title": "Message Processing Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(discord_messages_processed_total[5m])",
            "legendFormat": "{{channel}} - {{status}}"
          }
        ]
      },
      {
        "title": "AI Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(ai_response_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(ai_response_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ]
      },
      {
        "title": "System Resources",
        "type": "graph",
        "targets": [
          {
            "expr": "process_memory_usage_bytes",
            "legendFormat": "Memory Usage"
          },
          {
            "expr": "rate(process_cpu_usage_total[5m])",
            "legendFormat": "CPU Usage"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(discord_messages_processed_total{status=\"error\"}[5m]) / rate(discord_messages_processed_total[5m]) * 100",
            "legendFormat": "Error Rate %"
          }
        ]
      }
    ]
  }
}
```

### Cloud Monitoring ダッシュボード

```yaml
# cloud-monitoring-dashboard.yaml
displayName: "Discord Obsidian Memo Bot Dashboard"
mosaicLayout:
  tiles:
    # Cloud Run メトリクス
    - width: 6
      height: 4
      xPos: 0
      yPos: 0
      widget:
        title: "Request Count"
        xyChart:
          dataSets:
            - timeSeriesQuery:
                timeSeriesFilter:
                  filter: |
                    metric.type="run.googleapis.com/request_count"
                    resource.type="cloud_run_revision"
                  aggregation:
                    alignmentPeriod: 60s
                    perSeriesAligner: ALIGN_RATE

    # CPU 使用率
    - width: 6
      height: 4
      xPos: 6
      yPos: 0
      widget:
        title: "CPU Utilization"
        xyChart:
          dataSets:
            - timeSeriesQuery:
                timeSeriesFilter:
                  filter: |
                    metric.type="run.googleapis.com/container/cpu/utilizations"
                    resource.type="cloud_run_revision"

    # メモリ使用率
    - width: 6
      height: 4
      xPos: 0
      yPos: 4
      widget:
        title: "Memory Utilization"
        xyChart:
          dataSets:
            - timeSeriesQuery:
                timeSeriesFilter:
                  filter: |
                    metric.type="run.googleapis.com/container/memory/utilizations"
                    resource.type="cloud_run_revision"

    # エラーログ
    - width: 6
      height: 4
      xPos: 6
      yPos: 4
      widget:
        title: "Error Logs"
        logsPanel:
          filter: |
            resource.type="cloud_run_revision"
            resource.labels.service_name="mindbridge"
            severity>=ERROR
```

## ⚡ パフォーマンス監視

### アプリケーションパフォーマンス

```python
# src/monitoring/performance.py
import asyncio
import time
from collections import defaultdict, deque
from typing import Dict, List

class PerformanceMonitor:
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metrics = defaultdict(lambda: deque(maxlen=window_size))

    def record_timing(self, operation: str, duration: float):
        """処理時間を記録."""
        self.metrics[f"{operation}_duration"].append(duration)

    def record_counter(self, metric: str, value: int = 1):
        """カウンターを記録."""
        self.metrics[metric].append(value)

    def get_stats(self, metric: str) -> Dict[str, float]:
        """統計情報を取得."""
        values = list(self.metrics[metric])
        if not values:
            return {}

        return {
            "count": len(values),
            "avg": sum(values) / len(values),
            "min": min(values),
            "max": max(values),
            "p95": sorted(values)[int(len(values) * 0.95)] if values else 0,
            "p99": sorted(values)[int(len(values) * 0.99)] if values else 0
        }

    async def get_performance_report(self) -> Dict[str, Any]:
        """パフォーマンスレポートを生成."""
        report = {}

        for metric_name in self.metrics:
            if metric_name.endswith('_duration'):
                operation = metric_name.replace('_duration', '')
                report[operation] = self.get_stats(metric_name)

        return report

# グローバルインスタンス
perf_monitor = PerformanceMonitor()

# デコレーター
def monitor_performance(operation: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                perf_monitor.record_timing(operation, duration)
                perf_monitor.record_counter(f"{operation}_success")
                return result
            except Exception as e:
                duration = time.time() - start_time
                perf_monitor.record_timing(f"{operation}_error", duration)
                perf_monitor.record_counter(f"{operation}_error")
                raise
        return wrapper
    return decorator
```

### リソース使用量監視

```python
# src/monitoring/resource_monitor.py
import psutil
import asyncio
from datetime import datetime, timedelta

class ResourceMonitor:
    def __init__(self):
        self.process = psutil.Process()
        self.baseline_memory = self.process.memory_info().rss
        self.memory_samples = deque(maxlen=100)
        self.cpu_samples = deque(maxlen=100)

    async def collect_samples(self):
        """リソース使用量サンプルを収集."""
        while True:
            try:
                # メモリ使用量
                memory_info = self.process.memory_info()
                memory_usage = memory_info.rss / 1024 / 1024  # MB
                self.memory_samples.append({
                    "timestamp": datetime.utcnow(),
                    "usage_mb": memory_usage,
                    "growth_mb": memory_usage - (self.baseline_memory / 1024 / 1024)
                })

                # CPU 使用率
                cpu_percent = self.process.cpu_percent()
                self.cpu_samples.append({
                    "timestamp": datetime.utcnow(),
                    "usage_percent": cpu_percent
                })

                # メモリリーク検出
                if len(self.memory_samples) >= 10:
                    recent_avg = sum(s["usage_mb"] for s in list(self.memory_samples)[-10:]) / 10
                    older_avg = sum(s["usage_mb"] for s in list(self.memory_samples)[-50:-40]) / 10

                    if recent_avg > older_avg * 1.5:  # 50% 以上の増加
                        logger.warning(
                            "Potential memory leak detected",
                            recent_avg=recent_avg,
                            older_avg=older_avg,
                            growth_rate=(recent_avg / older_avg - 1) * 100
                        )

                await asyncio.sleep(30)  # 30 秒間隔

            except Exception as e:
                logger.error("Resource monitoring failed", error=str(e))
                await asyncio.sleep(60)

    def get_resource_summary(self) -> Dict[str, Any]:
        """リソース使用量サマリーを取得."""
        if not self.memory_samples:
            return {}

        recent_memory = list(self.memory_samples)[-10:]
        recent_cpu = list(self.cpu_samples)[-10:]

        return {
            "memory": {
                "current_mb": recent_memory[-1]["usage_mb"],
                "avg_mb": sum(s["usage_mb"] for s in recent_memory) / len(recent_memory),
                "max_mb": max(s["usage_mb"] for s in recent_memory),
                "growth_mb": recent_memory[-1]["growth_mb"]
            },
            "cpu": {
                "current_percent": recent_cpu[-1]["usage_percent"],
                "avg_percent": sum(s["usage_percent"] for s in recent_cpu) / len(recent_cpu),
                "max_percent": max(s["usage_percent"] for s in recent_cpu)
            }
        }
```

## 🔒 セキュリティ監視

### セキュリティイベント検出

```python
# src/monitoring/security_monitor.py
import re
from datetime import datetime, timedelta
from collections import defaultdict

class SecurityMonitor:
    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.suspicious_patterns = [
            r'(?i)(union|select|drop|insert|delete|update|exec)',  # SQL injection
            r'(?i)(<script|javascript:|onload=)',  # XSS
            r'(?i)(\.\.\/|\.\.\\)',  # Path traversal
        ]

    async def log_security_event(
        self,
        event_type: str,
        user_id: str,
        details: Dict[str, Any],
        severity: str = "info"
    ):
        """セキュリティイベントをログ記録."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "severity": severity,
            "details": details
        }

        # 構造化ログとして出力
        logger.bind(**event).info("Security event logged")

        # 重要度が高い場合はアラート送信
        if severity in ["warning", "error", "critical"]:
            await self.send_security_alert(event)

    async def analyze_message_content(self, user_id: str, content: str):
        """メッセージ内容をセキュリティ分析."""
        suspicious_findings = []

        for pattern in self.suspicious_patterns:
            if re.search(pattern, content):
                suspicious_findings.append({
                    "pattern": pattern,
                    "matched_text": re.search(pattern, content).group()
                })

        if suspicious_findings:
            await self.log_security_event(
                event_type="suspicious_content",
                user_id=user_id,
                details={
                    "content_length": len(content),
                    "findings": suspicious_findings
                },
                severity="warning"
            )

    async def detect_rate_limit_abuse(self, user_id: str):
        """レート制限濫用を検出."""
        now = datetime.utcnow()
        cutoff = now - timedelta(minutes=5)

        # 5 分間のリクエスト数を計算
        recent_requests = [
            req for req in self.failed_attempts[user_id]
            if req > cutoff
        ]

        if len(recent_requests) > 20:  # 5 分間で 20 回以上
            await self.log_security_event(
                event_type="rate_limit_abuse",
                user_id=user_id,
                details={
                    "request_count": len(recent_requests),
                    "time_window": "5_minutes"
                },
                severity="warning"
            )
```

## 🔧 トラブルシューティング支援

### 診断用エンドポイント

```python
# src/monitoring/diagnostics.py
from fastapi import FastAPI
from typing import Dict, Any

class DiagnosticsAPI:
    def __init__(self, app: FastAPI, bot_client):
        self.app = app
        self.bot = bot_client
        self.setup_routes()

    def setup_routes(self):
        @self.app.get("/health")
        async def health_check():
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "discord_ready": self.bot.is_ready() if self.bot else False
            }

        @self.app.get("/metrics")
        async def get_metrics():
            return await self.collect_all_metrics()

        @self.app.get("/debug/config")
        async def debug_config():
            # 機密情報を除いた設定情報
            return {
                "environment": os.getenv("ENVIRONMENT"),
                "log_level": os.getenv("LOG_LEVEL"),
                "obsidian_vault_configured": bool(os.getenv("OBSIDIAN_VAULT_PATH")),
                "channels_configured": self.count_configured_channels()
            }

        @self.app.get("/debug/discord")
        async def debug_discord():
            if not self.bot or not self.bot.is_ready():
                return {"status": "not_ready"}

            return {
                "status": "ready",
                "latency": round(self.bot.latency * 1000, 2),
                "guilds": len(self.bot.guilds),
                "users": sum(guild.member_count for guild in self.bot.guilds),
                "shards": len(self.bot.shards) if self.bot.shards else 1
            }

    async def collect_all_metrics(self) -> Dict[str, Any]:
        """全メトリクスを収集."""
        return {
            "system": await system_metrics.get_metrics(),
            "performance": await perf_monitor.get_performance_report(),
            "resources": resource_monitor.get_resource_summary(),
            "discord": await discord_metrics.collect_discord_metrics()
        }
```

### 自動診断スクリプト

```bash
#!/bin/bash
# scripts/diagnose.sh

echo "🔍 Discord Obsidian Memo Bot 診断ツール"
echo "========================================"

# 基本ヘルスチェック
echo "1. ヘルスチェック"
HEALTH_RESPONSE=$(curl -s http://localhost:8080/health)
echo "Status: $(echo $HEALTH_RESPONSE | jq -r '.status')"
echo "Discord Ready: $(echo $HEALTH_RESPONSE | jq -r '.discord_ready')"

# システムメトリクス
echo -e "\n2. システムメトリクス"
METRICS=$(curl -s http://localhost:8080/metrics)
echo "Memory Usage: $(echo $METRICS | jq -r '.system.memory.percent')%"
echo "CPU Usage: $(echo $METRICS | jq -r '.system.cpu.percent')%"
echo "Disk Usage: $(echo $METRICS | jq -r '.system.disk.percent')%"

# Discord 状態
echo -e "\n3. Discord 状態"
DISCORD_DEBUG=$(curl -s http://localhost:8080/debug/discord)
echo "Latency: $(echo $DISCORD_DEBUG | jq -r '.latency') ms"
echo "Guilds: $(echo $DISCORD_DEBUG | jq -r '.guilds')"

# 最近のエラー
echo -e "\n4. 最近のエラーログ"
tail -n 20 logs/bot.log | jq -r 'select(.level == "error") | "\(.timestamp) - \(.event): \(.error_message)"' | tail -5

# パフォーマンス
echo -e "\n5. パフォーマンス統計"
PERF=$(echo $METRICS | jq -r '.performance')
echo "Message Processing Avg: $(echo $PERF | jq -r '.message_processing.avg // "N/A"') s"
echo "AI Response Avg: $(echo $PERF | jq -r '.ai_analysis.avg // "N/A"') s"

echo -e "\n ✅ 診断完了"
```

## 📋 監視チェックリスト

### 日次チェック
- [ ] ヘルスチェックエンドポイントの確認
- [ ] エラーログの確認
- [ ] リソース使用量の確認
- [ ] パフォーマンスメトリクスの確認

### 週次チェック
- [ ] ダッシュボードの全体確認
- [ ] アラート設定の見直し
- [ ] ログローテーション
- [ ] バックアップの確認

### 月次チェック
- [ ] 監視設定の最適化
- [ ] アラートしきい値の調整
- [ ] パフォーマンストレンドの分析
- [ ] セキュリティログの分析

---

この監視・ログ管理ガイドを活用して、 MindBridge の安定稼働を確保してください。問題の早期発見と迅速な対応により、サービス品質を維持できます。
