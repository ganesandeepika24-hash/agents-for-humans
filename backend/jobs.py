"""
jobs.py

In-memory job tracking for long-running /check calls. Lets /check
return immediately with a job_id, while the actual agent invocation
runs in a background thread -- works around GitHub Codespaces' own
port-forwarding tunnel enforcing a shorter request timeout than our
backend's own (180s) timeout for the agent call itself.
"""

import threading
import uuid

_jobs: dict[str, dict] = {}
_lock = threading.Lock()


def create_job() -> str:
    job_id = str(uuid.uuid4())
    with _lock:
        _jobs[job_id] = {"status": "running", "result": None, "error": None}
    return job_id


def complete_job(job_id: str, result: dict):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id] = {"status": "done", "result": result, "error": None}


def fail_job(job_id: str, error: str):
    with _lock:
        if job_id in _jobs:
            _jobs[job_id] = {"status": "error", "result": None, "error": error}


def get_job(job_id: str) -> dict | None:
    with _lock:
        return _jobs.get(job_id)
