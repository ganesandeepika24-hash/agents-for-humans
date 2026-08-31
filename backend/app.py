"""
AgentNick backend — FastAPI app.

POST /check   -- runs a real evaluation against the deployed agent for
                 a given scenario, returns any staged cards.
POST /approve -- executes the chosen action for a card option (sends
                 an email via Resend, or acknowledges a link/dismiss
                 option). Built in the next step.
"""

import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from invoke_agent import invoke_agent_for_check
from send_email import send_action_email
from scheduler import start_scheduler

app = FastAPI(title="AgentNick Backend")

# Allow the Lovable frontend (any origin, for hackathon simplicity) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).parent.parent / "AgentNick" / "app" / "AgentNick" / "data"

_SCENARIO_FILES = {
    "tariff": "tariffs.json",
    "trial": "trial.json",
    "card_promo": "card_promo.json",
}


class CheckRequest(BaseModel):
    scenario_type: str
    as_of_date: str = "2026-08-30"


_scheduler = None

@app.on_event("startup")
def on_startup():
    global _scheduler
    _scheduler = start_scheduler()


@app.get("/")
def root():
    return {"status": "AgentNick backend running"}


class ApproveRequest(BaseModel):
    option_label: str
    option_type: str
    email_to: str | None = None
    email_subject: str | None = None
    email_body: str | None = None
    action_url: str | None = None


@app.post("/approve")
def approve(req: ApproveRequest):
    if req.option_type == "email":
        if not req.email_to or not req.email_body:
            raise HTTPException(status_code=400, detail="email_to and email_body required for email options")
        result = send_action_email(
            to=req.email_to,
            subject=req.email_subject or "Action requested",
            body=req.email_body,
        )
        return {"status": "email_sent", "resend_id": result.get("id")}

    if req.option_type == "action_url":
        return {"status": "acknowledged", "action_url": req.action_url}

    if req.option_type in ("dismiss", "remind_later", "reveal_warning", "reveal_comparison"):
        return {"status": "acknowledged", "option_type": req.option_type}

    raise HTTPException(status_code=400, detail=f"Unknown option_type: {req.option_type}")


@app.post("/check")
def check(req: CheckRequest):
    if req.scenario_type not in _SCENARIO_FILES:
        raise HTTPException(status_code=400, detail=f"Unknown scenario_type: {req.scenario_type}")

    data_path = DATA_DIR / _SCENARIO_FILES[req.scenario_type]
    with open(data_path) as f:
        raw_data = json.load(f)

    result = invoke_agent_for_check(
        scenario_type=req.scenario_type,
        raw_data=raw_data,
        as_of_date=req.as_of_date,
    )

    return {"cards": result["cards"], "summary_text": result["full_text"]}
