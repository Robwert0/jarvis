import io

import av.error
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _audio_upload(
    data: bytes = b"fake-wav-bytes",
    filename: str = "clip.wav",
    content_type: str = "audio/wav",
) -> dict:
    """Build the multipart `files=` payload the endpoint expects.

    The endpoint param is `file: UploadFile`, so the form field must be "file".
    """
    return {"file": (filename, io.BytesIO(data), content_type)}


def test_transcribe_returns_text(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Patch where main looks the name up, not where it's defined — and so the
    # real Whisper model is never loaded.
    monkeypatch.setattr(
        "app.main.transcribe", lambda audio: ("hello world", "en", 1.5)
    )

    response = client.post("/jarvis/transcribe", files=_audio_upload())

    assert response.status_code == 200
    assert response.json() == {
        "text": "hello world",
        "language": "en",
        "duration": 1.5,
    }


def test_transcribe_rejects_non_audio(client: TestClient) -> None:
    response = client.post(
        "/jarvis/transcribe",
        files=_audio_upload(content_type="text/plain", filename="notes.txt"),
    )
    assert response.status_code == 415


def test_transcribe_rejects_too_large(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Shrink the cap instead of uploading 5MB so the test stays fast.
    monkeypatch.setattr("app.main.MAX_AUDIO_BYTES", 4)

    response = client.post(
        "/jarvis/transcribe", files=_audio_upload(data=b"more-than-four-bytes")
    )
    assert response.status_code == 413


def test_transcribe_rejects_undecodable_audio(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(audio):
        raise av.error.FFmpegError(1, "Invalid data found when processing input")

    monkeypatch.setattr("app.main.transcribe", boom)

    response = client.post("/jarvis/transcribe", files=_audio_upload())
    assert response.status_code == 400


def test_transcribe_requires_file(client: TestClient) -> None:
    # No multipart body at all -> FastAPI validation rejects before our checks.
    response = client.post("/jarvis/transcribe")
    assert response.status_code == 422
