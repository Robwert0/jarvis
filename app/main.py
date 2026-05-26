import anthropic
from fastapi import Depends, FastAPI, HTTPException

from app.config import Settings, get_settings
from app.llm import chat, extract_text
from app.schemas import ChatRequest, ChatResponse

app = FastAPI(title="Jarvis", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    req: ChatRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    try:
        response = chat(req.message, system=req.system, settings=settings)
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message) from e
    except anthropic.APIConnectionError as e:
        raise HTTPException(status_code=503, detail="Upstream connection failed") from e

    return ChatResponse(
        reply=extract_text(response),
        model=response.model,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
    )
