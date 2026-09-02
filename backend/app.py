"""
AgentNick backend — FastAPI app.

POST /login    -- email-based session (no OAuth, no password; see README)
POST /check    -- runs a real evaluation for a scenario, for the
                   logged-in user; records any cards in the persistent
                   per-user store.
POST /approve  -- executes the chosen action for a card option; marks
                   the underlying signal resolved on success.
POST /subscribe -- registers a push subscription for the logged-in user.
"""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from invoke_agent import invoke_agent_for_check
from send_email import send_action_email
from scheduler import start_scheduler, pause as pause_scheduler, resume as resume_scheduler, is_paused
from push_notifications import add_subscription, send_push_to_user
from users import login as do_login, get_user_id_from_token
from cards import record_notification, mark_resolved, get_pending_cards_for_user, get_card_by_signal
from user_settings import get_threshold, set_threshold
from jobs import create_job, complete_job, fail_job, get_job
import threading

app = FastAPI(title="AgentNick Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: scope to the real frontend origin once finalized
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

DATA_DIR = Path(__file__).parent.parent / "AgentNick" / "app" / "AgentNick" / "data"
_SCENARIO_FILES = {
    "tariff": "tariffs.json",
    "trial": "trial.json",
    "card_promo": "card_promo.json",
    "card_promo_incomplete": "card_promo_incomplete.json",  # deliberately missing data, for testing request_missing_data
}


def require_user(authorization: str | None = Header(default=None)) -> str:
    """Extracts and validates a session token from the Authorization header
    (expected format: "Bearer <token>"). Raises 401 if missing/invalid."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization[len("Bearer "):]
    user_id = get_user_id_from_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session token")
    return user_id


_scheduler = None

@app.on_event("startup")
def on_startup():
    global _scheduler
    _scheduler = start_scheduler()


@app.get("/")
def root():
    return {"status": "AgentNick backend running"}


class LoginRequest(BaseModel):
    email: str


@app.post("/login")
def login(req: LoginRequest):
    if "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email")
    result = do_login(req.email)
    return result


@app.post("/scheduler/pause")
def scheduler_pause():
    pause_scheduler()
    return {"status": "paused"}


@app.post("/scheduler/resume")
def scheduler_resume():
    resume_scheduler()
    return {"status": "resumed"}


@app.get("/scheduler/status")
def scheduler_status():
    return {"paused": is_paused()}


@app.get("/vapid-public-key")
def vapid_public_key():
    return {"key": os.environ.get("VAPID_PUBLIC_KEY", "")}


@app.post("/subscribe")
def subscribe(subscription: dict, user_id: str = Depends(require_user)):
    add_subscription(user_id, subscription)
    return {"status": "subscribed"}


@app.post("/test-push")
def test_push(user_id: str = Depends(require_user)):
    send_push_to_user(user_id, title="AgentNick Test", body="This is a real push notification!")
    return {"status": "push_sent"}


class ApproveRequest(BaseModel):
    signal_id: str
    option_label: str
    option_type: str
    email_to: str | None = None
    email_subject: str | None = None
    email_body: str | None = None
    action_url: str | None = None


@app.post("/approve")
def approve(req: ApproveRequest, user_id: str = Depends(require_user)):
    if req.option_type == "email":
        if not req.email_to or not req.email_body:
            raise HTTPException(status_code=400, detail="email_to and email_body required for email options")
        # mailto: link returned instead of sending "as" the user -- see
        # README for why (real providers are unlikely to honor a
        # cancellation email that didn't come from the customer's own
        # verified address).
        mailto = f"mailto:{req.email_to}?subject={req.email_subject or ''}&body={req.email_body}"
        mark_resolved(user_id, req.signal_id)
        return {"status": "draft_ready", "mailto_url": mailto}

    if req.option_type == "action_url":
        # External action the agent can't complete itself -- acknowledged,
        # not resolved, since the user still has to go complete it.
        return {"status": "acknowledged", "action_url": req.action_url}

    if req.option_type in ("dismiss", "remind_later"):
        mark_resolved(user_id, req.signal_id)
        return {"status": "acknowledged", "option_type": req.option_type}

    if req.option_type in ("reveal_warning", "reveal_comparison"):
        return {"status": "acknowledged", "option_type": req.option_type}

    raise HTTPException(status_code=400, detail=f"Unknown option_type: {req.option_type}")


class CheckRequest(BaseModel):
    scenario_type: str
    as_of_date: str = "2026-08-30"


def _run_check_job(job_id: str, user_id: str, scenario_type: str, as_of_date: str):
    try:
        data_path = DATA_DIR / _SCENARIO_FILES[scenario_type]
        with open(data_path) as f:
            raw_data = json.load(f)

        user_threshold = get_threshold(user_id)
        result = invoke_agent_for_check(
            scenario_type=scenario_type,
            raw_data=raw_data,
            as_of_date=as_of_date,
            threshold_min_gbp=user_threshold.get("min_gbp"),
            threshold_min_pct=user_threshold.get("min_pct"),
        )

        frozen_cards = []
        for card in result.get("cards", []):
            signal_id = card.get("signal_id")
            if not signal_id:
                frozen_cards.append(card)
                continue
            existing = get_card_by_signal(user_id, signal_id)
            if existing is not None:
                if existing.get("status") != "resolved":
                    frozen_cards.append(existing)
                continue
            record_notification(user_id, signal_id, card)
            frozen_cards.append(card)

        complete_job(job_id, {"cards": frozen_cards, "summary_text": result["full_text"]})
    except Exception as e:
        fail_job(job_id, f"{type(e).__name__}: {e}")


@app.post("/check")
def check(req: CheckRequest, user_id: str = Depends(require_user)):
    """Starts a check job and returns immediately with a job_id, instead
    of blocking -- works around Codespaces' tunnel enforcing a shorter
    timeout than the agent call can take. Poll GET /check-status/{job_id}
    for the result."""
    if req.scenario_type not in _SCENARIO_FILES:
        raise HTTPException(status_code=400, detail=f"Unknown scenario_type: {req.scenario_type}")

    job_id = create_job()
    thread = threading.Thread(
        target=_run_check_job,
        args=(job_id, user_id, req.scenario_type, req.as_of_date),
        daemon=True,
    )
    thread.start()
    return {"job_id": job_id, "status": "running"}


@app.get("/check-status/{job_id}")
def check_status(job_id: str, user_id: str = Depends(require_user)):
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job["status"] == "error":
        raise HTTPException(status_code=503, detail=job["error"])
    return job


@app.get("/pending-cards")
def pending_cards(user_id: str = Depends(require_user)):
    """Returns previously-found cards still awaiting user action, without
    re-invoking the agent -- useful for a fast initial page load."""
    return {"cards": get_pending_cards_for_user(user_id)}


class ThresholdRequest(BaseModel):
    min_gbp: float | None = None
    min_pct: float | None = None


@app.get("/settings/threshold")
def get_threshold_endpoint(user_id: str = Depends(require_user)):
    return get_threshold(user_id)


@app.post("/settings/threshold")
def set_threshold_endpoint(req: ThresholdRequest, user_id: str = Depends(require_user)):
    set_threshold(user_id, req.min_gbp, req.min_pct)
    return {"status": "saved", **get_threshold(user_id)}
