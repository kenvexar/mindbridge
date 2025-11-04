"""
Utilities-level tests for SpeechProcessor text normalization helpers.
"""

from src.audio.models import TranscriptionResult
from src.audio.speech_processor import SpeechProcessor


class TestSpeechProcessorTextNormalization:
    def test_remove_filler_words_from_transcript(self):
        """代表的なフィラーを除去して自然な文に整形できること"""
        text = "えーと、今日はえっと、会議でした。"
        cleaned = SpeechProcessor._normalize_transcript_text(
            SpeechProcessor._remove_filler_words(text)
        )
        assert cleaned == "今日は、会議でした。"

    def test_keep_meaningful_words(self):
        """意味のある語句は削除せず保持する"""
        text = "そのため、追加の確認が必要です。"
        cleaned = SpeechProcessor._normalize_transcript_text(
            SpeechProcessor._remove_filler_words(text)
        )
        assert cleaned == text

    def test_apply_transcript_postprocessing_updates_alternatives(self):
        """ポストプロセスで代替候補も同様に整形する"""
        transcription = TranscriptionResult.create_from_confidence(
            transcript="あー、散歩しました。",
            confidence=0.8,
            processing_time_ms=12,
            model_used="test-model",
            alternatives=[{"transcript": "あー、散歩しました。"}],
        )

        cleaned = SpeechProcessor._apply_transcript_postprocessing(transcription)
        assert cleaned.transcript == "散歩しました。"
        assert cleaned.alternatives == [{"transcript": "散歩しました。"}]
