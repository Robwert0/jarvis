from functools import lru_cache
from typing import BinaryIO

from app.config import get_settings, Settings
from faster_whisper import WhisperModel


@lru_cache
def get_model() -> WhisperModel:
    return WhisperModel(get_settings().whisper_model, device='cpu', compute_type="int8")

def transcribe(
        audio: BinaryIO,
        *,
        model: WhisperModel | None = None,
        settings: Settings | None = None,
) -> tuple[str, str, float]:
    model = model or get_model()
    segments, info = model.transcribe(audio)
    text = " ".join(s.text.strip() for s in segments)

    return text, info.language, info.duration
