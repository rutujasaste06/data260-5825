"""Build the two acceptance-case CSVs (>= 500 rows each) from the real Bay Wheels trip files (seed 5825)."""
import csv
import json
import os
import random
from datetime import datetime, timedelta

import tools

SEED = 5825
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
FIELDS = ["ride_id", "rideable_type", "started_at", "ended_at", "member_casual"]


def read_valid(path, lo, hi, kind=None):
    """Real rows whose duration is between lo and hi minutes (optionally one bike type)."""
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                d = tools._minutes(r["started_at"], r["ended_at"])
            except (KeyError, ValueError):
                continue
            if lo <= d <= hi and (kind is None or r["rideable_type"] == kind):
                out.append(r)
    return out


def write_csv(path, rows):
    """Write rows with the common columns."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def scenario_heavy(rng):
    """Membership-wins case: 520 real July 2026 rides (all bike types, includes long rides)."""
    rows = read_valid(os.path.join(DATA, "202607-baywheels-tripdata.csv"), 1, 180)
    sample = sorted(rng.sample(rows, 520), key=lambda r: r["started_at"])
    write_csv(os.path.join(DATA, "scenario1_membership_wins.csv"), sample)
    return {"file": "scenario1_membership_wins.csv", "rows": 520, "note": "real rows, real timestamps (July 2026)"}


def scenario_light(rng):
    """Pay-per-use-wins case: 500 real short classic rides (2-15 min) spread out at about 8 rides a month."""
    rows = read_valid(os.path.join(DATA, "202601-baywheels-tripdata.csv"), 2, 15, "classic_bike")
    sample = rng.sample(rows, 500)
    start, out = datetime(2021, 1, 3), []
    for i, r in enumerate(sample):
        dur = tools._minutes(r["started_at"], r["ended_at"])
        t0 = datetime.strptime(r["started_at"][:19], "%Y-%m-%d %H:%M:%S")
        day = start + timedelta(days=int(i * 1900 / 500), hours=t0.hour, minutes=t0.minute, seconds=t0.second)
        out.append({**r, "started_at": day.strftime("%Y-%m-%d %H:%M:%S"),
                    "ended_at": (day + timedelta(minutes=dur)).strftime("%Y-%m-%d %H:%M:%S")})
    write_csv(os.path.join(DATA, "scenario2_pay_per_use_wins.csv"), out)
    return {"file": "scenario2_pay_per_use_wins.csv", "rows": 500,
            "note": "real durations and bike types; dates re-spaced to about 8 rides a month from 2021-01 (synthetic schedule)"}


def main():
    """Create both CSVs and write a README describing how they were built."""
    rng = random.Random(SEED)
    info = [scenario_heavy(rng), scenario_light(rng)]
    raw = os.path.join(DATA, "..", "..", "..", "reports", "hw07", "raw")
    os.makedirs(raw, exist_ok=True)
    with open(os.path.join(raw, "part4_scenarios_built.json"), "w") as f:
        json.dump({"seed": SEED, "scenarios": info}, f, indent=2)
    print("Rutuja Saste - scenarios built:", info)


if __name__ == "__main__":
    main()
