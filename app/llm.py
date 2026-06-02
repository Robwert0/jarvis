import anthropic
from anthropic.types import MessageParam

from functools import lru_cache

from app.config import Settings, get_settings

DEFAULT_SYSTEM = (
    "You are Jarvis, a concise and capable personal assistant. "
      "Answer directly. Skip preamble."
)

@lru_cache
def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_settings().anthropic_api_key)

def chat(
        message: str,
        *,
        system: str | None = None,
        client: anthropic.Anthropic | None = None,
        settings: Settings | None = None,
) -> anthropic.types.Message:
    client = client or get_client()
    settings = settings or get_settings()
    messages: list[MessageParam] = [{"role": "user", "content": message}]

    return client.messages.create(
        model=settings.anthropic_model,
        max_tokens=settings.max_tokens,
        system=system or DEFAULT_SYSTEM,
        messages=messages,
        stream=False,
    )

def extract_text(response: anthropic.types.Message) -> str:
    return "".join(block.text for block in response.content if block.type == "text")