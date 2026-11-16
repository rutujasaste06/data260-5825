"""
HW10 Part 3.2 and 3.3 - validate the judge against the hand labels.

Refuses to run unless eval_cases.json and human_labels.csv are complete AND already committed
(the labels must be frozen before any judge score exists).
Runs the judge (Writer Helpfulness criterion, same settings every time) on the same 20 drafts
3 times. Run 1 is the 3.2 comparison (Spearman, mean absolute difference); runs 1-3 give the 3.3
repeatability numbers. Raw per-case data goes to reports/hw10/raw/judge_validation.json.
It saves after every score, so if you stop it, running it again continues.

Run from the repo root:   python code/hw10/validate_judge.py
"""

import csv
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
sys.path.insert(0, HERE)

import judge_stats  # noqa: E402
from judge import SETTINGS, run_judge  # noqa: E402
from tracing import raw_dir  # noqa: E402

RUNS = 3
CASES = os.path.join(HERE, "eval_cases.json")
LABELS = os.path.join(HERE, "human_labels.csv")
OUT = os.path.join(raw_dir(), "judge_validation.json")


def check_frozen():
    for path in (CASES, LABELS):
        name = os.path.relpath(path, os.path.join(HERE, "..", ".."))
        log = subprocess.run(["git", "log", "--oneline", "-1", "--", path], capture_output=True, text=True,
                             cwd=HERE).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", path], capture_output=True, text=True,
                               cwd=HERE).stdout.strip()
        if not log or dirty:
            sys.exit(f"STOP: {name} is not committed yet (or has changes). Commit eval_cases.json and "
                     f"human_labels.csv first, then run this again.")


def load_inputs():
    with open(CASES) as f:
        cases = json.load(f)
    with open(LABELS, newline="") as f:
        labels = {row["case_id"]: row["human_label"] for row in csv.DictReader(f)}
    if sorted(labels) != sorted(c["case_id"] for c in cases) or not all(v in "12345" for v in labels.values()):
        sys.exit("STOP: human_labels.csv must hold one label (1-5) for each of the 20 cases.")
    return cases, {k: int(v) for k, v in labels.items()}


def main():
    check_frozen()
    cases, labels = load_inputs()
    if os.path.exists(OUT):
        with open(OUT) as f:
            data = json.load(f)
    else:
        data = {"settings": SETTINGS, "cases": [
            {"case_id": c["case_id"], "question": c["question"], "draft": c["draft"],
             "human": labels[c["case_id"]], "runs": []} for c in cases]}

    for run in range(RUNS):
        for case in data["cases"]:
            if len(case["runs"]) > run:
                continue
            result = run_judge("helpfulness", case["question"], case["draft"])
            case["runs"].append({k: result[k] for k in ("score", "raw", "reason", "error", "seconds")})
            print(f"run {run + 1}/{RUNS}  {case['case_id']}  human={case['human']}  judge={result['score']}"
                  + (f"  ERROR {result['error']}" if result["error"] else ""))
            os.makedirs(raw_dir(), exist_ok=True)
            with open(OUT, "w") as f:
                json.dump(data, f, indent=2)

    stats = judge_stats.compute(data)
    print("\n=== 3.2 Judge vs human labels (run 1) ===")
    print(f"cases used: {stats['n_usable']} of {stats['n_cases']}")
    rho = stats.get("spearman_rho")
    print("Spearman correlation: " + ("undefined (judge gave the same score every time)" if rho is None
          else f"{rho:.3f} (p = {stats['spearman_p']:.4f})"))
    print(f"Mean absolute difference: {stats['mean_abs_diff']:.2f}")
    rep = stats["repeat"]
    print("\n=== 3.3 Repeatability (3 runs, same settings) ===")
    print(f"judge settings: {SETTINGS}")
    print(f"cases whose score changed in any run: {rep['cases_with_any_change']} of {rep['n_cases']} "
          f"({rep['pct_cases_changed']:.0f}%)")
    print(f"mean absolute change: {rep['mean_abs_change']:.2f}   maximum absolute change: "
          f"{rep['max_abs_change']}")
    print("\nSaved raw data to reports/hw10/raw/judge_validation.json")


if __name__ == "__main__":
    main()
