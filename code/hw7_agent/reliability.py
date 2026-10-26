"""20+ attempt reliability run with varied seeds (HW7 Part 2)."""
import csv
import json
import os

import cases
import run_cases

ATTEMPTS = 21  # 7 attempts each for cases A, B, C
RAW = cases.RAW


def classify(run, verdict):
    """Failure classes seen in one attempt (rejected calls plus a lost chain)."""
    found = [i["type"] for i in run["invalid"]]
    if not verdict["chain_ok"]:
        found.append("lost_multistep_chain")
    return found


def attempt_row(i, case):
    """Run one attempt with seed = SEED + i and return a flat row."""
    seed = cases.SEED + i
    rec = run_cases.run_one(case, seed)
    run, v = rec["run"], rec["verdict"]
    clean = not run["invalid"] and v["chain_ok"]  # well-formed on the first try, no repair needed
    return {"attempt": i, "case": case["id"], "seed": seed, "tool_calls": run["tool_calls"],
            "rejected_calls": len(run["invalid"]), "repairs": run["repairs"],
            "stop_reason": run["stop_reason"], "well_formed_before_repair": clean,
            "well_formed_after_repair": v["chain_ok"] and run["stop_reason"] == "completed",
            "task_success": v["success"], "failure_classes": ";".join(classify(run, v)),
            "prompt_tokens": run["prompt_tokens"], "completion_tokens": run["completion_tokens"],
            "latency_ms": run["latency_ms"]}


def summarize(rows):
    """Aggregate rates and failure counts."""
    n = len(rows)
    classes = {}
    for r in rows:
        for c in filter(None, r["failure_classes"].split(";")):
            classes[c] = classes.get(c, 0) + 1
    return {"attempts": n,
            "well_formed_before_repair_rate": round(sum(r["well_formed_before_repair"] for r in rows) / n, 3),
            "well_formed_after_repair_rate": round(sum(r["well_formed_after_repair"] for r in rows) / n, 3),
            "task_success_rate": round(sum(r["task_success"] for r in rows) / n, 3),
            "failure_class_counts": classes}


def main():
    """Run all attempts, save CSV and JSON summary, print the table."""
    os.makedirs(RAW, exist_ok=True)
    run_cases.setup_logging(os.path.join(RAW, "..", "RUN_LOG.txt"))
    fixed = [c for c in cases.load_cases() if c["id"] in ("A", "B", "C")]
    rows = [attempt_row(i, fixed[i % 3]) for i in range(ATTEMPTS)]
    with open(os.path.join(RAW, "part2_reliability_20.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    summary = summarize(rows)
    with open(os.path.join(RAW, "part2_reliability_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("\nRELIABILITY SUMMARY (Rutuja Saste)")
    for k, v in summary.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
