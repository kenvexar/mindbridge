"""
Google Calendar サービスアカウント認証クライアント（シンプル実装）
"""

import os
from datetime import datetime, timedelta
from typing import Any

import structlog
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = structlog.get_logger(__name__)


class GoogleCalendarClient:
    """サービスアカウント認証での Google Calendar クライアント"""

    def __init__(self):
        self.service = None
        self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")
        self._initialized = False

    async def initialize(self) -> bool:
        """サービスアカウント認証で初期化"""
        if self._initialized:
            return True

        try:
            # サービスアカウントキーファイルのパス
            credentials_path = os.path.expanduser(
                os.getenv(
                    "GOOGLE_APPLICATION_CREDENTIALS", "~/mindbridge-calendar-key.json"
                )
            )

            if not os.path.exists(credentials_path):
                logger.error(
                    "サービスアカウントキーが見つかりません", path=credentials_path
                )
                return False

            # 認証情報の読み込み
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path,
                scopes=["https://www.googleapis.com/auth/calendar.readonly"],
            )

            # Calendar API サービスの構築
            self.service = build("calendar", "v3", credentials=credentials)

            # カレンダーID の設定（環境変数から取得、デフォルトは primary）
            self.calendar_id = os.getenv("GOOGLE_CALENDAR_ID", "primary")

            self._initialized = True
            logger.info(
                "Google Calendar クライアント初期化完了", calendar_id=self.calendar_id
            )
            return True

        except Exception as e:
            logger.error("Google Calendar 初期化失敗", error=str(e))
            return False

    async def get_today_events(self) -> list[dict[str, Any]]:
        """今日の予定を取得"""
        if not await self.initialize():
            return []

        try:
            # 今日の開始・終了時刻
            today = datetime.now().date()
            time_min = datetime.combine(today, datetime.min.time()).isoformat() + "Z"
            time_max = datetime.combine(today, datetime.max.time()).isoformat() + "Z"

            # イベント取得
            events_result = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            # イベント情報を整理
            formatted_events = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                formatted_events.append(
                    {
                        "title": event.get("summary", "無題"),
                        "start_time": start,
                        "description": event.get("description", ""),
                        "location": event.get("location", ""),
                    }
                )

            logger.info("今日の予定を取得", count=len(formatted_events))
            return formatted_events

        except Exception as e:
            logger.error("予定取得エラー", error=str(e))
            return []

    async def get_upcoming_events(self, days: int = 7) -> list[dict[str, Any]]:
        """今後の予定を取得"""
        if not await self.initialize():
            return []

        try:
            # 今から指定日数後まで
            now = datetime.utcnow().isoformat() + "Z"
            time_max = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"

            # イベント取得
            events_result = (
                self.service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=now,
                    timeMax=time_max,
                    maxResults=50,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            events = events_result.get("items", [])

            # イベント情報を整理
            formatted_events = []
            for event in events:
                start = event["start"].get("dateTime", event["start"].get("date"))
                formatted_events.append(
                    {
                        "title": event.get("summary", "無題"),
                        "start_time": start,
                        "description": event.get("description", ""),
                        "location": event.get("location", ""),
                    }
                )

            logger.info(f"{days}日間の予定を取得", count=len(formatted_events))
            return formatted_events

        except Exception as e:
            logger.error("予定取得エラー", error=str(e))
            return []

    async def test_connection(self) -> tuple[bool, str]:
        """接続テスト"""
        try:
            if not await self.initialize():
                return False, "サービスアカウント認証に失敗しました"

            # カレンダー情報取得でテスト
            calendar = (
                self.service.calendars().get(calendarId=self.calendar_id).execute()
            )
            calendar_name = calendar.get("summary", "Unknown")

            logger.info("Calendar API 接続成功", calendar_name=calendar_name)
            return True, f"接続成功: {calendar_name}"

        except Exception as e:
            error_msg = str(e)
            logger.error("Calendar API 接続失敗", error=error_msg)

            if "not found" in error_msg.lower():
                return False, f"カレンダーが見つかりません: {self.calendar_id}"
            elif "permission" in error_msg.lower() or "forbidden" in error_msg.lower():
                return (
                    False,
                    "カレンダーアクセス権限がありません。サービスアカウントにカレンダー共有設定が必要です。",
                )
            else:
                return False, f"接続エラー: {error_msg}"

    async def get_calendar_info(self) -> dict[str, Any] | None:
        """カレンダー情報を取得"""
        if not await self.initialize():
            return None

        try:
            calendar = (
                self.service.calendars().get(calendarId=self.calendar_id).execute()
            )
            return {
                "id": calendar.get("id"),
                "name": calendar.get("summary"),
                "description": calendar.get("description", ""),
                "timezone": calendar.get("timeZone"),
            }
        except Exception as e:
            logger.error("カレンダー情報取得エラー", error=str(e))
            return None
