import anthropic
from fastapi import FastAPI, Depends, HTTPException, APIRouter

from app.config import Settings, get_settings
from app.agent import run_agent
from app import conversation_store as store
from app import memory_store
from app import schemas

app = FastAPI(title="Jarvis", version="0.1.0")
router = APIRouter(prefix="/jarvis")


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/chat", response_model=schemas.ChatResponse)
def chat_endpoint(
    req: schemas.ChatRequest,
    settings: Settings = Depends(get_settings),
) -> schemas.ChatResponse:
    session_id = req.session_id or store.new_session()
    try:
        result = run_agent(
            store.get(session_id),
            req.message,
            memories=memory_store.list_memories(),
            settings=settings,
        )
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except anthropic.APIConnectionError as e:
        raise HTTPException(status_code=503, detail="Upstream connection failed") from e

    store.append(session_id, "user", req.message)
    store.append(session_id, "assistant", result.reply)

    return schemas.ChatResponse(
        reply=result.reply,
        session_id=session_id,
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        actions=[schemas.ActionView(tool=a.tool, summary=a.result) for a in result.actions],
    )


@router.get("/conversations", response_model=list[schemas.ConversationSummary])
def list_conversations_endpoint() -> list[schemas.ConversationSummary]:
    return [schemas.ConversationSummary(**c) for c in store.list_conversations()]


@router.get("/conversations/{session_id}", response_model=list[schemas.Message])
def get_conversation_endpoint(session_id: str) -> list[schemas.Message]:
    messages = store.get(session_id)
    if not messages:
        raise HTTPException(status_code=404, detail="No such conversation")
    return [schemas.Message(**m) for m in messages]


@router.get("/memories", response_model=list[str])
def list_memories_endpoint() -> list[str]:
    return memory_store.list_memories()


app.include_router(router)
