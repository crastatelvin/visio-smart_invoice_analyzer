from dataclasses import dataclass
from time import monotonic
from threading import Lock


@dataclass
class RateState:
    count: int
    window_start: float


class InMemoryStore:
    def __init__(self) -> None:
        self._latest_by_job: dict[str, dict] = {}
        self._rates: dict[str, RateState] = {}
        self._lock = Lock()

    def set_latest(self, job_id: str, payload: dict) -> None:
        with self._lock:
            self._latest_by_job[job_id] = payload

    def get_latest(self, job_id: str) -> dict | None:
        with self._lock:
            return self._latest_by_job.get(job_id)

    def latest_job_id(self) -> str | None:
        with self._lock:
            if not self._latest_by_job:
                return None
            return list(self._latest_by_job.keys())[-1]

    def allow_rate(self, key: str, limit: int, window_seconds: int) -> bool:
        now = monotonic()
        with self._lock:
            state = self._rates.get(key)
            if state is None or now - state.window_start > window_seconds:
                self._rates[key] = RateState(count=1, window_start=now)
                return True
            if state.count >= limit:
                return False
            state.count += 1
            return True
