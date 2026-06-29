import threading


class CancelToken:
    def __init__(self):
        self._cancel = threading.Event()
        self._stopped = threading.Event()
        self.progress = ""

    @property
    def cancelled(self):
        return self._cancel.is_set()

    def cancel(self):
        self._cancel.set()

    def set_progress(self, text):
        self.progress = text

    def mark_stopped(self):
        self._stopped.set()

    def wait_stopped(self, timeout):
        return self._stopped.wait(timeout)


_current = None
_lock = threading.Lock()


def begin():
    global _current
    with _lock:
        if _current is not None and not _current._stopped.is_set():
            print(
                "[cancellation] WARNING: starting a new op while one is still "
                "active — single-slot model only tracks the newest."
            )
        _current = CancelToken()
        return _current


def current():
    with _lock:
        return _current


def end(token):
    global _current
    with _lock:
        if _current is token:
            _current = None