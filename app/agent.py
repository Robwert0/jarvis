from collections.abc import Sequence
from dataclasses import dataclass, field

from app import llm, memory_store, tools

TOOL_GUIDANCE = (
    "You can take real actions with tools. When the user asks to open an app, "
    "call open_app. When they ask to open a named environment/setup, call "
    "run_macro. When they ask to stop something in progress, call cancel_action. "
    "When you learn a durable fact about the user worth recalling in future "
    "conversations, call remember with a short statement of that fact."
)

TOOLS = [
    {
        "name": "open_app",
        "description": "Open an application on the user's computer by name.",
        "input_schema": {
            "type": "object",
            "properties": {"app": {"type": "string", "description": "App name."}},
            "required": ["app"],
        },
    },
    {
        "name": "run_macro",
        "description": "Run a saved macro that opens a group of apps.",
        "input_schema": {
            "type": "object",
            "properties": {"macro": {"type": "string", "description": "Macro name."}},
            "required": ["macro"],
        },
    },
    {
        "name": "cancel_action",
        "description": "Cancel the action currently in progress.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "remember",
        "description": "Store a durable fact about the user for future conversations.",
        "input_schema": {
            "type": "object",
            "properties": {"fact": {"type": "string", "description": "The fact."}},
            "required": ["fact"],
        },
    },
]


def _remember(params):
    fact = (params or {}).get("fact", "").strip()
    if fact:
        memory_store.remember(fact)
    return "Got it — I'll remember that."


DISPATCH = {
    "open_app": tools.open_app,
    "run_macro": tools.run_macro,
    "cancel_action": tools.cancel_action,
    "remember": _remember,
}


@dataclass
class ActionEvent:
    tool: str
    input: dict
    result: str


@dataclass
class AgentResult:
    reply: str
    actions: list[ActionEvent] = field(default_factory=list)
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


def _system(memories):
    system = llm.DEFAULT_SYSTEM + "\n\n" + TOOL_GUIDANCE
    if memories:
        facts = "\n".join(f"- {m}" for m in memories)
        system += "\n\nWhat you remember about the user:\n" + facts
    return system


def run_agent(history, user_message, *, memories: Sequence[str] = (), settings=None, client=None, max_steps=8):
    settings = settings or llm.get_settings()
    client = client or llm.get_client()
    system = _system(memories)
    messages = [*history, {"role": "user", "content": user_message}]
    actions = []
    in_tok = out_tok = 0
    model = settings.anthropic_model

    for _ in range(max_steps):
        resp = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.max_tokens,
            system=system,
            tools=TOOLS,
            messages=messages,
        )
        in_tok += resp.usage.input_tokens
        out_tok += resp.usage.output_tokens
        model = resp.model
        if resp.stop_reason != "tool_use":
            return AgentResult(llm.extract_text(resp), actions, model, in_tok, out_tok)
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for block in resp.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            fn = DISPATCH.get(block.name)
            if fn is None:
                result = f"Unknown tool: {block.name}"
            else:
                try:
                    result = fn(dict(block.input))
                except Exception as exc:
                    result = f"Tool {block.name} raised an error: {exc}"
            actions.append(ActionEvent(block.name, dict(block.input), result))
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": result}
            )
        messages.append({"role": "user", "content": results})

    return AgentResult(
        "I stopped after several tool steps without finishing.", actions, model, in_tok, out_tok
    )
