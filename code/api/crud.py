from datetime import datetime, timedelta
import secrets

import bcrypt
from sqlalchemy.orm import Session

import models
import schema

SESSION_TTL_MINUTES = 30


# ---------- Trials ----------
def create_trial(db: Session, payload: schema.TrialCreate):
    trial = models.Trial(trial_title=payload.trial_title, nct_number=payload.nct_number)
    db.add(trial)
    db.commit()
    db.refresh(trial)
    return trial


def get_trials(db: Session):
    return db.query(models.Trial).order_by(models.Trial.id.asc()).all()


def get_trial(db: Session, trial_id: int):
    return db.query(models.Trial).filter(models.Trial.id == trial_id).first()


def update_trial(db: Session, trial_id: int, payload: schema.TrialUpdate):
    trial = get_trial(db, trial_id)
    if not trial:
        return None
    trial.trial_title = payload.trial_title
    trial.nct_number = payload.nct_number
    db.commit()
    db.refresh(trial)
    return trial


def delete_trial(db: Session, trial_id: int):
    trial = get_trial(db, trial_id)
    if not trial:
        return None
    db.delete(trial)
    db.commit()
    return trial


# ---------- Users ----------
def create_user(db: Session, payload: schema.UserCreate):
    hashed = bcrypt.hashpw(payload.password.encode(), bcrypt.gensalt()).decode()
    user = models.User(name=payload.name, email=payload.email, password_hash=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return None
    if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return None
    return user


# ---------- Sessions ----------
def create_session(db: Session, user_id: int):
    token = secrets.token_hex(32)
    expires = datetime.utcnow() + timedelta(minutes=SESSION_TTL_MINUTES)
    row = models.SessionToken(id=token, user_id=user_id, expires_at=expires)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_session(db: Session, token: str):
    s = db.query(models.SessionToken).filter(models.SessionToken.id == token).first()
    if not s:
        return None
    if s.expires_at < datetime.utcnow():
        db.delete(s)
        db.commit()
        return None
    return s


def delete_session(db: Session, token: str):
    s = db.query(models.SessionToken).filter(models.SessionToken.id == token).first()
    if not s:
        return False
    db.delete(s)
    db.commit()
    return True