import anthropic
from app.session import SessionStore, get_session_store
from fastapi import FastAPI, Depends, HTTPException, APIRouter

from app.config import Settings, get_settings
from app.llm import chat, extract_text
from app.schemas import ChatRequest, ChatResponse

app = FastAPI(title="Jarvis", version='0.1.0')
router = APIRouter(prefix="/jarvis")

@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
        req: ChatRequest,
        settings: Settings = Depends(get_settings),
        store: SessionStore = Depends(get_session_store),
) -> ChatResponse:
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

    return ChatResponse(
        reply=reply,
        session_id=session_id,
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )

app.include_router(router)