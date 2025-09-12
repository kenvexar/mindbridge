#!/usr/bin/env python3
"""
Garmin Connect 統合テストスクリプト

このスクリプトは Garmin Connect の統合機能をテストします:
- 認証テスト
- 健康データ取得テスト
- キャッシュ機能テスト
- エラーハンドリングテスト
"""

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

# プロジェクトのルートディレクトリを Python パスに追加
project_root = Path(__file__).parent.parent.parent  # tests/manual/../../ -> project root
sys.path.insert(0, str(project_root))

from src.garmin.client import GarminClient
from src.config.settings import get_settings


async def test_garmin_connection():
    """Garmin Connect 接続テスト"""
    print("🏃 Garmin Connect 統合テスト開始")
    print("=" * 50)
    
    # Garmin クライアントの初期化
    print("1. Garmin クライアント初期化中...")
    client = GarminClient()
    
    # 接続テスト
    print("\n2. 接続テスト実行中...")
    connection_result = await client.test_connection()
    
    if connection_result["success"]:
        print("✅ Garmin Connect 接続成功")
        print(f"   認証済み: {connection_result['authenticated']}")
        print(f"   ユーザーデータ利用可能: {connection_result['user_data_available']}")
        print(f"   連続失敗回数: {connection_result['consecutive_failures']}")
        print(f"   バックオフ期間中: {connection_result['in_backoff']}")
    else:
        print("❌ Garmin Connect 接続失敗")
        print(f"   エラー: {connection_result['message']}")
        print(f"   エラータイプ: {connection_result.get('error_type', 'Unknown')}")
        print(f"   ユーザー向けメッセージ: {connection_result.get('user_message', 'エラーが発生しました')}")
        
        if not connection_result["authenticated"]:
            print("\n 🔐 認証情報の確認:")
            settings = get_settings()
            has_email = hasattr(settings, "garmin_email") and settings.garmin_email
            has_password = hasattr(settings, "garmin_password") and settings.garmin_password
            
            print(f"   Garmin Email 設定: {'✅' if has_email else '❌ 未設定'}")
            print(f"   Garmin Password 設定: {'✅' if has_password else '❌ 未設定'}")
            
            if not (has_email and has_password):
                print("\n   ⚠️  認証情報が設定されていません")
                print("   環境変数 GARMIN_EMAIL と GARMIN_PASSWORD を設定してください")
                return False
    
    # キャッシュ統計表示
    cache_stats = connection_result.get("cache_stats", {})
    if cache_stats:
        print("\n 📦 キャッシュ統計:")
        print(f"   キャッシュサイズ: {cache_stats.get('cache_size', 0)} ファイル")
        print(f"   ディスクサイズ: {cache_stats.get('disk_size_mb', 0):.1f} MB")
        print(f"   最古のキャッシュ: {cache_stats.get('oldest_cache_days', 0)} 日前")
    
    return connection_result["success"]


async def test_health_data_retrieval():
    """健康データ取得テスト"""
    print("\n3. 健康データ取得テスト実行中...")
    
    client = GarminClient()
    
    # 今日のデータを取得
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    print(f"   今日 ({today}) のデータ取得中...")
    try:
        health_data = await client.get_health_data(today, use_cache=False)
        
        print(f"   データ品質: {health_data.data_quality}")
        print(f"   利用可能なデータタイプ: {health_data.available_data_types}")
        
        if health_data.has_any_data:
            print("   ✅ 健康データ取得成功")
            
            # 各データタイプの詳細表示
            if health_data.sleep and health_data.sleep.total_sleep_hours:
                print(f"      睡眠: {health_data.sleep.total_sleep_hours:.1f}時間")
                
            if health_data.steps and health_data.steps.total_steps:
                print(f"      歩数: {health_data.steps.total_steps:,}歩")
                
            if health_data.heart_rate and health_data.heart_rate.resting_heart_rate:
                print(f"      安静時心拍数: {health_data.heart_rate.resting_heart_rate}bpm")
                
            if health_data.activities:
                print(f"      アクティビティ: {len(health_data.activities)}件")
                
        else:
            print("   ⚠️  データが取得できませんでした")
            
        if health_data.detailed_errors:
            print(f"   エラー: {len(health_data.detailed_errors)}件")
            for error in health_data.detailed_errors:
                print(f"      - {error.source.value}: {error.user_message}")
                
    except Exception as e:
        print(f"   ❌ 健康データ取得失敗: {str(e)}")
        return False
    
    # キャッシュテスト
    print(f"\n   キャッシュテスト - 昨日 ({yesterday}) のデータ...")
    try:
        # キャッシュなしで取得
        fresh_data = await client.get_health_data(yesterday, use_cache=False)
        
        # キャッシュありで取得
        cached_data = await client.get_health_data(yesterday, use_cache=True)
        
        print(f"   キャッシュデータ利用可能: {cached_data.cache_age_hours is not None}")
        
        if cached_data.cache_age_hours is not None:
            print(f"   キャッシュ年齢: {cached_data.cache_age_hours:.1f}時間")
            
    except Exception as e:
        print(f"   キャッシュテスト失敗: {str(e)}")
    
    return True


async def test_cache_management():
    """キャッシュ管理テスト"""
    print("\n4. キャッシュ管理テスト実行中...")
    
    client = GarminClient()
    
    # キャッシュ統計取得
    cache_stats = client.get_cache_stats()
    print(f"   現在のキャッシュサイズ: {cache_stats.get('cache_size', 0)} ファイル")
    
    # 古いキャッシュのクリーンアップ
    try:
        cleaned_count = await client.cleanup_cache(days_to_keep=3)
        print(f"   クリーンアップされたキャッシュファイル: {cleaned_count}件")
        
        # クリーンアップ後の統計
        new_stats = client.get_cache_stats()
        print(f"   クリーンアップ後のキャッシュサイズ: {new_stats.get('cache_size', 0)} ファイル")
        
    except Exception as e:
        print(f"   キャッシュクリーンアップ失敗: {str(e)}")
        return False
    
    return True


async def main():
    """メインテスト実行"""
    print("🔧 Garmin Connect 統合テスト")
    print("このテストは Garmin Connect API との統合をテストします")
    print()
    
    success_count = 0
    total_tests = 3
    
    try:
        # 1. 接続テスト
        if await test_garmin_connection():
            success_count += 1
            
            # 2. データ取得テスト（接続成功時のみ）
            if await test_health_data_retrieval():
                success_count += 1
                
            # 3. キャッシュ管理テスト
            if await test_cache_management():
                success_count += 1
                
        else:
            print("接続テストが失敗したため、他のテストをスキップします")
            total_tests = 1
    
    except KeyboardInterrupt:
        print("\n ⚠️  テストが中断されました")
        return 1
    
    except Exception as e:
        print(f"\n ❌ 予期しないエラーが発生しました: {str(e)}")
        return 1
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print(f"📊 テスト結果: {success_count}/{total_tests} 成功")
    
    if success_count == total_tests:
        print("🎉 すべてのテストが成功しました！")
        print("Garmin Connect 統合が正常に動作しています。")
        return 0
    else:
        print("⚠️  一部のテストが失敗しました。")
        if success_count == 0:
            print("Garmin Connect の認証情報または接続を確認してください。")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))