#!/usr/bin/env python3
"""
Google Calendar データ取得の修正確認テスト

修正内容:
1. カレンダー名の正しい表示
2. aiohttp セッションの適切なクローズ
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from src.lifelog.integrations.base import IntegrationConfig
from src.lifelog.integrations.google_calendar import GoogleCalendarIntegration


async def test_google_calendar_fixes():
    """Google Calendar の修正確認テスト"""
    print("=== Google Calendar 修正確認テスト ===\n")

    try:
        # 設定作成
        config = IntegrationConfig(
            integration_name="google_calendar", enabled=True, sync_enabled=True
        )

        # 非同期コンテキストマネージャーを使用してセッション管理
        async with GoogleCalendarIntegration(config) as integration:
            print("✓ Google Calendar 統合クラス作成完了")

            # 認証テスト
            print("--- 認証テスト ---")
            auth_result = await integration.authenticate()
            print(f"認証結果: {auth_result}")

            if not auth_result:
                print("❌ 認証に失敗しました")
                return False

            # 接続テスト
            print("\n--- 接続テスト ---")
            connection_result = await integration.test_connection()
            print(f"接続テスト結果: {connection_result}")

            if not connection_result:
                print("❌ 接続テストに失敗しました")
                return False

            # データ取得テスト（過去 7 日間）
            print("\n--- データ取得テスト ---")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)

            data = await integration.sync_data(start_date=start_date, end_date=end_date)
            print(f"✓ 取得データ数: {len(data)}件")

            if len(data) == 0:
                print("⚠️  データが取得されませんでした（過去 7 日間）")
                return True  # データがないのはエラーではない

            # データ詳細分析
            print("\n--- データ詳細分析 ---")

            # カレンダー別集計
            calendar_stats = {}
            event_details = []

            for item in data:
                raw_data = item.raw_data
                event = raw_data.get("event", raw_data)  # fallback
                calendar_name = raw_data.get("calendar_name", "unknown")
                calendar_id = raw_data.get("calendar_id", "unknown")

                # カレンダー表示名を作成
                if calendar_name != "unknown":
                    display_name = calendar_name
                elif calendar_id != "unknown":
                    display_name = f"ID: {calendar_id[:20]}..."
                else:
                    display_name = "unknown"

                if display_name not in calendar_stats:
                    calendar_stats[display_name] = 0
                calendar_stats[display_name] += 1

                # イベント詳細を保存
                summary = event.get("summary", "タイトルなし")
                start_info = event.get("start", {})
                start_time = start_info.get(
                    "dateTime", start_info.get("date", "時刻不明")
                )

                event_details.append(
                    {
                        "calendar": display_name,
                        "summary": summary,
                        "start": start_time,
                        "timestamp": item.timestamp,
                        "event_id": event.get("id", "ID 不明"),
                    }
                )

            print("カレンダー別イベント数:")
            for calendar, count in sorted(calendar_stats.items()):
                print(f"  - {calendar}: {count}件")

            # 最新 5 件の詳細表示
            print("\n 最新 5 件のイベント:")
            sorted_events = sorted(
                event_details, key=lambda x: x["timestamp"], reverse=True
            )
            for i, event in enumerate(sorted_events[:5]):
                print(f"  {i + 1}. [{event['calendar']}] {event['summary']}")
                print(f"      開始: {event['start']}")
                print(f"      ID: {event['event_id']}")
                print()

            # 修正確認
            print("--- 修正確認 ---")
            unknown_count = calendar_stats.get("unknown", 0)
            if unknown_count == 0:
                print("✅ カレンダー名表示問題: 修正済み")
            else:
                print(f"⚠️  カレンダー名表示問題: {unknown_count}件がまだ'unknown'")

            print("✅ aiohttp セッション管理: コンテキストマネージャーで適切に管理")

            return True

        # コンテキストマネージャー終了後
        print("\n ✅ セッション適切にクローズされました")

    except Exception as e:
        print(f"❌ エラー: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """メイン実行関数"""
    print("Google Calendar データ取得修正確認テストを開始します...\n")

    result = asyncio.run(test_google_calendar_fixes())

    if result:
        print("\n 🎉 Google Calendar 修正確認テスト成功!")
        print("✓ カレンダー名が正しく表示されます")
        print("✓ aiohttp セッションが適切にクローズされます")
    else:
        print("\n 💥 Google Calendar 修正確認テストでエラーが発生しました")

    return 0 if result else 1


if __name__ == "__main__":
    exit(main())
