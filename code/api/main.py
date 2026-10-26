from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

import crud
import models
import schema
from database import Base, db_session_basede26, get_db
from jwt_auth import create_token, get_current_user, require_roles, verify_password

# Create the tables in MySQL if they don't exist yet
Base.metadata.create_all(bind=db_session_basede26)

app = FastAPI(title="Clinical Trial Registry API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-SQL-Count"],
)

PORT_BASE = 8425

# Counts every SQL statement sent to MySQL
SQL_COUNT = [0]


@event.listens_for(db_session_basede26, "before_cursor_execute")
def count_sql(conn, cursor, statement, parameters, context, executemany):
    SQL_COUNT[0] += 1


# ---------- HW7 role gates: reader < writer < moderator ----------
any_role = Depends(get_current_user)
writer_or_mod = Depends(require_roles("writer", "moderator"))
moderator_only = Depends(require_roles("moderator"))


# ---------- Auth (JWT) ----------
class LoginIn(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


@app.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return {"access_token": create_token(user), "token_type": "bearer", "role": user.role}


@app.get("/auth/me")
def me(user=any_role):
    return {"id": user.id, "username": user.username, "role": user.role}


# ---------- Sponsors ----------
@app.post("/sponsors", response_model=schema.SponsorOut, status_code=201)
def add_sponsor(payload: schema.SponsorCreate, db: Session = Depends(get_db),
                _u=writer_or_mod):
    try:
        return crud.create_sponsor(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")


@app.get("/sponsors", response_model=list[schema.SponsorOut])
def list_sponsors(skip: int = 0, limit: int = 20, db: Session = Depends(get_db),
                  _u=any_role):
    return crud.get_sponsors(db, skip, limit)


@app.get("/sponsors/{sponsor_id}", response_model=schema.SponsorOut)
def get_sponsor(sponsor_id: int, db: Session = Depends(get_db), _u=any_role):
    sponsor = crud.get_sponsor(db, sponsor_id)
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    return sponsor


@app.put("/sponsors/{sponsor_id}", response_model=schema.SponsorOut)
def edit_sponsor(sponsor_id: int, payload: schema.SponsorUpdate,
                 db: Session = Depends(get_db), _u=writer_or_mod):
    sponsor = crud.update_sponsor(db, sponsor_id, payload)
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    return sponsor


@app.delete("/sponsors/{sponsor_id}", response_model=schema.SponsorOut)
def remove_sponsor(sponsor_id: int, db: Session = Depends(get_db), _u=moderator_only):
    sponsor, reason = crud.delete_sponsor(db, sponsor_id)
    if reason == "not_found":
        raise HTTPException(status_code=404, detail="Sponsor not found")
    if reason == "has_trials":
        raise HTTPException(
            status_code=409, detail="Cannot delete sponsor: trials are still linked to it"
        )
    return sponsor


@app.get("/sponsors/{sponsor_id}/trials", response_model=list[schema.TrialOut])
def trials_for_sponsor(sponsor_id: int, db: Session = Depends(get_db), _u=any_role):
    sponsor = crud.get_sponsor(db, sponsor_id)
    if not sponsor:
        raise HTTPException(status_code=404, detail="Sponsor not found")
    return crud.get_trials_by_sponsor(db, sponsor_id)


# ---------- N+1 naive vs fixed list endpoints (HW4 Part 3) ----------
@app.get("/trials-naive", response_model=list[schema.TrialWithSitesOut])
def trials_naive(response: Response, limit: int = 10, db: Session = Depends(get_db),
                 _u=any_role):
    start = SQL_COUNT[0]
    trials = db.query(models.Trial).order_by(models.Trial.id).limit(limit).all()
    result = []
    for t in trials:
        sites = db.query(models.TrialSite).filter(models.TrialSite.trial_id == t.id).all()
        result.append({
            "id": t.id, "trial_title": t.trial_title, "nct_number": t.nct_number,
            "sites": [{"id": s.id, "site_name": s.site_name, "city": s.city} for s in sites],
        })
    response.headers["X-SQL-Count"] = str(SQL_COUNT[0] - start)
    return result


@app.get("/trials-fixed", response_model=list[schema.TrialWithSitesOut])
def trials_fixed(response: Response, limit: int = 10, db: Session = Depends(get_db),
                 _u=any_role):
    start = SQL_COUNT[0]
    trials = (db.query(models.Trial)
              .options(joinedload(models.Trial.sites))
              .order_by(models.Trial.id).limit(limit).all())
    response.headers["X-SQL-Count"] = str(SQL_COUNT[0] - start)
    return trials


# ---------- Trials ----------
@app.post("/trials", response_model=schema.TrialOut, status_code=201)
def add_trial(payload: schema.TrialCreate, db: Session = Depends(get_db),
              _u=writer_or_mod):
    return crud.create_trial(db, payload)


@app.get("/trials", response_model=list[schema.TrialOut])
def list_trials(db: Session = Depends(get_db), _u=any_role):
    return crud.get_trials(db)


@app.get("/trials/{trial_id}", response_model=schema.TrialOut)
def get_trial(trial_id: int, db: Session = Depends(get_db), _u=any_role):
    trial = crud.get_trial(db, trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial


@app.put("/trials/{trial_id}", response_model=schema.TrialOut)
def edit_trial(trial_id: int, payload: schema.TrialUpdate, db: Session = Depends(get_db),
               _u=writer_or_mod):
    trial = crud.update_trial(db, trial_id, payload)
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial


@app.delete("/trials/{trial_id}", response_model=schema.TrialOut)
def remove_trial(trial_id: int, db: Session = Depends(get_db), _u=moderator_only):
    trial = crud.delete_trial(db, trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial