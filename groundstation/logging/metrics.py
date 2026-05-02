import threading


class MetricsStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._values: dict[str, int | float] = {}

    def set(self, key: str, value: int | float) -> None:
        with self._lock:
            self._values[key] = value

    def inc(self, key: str, amount: int | float = 1) -> None:
        with self._lock:
            self._values[key] = self._values.get(key, 0) + amount

    def observe(self, key: str, value: float) -> None:
        with self._lock:
            self._values[key] = value

    def get(self, key: str, default=None):
        with self._lock:
            return self._values.get(key, default)

    def snapshot(self) -> dict[str, int | float]:
        with self._lock:
            return dict(self._values)

    def reset(self) -> None:
        with self._lock:
            self._values.clear()


metrics = MetricsStore()
