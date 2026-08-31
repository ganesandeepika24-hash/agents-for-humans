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


@app.get("/")
def root():
    return {"status": "AgentNick backend running"}


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
