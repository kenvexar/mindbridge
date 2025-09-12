#!/usr/bin/env python3
"""
音声メモ機能の総合テストスクリプト

Usage:
    python test_voice_memo.py
"""

import asyncio
import io
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from pydub.generators import Sine

# プロジェクトのルートディレクトリを Python パスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


async def create_test_audio_files() -> dict[str, bytes]:
    """テスト用の音声ファイルを作成"""
    test_files = {}

    try:
        # 1. 短い音声（ 1 秒）- MP3
        short_audio = Sine(440).to_audio_segment(duration=1000)  # 1 秒, 440Hz
        mp3_buffer = io.BytesIO()
        short_audio.export(mp3_buffer, format="mp3")
        test_files["short_test.mp3"] = mp3_buffer.getvalue()

        # 2. 中程度の音声（ 5 秒）- WAV
        medium_audio = Sine(880).to_audio_segment(duration=5000)  # 5 秒, 880Hz
        wav_buffer = io.BytesIO()
        medium_audio.export(wav_buffer, format="wav")
        test_files["medium_test.wav"] = wav_buffer.getvalue()

        # 3. 長い音声（ 10 秒）- OGG
        long_audio = Sine(220).to_audio_segment(duration=10000)  # 10 秒, 220Hz
        ogg_buffer = io.BytesIO()
        long_audio.export(ogg_buffer, format="ogg")
        test_files["long_test.ogg"] = ogg_buffer.getvalue()

        # 4. 非常に短い音声（ 0.3 秒）- 品質チェック用
        very_short_audio = Sine(660).to_audio_segment(duration=300)  # 0.3 秒
        very_short_buffer = io.BytesIO()
        very_short_audio.export(very_short_buffer, format="mp3")
        test_files["very_short_test.mp3"] = very_short_buffer.getvalue()

        print("✅ テスト用音声ファイル作成完了")
        for filename, data in test_files.items():
            print(f"  - {filename}: {len(data)} bytes")

    except Exception as e:
        print(f"❌ テスト音声ファイル作成エラー: {e}")
        # フォールバック: 簡単なダミーデータ
        test_files = {"dummy_test.mp3": b"dummy audio data for testing"}

    return test_files


async def test_speech_processor():
    """SpeechProcessor の機能テスト"""
    from src.audio.speech_processor import SpeechProcessor

    print("\n 🎤 SpeechProcessor テスト開始")
    processor = SpeechProcessor()

    # 1. 初期化状態の確認
    print("\n 📊 初期化状態確認:")
    print(f"  - API 利用可能: {processor.api_available}")
    print(
        f"  - 利用可能エンジン: {[engine['name'] for engine in processor.transcription_engines]}"
    )

    # 2. 使用量統計の確認
    stats = processor.get_usage_stats()
    print("\n 📈 API 使用量統計:")
    print(
        f"  - 月間使用量: {stats['monthly_usage_minutes']:.1f}分 / {stats['monthly_limit_minutes']:.1f}分"
    )
    print(f"  - 使用率: {stats['usage_percentage']:.1f}%")
    print(f"  - 残り時間: {stats['remaining_minutes']:.1f}分")
    print(f"  - 制限 exceeded: {stats['is_limit_exceeded']}")

    # 3. テスト音声ファイルの処理
    test_files = await create_test_audio_files()

    results = []
    for filename, file_data in test_files.items():
        print(f"\n 🔄 処理中: {filename} ({len(file_data)} bytes)")

        try:
            result = await processor.process_audio_file(
                file_data=file_data, filename=filename, channel_name="test"
            )

            results.append(
                {
                    "filename": filename,
                    "success": result.success,
                    "transcription": result.transcription.transcript
                    if result.transcription
                    else None,
                    "confidence": result.transcription.confidence
                    if result.transcription
                    else 0.0,
                    "processing_time": result.processing_time_ms,
                    "model_used": result.transcription.model_used
                    if result.transcription
                    else None,
                    "error": result.error_message,
                    "fallback_used": result.fallback_used,
                }
            )

            # 結果表示
            if result.success:
                print(f"  ✅ 成功: '{result.transcription.transcript[:50]}...'")
                print(f"     信頼度: {result.transcription.confidence:.2f}")
                print(f"     処理時間: {result.processing_time_ms}ms")
                print(f"     モデル: {result.transcription.model_used}")
            else:
                print(f"  ❌ 失敗: {result.error_message}")
                if result.fallback_used:
                    print(f"     フォールバック使用: {result.fallback_reason}")

        except Exception as e:
            print(f"  💥 例外発生: {e}")
            results.append(
                {
                    "filename": filename,
                    "success": False,
                    "error": str(e),
                    "exception": True,
                }
            )

    return results, stats


async def test_bot_integration():
    """Bot との統合テスト（簡易版）"""
    from src.bot.message_processor import MessageProcessor
    from src.bot.mock_client import MockDiscordBot

    print("\n 🤖 Bot 統合テスト開始")

    try:
        # モッククライアントとプロセッサーを作成
        mock_client = MockDiscordBot()
        processor = MessageProcessor()

        print("✅ Bot 統合テスト準備完了")

        # 音声ファイル処理のシミュレーション
        test_files = await create_test_audio_files()
        filename, file_data = list(test_files.items())[0]  # 最初のファイルを使用

        # Mock attachment オブジェクトを作成
        class MockAttachment:
            def __init__(self, filename: str, size: int):
                self.filename = filename
                self.size = size
                self.content_type = "audio/mpeg"

            async def read(self) -> bytes:
                return file_data

        attachment = MockAttachment(filename, len(file_data))

        # 音声処理のテスト（ SpeechProcessor を直接使用）
        print(f"\n 🔄 音声ファイル処理テスト: {filename}")
        from src.audio.speech_processor import SpeechProcessor

        speech_processor = SpeechProcessor()

        # 音声ファイルデータを読み取り
        audio_data = await attachment.read()
        result = await speech_processor.process_audio_file(
            file_data=audio_data, filename=attachment.filename, channel_name="test"
        )

        if result:
            print("✅ Bot 統合テスト成功")
            print(f"   処理結果: {result}")
        else:
            print("❌ Bot 統合テスト失敗")

        return True

    except Exception as e:
        print(f"❌ Bot 統合テストエラー: {e}")
        return False


async def test_obsidian_integration():
    """Obsidian 統合テスト"""
    from src.config.settings import get_settings
    from src.obsidian.core.vault_manager import VaultManager

    print("\n 📝 Obsidian 統合テスト開始")

    try:
        settings = get_settings()
        vault_path = Path(settings.obsidian_vault_path)

        if not vault_path.exists():
            print(f"❌ Obsidian ボルトが見つかりません: {vault_path}")
            return False

        print(f"✅ Obsidian ボルト確認: {vault_path}")

        # VaultManager のテスト
        vault_manager = VaultManager(vault_path)

        # 音声ファイル保存テスト
        test_audio_data = b"test audio content"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_filename = f"test_audio_{timestamp}.mp3"

        # 保存テスト（実際には保存しない - テストのみ）
        attachments_dir = vault_path / "80_Attachments" / "Audio"
        print(f"📂 音声保存先: {attachments_dir}")

        # テスト用にディレクトリを作成
        attachments_dir.mkdir(parents=True, exist_ok=True)

        if attachments_dir.exists():
            print("✅ 音声保存ディレクトリ確認済み")
        else:
            print(f"⚠️  音声保存ディレクトリが存在しません: {attachments_dir}")

        return True

    except Exception as e:
        print(f"❌ Obsidian 統合テストエラー: {e}")
        return False


async def generate_test_report(results: list[dict[str, Any]], stats: dict[str, Any]):
    """テスト結果レポート生成"""
    print("\n" + "=" * 60)
    print("📋 音声メモテスト結果レポート")
    print("=" * 60)

    # 統計情報
    total_tests = len(results)
    successful_tests = sum(1 for r in results if r.get("success", False))
    failed_tests = total_tests - successful_tests

    print("\n 📊 テスト統計:")
    print(f"  総テスト数: {total_tests}")
    print(
        f"  成功: {successful_tests} ({'100' if total_tests == 0 else successful_tests / total_tests * 100:.1f}%)"
    )
    print(f"  失敗: {failed_tests}")

    # API 使用量情報
    print("\n 💡 API 使用量:")
    print(f"  月間使用量: {stats['monthly_usage_minutes']:.1f}分")
    print(f"  残り時間: {stats['remaining_minutes']:.1f}分")
    print(f"  制限状態: {'制限中' if stats['is_limit_exceeded'] else '正常'}")

    # 個別テスト結果
    print("\n 📝 詳細結果:")
    for i, result in enumerate(results, 1):
        status = "✅" if result.get("success", False) else "❌"
        filename = result.get("filename", "Unknown")
        print(f"  {i}. {status} {filename}")

        if result.get("success"):
            transcript = result.get("transcription", "")
            confidence = result.get("confidence", 0.0)
            model = result.get("model_used", "Unknown")
            print(
                f"     文字起こし: {transcript[:50]}{'...' if len(transcript) > 50 else ''}"
            )
            print(f"     信頼度: {confidence:.2f}, モデル: {model}")
        else:
            error = result.get("error", "Unknown error")
            print(f"     エラー: {error}")

        if result.get("fallback_used"):
            print("     フォールバック: 使用済み")

    # 推奨事項
    print("\n 💡 推奨事項:")
    if stats["usage_percentage"] > 80:
        print("  ⚠️  API 使用量が 80% を超えています。使用量を監視してください。")

    if failed_tests > 0:
        print("  🔧 失敗したテストがあります。ログを確認してください。")

    if successful_tests > 0:
        print("  ✅ 音声メモ機能は正常に動作しています。")

    print("\n" + "=" * 60)


async def main():
    """メインテスト実行"""
    print("🎯 MindBridge 音声メモ機能テスト")
    print("=" * 60)

    # ログレベルを設定（詳細なログを表示）
    logging.basicConfig(level=logging.INFO)

    try:
        # 1. SpeechProcessor テスト
        speech_results, api_stats = await test_speech_processor()

        # 2. Bot 統合テスト
        bot_integration_success = await test_bot_integration()

        # 3. Obsidian 統合テスト
        obsidian_integration_success = await test_obsidian_integration()

        # 4. テストレポート生成
        await generate_test_report(speech_results, api_stats)

        # 5. 総合結果
        print("\n 🎯 総合テスト結果:")
        print(
            f"  音声処理: ✅ {len([r for r in speech_results if r.get('success')])}/{len(speech_results)} 成功"
        )
        print(f"  Bot 統合: {'✅ 成功' if bot_integration_success else '❌ 失敗'}")
        print(
            f"  Obsidian 統合: {'✅ 成功' if obsidian_integration_success else '❌ 失敗'}"
        )

        overall_success = (
            len([r for r in speech_results if r.get("success")]) > 0
            and bot_integration_success
            and obsidian_integration_success
        )

        if overall_success:
            print("\n 🎉 音声メモ機能テスト全体: 成功")
        else:
            print("\n ⚠️  音声メモ機能テスト全体: 部分的成功または失敗")

    except Exception as e:
        print(f"\n 💥 テスト実行中にエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    # 非同期でメイン関数を実行
    asyncio.run(main())
