"""In-memory job store.

Good enough for a single-process demo. The spec allows in-memory or SQLite;
in-memory keeps the dependency list short and the README simpler. If we needed
persistence across restarts or horizontal scale, swap this for SQLite + a
thread lock (or Redis) — the rest of the app talks to it through this interface.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from app.models.api import JobState
from app.models.mto import MTO


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Job:
    job_id: str
    filename: str
    state: JobState = JobState.PENDING
    message: Optional[str] = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    mto: Optional[MTO] = None


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, filename: str) -> Job:
        job_id = uuid.uuid4().hex
        job = Job(job_id=job_id, filename=filename)
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def update(
        self,
        job_id: str,
        *,
        state: Optional[JobState] = None,
        message: Optional[str] = None,
        mto: Optional[MTO] = None,
    ) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if state is not None:
                job.state = state
            if message is not None:
                job.message = message
            if mto is not None:
                job.mto = mto
            job.updated_at = _now()
            return job


# Single shared instance — FastAPI app reuses this across requests.
_store = JobStore()


def get_job_store() -> JobStore:
    return _store
