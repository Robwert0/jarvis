import signal

from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import Conversation
from elevenlabs.conversational_ai.default_audio_interface import DefaultAudioInterface

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    if not (settings.elevenlabs_api_key and settings.elevenlabs_agent_id):
        raise SystemExit(
            "Missing voice config. Set ELEVENLABS_API_KEY and "
            "ELEVENLABS_AGENT_ID in .env, then rerun."
        )

    client = ElevenLabs(api_key=settings.elevenlabs_api_key)
    conversation = Conversation(
        client,
        settings.elevenlabs_agent_id,
        requires_auth=True,
        audio_interface=DefaultAudioInterface(),
        callback_user_transcript=lambda text: print(f"You:    {text}"),
        callback_agent_response=lambda text: print(f"Jarvis: {text}"),
    )

    conversation.start_session()
    print("Listening — speak to Jarvis. Press Ctrl+C to stop.")

    signal.signal(signal.SIGINT, lambda *_: conversation.end_session())

    conversation_id = conversation.wait_for_session_end()
    print(f"Session ended. Conversation id: {conversation_id}")


if __name__ == "__main__":
    main()
