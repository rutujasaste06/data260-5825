"""HW7 data prep: link trials that have no sponsor to the existing sponsors (seed 5825)."""
import random

import agent_loop  # noqa: F401  (sets up sys.path for the HW5 code)
import models
from database import SessionLocal

SEED = 5825


def link_sponsors():
    """Assign a sponsor to every trial with sponsor_id NULL; return the counts per sponsor."""
    db = SessionLocal()
    ids = [s.id for s in db.query(models.Sponsor).order_by(models.Sponsor.id)]
    rng = random.Random(SEED)
    todo = db.query(models.Trial).filter(models.Trial.sponsor_id.is_(None)).order_by(models.Trial.id)
    for trial in todo:
        trial.sponsor_id = rng.choices(ids, weights=[5, 3, 2][: len(ids)])[0]
    db.commit()
    counts = {i: db.query(models.Trial).filter(models.Trial.sponsor_id == i).count() for i in ids}
    db.close()
    return counts


if __name__ == "__main__":
    print("Rutuja Saste - trials per sponsor after linking:", link_sponsors())
