#!/usr/bin/env python3
"""
実際の音声ファイルを使用したテスト
"""

import asyncio
import io
import sys
from pathlib import Path

from pydub.generators import Sine

# プロジェクトのルートディレクトリを Python パスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.audio.speech_processor import SpeechProcessor


async def create_real_audio_file():
    """実際の音声データを作成（テスト用）"""
    # 1 秒間の 440Hz 正弦波（ A の音）を作成
    audio = Sine(440).to_audio_segment(duration=1000)  # 1 秒

    # MP3 として出力
    buffer = io.BytesIO()
    audio.export(buffer, format="mp3", bitrate="128k")
    audio_data = buffer.getvalue()

    print(f"✅ 実際の音声データ作成完了: {len(audio_data)} bytes")
    return audio_data


async def test_with_real_audio():
    """実際の音声データでテスト"""
    print("🎵 実際の音声データでのテスト開始")
    print("=" * 50)

    processor = SpeechProcessor()

    # 実際の音声データを作成
    audio_data = await create_real_audio_file()

    # 処理実行
    result = await processor.process_audio_file(
        file_data=audio_data, filename="test_tone.mp3", channel_name="test"
    )

    print("\n 📊 テスト結果:")
    print(f"✓ 処理成功: {result.success}")
    print(f"✓ ファイルサイズ: {result.file_size_bytes} bytes")
    print(f"✓ 推定時間: {result.duration_seconds}秒")
    print(f"✓ 処理時間: {result.processing_time_ms}ms")

    if result.transcription:
        print(f"✓ 転写結果: {result.transcription.transcript}")
        print(f"✓ 信頼度: {result.transcription.confidence:.2f}")
        print(f"✓ 使用モデル: {result.transcription.model_used}")

    if result.fallback_used:
        print(f"⚠️ フォールバック使用: {result.fallback_reason}")
        if hasattr(result, "saved_file_path") and result.saved_file_path:
            print(f"📁 保存先: {result.saved_file_path}")


if __name__ == "__main__":
    asyncio.run(test_with_real_audio())
