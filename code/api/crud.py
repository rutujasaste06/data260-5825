from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
import secrets

import bcrypt
from sqlalchemy.orm import Session

import models
import schema

SESSION_TTL_MINUTES = 30

# ---------- Sponsors ----------
def create_sponsor(db: Session, payload: schema.SponsorCreate):
    sponsor = models.Sponsor(
        sponsor_name=payload.sponsor_name,
        contact_person=payload.contact_person,
        email=payload.email,
    )
    db.add(sponsor)
    db.commit()
    db.refresh(sponsor)
    return sponsor


def get_sponsors(db: Session, skip: int = 0, limit: int = 20):
    return db.query(models.Sponsor).order_by(models.Sponsor.id.asc()).offset(skip).limit(limit).all()


def get_sponsor(db: Session, sponsor_id: int):
    return db.query(models.Sponsor).filter(models.Sponsor.id == sponsor_id).first()


def update_sponsor(db: Session, sponsor_id: int, payload: schema.SponsorUpdate):
    sponsor = get_sponsor(db, sponsor_id)
    if not sponsor:
        return None
    sponsor.sponsor_name = payload.sponsor_name
    sponsor.contact_person = payload.contact_person
    sponsor.email = payload.email
    db.commit()
    db.refresh(sponsor)
    return sponsor

def delete_sponsor(db: Session, sponsor_id: int):
    sponsor = get_sponsor(db, sponsor_id)
    if not sponsor:
        return None, "not_found"

    # Prevent deletion if any trial still points to this sponsor
    linked_trials = db.query(models.Trial).filter(models.Trial.sponsor_id == sponsor_id).count()
    if linked_trials > 0:
        return None, "has_trials"

    db.delete(sponsor)
    db.commit()
    return sponsor, None


def get_trials_by_sponsor(db: Session, sponsor_id: int):
    return db.query(models.Trial).filter(models.Trial.sponsor_id == sponsor_id).all()

# ---------- Trials ----------
def create_trial(db: Session, payload: schema.TrialCreate):
    trial = models.Trial(
        trial_title=payload.trial_title,
        nct_number=payload.nct_number,
        available_slots=payload.available_slots,
        sponsor_id=payload.sponsor_id,
    )
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
    trial.available_slots = payload.available_slots
    trial.sponsor_id = payload.sponsor_id
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