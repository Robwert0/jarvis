from elevenlabs.conversational_ai.conversation import ClientTools
from app.launcher import launch
import time


def open_app(params):
    app = (params or {}).get("app", "").strip()
    if not app:
        return "Which app should i open?"
    start = time.perf_counter()
    result = launch(app)
    print(f"[open_app] took {time.perf_counter() - start:.2f}s -> {result!r}")
    return result


def build_client_tools():
    tools = ClientTools()
    tools.register("open_app", open_app)
    return tools