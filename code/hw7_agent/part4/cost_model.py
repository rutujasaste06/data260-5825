"""HW7 Part 4: deterministic cost model used to cross-check the agent (prices parsed from the snapshot)."""
import re
from collections import defaultdict

import tools


def parse_prices(lines):
    """Read the Bay Wheels prices from the page text; return a dict or None if anything is missing."""
    text = "\n".join(lines)
    month = re.search(r"\$(\d+(?:\.\d+)?)/month", text)
    classic = re.search(r"\$([\d.]+) to unlock, then \$([\d.]+)/min", text)
    ebike = re.search(r"\$([\d.]+) unlock \+ \$([\d.]+)/min", text)
    member_all = re.findall(r"(\d+) min free, then \$([\d.]+)/min", text)
    member_c = max(member_all, key=lambda m: int(m[0])) if member_all else None
    member_e = re.findall(r"Free unlocks \+ \$([\d.]+)/min", text)
    if not (month and classic and ebike and member_c and len(member_e) >= 2):
        return None
    return {"month_fee": float(month.group(1)), "unlock": float(classic.group(1)),
            "classic_per_min": float(classic.group(2)), "ebike_per_min": float(ebike.group(2)),
            "member_free_min": float(member_c[0]), "member_overage_per_min": float(member_c[1]),
            "member_ebike_per_min": float(member_e[1])}


def load_trips(csv_path):
    """Rows (type, started_at, duration_min, week) from the uploaded CSV."""
    db = tools.load_db(csv_path)
    rows = db.execute("SELECT rideable_type, started_at, duration_min, week FROM trips").fetchall()
    db.close()
    return rows


def ride_costs(kind, minutes, p):
    """(pay_per_use, membership_variable) cost of one ride."""
    if kind == "electric_bike":
        return p["unlock"] + p["ebike_per_min"] * minutes, p["member_ebike_per_min"] * minutes
    over = max(minutes - p["member_free_min"], 0)
    return p["unlock"] + p["classic_per_min"] * minutes, p["member_overage_per_min"] * over


def months_in_span(rows):
    """Calendar months from the first to the last ride (inclusive)."""
    first, last = min(r[1] for r in rows), max(r[1] for r in rows)
    return (int(last[:4]) - int(first[:4])) * 12 + int(last[5:7]) - int(first[5:7]) + 1


def weekly_table(rows, p):
    """Per-week ride count, average duration and pay-per-use spend."""
    weeks = defaultdict(list)
    for kind, _, minutes, week in rows:
        weeks[week].append((minutes, ride_costs(kind, minutes, p)[0]))
    return [{"week": w, "rides": len(v), "avg_minutes": round(sum(m for m, _ in v) / len(v), 1),
             "spend": round(sum(c for _, c in v), 2)} for w, v in sorted(weeks.items())]


def compare(csv_path, lines):
    """Full comparison: totals, decision, break-even and weekly table."""
    p = parse_prices(lines)
    if p is None:
        return None
    rows = load_trips(csv_path)
    pay = sum(ride_costs(k, m, p)[0] for k, _, m, _ in rows)
    var = sum(ride_costs(k, m, p)[1] for k, _, m, _ in rows)
    months = months_in_span(rows)
    member = months * p["month_fee"] + var
    saving_per_ride = (pay - var) / len(rows)
    return {"prices": p, "rides": len(rows), "months": months, "pay_per_use_total": round(pay, 2),
            "membership_fee_total": round(months * p["month_fee"], 2), "membership_residual": round(var, 2),
            "membership_total": round(member, 2), "decision": "Buy Monthly Membership" if member < pay else "Pay Per Ride/Minute",
            "rides_per_month_actual": round(len(rows) / months, 1),
            "break_even_rides_per_month": round(p["month_fee"] / saving_per_ride, 1) if saving_per_ride > 0 else None,
            "minutes_per_month_actual": round(sum(m for _, _, m, _ in rows) / months, 1),
            "weekly": weekly_table(rows, p)}
