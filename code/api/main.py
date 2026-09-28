from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import event
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from database import Base, db_session_basede26, get_db
import crud
import models
import schema
from auth import router as auth_router   # HW3 HTML login pages, kept as-is

# Create the tables in MySQL if they don't exist yet
Base.metadata.create_all(bind=db_session_basede26)

app = FastAPI(title="Clinical Trial Registry API")

# Lets the React app call this API and send its cookie
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-SQL-Count"],
)

# HW3 session cookie support (unchanged)
app.add_middleware(
    SessionMiddleware,
    secret_key="s5825-dev-secret-change-later",
    session_cookie="s5825_session",
    max_age=300,
    https_only=True,
)
app.include_router(auth_router)

PORT_BASE = 8425


# ---------- Counts every SQL statement sent to MySQL (for Part 3) ----------
SQL_COUNT = [0]

@event.listens_for(db_session_basede26, "before_cursor_execute")
def count_sql(conn, cursor, statement, parameters, context, executemany):
    SQL_COUNT[0] += 1


# ---------- Gatekeeper: blocks requests without a valid session ----------
def require_session(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("session_id")
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in")
    s = crud.get_session(db, token)
    if not s:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return s


# ---------- Auth ----------
@app.post("/auth/register")
def register(payload: schema.UserCreate, db: Session = Depends(get_db)):
    try:
        user = crud.create_user(db, payload)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already exists")
    return {"id": user.id, "name": user.name, "email": user.email}


@app.post("/auth/login")
def login(payload: schema.LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    s = crud.create_session(db, user.id)
    response.set_cookie(
        key="session_id",
        value=s.id,          # random opaque token, no user data inside
        httponly=True,
        samesite="lax",
        max_age=30 * 60,
    )
    return {"message": "logged in", "user_id": user.id, "name": user.name}


@app.get("/auth/me")
def me(session=Depends(require_session)):
    return {"logged_in": True, "user_id": session.user_id}


@app.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get("session_id")
    if token:
        crud.delete_session(db, token)
    response.delete_cookie("session_id")
    return {"message": "logged out"}


# ---------- Part 3: N+1 naive vs fixed list endpoints ----------
@app.get("/trials-naive", response_model=list[schema.TrialWithSitesOut])
def trials_naive(response: Response, limit: int = 10, db: Session = Depends(get_db),
                 _s=Depends(require_session)):
    start = SQL_COUNT[0]
    trials = db.query(models.Trial).order_by(models.Trial.id).limit(limit).all()   # 1 query
    result = []
    for t in trials:
        sites = db.query(models.TrialSite).filter(models.TrialSite.trial_id == t.id).all()  # +1 per record
        result.append({
            "id": t.id, "trial_title": t.trial_title, "nct_number": t.nct_number,
            "sites": [{"id": s.id, "site_name": s.site_name, "city": s.city} for s in sites],
        })
    response.headers["X-SQL-Count"] = str(SQL_COUNT[0] - start)
    return result


@app.get("/trials-fixed", response_model=list[schema.TrialWithSitesOut])
def trials_fixed(response: Response, limit: int = 10, db: Session = Depends(get_db),
                 _s=Depends(require_session)):
    start = SQL_COUNT[0]
    trials = (db.query(models.Trial)
                .options(joinedload(models.Trial.sites))   # one JOIN query
                .order_by(models.Trial.id).limit(limit).all())
    response.headers["X-SQL-Count"] = str(SQL_COUNT[0] - start)
    return trials


# ---------- Trials CRUD (all need a valid session) ----------
@app.post("/trials", response_model=schema.TrialOut)
def add_trial(payload: schema.TrialCreate, db: Session = Depends(get_db),
              _s=Depends(require_session)):
    return crud.create_trial(db, payload)


@app.get("/trials", response_model=list[schema.TrialOut])
def list_trials(db: Session = Depends(get_db), _s=Depends(require_session)):
    return crud.get_trials(db)


@app.get("/trials/{trial_id}", response_model=schema.TrialOut)
def get_trial(trial_id: int, db: Session = Depends(get_db), _s=Depends(require_session)):
    trial = crud.get_trial(db, trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial


@app.put("/trials/{trial_id}", response_model=schema.TrialOut)
def edit_trial(trial_id: int, payload: schema.TrialUpdate, db: Session = Depends(get_db),
               _s=Depends(require_session)):
    trial = crud.update_trial(db, trial_id, payload)
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial


@app.delete("/trials/{trial_id}", response_model=schema.TrialOut)
def remove_trial(trial_id: int, db: Session = Depends(get_db), _s=Depends(require_session)):
    trial = crud.delete_trial(db, trial_id)
    if not trial:
        raise HTTPException(status_code=404, detail="Trial not found")
    return trial