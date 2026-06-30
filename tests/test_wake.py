import app.wake as wake


class FakePorcupine:
    def __init__(self, hits):
        self.frame_length = 512
        self._hits = list(hits)   # values process() returns, in order
        self.deleted = False

    def process(self, frame):
        return self._hits.pop(0) if self._hits else -1

    def delete(self):
        self.deleted = True


class FakeRecorder:
    def __init__(self, frame_length, device_index):
        self.events = []
        self.deleted = False

    def start(self):
        self.events.append("start")

    def read(self):
        return [0] * 512

    def stop(self):
        self.events.append("stop")

    def delete(self):
        self.deleted = True


def test_wake_triggers_run_and_cleans_up():
    calls = []

    def fake_run():
        calls.append(1)
        raise KeyboardInterrupt  # simulate the user quitting after one wake

    porc = FakePorcupine([-1, 0])          # no detection, then detect on 2nd frame
    rec = FakeRecorder(512, -1)

    wake.listen_loop(
        access_key="k",
        run=fake_run,
        porcupine_factory=lambda access_key, keywords: porc,
        recorder_factory=lambda frame_length, device_index: rec,
    )

    assert calls == [1]                    # ran exactly once on the wake
    assert rec.events == ["start", "stop"] # exact sequence: start, detect, stop before run
    assert porc.deleted and rec.deleted    # resources released in finally
