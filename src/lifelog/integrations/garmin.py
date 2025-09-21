"""
Garmin Connect 連携

健康・フィットネスデータの自動取得とライフログ統合
"""

import asyncio
import os
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import structlog
from pydantic import BaseModel

from ..models import LifelogCategory, LifelogEntry, LifelogType
from .base import (
    BaseIntegration,
    IntegrationConfig,
    IntegrationData,
    IntegrationDataProcessor,
)

logger = structlog.get_logger(__name__)


class GarminActivityData(BaseModel):
    """Garmin アクティビティデータ"""

    activity_id: str
    activity_type: str
    activity_name: str
    start_time: datetime
    duration: int  # 秒
    distance: float | None = None  # メートル
    calories: int | None = None
    avg_heart_rate: int | None = None
    max_heart_rate: int | None = None
    elevation_gain: float | None = None  # メートル
    avg_speed: float | None = None  # m/s

    # 詳細データ
    steps: int | None = None
    avg_cadence: float | None = None
    training_effect: float | None = None
    recovery_time: int | None = None  # 時間


class GarminHealthData(BaseModel):
    """Garmin 健康データ"""

    date: datetime
    steps: int | None = None
    distance: float | None = None  # メートル
    calories: int | None = None
    active_calories: int | None = None
    floors_climbed: int | None = None

    # 睡眠データ
    sleep_start_time: datetime | None = None
    sleep_end_time: datetime | None = None
    sleep_duration: int | None = None  # 分
    deep_sleep: int | None = None  # 分
    light_sleep: int | None = None  # 分
    rem_sleep: int | None = None  # 分
    sleep_score: int | None = None

    # 心拍数データ
    resting_heart_rate: int | None = None
    max_heart_rate: int | None = None
    heart_rate_variability: float | None = None

    # ストレス・エネルギー
    stress_avg: int | None = None  # 0-100
    body_battery_max: int | None = None  # 0-100
    body_battery_min: int | None = None  # 0-100

    # 体重・体組成
    weight: float | None = None  # kg
    body_fat: float | None = None  # %
    body_water: float | None = None  # %
    muscle_mass: float | None = None  # kg


class GarminIntegration(BaseIntegration):
    """Garmin Connect 連携実装"""

    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.base_url = "https://connect.garmin.com"
        self.session: aiohttp.ClientSession | None = None

        # Garmin 固有設定
        garmin_settings = config.custom_settings.get("garmin", {})
        self.sync_activities = garmin_settings.get("sync_activities", True)
        self.sync_health_data = garmin_settings.get("sync_health_data", True)
        self.sync_sleep_data = garmin_settings.get("sync_sleep_data", True)
        self.activity_types_filter = garmin_settings.get("activity_types", [])

        # データタイプマッピング
        self.activity_type_mapping = {
            "running": {
                "category": LifelogCategory.HEALTH,
                "tags": ["ランニング", "有酸素運動"],
            },
            "cycling": {
                "category": LifelogCategory.HEALTH,
                "tags": ["サイクリング", "有酸素運動"],
            },
            "walking": {
                "category": LifelogCategory.HEALTH,
                "tags": ["ウォーキング", "歩行"],
            },
            "swimming": {
                "category": LifelogCategory.HEALTH,
                "tags": ["水泳", "全身運動"],
            },
            "strength_training": {
                "category": LifelogCategory.HEALTH,
                "tags": ["筋トレ", "無酸素運動"],
            },
            "yoga": {
                "category": LifelogCategory.HEALTH,
                "tags": ["ヨガ", "ストレッチ"],
            },
            "cardio": {
                "category": LifelogCategory.HEALTH,
                "tags": ["カーディオ", "有酸素運動"],
            },
        }

    async def validate_config(self) -> list[str]:
        """Garmin 連携の設定検証（ access_token は不要）"""
        errors = []

        if not self.config.integration_name:
            errors.append("連携名が設定されていません")

        if self.config.sync_interval < 60:
            errors.append("同期間隔は 60 秒以上である必要があります")

        # Garmin Connect は username/password 認証のため access_token は不要
        # OAuth2 トークンの検証はスキップ

        return errors

    async def authenticate(self) -> bool:
        """Garmin Connect 認証"""
        try:
            # 環境変数から認証情報を取得
            garmin_email = os.getenv("GARMIN_EMAIL")
            garmin_password = os.getenv("GARMIN_PASSWORD")

            if not garmin_email or not garmin_password:
                self.add_error(
                    "Garmin 認証情報が設定されていません（ GARMIN_EMAIL, GARMIN_PASSWORD ）"
                )
                return False

            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "MindBridge-Lifelog/1.0"},
            )

            # GarminClient を使用した実際の認証テスト
            from pathlib import Path

            from src.garmin.client import GarminClient

            cache_dir = Path(os.getenv("GARMIN_CACHE_DIR", "/app/.cache/garmin"))
            client = GarminClient(cache_dir)

            # 認証テスト
            success = await client.authenticate()
            if success:
                self._authenticated = True
                self.logger.info("Garmin integration authentication successful")
                return True
            else:
                self.add_error("Garmin Connect 認証に失敗しました")
                return False

        except Exception as e:
            self.logger.error(
                f"Exception in authenticate: {type(e).__name__}: {str(e)}"
            )
            self.add_error(f"Garmin 認証でエラー: {str(e)}")
            return False

    async def _authenticate_oauth(self) -> bool:
        """OAuth2 認証"""
        try:
            # トークンの有効性をテスト
            test_url = f"{self.base_url}/modern/proxy/userprofile-service/userprofile/personal-information"
            headers = {"Authorization": f"Bearer {self.config.access_token}"}

            if self.session is None:
                self.add_error("HTTP セッションが初期化されていません")
                return False

            async with self.session.get(test_url, headers=headers) as response:
                if response.status == 200:
                    self._authenticated = True
                    self.logger.info("Garmin OAuth 認証成功")
                    return True
                elif response.status == 401:
                    # トークン期限切れ - リフレッシュ試行
                    if await self._refresh_token():
                        return await self._authenticate_oauth()
                    else:
                        self.add_error("Garmin トークンが無効です。再認証が必要です")
                        return False
                else:
                    self.add_error(f"Garmin 認証失敗: HTTP {response.status}")
                    return False

        except Exception as e:
            self.add_error(f"Garmin OAuth 認証でエラー: {str(e)}")
            return False

    async def _refresh_token(self) -> bool:
        """Garmin トークンリフレッシュ"""
        if not self.config.refresh_token:
            return False

        try:
            # Garmin のリフレッシュトークンエンドポイント
            refresh_url = "https://connect.garmin.com/modern/di-oauth/exchange"
            data = {
                "client_id": self.config.client_id,
                "grant_type": "refresh_token",
                "refresh_token": self.config.refresh_token,
            }

            if self.session is None:
                self.add_error("HTTP セッションが初期化されていません")
                return False

            async with self.session.post(refresh_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.config.access_token = token_data.get("access_token")
                    self.config.refresh_token = token_data.get("refresh_token")

                    if token_data.get("expires_in"):
                        expires_in = int(token_data["expires_in"])
                        self.config.token_expires_at = datetime.now() + timedelta(
                            seconds=expires_in
                        )

                    self.logger.info("Garmin トークンリフレッシュ成功")
                    return True
                else:
                    self.add_error(
                        f"Garmin トークンリフレッシュ失敗: HTTP {response.status}"
                    )
                    return False

        except Exception as e:
            self.add_error(f"Garmin トークンリフレッシュでエラー: {str(e)}")
            return False

    async def test_connection(self) -> bool:
        """接続テスト"""
        try:
            # 環境変数から認証情報を取得
            garmin_email = os.getenv("GARMIN_EMAIL")
            garmin_password = os.getenv("GARMIN_PASSWORD")

            if not garmin_email or not garmin_password:
                self.add_error(
                    "Garmin 認証情報が設定されていません（ GARMIN_EMAIL, GARMIN_PASSWORD ）"
                )
                return False

            # GarminClient を使用した実際の接続テスト
            from pathlib import Path

            from src.garmin.client import GarminClient

            cache_dir = Path(os.getenv("GARMIN_CACHE_DIR", "/app/.cache/garmin"))
            client = GarminClient(cache_dir)

            # 接続テスト
            connection_result = await client.test_connection()
            success = connection_result.get("success", False)

            if success:
                self.logger.info("Garmin 接続テスト成功")
                self._authenticated = True
                return True
            else:
                error_msg = connection_result.get("message", "接続テストに失敗しました")
                self.add_error(f"Garmin 接続テスト失敗: {error_msg}")
                return False

        except Exception as e:
            self.add_error(f"Garmin 接続テストでエラー: {str(e)}")
            return False

    async def sync_data(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> list[IntegrationData]:
        """データ同期"""
        if not await self.check_rate_limit():
            self.logger.warning("Garmin API レート制限中")
            return []

        start_time = datetime.now()
        synced_data = []

        try:
            # デフォルトで過去 7 日間
            if not start_date:
                start_date = datetime.now() - timedelta(days=7)
            if not end_date:
                end_date = datetime.now()

            # アクティビティデータ同期
            if self.sync_activities:
                activities = await self._sync_activities(start_date, end_date)
                synced_data.extend(activities)

            # 健康データ同期
            if self.sync_health_data:
                health_data = await self._sync_health_data(start_date, end_date)
                synced_data.extend(health_data)

            # 同期成功統計更新
            sync_duration = (datetime.now() - start_time).total_seconds()
            self.update_metrics(
                total_records_synced=self.metrics.total_records_synced
                + len(synced_data),
                records_synced_today=self.metrics.records_synced_today
                + len(synced_data),
                last_sync_duration=sync_duration,
                health_score=min(100.0, self.metrics.health_score + 1.0),
            )

            self.config.last_sync = datetime.now()
            self.logger.info(
                "Garmin データ同期完了",
                records=len(synced_data),
                duration=f"{sync_duration:.1f}s",
            )

            return synced_data

        except Exception as e:
            self.add_error(f"Garmin データ同期でエラー: {str(e)}")
            self.update_metrics(health_score=max(0.0, self.metrics.health_score - 10.0))
            return []

    async def _sync_activities(
        self, start_date: datetime, end_date: datetime
    ) -> list[IntegrationData]:
        """アクティビティデータ同期"""
        activities_data: list[IntegrationData] = []

        try:
            # Garmin Connect アクティビティ API
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")

            url = f"{self.base_url}/modern/proxy/activitylist-service/activities/search/activities"
            params = {
                "start": "0",
                "limit": "100",
                "startDate": start_str,
                "endDate": end_str,
            }
            headers = {"Authorization": f"Bearer {self.config.access_token}"}

            if self.session is None:
                self.add_error("HTTP セッションが初期化されていません")
                return activities_data

            self.increment_request_count()
            async with self.session.get(
                url, headers=headers, params=params
            ) as response:
                if response.status != 200:
                    self.add_error(
                        f"Garmin アクティビティ取得失敗: HTTP {response.status}"
                    )
                    return activities_data

                activities_json = await response.json()

                for activity in activities_json:
                    try:
                        # アクティビティタイプフィルター
                        activity_type = (
                            activity.get("activityType", {}).get("typeKey", "").lower()
                        )
                        if (
                            self.activity_types_filter
                            and activity_type not in self.activity_types_filter
                        ):
                            continue

                        # アクティビティデータ構造化
                        activity_data = GarminActivityData(
                            activity_id=str(activity["activityId"]),
                            activity_type=activity_type,
                            activity_name=activity.get("activityName", ""),
                            start_time=IntegrationDataProcessor.normalize_timestamp(
                                activity["startTimeLocal"]
                            ),
                            duration=activity.get("duration", 0),
                            distance=activity.get("distance"),
                            calories=activity.get("calories"),
                            avg_heart_rate=activity.get("averageHR"),
                            max_heart_rate=activity.get("maxHR"),
                            elevation_gain=activity.get("elevationGain"),
                            avg_speed=activity.get("averageSpeed"),
                            steps=activity.get("steps"),
                        )

                        # IntegrationData に変換
                        integration_data = IntegrationData(
                            integration_name="garmin",
                            external_id=activity_data.activity_id,
                            data_type="activity",
                            timestamp=activity_data.start_time,
                            raw_data=activity,
                            processed_data=activity_data.model_dump(),
                            confidence_score=0.95,
                            data_quality=IntegrationDataProcessor.calculate_data_quality(
                                activity, ["activityId", "startTimeLocal", "duration"]
                            ),
                        )

                        activities_data.append(integration_data)

                    except Exception as e:
                        self.logger.warning(
                            "Garmin アクティビティ処理でエラー",
                            activity_id=activity.get("activityId"),
                            error=str(e),
                        )
                        continue

                self.logger.info(
                    f"Garmin アクティビティ取得完了: {len(activities_data)}件"
                )

        except Exception as e:
            self.add_error(f"Garmin アクティビティ同期でエラー: {str(e)}")

        return activities_data

    async def _sync_health_data(
        self, start_date: datetime, end_date: datetime
    ) -> list[IntegrationData]:
        """健康データ同期"""
        health_data = []

        try:
            # 日別で健康データを取得
            current_date = start_date.date()
            end_date_date = end_date.date()

            while current_date <= end_date_date:
                date_str = current_date.strftime("%Y-%m-%d")

                # 複数のエンドポイントから並列取得
                tasks = [
                    self._get_daily_steps(date_str),
                    self._get_daily_sleep(date_str),
                    self._get_daily_heart_rate(date_str),
                    self._get_daily_stress(date_str),
                ]

                if self.sync_sleep_data:
                    tasks.append(self._get_daily_body_composition(date_str))

                daily_results = await asyncio.gather(*tasks, return_exceptions=True)

                # データ統合
                daily_health = GarminHealthData(
                    date=datetime.combine(current_date, datetime.min.time())
                )

                for result in daily_results:
                    if isinstance(result, Exception):
                        continue
                    if result and isinstance(result, dict):
                        # 各データタイプの結果を統合
                        for key, value in result.items():
                            if hasattr(daily_health, key) and value is not None:
                                setattr(daily_health, key, value)

                # IntegrationData 作成
                if any(
                    getattr(daily_health, field) is not None
                    for field in [
                        "steps",
                        "sleep_duration",
                        "resting_heart_rate",
                        "weight",
                    ]
                ):
                    integration_data = IntegrationData(
                        integration_name="garmin",
                        external_id=f"health_{date_str}",
                        data_type="health",
                        timestamp=daily_health.date,
                        raw_data={},
                        processed_data=daily_health.model_dump(exclude_none=True),
                        confidence_score=0.9,
                        data_quality="good",
                    )

                    health_data.append(integration_data)

                current_date += timedelta(days=1)
                await asyncio.sleep(0.1)  # API 負荷軽減

            self.logger.info(f"Garmin 健康データ取得完了: {len(health_data)}件")

        except Exception as e:
            self.add_error(f"Garmin 健康データ同期でエラー: {str(e)}")

        return health_data

    async def _get_daily_steps(self, date_str: str) -> dict[str, Any]:
        """日別歩数データ取得"""
        try:
            url = f"{self.base_url}/modern/proxy/userstats-service/wellness/{date_str}"
            headers = {"Authorization": f"Bearer {self.config.access_token}"}

            if self.session is None:
                self.add_error("HTTP セッションが初期化されていません")
                return {}

            self.increment_request_count()
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "steps": data.get("totalSteps"),
                        "distance": data.get("totalDistance"),
                        "calories": data.get("activeKilocalories"),
                        "floors_climbed": data.get("floorsAscended"),
                    }
        except Exception as e:
            self.logger.debug(f"歩数データ取得エラー {date_str}: {str(e)}")

        return {}

    async def _get_daily_sleep(self, date_str: str) -> dict[str, Any]:
        """日別睡眠データ取得 - wellness summary から取得"""
        try:
            # まず wellness サマリーから基本的な睡眠データを取得
            url = f"{self.base_url}/modern/proxy/usersummary-service/usersummary/daily/{self._get_user_uuid()}"
            params = {"calendarDate": date_str}
            headers = {"Authorization": f"Bearer {self.config.access_token}"}

            if self.session is None:
                self.add_error("HTTP セッションが初期化されていません")
                return {}

            self.increment_request_count()
            async with self.session.get(
                url, headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()

                    # wellness summary から睡眠データを抽出
                    sleeping_seconds = data.get("sleepingSeconds", 0)
                    measurable_sleep = data.get("measurableAsleepDuration", 0)
                    body_battery_sleep = data.get("bodyBatteryDuringSleep", 0)

                    # 詳細睡眠データも試行
                    detailed_sleep = {}
                    try:
                        sleep_url = f"{self.base_url}/modern/proxy/wellness-service/wellness/dailySleepData/{self._get_user_uuid()}"
                        sleep_params = {"date": date_str}

                        async with self.session.get(
                            sleep_url, headers=headers, params=sleep_params
                        ) as sleep_response:
                            if sleep_response.status == 200:
                                sleep_data = await sleep_response.json()
                                if sleep_data.get("dailySleepDTO"):
                                    sleep_dto = sleep_data["dailySleepDTO"]
                                    detailed_sleep = {
                                        "sleep_start_time": IntegrationDataProcessor.normalize_timestamp(
                                            sleep_dto.get("sleepStartTimestampLocal")
                                        )
                                        if sleep_dto.get("sleepStartTimestampLocal")
                                        else None,
                                        "sleep_end_time": IntegrationDataProcessor.normalize_timestamp(
                                            sleep_dto.get("sleepEndTimestampLocal")
                                        )
                                        if sleep_dto.get("sleepEndTimestampLocal")
                                        else None,
                                        "deep_sleep": sleep_dto.get(
                                            "deepSleepSeconds", 0
                                        )
                                        // 60,
                                        "light_sleep": sleep_dto.get(
                                            "lightSleepSeconds", 0
                                        )
                                        // 60,
                                        "rem_sleep": sleep_dto.get("remSleepSeconds", 0)
                                        // 60,
                                        "sleep_score": sleep_dto.get(
                                            "overallSleepScore"
                                        ),
                                    }
                    except Exception as e:
                        self.logger.debug(
                            f"詳細睡眠データ取得エラー {date_str}: {str(e)}"
                        )

                    # 基本データと詳細データを統合
                    result = {
                        "sleep_duration": sleeping_seconds // 60
                        if sleeping_seconds > 0
                        else None,  # 分に変換
                        "measurable_sleep_duration": measurable_sleep // 60
                        if measurable_sleep > 0
                        else None,
                        "body_battery_during_sleep": body_battery_sleep
                        if body_battery_sleep > 0
                        else None,
                        **detailed_sleep,  # 詳細データがあれば統合
                    }

                    # データが存在する場合のみ返す
                    if any(
                        v is not None and v > 0
                        for v in result.values()
                        if isinstance(v, (int, float))
                    ):
                        self.logger.debug(f"睡眠データ取得成功 {date_str}: {result}")
                        return result
                    else:
                        self.logger.debug(f"睡眠データなし {date_str}")
                        return {}

                else:
                    self.logger.debug(
                        f"睡眠データ API エラー {date_str}: {response.status}"
                    )

        except Exception as e:
            self.logger.debug(f"睡眠データ取得エラー {date_str}: {str(e)}")

        return {}

    async def _get_daily_heart_rate(self, date_str: str) -> dict[str, Any]:
        """日別心拍数データ取得"""
        try:
            url = f"{self.base_url}/modern/proxy/userstats-service/wellness/{date_str}"
            headers = {"Authorization": f"Bearer {self.config.access_token}"}

            if self.session is None:
                self.add_error("HTTP セッションが初期化されていません")
                return {}

            self.increment_request_count()
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "resting_heart_rate": data.get("restingHeartRate"),
                        "max_heart_rate": data.get("maxHeartRate"),
                    }
        except Exception as e:
            self.logger.debug(f"心拍数データ取得エラー {date_str}: {str(e)}")

        return {}

    async def _get_daily_stress(self, date_str: str) -> dict[str, Any]:
        """日別ストレスデータ取得"""
        try:
            url = f"{self.base_url}/modern/proxy/userstats-service/stress-level/{date_str}"
            headers = {"Authorization": f"Bearer {self.config.access_token}"}

            if self.session is None:
                self.add_error("HTTP セッションが初期化されていません")
                return {}

            self.increment_request_count()
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        "stress_avg": data.get("overallStressLevel"),
                        "body_battery_max": data.get("maxStressLevel"),
                        "body_battery_min": data.get("minStressLevel"),
                    }
        except Exception as e:
            self.logger.debug(f"ストレスデータ取得エラー {date_str}: {str(e)}")

        return {}

    async def _get_daily_body_composition(self, date_str: str) -> dict[str, Any]:
        """日別体組成データ取得"""
        try:
            url = f"{self.base_url}/modern/proxy/weight-service/weight/dateRange"
            params = {"startDate": date_str, "endDate": date_str}
            headers = {"Authorization": f"Bearer {self.config.access_token}"}

            if self.session is None:
                self.add_error("HTTP セッションが初期化されていません")
                return {}

            self.increment_request_count()
            async with self.session.get(
                url, headers=headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0:
                        weight_data = data[0]
                        return {
                            "weight": weight_data.get("weight"),
                            "body_fat": weight_data.get("bodyFat"),
                            "body_water": weight_data.get("bodyWater"),
                            "muscle_mass": weight_data.get("muscleMass"),
                        }
        except Exception as e:
            self.logger.debug(f"体組成データ取得エラー {date_str}: {str(e)}")

        return {}

    def _get_user_uuid(self) -> str:
        """ユーザー UUID 取得（キャッシュ化推奨）"""
        # 実装では認証時にユーザー UUID を取得してキャッシュする
        return self.config.custom_settings.get("garmin", {}).get("user_uuid", "")

    async def get_available_data_types(self) -> list[str]:
        """利用可能なデータタイプ"""
        return [
            "activity",
            "health",
            "steps",
            "sleep",
            "heart_rate",
            "stress",
            "body_composition",
        ]

    async def __aenter__(self):
        """非同期コンテキストマネージャー"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """リソースクリーンアップ"""
        if self.session:
            await self.session.close()

    def convert_to_lifelog_entry(
        self, integration_data: IntegrationData
    ) -> LifelogEntry:
        """IntegrationData を LifelogEntry に変換"""
        processed_data = integration_data.processed_data

        if integration_data.data_type == "activity":
            return self._convert_activity_to_lifelog(integration_data, processed_data)
        elif integration_data.data_type == "health":
            return self._convert_health_to_lifelog(integration_data, processed_data)
        else:
            # 汎用変換
            return LifelogEntry(
                category=LifelogCategory.HEALTH,
                type=LifelogType.METRIC,
                title=f"Garmin {integration_data.data_type}データ",
                content=f"Garmin から自動取得: {integration_data.data_type}",
                timestamp=integration_data.timestamp,
                source="garmin_integration",
                metadata={"external_id": integration_data.external_id},
            )

    def _convert_activity_to_lifelog(
        self, integration_data: IntegrationData, data: dict[str, Any]
    ) -> LifelogEntry:
        """アクティビティを LifelogEntry に変換"""
        activity_type = data.get("activity_type", "").lower()
        activity_name = data.get("activity_name", "")
        duration_minutes = (data.get("duration", 0)) // 60
        distance_km = (data.get("distance", 0) or 0) / 1000
        calories = data.get("calories", 0)

        # アクティビティタイプから設定取得
        type_config = self.activity_type_mapping.get(
            activity_type,
            {"category": LifelogCategory.HEALTH, "tags": ["運動", "フィットネス"]},
        )

        # タイトル生成
        title_parts = []
        if activity_name:
            title_parts.append(activity_name)
        else:
            title_parts.append(activity_type.replace("_", " ").title())

        if distance_km > 0:
            title_parts.append(f"{distance_km:.1f}km")
        if duration_minutes > 0:
            title_parts.append(f"{duration_minutes}分")

        title = " - ".join(title_parts)

        # 詳細コンテンツ
        content_parts = [
            f"Garmin Connect から自動記録された{activity_type}アクティビティ"
        ]

        if duration_minutes > 0:
            content_parts.append(f"時間: {duration_minutes}分")
        if distance_km > 0:
            content_parts.append(f"距離: {distance_km:.2f}km")
        if calories > 0:
            content_parts.append(f"消費カロリー: {calories}kcal")
        if data.get("avg_heart_rate"):
            content_parts.append(f"平均心拍数: {data['avg_heart_rate']}bpm")

        content = "\n".join(content_parts)

        return LifelogEntry(
            category=type_config["category"],
            type=LifelogType.EVENT,
            title=title,
            content=content,
            timestamp=integration_data.timestamp,
            numeric_value=distance_km if distance_km > 0 else duration_minutes,
            unit="km" if distance_km > 0 else "分",
            tags=type_config["tags"],
            source="garmin_integration",
            metadata={
                "external_id": integration_data.external_id,
                "activity_type": activity_type,
                "garmin_data": data,
            },
        )

    def _convert_health_to_lifelog(
        self, integration_data: IntegrationData, data: dict[str, Any]
    ) -> LifelogEntry:
        """健康データを LifelogEntry に変換"""
        date_str = integration_data.timestamp.strftime("%Y 年%m 月%d 日")

        # 主要メトリクスを特定
        main_metrics = []
        if data.get("steps"):
            main_metrics.append(f"歩数: {data['steps']:,}歩")
        if data.get("sleep_duration"):
            sleep_hours = data["sleep_duration"] / 60
            main_metrics.append(f"睡眠: {sleep_hours:.1f}時間")
        if data.get("resting_heart_rate"):
            main_metrics.append(f"安静時心拍数: {data['resting_heart_rate']}bpm")
        if data.get("weight"):
            main_metrics.append(f"体重: {data['weight']:.1f}kg")

        title = f"{date_str}の健康データ"
        if main_metrics:
            title += f" - {main_metrics[0]}"

        # 詳細コンテンツ
        content_sections = ["Garmin Connect から自動取得された健康データ"]

        if data.get("steps") or data.get("distance") or data.get("calories"):
            activity_section = ["## 活動データ"]
            if data.get("steps"):
                activity_section.append(f"- 歩数: {data['steps']:,}歩")
            if data.get("distance"):
                distance_km = data["distance"] / 1000
                activity_section.append(f"- 距離: {distance_km:.2f}km")
            if data.get("calories"):
                activity_section.append(f"- カロリー: {data['calories']}kcal")
            content_sections.extend(activity_section)

        if any(
            data.get(key)
            for key in ["sleep_duration", "deep_sleep", "light_sleep", "rem_sleep"]
        ):
            sleep_section = ["## 睡眠データ"]
            if data.get("sleep_duration"):
                hours = data["sleep_duration"] / 60
                sleep_section.append(f"- 総睡眠時間: {hours:.1f}時間")
            if data.get("deep_sleep"):
                deep_hours = data["deep_sleep"] / 60
                sleep_section.append(f"- 深い睡眠: {deep_hours:.1f}時間")
            if data.get("sleep_score"):
                sleep_section.append(f"- 睡眠スコア: {data['sleep_score']}/100")
            content_sections.extend(sleep_section)

        if any(data.get(key) for key in ["resting_heart_rate", "stress_avg"]):
            vital_section = ["## バイタルデータ"]
            if data.get("resting_heart_rate"):
                vital_section.append(f"- 安静時心拍数: {data['resting_heart_rate']}bpm")
            if data.get("stress_avg"):
                vital_section.append(f"- 平均ストレス: {data['stress_avg']}/100")
            content_sections.extend(vital_section)

        content = "\n".join(content_sections)

        # 主要な数値メトリクスを決定
        numeric_value = None
        unit = None
        if data.get("steps"):
            numeric_value = float(data["steps"])
            unit = "歩"
        elif data.get("sleep_duration"):
            numeric_value = data["sleep_duration"] / 60
            unit = "時間"
        elif data.get("weight"):
            numeric_value = data["weight"]
            unit = "kg"

        return LifelogEntry(
            category=LifelogCategory.HEALTH,
            type=LifelogType.METRIC,
            title=title,
            content=content,
            timestamp=integration_data.timestamp,
            numeric_value=numeric_value,
            unit=unit,
            tags=["健康データ", "Garmin", "自動記録"],
            source="garmin_integration",
            metadata={
                "external_id": integration_data.external_id,
                "data_type": "health",
                "garmin_data": data,
            },
        )
