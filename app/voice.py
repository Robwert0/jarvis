from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

from app.config import get_settings
from app import memory_store
from app.tools import build_client_tools


def memory_block(memories: list[str]) -> str:
    if not memories:
        return ""
    facts = "\n".join(f"- {m}" for m in memories)
    return "Here's what you should remember about the user:\n" + facts


def _default_factory(settings):
    if not (settings.elevenlabs_api_key and settings.elevenlabs_agent_id):
        raise SystemExit(
            "Missing voice config. Set ELEVENLABS_API_KEY and "
            "ELEVENLABS_AGENT_ID in .env, then rerun."
        )
    client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    return Conversation(
        client,
        settings.elevenlabs_agent_id,
        requires_auth=True,
        audio_interface=DefaultAudioInterface(),
        client_tools=build_client_tools(),
        callback_user_transcript=lambda text: print(f"You:    {text}"),
        callback_agent_response=lambda text: print(f"Jarvis: {text}"),
    )


def run_session(*, settings=None, conversation_factory=None) -> str | None:
    settings = settings or get_settings()
    factory = conversation_factory or _default_factory
    conversation = factory(settings)
    conversation.start_session()
    try:
        block = memory_block(memory_store.list_memories())
        if block:
            conversation.send_contextual_update(block)
        return conversation.wait_for_session_end()
    except KeyboardInterrupt:
        conversation.end_session()
        raise


def main():
    print("Listening — speak to Jarvis. Press Ctrl+C to stop.")
    try:
        conversation_id = run_session()
        print(f"Session ended. Conversation id: {conversation_id}")
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
