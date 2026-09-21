from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from starlette.middleware.sessions import SessionMiddleware
from auth import router as auth_router

app = FastAPI(title="Clinical Trial Registry API")

# Allow your webpage (opened as a local file) to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session/cookie support for the login system 
app.add_middleware(
    SessionMiddleware,
    secret_key="s5825-dev-secret-change-later",  # signs the cookie
    session_cookie="s5825_session",                # namespaced with your PREFIX
    max_age=300,                                    # idle timeout: 5 minutes
    https_only=True,                                # sets the Secure flag
)

app.include_router(auth_router)

PORT_BASE = 8425  # SID4 5825 -> 8000 + (5825 mod 900)


# --Pydantic model-Valid trials fields defined with the specific datatypes 

class Trial(BaseModel):    
    trialTitle: str
    nctNumber: str
    submitterEmail: str
    trialDescription: str
    trialPhase: str

#Trial record inserted in the db is assigned with an id as int
class TrialRecord(Trial):
    id: int


# --In-memory store having 2 sample records 

trials_db: list[TrialRecord] = [
    TrialRecord(
        id=1,
        trialTitle="Metformin Extended-Release for Type 2 Diabetes",
        nctNumber="NCT04567890",
        submitterEmail="researcher@sjsu.edu",
        trialDescription="Evaluates efficacy and safety of extended-release metformin in adults with type 2 diabetes over 12 weeks.",
        trialPhase="Phase II",
    ),
    TrialRecord(
        id=2,
        trialTitle="Aspirin Cardioprotective Study",
        nctNumber="NCT04987654",
        submitterEmail="researcher2@sjsu.edu",
        trialDescription="Assesses low-dose aspirin's effect on cardiovascular event rates in older adults.",
        trialPhase="Phase III",
    ),
]

next_id = 3


# --Endpoints- POST,GET,PUT,DELETE

@app.get("/trials")
def list_trials():
    return trials_db


@app.get("/trials/search")
def search_trials(q: str = ""):
    q_lower = q.lower()
    return [
        t for t in trials_db
        if q_lower in t.trialTitle.lower() or q_lower in t.nctNumber.lower()
    ]


@app.post("/trials")
def add_trial(trial: Trial):
    global next_id
    new_record = TrialRecord(id=next_id, **trial.model_dump())
    trials_db.append(new_record)
    next_id += 1
    return {"message": "Trial added", "trial": new_record}


@app.put("/trials/1")
def update_trial_1(trial: Trial):
    for i, t in enumerate(trials_db):
        if t.id == 1:
            trials_db[i] = TrialRecord(id=1, **trial.model_dump())
            return {"message": "Trial 1 updated", "trial": trials_db[i]}
    raise HTTPException(status_code=404, detail="Trial with ID 1 not found")


@app.delete("/trials/highest")
def delete_highest_trial():
    if not trials_db:
        raise HTTPException(status_code=404, detail="No trials to delete")
    highest = max(trials_db, key=lambda t: t.id)
    trials_db.remove(highest)
    return {"message": f"Deleted trial with highest ID ({highest.id})", "trial": highest}