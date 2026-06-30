import pvporcupine
from pvrecorder import PvRecorder

from app.config import get_settings
from app.voice import run_session


def listen_loop(*, access_key, keyword="jarvis", run=run_session,
                porcupine_factory=pvporcupine.create, recorder_factory=PvRecorder):
    porcupine = porcupine_factory(access_key=access_key, keywords=[keyword])
    recorder = recorder_factory(frame_length=porcupine.frame_length, device_index=-1)
    try:
        recorder.start()
        while True:
            if porcupine.process(recorder.read()) >= 0:
                recorder.stop()
                run()
                recorder.start()
    except KeyboardInterrupt:
        pass
    finally:
        recorder.delete()
        porcupine.delete()


def main():
    settings = get_settings()
    if not settings.picovoice_access_key:
        raise SystemExit("Set PICOVOICE_ACCESS_KEY in .env, then rerun.")
    print('Say "Jarvis" to wake me. Press Ctrl+C to quit.')
    listen_loop(access_key=settings.picovoice_access_key)


if __name__ == "__main__":
    main()
