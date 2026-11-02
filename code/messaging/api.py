"""
HW8 Part 1 - FastAPI wrapper

This is the "FastAPI service" the assignment asks for. It exposes
simple HTTP endpoints that, under the hood, send CREATE_TRIAL / GET_TRIAL
requests over Kafka and wait for the worker's response - so from the
assignment's point of view, this FastAPI app plays the role of "the
client or FastAPI service" that talks to the worker only through Kafka
messages, never by calling worker code directly.
"""

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from client import send_request

PORT_BASE = int(os.environ.get("PORT_BASE", 8425))

app = FastAPI(title="HW8 Kafka Trial API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TrialCreateIn(BaseModel):
    trialTitle: str
    nctNumber: str
    trialPhase: str


@app.on_event("startup")
def on_startup():
    print(f"FastAPI server started at http://127.0.0.1:{PORT_BASE}")


@app.post("/trials")
def create_trial(payload: TrialCreateIn):
    response = send_request("CREATE_TRIAL", payload.model_dump())
    if not response.get("success"):
        raise HTTPException(status_code=400, detail=response.get("error"))
    return response


@app.get("/trials/{trial_id}")
def get_trial(trial_id: str):
    response = send_request("GET_TRIAL", {"trial_id": trial_id})
    if not response.get("success"):
        raise HTTPException(status_code=404, detail=response.get("error"))
    return response
