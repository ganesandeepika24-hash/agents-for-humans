"""
jobs.py

Persistent (SQLite-backed) job tracking for long-running /check,
/submit-data, /upload-document calls. Previously in-memory, which
turned out to be unsafe -- Replit's free tier can restart/recycle the
backend process, silently losing any in-flight job state. SQLite
survives that.
"""

import sqlite3
import json
import uuid
from pathlib import Path

_DB_PATH = Path(__file__).parent / "jobs.db"


def _get_connection():
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            result_json TEXT,
            error TEXT
        )
    """)
    return conn


def create_job() -> str:
    job_id = str(uuid.uuid4())
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO jobs (job_id, status, result_json, error) VALUES (?, 'running', NULL, NULL)",
            (job_id,),
        )
        conn.commit()
    finally:
        conn.close()
    return job_id


def complete_job(job_id: str, result: dict):
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE jobs SET status = 'done', result_json = ? WHERE job_id = ?",
            (json.dumps(result), job_id),
        )
        conn.commit()
    finally:
        conn.close()


def fail_job(job_id: str, error: str):
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE jobs SET status = 'error', error = ? WHERE job_id = ?",
            (error, job_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_job(job_id: str) -> dict | None:
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT status, result_json, error FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        if row is None:
            return None
        status, result_json, error = row
        return {
            "status": status,
            "result": json.loads(result_json) if result_json else None,
            "error": error,
        }
    finally:
        conn.close()
