"""
Garmin Connect client for health data retrieval
"""

import asyncio
import socket
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import get_settings
from src.garmin.cache import GarminDataCache
from src.garmin.models import (
    ActivityData,
    DataError,
    DataSource,
    GarminAuthenticationError,
    GarminConnectionError,
    GarminDataRetrievalError,
    GarminOfflineError,
    GarminRateLimitError,
    GarminTimeoutError,
    HealthData,
    HeartRateData,
    SleepData,
    StepsData,
)
from src.utils.mixins import LoggerMixin

# Settings loaded lazily to avoid circular imports


class GarminClient(LoggerMixin):
    """Garmin Connect API クライアント"""

    def __init__(self, cache_dir: Path | None = None):
        """初期化処理"""
        self.client: Garmin | None = None
        self.is_authenticated = False
        self._last_authentication: datetime | None = None
        self._consecutive_failures = 0
        self._backoff_until: datetime | None = None

        # 認証情報の確認
        self.email: str | None = None
        self.password: str | None = None
        self._check_credentials()

        # キャッシュシステムの初期化
        if cache_dir is None:
            cache_dir = Path.cwd() / ".cache" / "garmin"
        self.cache = GarminDataCache(cache_dir)

        # 設定
        self.api_timeout = 30.0  # 30秒
        self.max_consecutive_failures = 3
        self.backoff_hours = 1.0

        self.logger.info(
            "Garmin client initialized",
            has_credentials=bool(self.email and self.password),
            cache_dir=str(cache_dir),
        )

    def _check_credentials(self) -> None:
        """認証情報の確認"""
        try:
            settings = get_settings()
            if hasattr(settings, "garmin_email") and settings.garmin_email:
                if hasattr(settings.garmin_email, "get_secret_value"):
                    self.email = settings.garmin_email.get_secret_value()
                else:
                    self.email = str(settings.garmin_email)

            if hasattr(settings, "garmin_password") and settings.garmin_password:
                if hasattr(settings.garmin_password, "get_secret_value"):
                    self.password = settings.garmin_password.get_secret_value()
                else:
                    self.password = str(settings.garmin_password)

        except Exception as e:
            self.logger.error("Error checking Garmin credentials", error=str(e))

        if not (self.email and self.password):
            self.logger.warning(
                "Garmin credentials not found - health data integration will be disabled"
            )

    def _check_network_connectivity(self) -> bool:
        """ネットワーク接続をチェック"""
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            return True
        except OSError:
            return False

    def _is_in_backoff_period(self) -> bool:
        """バックオフ期間中かどうかを確認"""
        if self._backoff_until is None:
            return False
        return datetime.now() < self._backoff_until

    def _enter_backoff_period(self) -> None:
        """バックオフ期間に入る"""
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.max_consecutive_failures:
            self._backoff_until = datetime.now() + timedelta(hours=self.backoff_hours)
            self.logger.warning(
                "Entering backoff period due to consecutive failures",
                consecutive_failures=self._consecutive_failures,
                backoff_until=self._backoff_until.isoformat()
                if self._backoff_until
                else "unknown",
            )

    def _reset_failure_count(self) -> None:
        """失敗カウントをリセット"""
        self._consecutive_failures = 0
        self._backoff_until = None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type(
            (GarminConnectConnectionError, GarminConnectTooManyRequestsError)
        ),
    )
    async def authenticate(self) -> bool:
        """Garmin Connect に認証"""
        if not (self.email and self.password):
            raise GarminAuthenticationError("Garmin credentials not configured")

        # バックオフ期間チェック
        if self._is_in_backoff_period():
            raise GarminOfflineError(f"In backoff period until {self._backoff_until}")

        # ネットワーク接続チェック
        if not self._check_network_connectivity():
            raise GarminOfflineError("Network connectivity not available")

        try:
            self.logger.info("Attempting to authenticate with Garmin Connect")

            # タイムアウト付きで非同期実行
            loop = asyncio.get_event_loop()
            self.client = await asyncio.wait_for(
                loop.run_in_executor(None, self._create_client),
                timeout=self.api_timeout,
            )

            self.is_authenticated = True
            self._last_authentication = datetime.now()
            self._reset_failure_count()

            self.logger.info("Successfully authenticated with Garmin Connect")
            return True

        except TimeoutError as e:
            self._enter_backoff_period()
            raise GarminTimeoutError("Authentication request timed out") from e

        except GarminConnectAuthenticationError as e:
            self._enter_backoff_period()
            self.logger.error("Garmin authentication failed", error=str(e))
            raise GarminAuthenticationError(f"Authentication failed: {str(e)}") from e

        except GarminConnectTooManyRequestsError as e:
            self.logger.error("Garmin rate limit exceeded", error=str(e))
            raise GarminRateLimitError(f"Rate limit exceeded: {str(e)}") from e

        except GarminConnectConnectionError as e:
            self._enter_backoff_period()
            self.logger.error("Garmin connection error", error=str(e))
            raise GarminConnectionError(f"Connection error: {str(e)}") from e

        except Exception as e:
            self._enter_backoff_period()
            self.logger.error(
                "Unexpected error during Garmin authentication",
                error=str(e),
                exc_info=True,
            )
            raise GarminAuthenticationError(
                f"Unexpected authentication error: {str(e)}"
            ) from e

    def _create_client(self) -> Garmin:
        """Garminクライアントを作成（同期処理）"""
        client = Garmin(self.email, self.password)
        client.login()  # ログイン実行
        return client

    async def ensure_authenticated(self) -> None:
        """認証状態を確認し、必要に応じて再認証"""
        if not self.is_authenticated or not self.client:
            await self.authenticate()
            return

        # 1時間以上経過している場合は再認証
        if self._last_authentication:
            elapsed = datetime.now() - self._last_authentication
            if elapsed.total_seconds() > 3600:  # 1時間
                self.logger.info("Re-authenticating due to session timeout")
                await self.authenticate()

    async def get_health_data(
        self, target_date: date, use_cache: bool = True
    ) -> HealthData:
        """指定日の健康データを取得（キャッシュ対応）"""

        # キャッシュからデータ取得を試行
        if use_cache:
            cached_data = self.cache.load_health_data(target_date, allow_stale=True)
            if cached_data:
                # キャッシュデータが新しい場合はそのまま返す
                if self.cache.is_cache_valid(target_date):
                    self.logger.info(
                        "Using fresh cached health data",
                        date=target_date.isoformat(),
                        cache_age_hours=cached_data.cache_age_hours,
                    )
                    return cached_data
                self.logger.info(
                    "Found stale cached data, attempting fresh retrieval",
                    date=target_date.isoformat(),
                    cache_age_hours=cached_data.cache_age_hours,
                )

        try:
            # 新鮮なデータ取得を試行
            health_data = await self._retrieve_fresh_health_data(target_date)

            # 成功した場合はキャッシュに保存
            if health_data.has_any_data:
                self.cache.save_health_data(health_data)

            return health_data

        except (
            GarminConnectionError,
            GarminAuthenticationError,
            GarminTimeoutError,
            GarminOfflineError,
        ) as e:
            # 接続エラーの場合、キャッシュデータがあれば返す
            if use_cache:
                cached_data = self.cache.load_health_data(target_date, allow_stale=True)
                if cached_data:
                    self.logger.warning(
                        "Using stale cached data due to connection error",
                        date=target_date.isoformat(),
                        cache_age_hours=cached_data.cache_age_hours,
                        error=str(e),
                    )
                    # エラー情報を追加
                    cached_data.detailed_errors.append(
                        DataError(
                            source=DataSource.SLEEP,  # 代表的なソース
                            error_type=type(e).__name__,
                            message=str(e),
                            is_recoverable=True,
                            user_message="Garminサーバーとの接続に問題があるため、キャッシュされたデータを表示しています",
                        )
                    )
                    return cached_data

            # キャッシュもない場合は空のHealthDataを返す
            health_data = HealthData(date=target_date)
            health_data.detailed_errors.append(
                DataError(
                    source=DataSource.SLEEP,
                    error_type=type(e).__name__,
                    message=str(e),
                    is_recoverable=True,
                    user_message=self._get_user_friendly_error_message(e),
                )
            )
            return health_data

    async def _retrieve_fresh_health_data(self, target_date: date) -> HealthData:
        """新鮮な健康データを取得"""
        await self.ensure_authenticated()

        self.logger.info("Retrieving fresh health data", date=target_date.isoformat())

        health_data = HealthData(date=target_date)
        detailed_errors = []

        # 各データ取得にスリープを追加してレート制限を回避
        data_sources = [
            (DataSource.SLEEP, self._get_sleep_data_with_delay),
            (DataSource.STEPS, self._get_steps_data_with_delay),
            (DataSource.HEART_RATE, self._get_heart_rate_data_with_delay),
            (DataSource.ACTIVITIES, self._get_activities_data_with_delay),
        ]

        for source, get_data_func in data_sources:
            try:
                await asyncio.sleep(0.5)  # レート制限対策
                data = await get_data_func(target_date)

                # データの設定
                if source == DataSource.SLEEP and isinstance(data, SleepData):
                    health_data.sleep = data
                elif source == DataSource.STEPS and isinstance(data, StepsData):
                    health_data.steps = data
                elif source == DataSource.HEART_RATE and isinstance(
                    data, HeartRateData
                ):
                    health_data.heart_rate = data
                elif source == DataSource.ACTIVITIES and isinstance(data, list):
                    health_data.activities = data

            except Exception as e:
                # 詳細なエラー情報を記録
                error = DataError(
                    source=source,
                    error_type=type(e).__name__,
                    message=str(e),
                    is_recoverable=self._is_recoverable_error(e),
                    user_message=self._get_user_friendly_error_message(e),
                )
                detailed_errors.append(error)

                self.logger.warning(
                    "Failed to retrieve data from source",
                    source=source.value,
                    error_type=type(e).__name__,
                    error=str(e),
                )

        # エラー情報を設定
        health_data.detailed_errors = detailed_errors
        health_data.errors = [error.message for error in detailed_errors]  # 後方互換性
        health_data.data_quality = health_data.assess_data_quality()

        self.logger.info(
            "Fresh health data retrieval completed",
            date=target_date.isoformat(),
            data_quality=health_data.data_quality,
            available_types=health_data.available_data_types,
            error_count=len(detailed_errors),
        )

        return health_data

    def _is_recoverable_error(self, error: Exception) -> bool:
        """エラーが回復可能かどうかを判定"""
        recoverable_types = (
            GarminConnectConnectionError,
            GarminConnectTooManyRequestsError,
            GarminTimeoutError,
            GarminOfflineError,
            asyncio.TimeoutError,
        )
        return isinstance(error, recoverable_types)

    def _get_user_friendly_error_message(self, error: Exception) -> str:
        """ユーザーフレンドリーなエラーメッセージを生成"""
        if isinstance(error, GarminConnectAuthenticationError):
            return "Garminアカウントの認証に失敗しました。設定を確認してください。"
        if isinstance(error, GarminConnectTooManyRequestsError):
            return "Garmin APIの利用制限に達しました。しばらく時間をおいてから再試行してください。"
        if isinstance(error, GarminConnectConnectionError):
            return "Garminサーバーとの接続に問題があります。ネットワーク接続を確認してください。"
        if isinstance(error, asyncio.TimeoutError):
            return "Garminサーバーからの応答がタイムアウトしました。"
        return "Garminとの連携で予期しないエラーが発生しました。"

    async def _get_sleep_data_with_delay(self, target_date: date) -> SleepData:
        """遅延付き睡眠データ取得"""
        return await self._get_sleep_data(target_date)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(
            (
                GarminConnectConnectionError,
                GarminConnectTooManyRequestsError,
                asyncio.TimeoutError,
            )
        ),
    )
    async def _get_sleep_data(self, target_date: date) -> SleepData:
        """睡眠データを取得"""
        if not self.client:
            raise GarminConnectionError("Garmin client not authenticated")

        try:
            loop = asyncio.get_event_loop()

            # 睡眠データの取得（タイムアウト付き）
            raw_sleep_data = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.get_sleep_data(target_date.isoformat()),  # type: ignore
                ),
                timeout=self.api_timeout,
            )

            if not raw_sleep_data:
                raise GarminDataRetrievalError("No sleep data available")

            # 🔧 修正: 正しいデータ構造からデータを取得
            # GarminのSleep APIは dailySleepDTO キーに実際の睡眠データが格納されている
            daily_sleep_dto = raw_sleep_data.get("dailySleepDTO")
            if not daily_sleep_dto:
                # フォールバック: 古い形式も試す
                daily_sleep_dto = raw_sleep_data

            # データの変換（正しいキー名を使用）
            total_sleep_seconds = daily_sleep_dto.get("sleepTimeSeconds", 0)
            deep_sleep_seconds = daily_sleep_dto.get("deepSleepSeconds", 0)
            light_sleep_seconds = daily_sleep_dto.get("lightSleepSeconds", 0)
            rem_sleep_seconds = daily_sleep_dto.get("remSleepSeconds", 0)
            awake_seconds = daily_sleep_dto.get("awakeSleepSeconds", 0)

            # 睡眠スコアの取得
            sleep_score = None
            sleep_scores = daily_sleep_dto.get("sleepScores")
            if sleep_scores and isinstance(sleep_scores, dict):
                overall_score = sleep_scores.get("overall")
                if overall_score and isinstance(overall_score, dict):
                    sleep_score = overall_score.get("value")

            # タイムスタンプの取得（ミリ秒単位をsecondに変換）
            sleep_start_ts = daily_sleep_dto.get("sleepStartTimestampGMT")
            sleep_end_ts = daily_sleep_dto.get("sleepEndTimestampGMT")

            # タイムスタンプをdatetimeに変換
            bedtime = None
            wake_time = None

            if sleep_start_ts:
                # ミリ秒をsecondに変換
                bedtime = self._parse_timestamp(sleep_start_ts / 1000)

            if sleep_end_ts:
                # ミリ秒をsecondに変換
                wake_time = self._parse_timestamp(sleep_end_ts / 1000)

            return SleepData(
                date=target_date,
                total_sleep_hours=(
                    total_sleep_seconds / 3600 if total_sleep_seconds else None
                ),
                deep_sleep_hours=(
                    deep_sleep_seconds / 3600 if deep_sleep_seconds else None
                ),
                light_sleep_hours=(
                    light_sleep_seconds / 3600 if light_sleep_seconds else None
                ),
                rem_sleep_hours=rem_sleep_seconds / 3600 if rem_sleep_seconds else None,
                awake_hours=awake_seconds / 3600 if awake_seconds else None,
                sleep_score=sleep_score,
                bedtime=bedtime,
                wake_time=wake_time,
            )

        except Exception as e:
            self.logger.warning(
                "Failed to retrieve sleep data",
                date=target_date.isoformat(),
                error=str(e),
            )
            raise GarminDataRetrievalError(
                f"Sleep data retrieval failed: {str(e)}"
            ) from e

    async def _get_steps_data_with_delay(self, target_date: date) -> StepsData:
        """遅延付き歩数データ取得"""
        return await self._get_steps_data(target_date)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(
            (
                GarminConnectConnectionError,
                GarminConnectTooManyRequestsError,
                asyncio.TimeoutError,
            )
        ),
    )
    async def _get_steps_data(self, target_date: date) -> StepsData:
        """歩数データを取得"""
        if not self.client:
            raise GarminConnectionError("Garmin client not authenticated")

        try:
            loop = asyncio.get_event_loop()

            # 🔧 修正: ユーザーサマリーから日次集計データを取得
            # Steps APIは15分間隔のタイムスロットデータを返すため、
            # ユーザーサマリーから日次集計値を直接取得する方が効率的
            user_summary = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.get_user_summary(target_date.isoformat()),  # type: ignore
                ),
                timeout=self.api_timeout,
            )

            if not user_summary:
                raise GarminDataRetrievalError("No user summary data available")

            # ユーザーサマリーから必要なデータを抽出
            total_steps = user_summary.get("totalSteps")
            total_distance_meters = user_summary.get("totalDistanceMeters")
            active_calories = user_summary.get("activeKilocalories")
            total_calories = user_summary.get("totalKilocalories")
            floors_ascended = user_summary.get("floorsAscended")

            # アクティブ分数の計算（カロリーベースで推定）
            # activeKilocalories から概算でアクティブ時間を推定
            active_minutes = None
            if active_calories and active_calories > 0:
                # 1分あたり約0.5kcalと仮定してアクティブ分数を推定
                active_minutes = int(active_calories / 0.5)

            return StepsData(
                date=target_date,
                total_steps=total_steps,
                distance_km=(
                    total_distance_meters / 1000 if total_distance_meters else None
                ),
                calories_burned=total_calories,  # 総カロリー消費
                floors_climbed=floors_ascended,
                active_minutes=active_minutes,
            )

        except Exception as e:
            self.logger.warning(
                "Failed to retrieve steps data",
                date=target_date.isoformat(),
                error=str(e),
            )
            raise GarminDataRetrievalError(
                f"Steps data retrieval failed: {str(e)}"
            ) from e

    async def _get_heart_rate_data_with_delay(self, target_date: date) -> HeartRateData:
        """遅延付き心拍数データ取得"""
        return await self._get_heart_rate_data(target_date)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(
            (
                GarminConnectConnectionError,
                GarminConnectTooManyRequestsError,
                asyncio.TimeoutError,
            )
        ),
    )
    async def _get_heart_rate_data(self, target_date: date) -> HeartRateData:
        """心拍数データを取得"""
        if not self.client:
            raise GarminConnectionError("Garmin client not authenticated")

        try:
            loop = asyncio.get_event_loop()

            # 心拍数データの取得（タイムアウト付き）
            hr_data = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.get_heart_rates(target_date.isoformat()),  # type: ignore
                ),
                timeout=self.api_timeout,
            )

            if not hr_data:
                raise GarminDataRetrievalError("No heart rate data available")

            # 心拍数ゾーンの処理
            heart_rate_zones = {}
            if "heartRateZones" in hr_data:
                for zone in hr_data["heartRateZones"]:
                    zone_name = zone.get("zoneName", "Unknown")
                    zone_time = zone.get("secsInZone", 0) // 60  # 分に変換
                    heart_rate_zones[zone_name] = zone_time

            return HeartRateData(
                date=target_date,
                resting_heart_rate=hr_data.get("restingHeartRate"),
                max_heart_rate=hr_data.get("maxHeartRate"),
                average_heart_rate=hr_data.get("averageHeartRate"),
                heart_rate_zones=heart_rate_zones if heart_rate_zones else None,
            )

        except Exception as e:
            self.logger.warning(
                "Failed to retrieve heart rate data",
                date=target_date.isoformat(),
                error=str(e),
            )
            raise GarminDataRetrievalError(
                f"Heart rate data retrieval failed: {str(e)}"
            ) from e

    async def _get_activities_data_with_delay(
        self, target_date: date
    ) -> list[ActivityData]:
        """遅延付き活動データ取得"""
        return await self._get_activities_data(target_date)

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type(
            (
                GarminConnectConnectionError,
                GarminConnectTooManyRequestsError,
                asyncio.TimeoutError,
            )
        ),
    )
    async def _get_activities_data(self, target_date: date) -> list[ActivityData]:
        """活動データを取得"""
        if not self.client:
            raise GarminConnectionError("Garmin client not authenticated")

        try:
            loop = asyncio.get_event_loop()

            # 活動データの取得（タイムアウト付き）
            activities = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.get_activities_by_date(  # type: ignore
                        target_date.isoformat(), target_date.isoformat()
                    ),
                ),
                timeout=self.api_timeout,
            )

            if not activities:
                return []

            activity_list = []
            for activity in activities:
                try:
                    activity_data = ActivityData(
                        date=target_date,
                        activity_type=activity.get("activityType", {}).get(
                            "typeKey", "unknown"
                        ),
                        activity_name=activity.get("activityName"),
                        duration_minutes=(
                            activity.get("duration", 0) // 60
                            if activity.get("duration")
                            else None
                        ),
                        distance_km=(
                            activity.get("distance", 0) / 1000
                            if activity.get("distance")
                            else None
                        ),
                        calories=activity.get("calories"),
                        average_heart_rate=activity.get("averageHR"),
                        start_time=self._parse_datetime(activity.get("startTimeGMT")),
                        end_time=self._parse_datetime(
                            activity.get("startTimeGMT"), activity.get("duration")
                        ),
                    )

                    if activity_data.is_valid:
                        activity_list.append(activity_data)

                except Exception as e:
                    self.logger.warning(
                        "Failed to parse individual activity", error=str(e)
                    )
                    continue

            return activity_list

        except Exception as e:
            self.logger.warning(
                "Failed to retrieve activities data",
                date=target_date.isoformat(),
                error=str(e),
            )
            raise GarminDataRetrievalError(
                f"Activities data retrieval failed: {str(e)}"
            ) from e

    def _parse_datetime(
        self, timestamp: str | None, duration_seconds: int | None = None
    ) -> datetime | None:
        """タイムスタンプをdatetimeに変換"""
        if not timestamp:
            return None

        try:
            # Garmin のタイムスタンプフォーマットを解析
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            # 継続時間が指定されている場合は加算
            if duration_seconds:
                dt += timedelta(seconds=duration_seconds)

            return dt

        except Exception as e:
            self.logger.warning(
                "Failed to parse datetime", timestamp=timestamp, error=str(e)
            )
            return None

    def _parse_timestamp(self, timestamp_seconds: float | None) -> datetime | None:
        """Unix タイムスタンプを datetime に変換"""
        if not timestamp_seconds:
            return None

        try:
            # Unix タイムスタンプから datetime を作成
            dt = datetime.fromtimestamp(timestamp_seconds, tz=None)
            return dt

        except Exception as e:
            self.logger.warning(
                "Failed to parse timestamp", timestamp=timestamp_seconds, error=str(e)
            )
            return None

    def get_cache_stats(self) -> dict[str, Any]:
        """キャッシュの統計情報を取得"""
        return self.cache.get_cache_stats()

    async def cleanup_cache(self, days_to_keep: int = 7) -> int:
        """古いキャッシュをクリーンアップ"""
        return self.cache.cleanup_old_cache(days_to_keep)

    async def test_connection(self) -> dict[str, Any]:
        """接続テスト"""
        try:
            await self.ensure_authenticated()

            if not self.client:
                raise GarminConnectionError("Garmin client not authenticated")

            # 基本的なユーザー情報を取得してテスト（タイムアウト付き）
            loop = asyncio.get_event_loop()
            user_summary = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.client.get_user_summary(  # type: ignore
                        datetime.now().date().isoformat()
                    ),
                ),
                timeout=self.api_timeout,
            )

            return {
                "success": True,
                "authenticated": self.is_authenticated,
                "user_data_available": bool(user_summary),
                "consecutive_failures": self._consecutive_failures,
                "in_backoff": self._is_in_backoff_period(),
                "cache_stats": self.get_cache_stats(),
                "message": "Garmin connection successful",
            }

        except Exception as e:
            return {
                "success": False,
                "authenticated": False,
                "user_data_available": False,
                "consecutive_failures": self._consecutive_failures,
                "in_backoff": self._is_in_backoff_period(),
                "cache_stats": self.get_cache_stats(),
                "message": f"Connection test failed: {str(e)}",
                "error_type": type(e).__name__,
                "user_message": self._get_user_friendly_error_message(e),
            }

    def logout(self) -> None:
        """ログアウト処理"""
        try:
            if self.client:
                # garminconnectライブラリにはlogoutメソッドがないため、クライアントをリセット
                self.client = None

            self.is_authenticated = False
            self._last_authentication = None

            self.logger.info("Logged out from Garmin Connect")

        except Exception as e:
            self.logger.warning("Error during logout", error=str(e))
