from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, description="User message to send to Jarvis"
    )
    session_id: str | None = Field(
        default=None, description="Existing conversation id; omit to start a new one"
    )
    system: str | None = Field(default=None, description="Optional system prompt override")


class ActionView(BaseModel):
    tool: str
    summary: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    updated_at: str


class Message(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    reply: str
    session_id: str
    model: str
    input_tokens: int
    output_tokens: int
    actions: list[ActionView] = []