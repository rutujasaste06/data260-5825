"""Build and load the fixed verification cases (HW7 Part 2) from the real trials database."""
import json
import os
import re
from collections import Counter

import agent_loop  # noqa: F401  (sets up sys.path for the HW5 tools)
import domain_core as core
import models
from database import SessionLocal

SEED = 5825
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "..", "reports", "hw07", "raw")
CASES_PATH = os.path.join(RAW, "verification_cases.json")
MISSING_ID = 99999999


def _slots(trial_id):
    """Available slots of one trial (used to pick comparable trials)."""
    return core.get_trial(trial_id)["data"]["available_slots"]


def _candidate_terms(db):
    """Frequent title words, most common first."""
    rows = db.query(models.Trial.trial_title).limit(400).all()
    words = Counter(w.lower() for (t,) in rows for w in re.findall(r"[A-Za-z]{6,}", t))
    return [w for w, _ in words.most_common(60)]


def _case_a(term):
    """Case A: search a term, then look up the first result (the sponsor name needs get_trial)."""
    first = core.search_trials(term, 10)["data"][0]
    full = core.get_trial(first["id"])["data"]
    return {"id": "A", "kind": "search_then_detail", "term": term, "first_id": first["id"],
            "nct": full["nct_number"], "title": full["trial_title"],
            "sponsor": full["sponsor"]["sponsor_name"],
            "prompt": (f"Search for clinical trials about '{term}'. Then look up the first result "
                       "in detail and tell me its NCT number and the name of its sponsor.")}


def _different_sponsor_pair(term):
    """Two search results with different sponsors (first such pair), or the first two."""
    rows = core.search_trials(term, 20)["data"]
    for i, x in enumerate(rows):
        for y in rows[i + 1:]:
            if x["sponsor_id"] != y["sponsor_id"]:
                return [x["id"], y["id"]]
    return [r["id"] for r in rows[:2]]


def _case_c(terms):
    """Case C: search, then compare the sponsors of two results with two detail lookups."""
    term = terms[0]
    ids = _different_sponsor_pair(term)
    full = [core.get_trial(i)["data"] for i in ids]
    names = [t["sponsor"]["sponsor_name"] for t in full]
    return {"id": "C", "kind": "compare_two", "term": term, "ids": ids,
            "ncts": [t["nct_number"] for t in full], "sponsors": names,
            "same_sponsor": names[0] == names[1],
            "prompt": (f"Search for clinical trials about '{term}'. Then compare trial {ids[0]} "
                       f"and trial {ids[1]} using get_trial for each one. Give each trial's NCT "
                       "number and sponsor name, and say whether they have the same sponsor.")}


def _case_b(db):
    """Case B: aggregate for the busiest sponsor plus one supporting example trial."""
    from sqlalchemy import func

    row = (db.query(models.Trial.sponsor_id, func.count(models.Trial.id).label("n"))
           .filter(models.Trial.sponsor_id.isnot(None))
           .group_by(models.Trial.sponsor_id).order_by(func.count(models.Trial.id).desc(),
                                                      models.Trial.sponsor_id).first())
    sid = row[0]
    agg = core.count_trials_by_sponsor(sid)["data"]
    t = db.query(models.Trial).filter(models.Trial.sponsor_id == sid).order_by(models.Trial.id).first()
    return {"id": "B", "kind": "aggregate_plus_example", "sponsor_id": sid,
            "sponsor_name": agg["sponsor_name"], "count": agg["trial_count"],
            "example_id": t.id, "example_nct": t.nct_number, "example_title": t.trial_title,
            "prompt": (f"How many trials does sponsor {sid} have in total? Then, as one "
                       f"supporting example, look up trial {t.id} and tell me its title.")}


def _case_e():
    """Case E: error recovery for a nonexistent id."""
    return {"id": "E", "kind": "error_recovery", "missing_id": MISSING_ID,
            "prompt": f"Give me the full details of trial {MISSING_ID}."}


def build_cases():
    """Pick terms and ids from the database and save the four fixed cases."""
    db = SessionLocal()
    terms = [w for w in _candidate_terms(db) if len(core.search_trials(w, 10)["data"]) >= 4]
    term_a = terms[0]
    cases = [_case_a(term_a), _case_b(db), _case_c(terms[1:]), _case_e()]
    db.close()
    os.makedirs(RAW, exist_ok=True)
    with open(CASES_PATH, "w") as f:
        json.dump(cases, f, indent=2)
    return cases


def load_cases():
    """Load the saved fixed cases (build them first if the file is missing)."""
    if not os.path.exists(CASES_PATH):
        return build_cases()
    with open(CASES_PATH) as f:
        return json.load(f)


if __name__ == "__main__":
    for c in build_cases():
        print(c["id"], c["kind"], "->", c["prompt"])
    print("saved", os.path.relpath(CASES_PATH))
