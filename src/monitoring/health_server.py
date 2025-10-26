"""
Health check server for Cloud Run
"""

import base64
import binascii
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

from cryptography.fernet import Fernet

from src import __version__
from src.config import get_settings
from src.config.secure_settings import get_secure_settings
from src.utils import get_logger


class OAuthCodeVault:
    """Secure storage helper for OAuth authorization codes."""

    def __init__(
        self,
        storage_path: Path | None = None,
        secure_settings: Any | None = None,
    ) -> None:
        self.logger = get_logger("oauth_code_vault")
        self.secure_settings = secure_settings or get_secure_settings()
        self.storage_path = (
            storage_path or Path("logs") / "google_calendar_auth_code.enc"
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def store_code(self, code: str) -> Path | None:
        """Encrypt and persist the OAuth code if possible."""
        encryption_key = self.secure_settings.get_secure_setting("encryption_key")
        if not encryption_key:
            self.logger.warning(
                "Encryption key not configured; OAuth code will not be persisted"
            )
            return None

        try:
            fernet = Fernet(self._normalize_key(encryption_key))
            encrypted_code = fernet.encrypt(code.encode("utf-8")).decode("utf-8")
            record = {
                "timestamp": datetime.now().isoformat(),
                "payload": encrypted_code,
            }
            with self.storage_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")

            self.logger.info(
                "Encrypted OAuth code stored",
                storage=str(self.storage_path),
            )
            return self.storage_path
        except Exception as exc:
            self.logger.error("Failed to store OAuth code securely", error=str(exc))
            return None

    def _normalize_key(self, key: str) -> bytes:
        """Normalize incoming key strings to a Fernet-compatible key."""
        try:
            decoded = base64.urlsafe_b64decode(key)
            if len(decoded) == 32:
                return base64.urlsafe_b64encode(decoded)
        except (binascii.Error, ValueError) as exc:
            self.logger.debug("Failed to base64 decode encryption key", error=str(exc))

        raw = key.encode("utf-8")
        if len(raw) == 32:
            return base64.urlsafe_b64encode(raw)

        raise ValueError("Encryption key must be 32 bytes or valid base64")


class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health check endpoints"""

    def __init__(self, *args: Any, bot_instance: Any = None, **kwargs: Any) -> None:
        self.bot_instance = bot_instance
        self.logger = get_logger("health_server")
        self.settings = get_settings()
        self.oauth_vault = OAuthCodeVault()
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        """Handle GET requests"""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/ready":
            self._handle_ready()
        elif self.path == "/metrics":
            self._handle_metrics()
        elif self.path.startswith("/callback"):
            self._handle_callback()
        else:
            self._send_response(404, {"error": "Not Found"})

    def _handle_health(self) -> None:
        """Basic health check - always returns healthy if server is running"""
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "mindbridge",
            "version": __version__,
        }
        self._send_response(200, health_data)

    def _handle_ready(self) -> None:
        """Readiness check - checks if bot is connected and operational"""
        if not self.bot_instance:
            self._send_response(
                503, {"status": "not_ready", "reason": "bot_not_initialized"}
            )
            return

        if not self.bot_instance.is_ready:
            self._send_response(
                503, {"status": "not_ready", "reason": "bot_not_connected"}
            )
            return

        # Check guild connection using the bot's Discord client
        guild_connected = False
        if hasattr(self.bot_instance, "bot") and self.bot_instance.bot:
            guild_connected = len(self.bot_instance.bot.guilds) > 0

        ready_data = {
            "status": "ready",
            "timestamp": datetime.now().isoformat(),
            "bot_connected": True,
            "guild_connected": guild_connected,
            "uptime_seconds": (
                datetime.now() - self.bot_instance.start_time
            ).total_seconds(),
        }
        self._send_response(200, ready_data)

    def _handle_metrics(self) -> None:
        """Expose basic metrics for monitoring"""
        if not self._authorize_request("metrics"):
            return

        if not self.bot_instance:
            self._send_response(503, {"error": "bot_not_available"})
            return

        # Build metrics based on actual bot attributes
        guild_count = 0
        if hasattr(self.bot_instance, "bot") and self.bot_instance.bot:
            try:
                guild_count = len(self.bot_instance.bot.guilds)  # type: ignore[attr-defined]
            except Exception:
                guild_count = 0

        start_time = getattr(self.bot_instance, "start_time", None)

        metrics = {
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (
                (datetime.now() - start_time).total_seconds() if start_time else 0
            ),
            "bot_status": {
                "connected": self.bot_instance.is_ready,
                "guild_count": guild_count,
            },
        }

        # Add system metrics if available
        if hasattr(self.bot_instance, "system_metrics"):
            metrics["system_metrics"] = (
                self.bot_instance.system_metrics.get_system_health_status()
            )

        # Add API usage metrics if available
        if hasattr(self.bot_instance, "api_usage_monitor"):
            metrics["api_usage"] = (
                self.bot_instance.api_usage_monitor.get_usage_dashboard()
            )

        self._send_response(200, metrics)

    def _send_response(self, status_code: int, data: dict[str, Any]) -> None:
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        response_body = json.dumps(data, ensure_ascii=False, indent=2)
        self.wfile.write(response_body.encode("utf-8"))

    def _send_html(self, status_code: int, html: str) -> None:
        """Send HTML response"""
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _authorize_request(self, scope: str) -> bool:
        """Ensure sensitive endpoints require an authorization token."""

        token_secret = self._expected_endpoint_token()
        if not token_secret:
            self.logger.warning(
                "Health endpoint token missing; rejecting request",
                scope=scope,
            )
            self._send_response(503, {"error": "health_token_not_configured"})
            return False

        provided_token = self._extract_token_from_headers()
        if provided_token != token_secret:
            self.logger.warning(
                "Unauthorized health endpoint access attempt",
                scope=scope,
                client=self.client_address[0] if self.client_address else "unknown",
            )
            self._send_response(401, {"error": "unauthorized"})
            return False

        return True

    def _extract_token_from_headers(self) -> str | None:
        header_token = self.headers.get("X-Health-Token")
        if header_token:
            return header_token.strip()

        auth_header = self.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            return auth_header.split(" ", 1)[1].strip()

        return None

    def _expected_endpoint_token(self) -> str | None:
        token = getattr(self.settings, "health_endpoint_token", None)
        if token is None:
            return None

        if hasattr(token, "get_secret_value"):
            try:
                return token.get_secret_value()
            except Exception:
                return None

        return str(token)

    def _validate_callback_state(self, state: str | None) -> tuple[bool, str | None]:
        expected = getattr(self.settings, "health_callback_state", None)
        if expected is None:
            return False, "state_not_configured"

        expected_value: str
        if hasattr(expected, "get_secret_value"):
            expected_value = expected.get_secret_value()
        else:
            expected_value = str(expected)

        if not state or state != expected_value:
            return False, "invalid_state"

        return True, None

    def _handle_callback(self) -> None:
        """Handle OAuth callback to capture 'code' and show a friendly page"""
        try:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]

            state_valid, state_issue = self._validate_callback_state(state)
            if not state_valid:
                self.logger.warning(
                    "OAuth callback rejected",
                    reason=state_issue,
                    client=self.client_address[0] if self.client_address else "unknown",
                )
                status_code = 503 if state_issue == "state_not_configured" else 403
                self._send_html(
                    status_code,
                    """
                    <html><body>
                    <h1>Authorization Error</h1>
                    <p>OAuth state token is invalid or missing. Please restart the authorization flow.</p>
                    </body></html>
                    """,
                )
                return

            if not code:
                self._send_html(
                    400,
                    """
                    <html><body>
                    <h1>OAuth Callback</h1>
                    <p>No 'code' parameter was found in the URL.</p>
                    </body></html>
                    """,
                )
                return

            storage_path = self.oauth_vault.store_code(code)
            persisted_message = (
                f"Encrypted record saved to: {storage_path}"
                if storage_path
                else "Secure storage unavailable. Please store the code manually and configure ENCRYPTION_KEY."
            )

            self.logger.info(
                "Received OAuth code", path=self.path, persisted=bool(storage_path)
            )

            self._send_html(
                200,
                f"""
                <html><body>
                <h1>Authentication Code Received</h1>
                <p>Copy this code and paste it in Discord using:<br>
                <code>/calendar_token code:&lt;paste-code-here&gt;</code></p>
                <p><strong>Code:</strong> <code>{code}</code></p>
                <p>{persisted_message}</p>
                </body></html>
                """,
            )
        except Exception as e:
            self.logger.error(f"Failed to handle OAuth callback: {e}")
            self._send_html(
                500,
                """
                <html><body>
                <h1>Error</h1>
                <p>Failed to handle OAuth callback.</p>
                </body></html>
                """,
            )

    def log_message(self, format: str, *args: Any) -> None:
        """Override to use our logger instead of stderr"""
        self.logger.debug(f"Health server: {format % args}")


class HealthServer:
    """Health check server for Cloud Run deployment"""

    def __init__(self, bot_instance: Any = None, port: int = 8080) -> None:
        self.bot_instance = bot_instance
        # Cloud Run uses PORT environment variable
        import os

        cloud_run_port = int(os.environ.get("PORT", port))
        self.port = self._find_available_port(cloud_run_port)
        self.server: HTTPServer | None = None
        self.thread: Thread | None = None
        self.logger = get_logger("health_server")

    def _find_available_port(self, start_port: int) -> int:
        """Find an available port starting from start_port"""
        import socket

        for port in range(start_port, start_port + 10):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("", port))
                    return port
            except OSError:
                continue
        raise OSError(
            f"No available ports found in range {start_port}-{start_port + 9}"
        )

    def start(self) -> None:
        """Start the health check server"""

        def handler(*args: Any, **kwargs: Any) -> HealthCheckHandler:
            return HealthCheckHandler(*args, bot_instance=self.bot_instance, **kwargs)

        try:
            self.server = HTTPServer(("0.0.0.0", self.port), handler)  # nosec: B104
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()

            self.logger.info(f"Health check server started on port {self.port}")
            self.logger.info("Available endpoints:")
            self.logger.info("  - GET /health  - Basic health check")
            self.logger.info("  - GET /ready   - Readiness probe")
            self.logger.info(
                "  - GET /metrics - Application metrics (requires X-Health-Token)"
            )
            self.logger.info(
                "  - GET /callback - OAuth redirect (requires configured state token)"
            )

        except Exception as e:
            self.logger.error(f"Failed to start health server: {e}")
            raise

    def stop(self) -> None:
        """Stop the health check server"""
        if self.server:
            self.logger.info("Stopping health check server")
            self.server.shutdown()
            self.server.server_close()

        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)

        self.logger.info("Health check server stopped")
