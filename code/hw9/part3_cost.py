"""
HW9 Part 3.4 - cost model and threshold choice.

Total cost at a threshold = (cache misses x MISS_COST) + (false hits x FALSE_HIT_COST).
Every query that is not a hit runs the HW8 agent, so misses = 40 - hits.

The two costs are stated assumptions (not measured) - see the report for the justification:
  MISS_COST      $0.01  one agent run = an embedding plus two LLM calls (Planner, Writer),
                        about what a hosted model would charge for ~1k tokens each.
  FALSE_HIT_COST $5.00  a wrong answer reaches a patient or coordinator and needs a
                        support follow-up: about 10 minutes of staff time at ~$30/hour.

Run from the repo root:   python code/hw9/part3_cost.py
"""

import json
import os

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reports", "hw09", "raw")
MISS_COST = 0.01
FALSE_HIT_COST = 5.00


def main():
    with open(os.path.join(RAW_DIR, "part3_sweep.json")) as f:
        sweep = json.load(f)

    total_cases = len(sweep["cases"])
    print(f"=== Part 3.4 cost model (miss = ${MISS_COST:.2f}, false hit = ${FALSE_HIT_COST:.2f}) ===\n")
    print("Threshold  Hit rate  False-hit rate  Mean latency (ms)  Misses  False hits  Total cost")
    rows = []
    for t in sweep["table"]:
        misses = total_cases - t["hits"]
        cost = misses * MISS_COST + t["false_hits"] * FALSE_HIT_COST
        rows.append({**t, "misses": misses, "total_cost": cost})
        print(f"  {t['threshold']:.2f}     {t['hit_rate_percent']:>5.1f}%     {t['false_hit_rate_percent']:>5.1f}%"
              f"          {t['mean_latency_ms']:>10.1f}      {misses:>3}       {t['false_hits']:>3}"
              f"      ${cost:>6.2f}")

    best = min(rows, key=lambda r: r["total_cost"])
    print(f"\nLowest total cost: threshold {best['threshold']:.2f} (${best['total_cost']:.2f})")

    # How sure is that choice? 0.95 vs 0.85: 0.95 has more misses but fewer false hits.
    a = next(r for r in rows if r["threshold"] == 0.85)
    b = next(r for r in rows if r["threshold"] == 0.95)
    extra_misses = b["misses"] - a["misses"]
    saved_false = a["false_hits"] - b["false_hits"]
    ratio = extra_misses / saved_false
    print(f"0.95 beats 0.85 whenever one false hit costs more than {ratio:.1f}x one miss "
          f"(assumed ratio here: {FALSE_HIT_COST / MISS_COST:.0f}x).")

    with open(os.path.join(RAW_DIR, "part3_cost.json"), "w") as f:
        json.dump({"miss_cost": MISS_COST, "false_hit_cost": FALSE_HIT_COST, "rows": rows}, f, indent=2)
    print("\nSaved details to reports/hw09/raw/part3_cost.json")


if __name__ == "__main__":
    main()
