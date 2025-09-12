"""
外部連携の基盤クラス群

すべての外部連携実装のベースとなる抽象クラスとデータモデル
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class IntegrationStatus(str, Enum):
    """連携ステータス"""

    DISABLED = "disabled"  # 無効
    ENABLED = "enabled"  # 有効
    AUTHENTICATED = "authenticated"  # 認証済み
    ERROR = "error"  # エラー状態
    SYNCING = "syncing"  # 同期中
    RATE_LIMITED = "rate_limited"  # レート制限中


class IntegrationConfig(BaseModel):
    """連携設定"""

    integration_name: str = Field(..., description="連携名")
    enabled: bool = Field(default=False, description="有効/無効")

    # 認証設定
    auth_type: str = Field(default="oauth2", description="認証タイプ")
    client_id: str | None = Field(None, description="クライアント ID")
    client_secret: str | None = Field(None, description="クライアントシークレット")
    access_token: str | None = Field(None, description="アクセストークン")
    refresh_token: str | None = Field(None, description="リフレッシュトークン")
    token_expires_at: datetime | None = Field(None, description="トークン有効期限")

    # 同期設定
    sync_enabled: bool = Field(default=True, description="自動同期有効")
    sync_interval: int = Field(default=3600, description="同期間隔（秒）")  # 1 時間
    last_sync: datetime | None = Field(None, description="最終同期日時")

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

    # カスタム設定
    custom_settings: dict[str, Any] = Field(
        default_factory=dict, description="カスタム設定"
    )


class IntegrationMetrics(BaseModel):
    """連携メトリクス"""

    integration_name: str
    status: IntegrationStatus = Field(default=IntegrationStatus.DISABLED)

    # 統計情報
    total_records_synced: int = Field(default=0, description="同期済み総レコード数")
    records_synced_today: int = Field(default=0, description="本日同期レコード数")
    last_sync_duration: float | None = Field(None, description="最終同期時間（秒）")
    average_sync_duration: float | None = Field(None, description="平均同期時間（秒）")

    # エラー統計
    total_errors: int = Field(default=0, description="総エラー数")
    recent_errors: list[str] = Field(default_factory=list, description="最近のエラー")

    # レート制限情報
    requests_made_today: int = Field(default=0, description="本日リクエスト数")
    rate_limit_remaining: int | None = Field(None, description="レート制限残数")
    rate_limit_reset_at: datetime | None = Field(
        None, description="レート制限リセット時刻"
    )

    # パフォーマンス
    health_score: float = Field(default=100.0, description="ヘルススコア（ 0-100 ）")
    uptime_percentage: float = Field(default=100.0, description="稼働率（% ）")

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class IntegrationData(BaseModel):
    """外部連携から取得したデータの基本構造"""

    integration_name: str = Field(..., description="データソース")
    external_id: str = Field(..., description="外部システムでの ID")
    data_type: str = Field(..., description="データタイプ")
    timestamp: datetime = Field(..., description="データ発生日時")

    # メタデータ
    raw_data: dict[str, Any] = Field(..., description="生データ")
    processed_data: dict[str, Any] = Field(
        default_factory=dict, description="処理済みデータ"
    )

    # 品質情報
    confidence_score: float = Field(
        default=1.0, description="データ信頼度（ 0-1 ）", ge=0, le=1
    )
    data_quality: str = Field(default="good", description="データ品質")

    # 処理状態
    processed: bool = Field(default=False, description="処理済みフラグ")
    lifelog_entry_created: bool = Field(
        default=False, description="ライフログエントリー作成済み"
    )
    lifelog_entry_id: str | None = Field(
        None, description="関連ライフログエントリー ID"
    )

    created_at: datetime = Field(default_factory=datetime.now)


class BaseIntegration(ABC):
    """外部連携の基底クラス"""

    def __init__(self, config: IntegrationConfig):
        self.config = config
        self.logger = structlog.get_logger(
            __name__, integration=config.integration_name
        )
        self.metrics = IntegrationMetrics(integration_name=config.integration_name)
        self._authenticated = False
        self._last_error: str | None = None

    # === 必須実装メソッド ===

    @abstractmethod
    async def authenticate(self) -> bool:
        """認証を実行"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """接続テスト"""
        pass

    @abstractmethod
    async def sync_data(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> list[IntegrationData]:
        """データ同期"""
        pass

    @abstractmethod
    async def get_available_data_types(self) -> list[str]:
        """利用可能なデータタイプを取得"""
        pass

    # === 共通メソッド ===

    async def is_authenticated(self) -> bool:
        """認証状態確認"""
        return self._authenticated

    async def refresh_authentication(self) -> bool:
        """認証更新"""
        try:
            if self.config.refresh_token:
                # リフレッシュトークンがある場合は自動更新を試行
                return await self._refresh_token()
            else:
                # リフレッシュトークンがない場合は再認証が必要
                self.logger.warning(
                    "リフレッシュトークンがありません。再認証が必要です"
                )
                return False
        except Exception as e:
            self.logger.error("認証更新でエラー", error=str(e))
            return False

    async def _refresh_token(self) -> bool:
        """トークンリフレッシュ（サブクラスでオーバーライド）"""
        return False

    def update_metrics(self, **kwargs):
        """メトリクス更新"""
        for key, value in kwargs.items():
            if hasattr(self.metrics, key):
                setattr(self.metrics, key, value)
        self.metrics.updated_at = datetime.now()

    def add_error(self, error_message: str):
        """エラー記録"""
        self._last_error = error_message
        self.metrics.total_errors += 1
        self.metrics.recent_errors.append(
            f"{datetime.now().isoformat()}: {error_message}"
        )

        # 最新 10 件のエラーのみ保持
        if len(self.metrics.recent_errors) > 10:
            self.metrics.recent_errors = self.metrics.recent_errors[-10:]

        self.logger.error("連携エラー", error=error_message)

    def get_status(self) -> IntegrationStatus:
        """現在のステータス取得"""
        if not self.config.enabled:
            return IntegrationStatus.DISABLED
        elif self._last_error:
            return IntegrationStatus.ERROR
        elif self._authenticated:
            return IntegrationStatus.AUTHENTICATED
        else:
            return IntegrationStatus.ENABLED

    async def check_rate_limit(self) -> bool:
        """レート制限チェック"""
        if self.metrics.rate_limit_reset_at:
            if datetime.now() < self.metrics.rate_limit_reset_at:
                if self.metrics.requests_made_today >= self.config.rate_limit_requests:
                    return False
        return True

    def increment_request_count(self):
        """リクエスト数をインクリメント"""
        self.metrics.requests_made_today += 1

        # 日が変わったらリセット
        now = datetime.now()
        if self.metrics.updated_at.date() != now.date():
            self.metrics.requests_made_today = 1
            self.metrics.records_synced_today = 0

    async def validate_config(self) -> list[str]:
        """設定検証"""
        errors = []

        if not self.config.integration_name:
            errors.append("連携名が設定されていません")

        if self.config.enabled and not self.config.access_token:
            errors.append("アクセストークンが設定されていません")

        if self.config.sync_interval < 60:
            errors.append("同期間隔は 60 秒以上である必要があります")

        return errors

    async def get_health_info(self) -> dict[str, Any]:
        """ヘルス情報取得"""
        return {
            "integration_name": self.config.integration_name,
            "status": self.get_status().value,
            "authenticated": self._authenticated,
            "last_sync": self.config.last_sync.isoformat()
            if self.config.last_sync
            else None,
            "health_score": self.metrics.health_score,
            "uptime_percentage": self.metrics.uptime_percentage,
            "total_records": self.metrics.total_records_synced,
            "recent_errors": len(self.metrics.recent_errors),
            "rate_limit_remaining": self.metrics.rate_limit_remaining,
        }

    async def cleanup_old_data(self):
        """古いデータのクリーンアップ"""
        cutoff_date = datetime.now() - timedelta(days=self.config.data_retention_days)
        self.logger.info(
            "古いデータをクリーンアップ",
            cutoff_date=cutoff_date.isoformat(),
            retention_days=self.config.data_retention_days,
        )
        # サブクラスでオーバーライドして具体的なクリーンアップ処理を実装


class IntegrationDataProcessor:
    """外部連携データの処理ユーティリティ"""

    @staticmethod
    def parse_timestamp(timestamp: str | int | float | datetime) -> datetime:
        """タイムスタンプを datetime オブジェクトに変換"""
        if isinstance(timestamp, datetime):
            return timestamp
        elif isinstance(timestamp, str):
            # ISO 8601 形式を試行
            try:
                return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except ValueError:
                # その他の形式を試行
                from dateutil.parser import parse

                return parse(timestamp)
        elif isinstance(timestamp, int | float):
            # UNIX タイムスタンプ
            return datetime.fromtimestamp(timestamp)
        else:
            raise ValueError(f"無効なタイムスタンプ形式: {type(timestamp)}")

    @staticmethod
    def normalize_timestamp(timestamp: str | int | float | datetime) -> datetime:
        """タイムスタンプを正規化（ parse_timestamp のエイリアス）"""
        return IntegrationDataProcessor.parse_timestamp(timestamp)

    @staticmethod
    def extract_numeric_value(data: dict[str, Any], keys: list[str]) -> float | None:
        """辞書から数値を抽出"""
        for key in keys:
            value = data.get(key)
            if value is not None:
                try:
                    return float(value)
                except (ValueError, TypeError):
                    continue
        return None

    @staticmethod
    def normalize_data(
        data: dict[str, Any],
        field_mapping: dict[str, list[str]],
    ) -> dict[str, Any]:
        """フィールドマッピングを使用してデータを正規化"""
        normalized = {}
        for field, keys in field_mapping.items():
            value = IntegrationDataProcessor.extract_numeric_value(data, keys)
            if value is not None:
                normalized[field] = value
        return normalized

    @staticmethod
    def calculate_data_quality(
        data: dict[str, Any], required_fields: list[str] | None = None
    ) -> str:
        """データ品質を計算"""
        if not data:
            return "poor"

        # デフォルトの必須フィールド
        if required_fields is None:
            required_fields = ["timestamp", "id", "type"]

        # 必須フィールドの存在をチェック
        missing_fields = set(required_fields) - set(data.keys())

        if len(missing_fields) == 0:
            return "excellent"
        elif len(missing_fields) == 1:
            return "good"
        elif len(missing_fields) == 2:
            return "fair"
        else:
            return "poor"
