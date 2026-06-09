import anthropic
import av.error
from app.session import SessionStore, get_session_store
from fastapi import FastAPI, Depends, HTTPException, APIRouter, UploadFile

from app.config import Settings, get_settings
from app.llm import chat, extract_text
from app.stt import transcribe
from app import schemas

app = FastAPI(title="Jarvis", version='0.1.0')
router = APIRouter(prefix="/jarvis")

MAX_AUDIO_BYTES = 5 * 1024 * 1024

def _ensure_audio(file: UploadFile):
    if not (file.content_type or "").startswith("audio/"):
        raise HTTPException(
            status_code=415,
            detail=f"Expected an audio file, got '{file.content_type}'",
        )
    if file.size is not None and file.size > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Audio too large, got {file.size} bytes max {MAX_AUDIO_BYTES}",
        )

@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}

@router.post("/chat", response_model=schemas.ChatResponse)
def chat_endpoint(
        req: schemas.ChatRequest,
        settings: Settings = Depends(get_settings),
        store: SessionStore = Depends(get_session_store),
) -> schemas.ChatResponse:
    session_id = req.session_id or store.new_session()
    user_msg ={"role": "user", "content": req.message}

    try:
        response = chat([*store.get(session_id), user_msg], system=req.system, settings=settings)
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except anthropic.APIConnectionError as e:
        raise HTTPException(status_code=503, detail="Upstream connection failed") from e

    reply = extract_text(response)
    store.append(session_id, user_msg)
    store.append(session_id, {"role": "assistant", "content": reply})

    return schemas.ChatResponse(
        reply=reply,
        session_id=session_id,
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )

@router.post("/transcribe", response_model=schemas.TranscriptionResponse,)
def transcribe_endpoint(file: UploadFile):
    _ensure_audio(file)
    try:
        text, language, duration = transcribe(file.file)
    except av.error.FFmpegError as e:
        raise HTTPException(status_code=400, detail="Could not decode audio") from e
    return schemas.TranscriptionResponse(
        text=text,
        language=language,
        duration=duration,
    )

app.include_router(router)