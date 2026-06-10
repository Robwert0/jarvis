from functools import lru_cache
from app.config import get_settings, Settings
from elevenlabs.client import ElevenLabs

MODEL_ID = "eleven_flash_v2_5"
OUTPUT_FORMAT = "mp3_44100_128"

@lru_cache
def get_client() -> ElevenLabs:
    return ElevenLabs(api_key=get_settings().elevenlabs_api_key)

def synthesize(
        text: str,
        *,
        client: ElevenLabs | None = None,
        settings: Settings |None = None,
) -> bytes:
    client = client or get_client()
    settings = settings or get_settings()

    audio = client.text_to_speech.convert(
        voice_id= settings.elevenlabs_voice_id,
        text= text,
        model_id=MODEL_ID,
        output_format=OUTPUT_FORMAT,
    )

    return b"".join(audio)