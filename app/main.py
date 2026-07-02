import anthropic
from fastapi import FastAPI, Depends, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import Settings, get_settings
from app.agent import run_agent
from app import conversation_store as store
from app import macros_api
from app import memory_store
from app import voice_api
from app import schemas

app = FastAPI(title="Jarvis", version="0.1.0")

# The desktop app (Electron) calls this API from another origin: the Vite dev
# server in development, file:// when packaged. Single-user API bound to
# localhost, so any-origin is acceptable.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@router.delete("/conversations/{session_id}", status_code=204, response_model=None)
def delete_conversation_endpoint(session_id: str) -> None:
    if not store.delete_conversation(session_id):
        raise HTTPException(status_code=404, detail="No such conversation")


@router.get("/memories", response_model=list[schemas.MemoryView])
def list_memories_endpoint() -> list[schemas.MemoryView]:
    return [schemas.MemoryView(**m) for m in memory_store.list_memories_detailed()]


@router.delete("/memories/{memory_id}", status_code=204, response_model=None)
def delete_memory_endpoint(memory_id: int) -> None:
    if not memory_store.delete_memory(memory_id):
        raise HTTPException(status_code=404, detail="No such memory")


app.include_router(router)
app.include_router(macros_api.router)
app.include_router(voice_api.router)

app.mount(
    "/",
    StaticFiles(directory=Path(__file__).parent / "static", html=True),
    name="static",
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
