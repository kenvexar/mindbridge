#!/usr/bin/env python3
"""
音声メモ機能のクイックテスト（モック機能使用）
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトのルートディレクトリを Python パスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.audio.speech_processor import SpeechProcessor


async def quick_test():
    print("🎤 音声メモ機能クイックテスト")
    print("=" * 50)

    # SpeechProcessor の初期化
    processor = SpeechProcessor()

    # 初期化状態の確認
    print(f"✓ API 利用可能: {processor.api_available}")
    print(f"✓ 利用可能エンジン: {[e['name'] for e in processor.transcription_engines]}")

    # API 使用量統計
    stats = processor.get_usage_stats()
    print(
        f"✓ 月間使用量: {stats['monthly_usage_minutes']:.1f}/{stats['monthly_limit_minutes']:.1f}分"
    )
    print(f"✓ 使用率: {stats['usage_percentage']:.1f}%")

    # 簡単な音声ファイルテスト（モックデータ）
    print("\n 🔄 音声ファイル処理テスト（モック）")
    test_audio_data = b"mock audio data for testing"

    try:
        result = await processor.process_audio_file(
            file_data=test_audio_data, filename="test.mp3", channel_name="test"
        )

        print(f"✓ 処理成功: {result.success}")
        if result.transcription:
            print(f"✓ 転写結果: {result.transcription.transcript}")
            print(f"✓ 信頼度: {result.transcription.confidence:.2f}")
            print(f"✓ 処理時間: {result.processing_time_ms}ms")
            print(f"✓ 使用モデル: {result.transcription.model_used}")

        if result.fallback_used:
            print(f"⚠️ フォールバック使用: {result.fallback_reason}")

    except Exception as e:
        print(f"❌ テストエラー: {e}")

    # サポートされているファイル形式の確認
    print(f"\n 📁 サポート形式: {list(processor.supported_formats.keys())}")

    # 各形式のテスト
    for ext in ["mp3", "wav", "ogg"]:
        is_supported = processor.is_audio_file(f"test.{ext}")
        print(f"✓ {ext.upper()}: {'サポート' if is_supported else '非サポート'}")

    print("\n 🎉 クイックテスト完了!")


if __name__ == "__main__":
    asyncio.run(quick_test())
