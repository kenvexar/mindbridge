"""
Audio processing module for Discord-Obsidian Memo Bot
"""

from src.audio.speech_processor import SpeechProcessor
from src.obsidian.models import AudioProcessingResult, TranscriptionResult

__all__ = [
    "SpeechProcessor",
    "AudioProcessingResult",
    "TranscriptionResult",
]
