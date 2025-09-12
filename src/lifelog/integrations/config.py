"""
外部連携専用設定管理

外部連携の設定とシークレット情報を安全に管理するためのモジュール
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from cryptography.fernet import Fernet
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_serializer

logger = structlog.get_logger(__name__)


@dataclass
class EncryptionConfig:
    """暗号化設定"""

    key_file: str = "integration_key.key"
    encrypted_suffix: str = ".encrypted"

    def generate_key(self) -> bytes:
        """新しい暗号化キーを生成"""
        return Fernet.generate_key()

    def get_key_path(self, config_dir: Path) -> Path:
        """暗号化キーのパスを取得"""
        return config_dir / self.key_file


class IntegrationCredentials(BaseModel):
    """外部連携認証情報"""

    integration_name: str = Field(..., description="連携名")

    # OAuth2 設定
    client_id: SecretStr | None = Field(None, description="クライアント ID")
    client_secret: SecretStr | None = Field(
        None, description="クライアントシークレット"
    )
    access_token: SecretStr | None = Field(None, description="アクセストークン")
    refresh_token: SecretStr | None = Field(None, description="リフレッシュトークン")
    token_expires_at: datetime | None = Field(None, description="トークン有効期限")

    # API キー認証
    api_key: SecretStr | None = Field(None, description="API キー")
    api_secret: SecretStr | None = Field(None, description="API シークレット")

    # その他認証情報
    username: SecretStr | None = Field(None, description="ユーザー名")
    password: SecretStr | None = Field(None, description="パスワード")

    # メタデータ
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict()

    @field_serializer("access_token", "refresh_token", "client_secret")
    def serialize_secret(self, value: SecretStr | None) -> str | None:
        """SecretStr を安全にシリアライズ"""
        return value.get_secret_value() if value else None

    @field_serializer("created_at", "updated_at", "token_expires_at")
    def serialize_datetime(self, value: datetime | None) -> str | None:
        """datetime を ISO format で出力"""
        return value.isoformat() if value else None


class IntegrationSettings(BaseModel):
    """外部連携設定"""

    integration_name: str = Field(..., description="連携名")
    enabled: bool = Field(default=False, description="有効/無効")

    # 同期設定
    sync_enabled: bool = Field(default=True, description="自動同期有効")
    sync_interval: int = Field(default=3600, description="同期間隔（秒）")
    sync_on_startup: bool = Field(default=False, description="起動時同期")

    # データ設定
    data_retention_days: int = Field(default=90, description="データ保持日数")
    sync_historical_data: bool = Field(default=False, description="過去データ同期")

    # API 制限設定
    rate_limit_requests: int = Field(
        default=1000, description="レート制限（リクエスト数）"
    )
    rate_limit_window: int = Field(
        default=3600, description="レート制限ウィンドウ（秒）"
    )

    # 通知設定
    notify_on_success: bool = Field(default=False, description="成功通知")
    notify_on_error: bool = Field(default=True, description="エラー通知")

    # カスタム設定
    custom_settings: dict[str, Any] = Field(
        default_factory=dict, description="カスタム設定"
    )

    # メタデータ
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class IntegrationConfigManager:
    """外部連携設定マネージャー"""

    def __init__(self, config_dir: Path | None = None):
        # 設定ディレクトリ
        if config_dir is None:
            home_dir = Path.home()
            config_dir = home_dir / ".mindbridge" / "integrations"

        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # 設定ファイル
        self.settings_file = self.config_dir / "settings.json"
        self.credentials_file = self.config_dir / "credentials.json.encrypted"

        # 暗号化設定
        self.encryption_config = EncryptionConfig()
        self._encryption_key: bytes | None = None

        # キャッシュ
        self._settings_cache: dict[str, IntegrationSettings] = {}
        self._credentials_cache: dict[str, IntegrationCredentials] = {}

        self.logger = structlog.get_logger(__name__)

    def _get_encryption_key(self) -> bytes:
        """暗号化キーを取得（初回時は生成）"""
        if self._encryption_key is not None:
            return self._encryption_key

        key_path = self.encryption_config.get_key_path(self.config_dir)

        if key_path.exists():
            # 既存キーを読み込み
            with open(key_path, "rb") as f:
                self._encryption_key = f.read()
        else:
            # 新規キー生成
            self._encryption_key = self.encryption_config.generate_key()

            # キーを保存（権限を厳しく設定）
            with open(key_path, "wb") as f:
                f.write(self._encryption_key)

            # ファイル権限を所有者のみ読み書き可能に設定（ Unix 系）
            if hasattr(os, "chmod"):
                key_path.chmod(0o600)

            self.logger.info("新しい暗号化キーを生成しました", key_file=str(key_path))

        return self._encryption_key

    def _encrypt_data(self, data: str) -> bytes:
        """データを暗号化"""
        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.encrypt(data.encode("utf-8"))

    def _decrypt_data(self, encrypted_data: bytes) -> str:
        """データを復号化"""
        key = self._get_encryption_key()
        fernet = Fernet(key)
        return fernet.decrypt(encrypted_data).decode("utf-8")

    def _save_settings(self):
        """設定を保存"""
        settings_data = {}
        for name, settings in self._settings_cache.items():
            settings_dict = settings.model_dump()
            # datetime を ISO 文字列に変換
            for key, value in settings_dict.items():
                if isinstance(value, datetime):
                    settings_dict[key] = value.isoformat()
            settings_data[name] = settings_dict

        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=2)

        # ファイル権限設定
        if hasattr(os, "chmod"):
            self.settings_file.chmod(0o600)

    def _load_settings(self):
        """設定を読み込み"""
        if not self.settings_file.exists():
            return

        try:
            with open(self.settings_file, encoding="utf-8") as f:
                settings_data = json.load(f)

            for name, settings_dict in settings_data.items():
                # datetime 文字列を datetime オブジェクトに変換
                for key, value in settings_dict.items():
                    if key in ["created_at", "updated_at"] and isinstance(value, str):
                        settings_dict[key] = datetime.fromisoformat(value)

                self._settings_cache[name] = IntegrationSettings(**settings_dict)

        except Exception as e:
            self.logger.error("設定読み込みでエラー", error=str(e))

    def _save_credentials(self):
        """認証情報を暗号化して保存"""
        credentials_data = {}
        for name, credentials in self._credentials_cache.items():
            # SecretStr と datetime を適切にシリアライズ
            cred_dict = credentials.model_dump()

            # SecretStr の値を取得
            for key, value in cred_dict.items():
                if key in [
                    "client_id",
                    "client_secret",
                    "access_token",
                    "refresh_token",
                    "api_key",
                    "api_secret",
                    "username",
                    "password",
                ]:
                    if value:
                        # SecretStr の場合は get_secret_value() で値を取得
                        actual_value = getattr(credentials, key)
                        if actual_value:
                            cred_dict[key] = actual_value.get_secret_value()
                elif isinstance(value, datetime):
                    cred_dict[key] = value.isoformat()

            credentials_data[name] = cred_dict

        # JSON 文字列に変換
        json_data = json.dumps(credentials_data, ensure_ascii=False, indent=2)

        # 暗号化
        encrypted_data = self._encrypt_data(json_data)

        # 保存
        with open(self.credentials_file, "wb") as f:
            f.write(encrypted_data)

        # ファイル権限設定
        if hasattr(os, "chmod"):
            self.credentials_file.chmod(0o600)

    def _load_credentials(self):
        """認証情報を復号化して読み込み"""
        if not self.credentials_file.exists():
            return

        try:
            # 暗号化されたデータを読み込み
            with open(self.credentials_file, "rb") as f:
                encrypted_data = f.read()

            # 復号化
            json_data = self._decrypt_data(encrypted_data)
            credentials_data = json.loads(json_data)

            for name, cred_dict in credentials_data.items():
                # datetime 文字列を datetime オブジェクトに変換
                for key, value in cred_dict.items():
                    if key in [
                        "created_at",
                        "updated_at",
                        "token_expires_at",
                    ] and isinstance(value, str):
                        cred_dict[key] = datetime.fromisoformat(value)

                self._credentials_cache[name] = IntegrationCredentials(**cred_dict)

        except Exception as e:
            self.logger.error("認証情報読み込みでエラー", error=str(e))

    def initialize(self):
        """初期化"""
        self._load_settings()
        self._load_credentials()
        self.logger.info(
            "外部連携設定マネージャーを初期化", config_dir=str(self.config_dir)
        )

    # === 設定管理 ===

    def get_settings(self, integration_name: str) -> IntegrationSettings | None:
        """設定を取得"""
        return self._settings_cache.get(integration_name)

    def set_settings(self, settings: IntegrationSettings):
        """設定を保存"""
        settings.updated_at = datetime.now()
        self._settings_cache[settings.integration_name] = settings
        self._save_settings()
        self.logger.info("設定を保存", integration_name=settings.integration_name)

    def get_all_settings(self) -> dict[str, IntegrationSettings]:
        """全設定を取得"""
        return self._settings_cache.copy()

    def delete_settings(self, integration_name: str) -> bool:
        """設定を削除"""
        if integration_name in self._settings_cache:
            del self._settings_cache[integration_name]
            self._save_settings()
            self.logger.info("設定を削除", integration_name=integration_name)
            return True
        return False

    # === 認証情報管理 ===

    def get_credentials(self, integration_name: str) -> IntegrationCredentials | None:
        """認証情報を取得"""
        return self._credentials_cache.get(integration_name)

    def set_credentials(self, credentials: IntegrationCredentials):
        """認証情報を保存"""
        credentials.updated_at = datetime.now()
        self._credentials_cache[credentials.integration_name] = credentials
        self._save_credentials()
        self.logger.info(
            "認証情報を保存", integration_name=credentials.integration_name
        )

    def delete_credentials(self, integration_name: str) -> bool:
        """認証情報を削除"""
        if integration_name in self._credentials_cache:
            del self._credentials_cache[integration_name]
            self._save_credentials()
            self.logger.info("認証情報を削除", integration_name=integration_name)
            return True
        return False

    def update_tokens(
        self,
        integration_name: str,
        access_token: str | None = None,
        refresh_token: str | None = None,
        expires_at: datetime | None = None,
    ) -> bool:
        """トークン情報を更新"""
        if integration_name not in self._credentials_cache:
            return False

        credentials = self._credentials_cache[integration_name]

        if access_token:
            credentials.access_token = SecretStr(access_token)
        if refresh_token:
            credentials.refresh_token = SecretStr(refresh_token)
        if expires_at:
            credentials.token_expires_at = expires_at

        credentials.updated_at = datetime.now()
        self._save_credentials()

        self.logger.info("トークン情報を更新", integration_name=integration_name)
        return True

    # === ユーティリティ ===

    def list_integrations(self) -> list[str]:
        """設定されている連携一覧を取得"""
        settings_keys = set(self._settings_cache.keys())
        credentials_keys = set(self._credentials_cache.keys())
        return sorted(settings_keys.union(credentials_keys))

    def is_configured(self, integration_name: str) -> bool:
        """連携が設定されているかチェック"""
        return (
            integration_name in self._settings_cache
            or integration_name in self._credentials_cache
        )

    def is_authenticated(self, integration_name: str) -> bool:
        """認証済みかチェック"""
        credentials = self.get_credentials(integration_name)
        if not credentials:
            return False

        # トークンベース認証
        if credentials.access_token:
            # 有効期限チェック
            if credentials.token_expires_at:
                return datetime.now() < credentials.token_expires_at
            return True

        # API キー認証
        if credentials.api_key:
            return True

        # ユーザー名/パスワード認証
        if credentials.username and credentials.password:
            return True

        return False

    def get_integration_status(self, integration_name: str) -> dict[str, Any]:
        """連携ステータス情報を取得"""
        settings = self.get_settings(integration_name)
        credentials = self.get_credentials(integration_name)

        status: dict[str, Any] = {
            "configured": self.is_configured(integration_name),
            "authenticated": self.is_authenticated(integration_name),
            "enabled": settings.enabled if settings else False,
            "sync_enabled": settings.sync_enabled if settings else False,
        }

        if credentials and credentials.token_expires_at:
            status["token_expires_at"] = credentials.token_expires_at.isoformat()
            status["token_expires_soon"] = (
                credentials.token_expires_at - datetime.now()
            ).total_seconds() < 1800  # 30 分以内

        return status

    def backup_config(self, backup_path: Path):
        """設定をバックアップ"""
        backup_data = {
            "settings": {
                name: settings.model_dump()
                for name, settings in self._settings_cache.items()
            },
            "backup_created_at": datetime.now().isoformat(),
        }

        # 認証情報は含めない（セキュリティのため）

        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)

        self.logger.info("設定をバックアップ", backup_path=str(backup_path))

    def cleanup_expired_tokens(self) -> int:
        """期限切れトークンをクリーンアップ"""
        cleaned_count = 0
        now = datetime.now()

        for integration_name, credentials in self._credentials_cache.items():
            if credentials.token_expires_at and credentials.token_expires_at < now:
                # 期限切れトークンを削除
                credentials.access_token = None
                credentials.token_expires_at = None
                credentials.updated_at = now
                cleaned_count += 1

                self.logger.info(
                    "期限切れトークンをクリーンアップ",
                    integration_name=integration_name,
                )

        if cleaned_count > 0:
            self._save_credentials()

        return cleaned_count
