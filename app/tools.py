from elevenlabs.conversational_ai.conversation import ClientTools
from app.launcher import launch
from app.cancellation import current
import time

CANCEL_WAIT_TIMEOUT = 5.0


def open_app(params):
    app = (params or {}).get("app", "").strip()
    if not app:
        return "Which app should i open?"
    start = time.perf_counter()
    result = launch(app)
    print(f"[open_app] took {time.perf_counter() - start:.2f}s -> {result!r}")
    return result


def cancel_action(params):
    token = current()
    if token is None or token.cancelled:
        return "There's nothing running to cancel."

    token.cancel()
    if token.wait_stopped(timeout=CANCEL_WAIT_TIMEOUT):
        return f"Stopped. {token.progress}"
    return "Cancellation requested, but it hasn't stopped yet."


def build_client_tools():
    tools = ClientTools()
    tools.register("open_app", open_app)
    tools.register("cancel_action", cancel_action)
    return tools
