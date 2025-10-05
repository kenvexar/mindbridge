"""
Google Calendar 連携

カレンダーイベントの自動取得とライフログ統合
"""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import structlog
from pydantic import BaseModel, Field

from src.integrations.google_calendar import GoogleCalendarService
from src.integrations.google_calendar.schemas import CalendarEventRecord

from ..models import LifelogCategory, LifelogEntry, LifelogType
from .base import (
    BaseIntegration,
    IntegrationConfig,
    IntegrationData,
    IntegrationDataProcessor,
)

logger = structlog.get_logger(__name__)


class GoogleCalendarEvent(BaseModel):
    """Google Calendar イベントデータ"""

    event_id: str
    summary: str | None = None
    description: str | None = None
    location: str | None = None

    start_time: datetime
    end_time: datetime
    all_day: bool = Field(default=False)

    # 分類情報
    calendar_id: str
    calendar_name: str | None = None
    event_type: str = Field(default="event")  # event, meeting, task, reminder

    # 参加者情報
    attendees: list[str] = Field(default_factory=list)
    organizer: str | None = None

    # ステータス
    status: str = Field(default="confirmed")  # confirmed, tentative, cancelled
    transparency: str = Field(default="opaque")  # opaque, transparent

    # 繰り返し情報
    recurring: bool = Field(default=False)
    recurrence_rule: str | None = None

    # メタデータ
    created_time: datetime | None = None
    updated_time: datetime | None = None


class GoogleCalendarIntegration(BaseIntegration):
    """Google Calendar 連携実装"""

    def __init__(self, config: IntegrationConfig):
        super().__init__(config)
        self.base_url = "https://www.googleapis.com/calendar/v3"
        self.service = GoogleCalendarService(base_url=self.base_url)

        # Google Calendar 固有設定
        calendar_settings = config.custom_settings.get("google_calendar", {})

        # 環境変数から設定を読み込み（設定ファイルを上書き）
        auto_discover = (
            os.getenv("GOOGLE_CALENDAR_AUTO_DISCOVER", "false").lower() == "true"
        )
        sync_selected_only = (
            os.getenv("GOOGLE_CALENDAR_SYNC_SELECTED_ONLY", "false").lower() == "true"
        )
        additional_ids = os.getenv("GOOGLE_CALENDAR_ADDITIONAL_IDS", "")

        # 基本設定
        base_calendars = calendar_settings.get("calendars", ["primary"])

        # 環境変数で追加されたカレンダー ID があれば追加
        if additional_ids.strip():
            additional_calendar_list = [
                cal.strip() for cal in additional_ids.split(",") if cal.strip()
            ]
            base_calendars.extend(additional_calendar_list)

        self.calendars_to_sync = list(set(base_calendars))  # 重複除去
        self.auto_discover_calendars = calendar_settings.get(
            "auto_discover_calendars", auto_discover
        )
        self.sync_selected_only = calendar_settings.get(
            "sync_selected_only", sync_selected_only
        )
        self.sync_past_events = calendar_settings.get("sync_past_events", False)
        self.sync_all_day_events = calendar_settings.get("sync_all_day_events", True)
        self.event_duration_threshold = calendar_settings.get(
            "min_duration_minutes", 15
        )
        self.exclude_keywords = calendar_settings.get("exclude_keywords", [])

        # 検出されたカレンダーのキャッシュ
        self.discovered_calendars: list[str] = []

        # イベントカテゴリマッピング
        self.event_category_mapping = {
            "meeting": {
                "category": LifelogCategory.WORK,
                "tags": ["会議", "ミーティング"],
            },
            "work": {"category": LifelogCategory.WORK, "tags": ["仕事", "業務"]},
            "appointment": {
                "category": LifelogCategory.ROUTINE,
                "tags": ["アポイント", "予定"],
            },
            "health": {"category": LifelogCategory.HEALTH, "tags": ["健康", "医療"]},
            "exercise": {
                "category": LifelogCategory.HEALTH,
                "tags": ["運動", "トレーニング"],
            },
            "learning": {
                "category": LifelogCategory.LEARNING,
                "tags": ["学習", "勉強"],
            },
            "social": {
                "category": LifelogCategory.RELATIONSHIP,
                "tags": ["社交", "人間関係"],
            },
            "travel": {"category": LifelogCategory.ROUTINE, "tags": ["移動", "旅行"]},
            "personal": {
                "category": LifelogCategory.ROUTINE,
                "tags": ["個人", "プライベート"],
            },
        }

        # キーワードベース自動分類
        self.keyword_categories = {
            LifelogCategory.WORK: [
                "meeting",
                "会議",
                "ミーティング",
                "打ち合わせ",
                "商談",
                "プレゼン",
                "面接",
                "研修",
                "セミナー",
                "会社",
                "office",
                "work",
            ],
            LifelogCategory.HEALTH: [
                "病院",
                "医者",
                "検診",
                "歯医者",
                "薬局",
                "ヨガ",
                "ジム",
                "運動",
                "hospital",
                "doctor",
                "medical",
                "gym",
                "exercise",
                "yoga",
            ],
            LifelogCategory.LEARNING: [
                "勉強",
                "学習",
                "授業",
                "講義",
                "研究",
                "読書",
                "資格",
                "試験",
                "study",
                "learning",
                "class",
                "course",
                "training",
                "education",
            ],
            LifelogCategory.RELATIONSHIP: [
                "友達",
                "家族",
                "デート",
                "食事",
                "飲み会",
                "パーティー",
                "結婚式",
                "friend",
                "family",
                "date",
                "dinner",
                "party",
                "wedding",
            ],
            LifelogCategory.ENTERTAINMENT: [
                "映画",
                "コンサート",
                "旅行",
                "観光",
                "ショッピング",
                "ゲーム",
                "movie",
                "concert",
                "travel",
                "shopping",
                "game",
                "entertainment",
            ],
        }

    async def authenticate(self) -> bool:
        """Google Calendar 認証"""
        try:
            # 環境変数から不足分を補完（.env 反映後に自動読込）
            if not self.config.client_id:
                self.config.client_id = os.getenv("GOOGLE_CALENDAR_CLIENT_ID")
            if not self.config.client_secret:
                self.config.client_secret = os.getenv("GOOGLE_CALENDAR_CLIENT_SECRET")
            if not self.config.access_token:
                self.config.access_token = os.getenv("GOOGLE_CALENDAR_ACCESS_TOKEN")
            if not self.config.refresh_token:
                self.config.refresh_token = os.getenv("GOOGLE_CALENDAR_REFRESH_TOKEN")

            if self.config.access_token:
                return await self._authenticate_oauth()

            if (
                self.config.refresh_token
                and self.config.client_id
                and self.config.client_secret
            ):
                refreshed = await self._refresh_token()
                if refreshed:
                    return await self._authenticate_oauth()
                self.add_error("Google Calendar トークンのリフレッシュに失敗しました")
                return False

            self.add_error("Google Calendar 認証情報が設定されていません")
            return False

        except Exception as e:
            self.add_error(f"Google Calendar 認証でエラー: {str(e)}")
            return False

    async def _authenticate_oauth(self) -> bool:
        """OAuth2 認証"""
        try:
            if not self.config.access_token:
                self.add_error("Google Calendar アクセストークンがありません")
                return False

            session = await self.service.get_session(
                headers={
                    "Authorization": f"Bearer {self.config.access_token}",
                    "User-Agent": "MindBridge-Lifelog/1.0",
                }
            )
            url = f"{self.base_url}/users/me/calendarList"
            async with session.get(url) as response:
                if response.status == 200:
                    calendar_data = await response.json()
                    calendars = (
                        calendar_data.get("items", [])
                        if isinstance(calendar_data, dict)
                        else []
                    )

                    self._authenticated = True
                    self.logger.info(
                        "Google Calendar OAuth 認証成功", calendar_count=len(calendars)
                    )

                    await self._cache_calendar_info(calendars)
                    await self._discover_and_update_calendars(calendars)
                    return True

                if response.status == 401:
                    if await self._refresh_token():
                        return await self._authenticate_oauth()
                    self.add_error(
                        "Google Calendar トークンが無効です。再認証が必要です"
                    )
                    return False

                self.add_error(f"Google Calendar 認証失敗: HTTP {response.status}")
                return False

        except Exception as e:
            self.add_error(f"Google Calendar OAuth 認証でエラー: {str(e)}")
            return False

    async def _refresh_token(self) -> bool:
        """Google トークンリフレッシュ"""
        if not (
            self.config.refresh_token
            and self.config.client_id
            and self.config.client_secret
        ):
            self.add_error("トークンリフレッシュに必要な情報が不足しています")
            return False

        try:
            from aiohttp import ClientSession, ClientTimeout

            refresh_url = "https://oauth2.googleapis.com/token"
            data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "refresh_token": self.config.refresh_token,
                "grant_type": "refresh_token",
            }

            async with ClientSession(timeout=ClientTimeout(total=30)) as session:
                async with session.post(refresh_url, data=data) as response:
                    if response.status == 200:
                        token_data = await response.json()
                        self.config.access_token = token_data.get("access_token")
                        if token_data.get("refresh_token"):
                            self.config.refresh_token = token_data["refresh_token"]
                        if token_data.get("expires_in"):
                            expires_in = int(token_data["expires_in"])
                            self.config.token_expires_at = datetime.now() + timedelta(
                                seconds=expires_in
                            )
                        self.logger.info("Google Calendar トークンリフレッシュ成功")
                        return True

                    self.add_error(
                        f"Google Calendar トークンリフレッシュ失敗: HTTP {response.status}"
                    )
                    return False

        except Exception as e:
            self.add_error(f"Google Calendar トークンリフレッシュでエラー: {str(e)}")
            return False

    async def _cache_calendar_info(self, calendars: list[dict[str, Any]]):
        """カレンダー情報キャッシュ"""
        calendar_info = {}
        for cal in calendars:
            calendar_info[cal["id"]] = {
                "name": cal.get("summary", ""),
                "description": cal.get("description", ""),
                "primary": cal.get("primary", False),
                "access_role": cal.get("accessRole", ""),
            }

        # 設定にカレンダー情報を保存
        if "google_calendar" not in self.config.custom_settings:
            self.config.custom_settings["google_calendar"] = {}
        self.config.custom_settings["google_calendar"]["calendar_info"] = calendar_info

        # 自動検出が有効な場合、カレンダー一覧を更新
        if self.auto_discover_calendars:
            await self._discover_and_update_calendars(calendars)

    async def _discover_and_update_calendars(self, calendars: list[dict[str, Any]]):
        """カレンダー自動検出と同期対象更新"""
        discovered_calendar_ids = []

        for cal in calendars:
            cal_id = cal["id"]
            access_role = cal.get("accessRole", "")
            selected = cal.get("selected", False)
            summary = cal.get("summary", "")

            # アクセス権限があり、かつ以下の条件を満たすカレンダーを自動検出
            should_include = False

            if self.sync_selected_only:
                # 選択されたカレンダーのみ
                should_include = selected
            else:
                # 読み取り権限があるカレンダー（owner, writer のみ - reader は除外）
                should_include = access_role in ["owner", "writer"]

            # 除外条件チェック
            if should_include:
                # システム系カレンダーとホリデーカレンダーを除外
                exclude_patterns = [
                    "#contacts@",
                    "@import.calendar.google.com",
                    "#holiday@",  # 祝日カレンダー全般
                    "japanese#holiday@",  # 日本の祝日カレンダー
                ]

                exclude_names = [
                    "日本の祝日",
                    "Holidays in Japan",
                    "祝日",
                ]

                # IDパターンでの除外チェック
                for pattern in exclude_patterns:
                    if pattern in cal_id:
                        should_include = False
                        self.logger.debug(
                            f"カレンダー除外 (IDパターン): {summary} ({cal_id})",
                            pattern=pattern,
                            calendar_id=cal_id,
                        )
                        break

                # 名前パターンでの除外チェック
                if should_include:
                    for name_pattern in exclude_names:
                        if name_pattern in summary:
                            should_include = False
                            self.logger.debug(
                                f"カレンダー除外 (名前パターン): {summary} ({cal_id})",
                                pattern=name_pattern,
                                calendar_id=cal_id,
                            )
                            break

            if should_include:
                discovered_calendar_ids.append(cal_id)
                self.logger.info(
                    f"カレンダー自動検出: {summary} ({cal_id})",
                    calendar_id=cal_id,
                    access_role=access_role,
                    selected=selected,
                )
            else:
                self.logger.debug(
                    f"カレンダースキップ: {summary} ({cal_id})",
                    calendar_id=cal_id,
                    access_role=access_role,
                    selected=selected,
                    reason="除外条件に該当",
                )

        # 検出されたカレンダー一覧を更新
        self.discovered_calendars = discovered_calendar_ids

        # 明示的に指定されたカレンダーと統合
        all_calendars = list(set(self.calendars_to_sync + discovered_calendar_ids))

        self.logger.info(
            f"同期対象カレンダー: {len(all_calendars)}件 "
            f"(設定: {len(self.calendars_to_sync)}件, 自動検出: {len(discovered_calendar_ids)}件)"
        )

        # 動的に同期対象を更新
        self.calendars_to_sync = all_calendars

    async def test_connection(self) -> bool:
        """接続テスト"""
        if not self._authenticated or not self.config.access_token:
            return False

        try:
            calendars = await self.service.fetch_calendar_list(
                access_token=self.config.access_token,
                on_request=self.increment_request_count,
            )
            success = len(calendars) > 0
            if success:
                self.logger.info("Google Calendar 接続テスト成功")
            else:
                self.add_error("Google Calendar 接続テストに失敗しました")
            return success
        except Exception as e:
            self.add_error(f"Google Calendar 接続テストでエラー: {str(e)}")
            return False

    async def sync_data(
        self, start_date: datetime | None = None, end_date: datetime | None = None
    ) -> list[IntegrationData]:
        """データ同期"""
        if not await self.check_rate_limit():
            self.logger.warning("Google Calendar API レート制限中")
            return []

        if not self._authenticated:
            await self.authenticate()
            if not self._authenticated:
                self.logger.warning("Google Calendar 未認証のため同期をスキップします")
                return []

        if not self.config.access_token:
            self.add_error("Google Calendar アクセストークンがありません")
            return []

        start_time = datetime.now()
        synced_data: list[IntegrationData] = []

        start_date = start_date or datetime.now() - timedelta(
            days=1 if self.sync_past_events else 0
        )
        end_date = end_date or datetime.now() + timedelta(days=7)

        start_utc = self._ensure_utc(start_date)
        end_utc = self._ensure_utc(end_date)

        try:
            tasks = [
                self._sync_calendar_events(calendar_id, start_utc, end_utc)
                for calendar_id in self.calendars_to_sync
            ]
            calendar_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in calendar_results:
                if isinstance(result, Exception):
                    self.logger.warning("カレンダー同期でエラー", error=str(result))
                    continue
                if isinstance(result, list) and result:
                    synced_data.extend(result)

            unique_events: dict[str, IntegrationData] = {}
            for event in synced_data:
                event_key = f"{event.external_id}_{event.timestamp.isoformat()}"
                unique_events.setdefault(event_key, event)
            synced_data = list(unique_events.values())

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
                "Google Calendar データ同期完了",
                records=len(synced_data),
                duration=f"{sync_duration:.1f}s",
            )
            return synced_data

        except Exception as e:
            self.add_error(f"Google Calendar データ同期でエラー: {str(e)}")
            self.update_metrics(health_score=max(0.0, self.metrics.health_score - 10.0))
            return []

    async def _sync_calendar_events(
        self, calendar_id: str, start_date: datetime, end_date: datetime
    ) -> list[IntegrationData]:
        """指定カレンダーのイベント同期"""
        events_data: list[IntegrationData] = []

        if not self.config.access_token:
            return events_data

        calendar_name = self._get_calendar_name(calendar_id)
        params = {
            "maxResults": "100",
            "singleEvents": "true",
            "orderBy": "startTime",
        }

        raw_events = await self.service.fetch_events(
            access_token=self.config.access_token,
            calendar_id=calendar_id,
            time_min=start_date,
            time_max=end_date,
            params=params,
            on_request=self.increment_request_count,
        )

        for event in raw_events:
            try:
                summary = event.get("summary", "")
                if self._should_exclude_event(summary, event.get("description", "")):
                    continue

                record = self.service.build_event_record(
                    event,
                    calendar_id=calendar_id,
                    calendar_name=calendar_name,
                )
                if record is None:
                    continue

                if (
                    not record.all_day
                    and record.duration_minutes() < self.event_duration_threshold
                ):
                    continue

                integration_event = self._record_to_calendar_event(record)
                processed_data = integration_event.model_dump()

                enhanced_raw = dict(record.raw)
                enhanced_raw.setdefault("calendar_id", calendar_id)
                enhanced_raw.setdefault("calendar_name", calendar_name)

                integration_data = IntegrationData(
                    integration_name="google_calendar",
                    external_id=record.event_id,
                    data_type="calendar_event",
                    timestamp=integration_event.start_time,
                    raw_data=enhanced_raw,
                    processed_data=processed_data,
                    confidence_score=0.9,
                    data_quality=IntegrationDataProcessor.calculate_data_quality(
                        event,
                        ["id", "summary", "start"],
                    ),
                )
                events_data.append(integration_data)

            except Exception as exc:
                self.logger.warning(
                    "Google Calendar イベント処理でエラー",
                    event_id=event.get("id"),
                    error=str(exc),
                )
                continue

        if events_data:
            self.logger.info(
                "Google Calendar イベント取得完了",
                calendar_id=calendar_id,
                calendar_name=calendar_name,
                count=len(events_data),
            )
        else:
            self.logger.debug(
                "Google Calendar イベントなし",
                calendar_id=calendar_id,
                calendar_name=calendar_name,
            )

        return events_data

    def _record_to_calendar_event(
        self, record: CalendarEventRecord
    ) -> GoogleCalendarEvent:
        data = record.model_dump(exclude={"raw"}, exclude_none=True)
        return GoogleCalendarEvent(**data)

    @staticmethod
    def _ensure_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _get_calendar_name(self, calendar_id: str) -> str:
        """カレンダー名取得"""
        calendar_info = self.config.custom_settings.get("google_calendar", {}).get(
            "calendar_info", {}
        )

        # primary カレンダーの場合、実際のプライマリカレンダーIDを探す
        if calendar_id == "primary":
            for cal_id, info in calendar_info.items():
                if info.get("primary", False):
                    calendar_name = info.get("name", cal_id)
                    self.logger.debug(
                        "プライマリカレンダー名解決",
                        primary_id=cal_id,
                        name=calendar_name,
                    )
                    return calendar_name
            # プライマリカレンダーが見つからない場合
            return "primary"

        # 通常のカレンダーID
        cached_info = calendar_info.get(calendar_id, {})
        calendar_name = cached_info.get("name", "")

        # デバッグ情報をログに出力
        self.logger.debug(
            "カレンダー名取得",
            calendar_id=calendar_id,
            cached_name=calendar_name,
            has_cache=bool(cached_info),
            total_cached_calendars=len(calendar_info),
        )

        # カレンダー名が取得できない場合の fallback
        if not calendar_name:
            if "@" in calendar_id:
                # email形式の場合、@より前の部分を使用
                return calendar_id.split("@")[0]
            else:
                # その他の場合、最初の20文字を使用
                return calendar_id[:20] + ("..." if len(calendar_id) > 20 else "")

        return calendar_name

    def _should_exclude_event(self, summary: str, description: str) -> bool:
        """イベント除外判定"""
        text = f"{summary} {description}".lower()

        for keyword in self.exclude_keywords:
            if keyword.lower() in text:
                return True

        # 自動生成されたイベント（例： Zoom 自動生成）
        auto_generated_patterns = [
            "zoom meeting",
            "automatically generated",
            "recurring",
        ]

        for pattern in auto_generated_patterns:
            if pattern in text:
                return True

        return False

    def _classify_event_type(
        self, summary: str, description: str, attendee_count: int
    ) -> str:
        """イベントタイプ分類"""
        text = f"{summary} {description}".lower()

        # キーワードベース分類
        type_keywords = {
            "meeting": ["会議", "ミーティング", "meeting", "打ち合わせ", "商談"],
            "appointment": ["アポ", "面談", "相談", "診察", "appointment"],
            "health": [
                "病院",
                "医者",
                "歯医者",
                "検診",
                "ヨガ",
                "ジム",
                "doctor",
                "hospital",
            ],
            "learning": [
                "勉強",
                "授業",
                "講義",
                "研修",
                "セミナー",
                "class",
                "training",
            ],
            "social": ["食事", "飲み会", "パーティー", "デート", "dinner", "party"],
            "travel": ["移動", "出張", "旅行", "travel", "trip"],
        }

        for event_type, keywords in type_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return event_type

        # 参加者数による分類
        if attendee_count > 3:
            return "meeting"
        elif attendee_count > 0:
            return "appointment"

        return "personal"

    async def get_available_data_types(self) -> list[str]:
        """利用可能なデータタイプ"""
        return [
            "calendar_event",
            "meeting",
            "appointment",
            "personal_event",
            "recurring_event",
        ]

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了処理"""
        await self.service.close()

    def convert_to_lifelog_entry(
        self, integration_data: IntegrationData
    ) -> LifelogEntry:
        """IntegrationData を LifelogEntry に変換"""
        processed_data = integration_data.processed_data
        event_data = GoogleCalendarEvent(**processed_data)

        # カテゴリ決定
        category = self._determine_lifelog_category(event_data)

        # タイトル生成
        title = self._generate_lifelog_title(event_data)

        # コンテンツ生成
        content = self._generate_lifelog_content(event_data)

        # タグ生成
        tags = self._generate_lifelog_tags(event_data)

        # 数値データ（時間）
        if not event_data.all_day:
            duration_hours = (
                event_data.end_time - event_data.start_time
            ).total_seconds() / 3600
            numeric_value = round(duration_hours, 1)
            unit = "時間"
        else:
            numeric_value = None
            unit = None

        return LifelogEntry(
            category=category,
            type=LifelogType.EVENT,
            title=title,
            content=content,
            timestamp=event_data.start_time,
            numeric_value=numeric_value,
            unit=unit,
            tags=tags,
            location=event_data.location,
            source="google_calendar_integration",
            metadata={
                "external_id": integration_data.external_id,
                "calendar_name": event_data.calendar_name,
                "event_type": event_data.event_type,
                "attendee_count": len(event_data.attendees),
                "all_day": event_data.all_day,
                "google_calendar_data": processed_data,
            },
        )

    def _determine_lifelog_category(
        self, event: GoogleCalendarEvent
    ) -> LifelogCategory:
        """ライフログカテゴリ決定"""
        # イベントタイプからマッピング
        if event.event_type in self.event_category_mapping:
            return cast(
                LifelogCategory,
                self.event_category_mapping[event.event_type]["category"],
            )

        # キーワードベース分類
        text = f"{event.summary} {event.description or ''}".lower()

        for category, keywords in self.keyword_categories.items():
            for keyword in keywords:
                if keyword in text:
                    return category

        # デフォルト分類
        if len(event.attendees) > 2:
            return LifelogCategory.WORK  # 複数参加者 = 仕事関連
        elif event.calendar_name and "work" in event.calendar_name.lower():
            return LifelogCategory.WORK
        else:
            return LifelogCategory.ROUTINE  # 個人の予定

    def _generate_lifelog_title(self, event: GoogleCalendarEvent) -> str:
        """ライフログタイトル生成"""
        title_parts = []

        # 基本タイトル
        if event.summary:
            title_parts.append(event.summary)
        else:
            title_parts.append("カレンダーイベント")

        # 時間情報追加
        if not event.all_day:
            start_time = event.start_time.strftime("%H:%M")
            duration = event.end_time - event.start_time
            duration_minutes = int(duration.total_seconds() / 60)

            if duration_minutes < 60:
                title_parts.append(f"({start_time}〜、{duration_minutes}分)")
            else:
                duration_hours = duration_minutes / 60
                title_parts.append(f"({start_time}〜、{duration_hours:.1f}時間)")

        return " ".join(title_parts)

    def _generate_lifelog_content(self, event: GoogleCalendarEvent) -> str:
        """ライフログコンテンツ生成"""
        content_parts = []

        # 基本情報
        content_parts.append("Google Calendar から自動記録されたイベント")

        if event.description:
            content_parts.append(f"\n## 詳細\n{event.description}")

        # 時間情報
        if event.all_day:
            date_str = event.start_time.strftime("%Y 年%m 月%d 日")
            content_parts.append(f"\n**日付**: {date_str}（終日）")
        else:
            start_str = event.start_time.strftime("%Y 年%m 月%d 日 %H:%M")
            end_str = event.end_time.strftime("%H:%M")
            duration = event.end_time - event.start_time
            duration_str = f"{int(duration.total_seconds() / 60)}分"
            content_parts.append(
                f"\n**時間**: {start_str} 〜 {end_str} ({duration_str})"
            )

        # 場所情報
        if event.location:
            content_parts.append(f"**場所**: {event.location}")

        # 参加者情報
        if event.attendees:
            attendee_count = len(event.attendees)
            if attendee_count <= 3:
                content_parts.append(f"**参加者**: {attendee_count}名")
            else:
                content_parts.append(f"**参加者**: {attendee_count}名（大規模）")

        # カレンダー情報
        if event.calendar_name and event.calendar_name != "primary":
            content_parts.append(f"**カレンダー**: {event.calendar_name}")

        return "\n".join(content_parts)

    def _generate_lifelog_tags(self, event: GoogleCalendarEvent) -> list[str]:
        """ライフログタグ生成"""
        tags = ["カレンダー", "自動記録"]

        # イベントタイプタグ
        if event.event_type in self.event_category_mapping:
            tags.extend(self.event_category_mapping[event.event_type]["tags"])

        # その他タグ
        if event.all_day:
            tags.append("終日")

        if len(event.attendees) > 0:
            tags.append("他者")

        if event.recurring:
            tags.append("定期")

        if event.location:
            tags.append("場所指定")

        # カレンダー名タグ
        if event.calendar_name and event.calendar_name != "primary":
            calendar_tag = f"カレンダー:{event.calendar_name}"
            tags.append(calendar_tag)

        return list(set(tags))  # 重複除去
