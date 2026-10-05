import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from sqlalchemy import func
from database import SessionLocal
import models

logging.basicConfig(stream=sys.stderr, level=logging.INFO)  # never stdout
log = logging.getLogger("domain")


def ok(data):
    return {"ok": True, "data": data, "error": None}


def err(message):
    return {"ok": False, "data": None, "error": message}


def search_trials(query, limit=10, db=None):
    if not isinstance(query, str) or not query.strip():
        return err("query must be a non-empty string")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 50:
        return err("limit must be an integer between 1 and 50")
    own = db is None
    db = db or SessionLocal()
    try:
        rows = (db.query(models.Trial)
                  .filter(models.Trial.trial_title.like(f"%{query.strip()}%"))
                  .order_by(models.Trial.id).limit(limit).all())
        return ok([{"id": t.id, "trial_title": t.trial_title,
                    "nct_number": t.nct_number,
                    "available_slots": t.available_slots,
                    "sponsor_id": t.sponsor_id} for t in rows])
    except Exception as e:
        log.error("search_trials failed: %s", e)
        return err(f"database error: {e}")
    finally:
        if own:
            db.close()


def get_trial(trial_id, db=None):
    if not isinstance(trial_id, int) or isinstance(trial_id, bool) or trial_id < 1:
        return err("trial_id must be a positive integer")
    own = db is None
    db = db or SessionLocal()
    try:
        t = db.query(models.Trial).filter(models.Trial.id == trial_id).first()
        if not t:
            return err(f"trial {trial_id} not found")
        sponsor = None
        if t.sponsor_id:
            s = db.query(models.Sponsor).filter(models.Sponsor.id == t.sponsor_id).first()
            if s:
                sponsor = {"id": s.id, "sponsor_name": s.sponsor_name}
        return ok({"id": t.id, "trial_title": t.trial_title,
                   "nct_number": t.nct_number,
                   "available_slots": t.available_slots,
                   "sponsor": sponsor})
    except Exception as e:
        log.error("get_trial failed: %s", e)
        return err(f"database error: {e}")
    finally:
        if own:
            db.close()


def count_trials_by_sponsor(sponsor_id, db=None):
    if not isinstance(sponsor_id, int) or isinstance(sponsor_id, bool) or sponsor_id < 1:
        return err("sponsor_id must be a positive integer")
    own = db is None
    db = db or SessionLocal()
    try:
        s = db.query(models.Sponsor).filter(models.Sponsor.id == sponsor_id).first()
        if not s:
            return err(f"sponsor {sponsor_id} not found")
        count, slots = (db.query(func.count(models.Trial.id),
                                 func.coalesce(func.sum(models.Trial.available_slots), 0))
                          .filter(models.Trial.sponsor_id == sponsor_id).one())
        return ok({"sponsor_id": sponsor_id, "sponsor_name": s.sponsor_name,
                   "trial_count": int(count), "total_available_slots": int(slots)})
    except Exception as e:
        log.error("count_trials_by_sponsor failed: %s", e)
        return err(f"database error: {e}")
    finally:
        if own:
            db.close()