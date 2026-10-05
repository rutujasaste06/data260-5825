import csv
import json
import os
import statistics
import sys
import time

import domain_core as core
from resilience import call_with_retry, FlakyInjector, ScriptedInjector

SID4 = 5825
VERIFY_SEED = 260000 + SID4          # 265825
RATES = [0.0, 0.2, 0.5]
CALLS_PER_RATE = 50
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reports", "hw05", "raw")
os.makedirs(OUT, exist_ok=True)


def demo(title, outcomes):
    print(f"\n=== DEMO: {title} ===")
    inj = ScriptedInjector(outcomes)
    t0 = time.perf_counter()
    result, attempts = call_with_retry(inj.wrap(core.get_trial), 1)
    ms = (time.perf_counter() - t0) * 1000
    print(f"outcomes script : {outcomes}  (True = injected failure)")
    print(f"attempts used   : {attempts}")
    print(f"latency (ms)    : {ms:.1f}")
    print(f"result ok       : {result['ok']}")
    print(f"error           : {result['error']}")


def percentile(values, p):
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(round(p / 100 * len(s) + 0.5)) - 1))
    return s[k]


def run_rate(rate):
    inj = FlakyInjector(rate, VERIFY_SEED)
    flaky_get_trial = inj.wrap(core.get_trial)
    rows = []
    for i in range(1, CALLS_PER_RATE + 1):
        t0 = time.perf_counter()
        result, attempts = call_with_retry(flaky_get_trial, 1)
        ms = (time.perf_counter() - t0) * 1000
        rows.append({
            "failure_rate": rate, "call_no": i, "attempts": attempts,
            "ok": result["ok"], "latency_ms": round(ms, 2),
            "error": result["error"] or "",
        })
    return rows


def main():
    print(f"VERIFY_SEED = {VERIFY_SEED}")
    demo("success on the first attempt", [False])
    demo("failure first, success after retry", [True, False])
    demo("failure after all retries (clean error)", [True, True, True, True])

    all_rows, summary = [], []
    for rate in RATES:
        rows = run_rate(rate)
        all_rows.extend(rows)
        lat = [r["latency_ms"] for r in rows]
        succ = sum(1 for r in rows if r["ok"]) / len(rows) * 100
        summary.append({
            "injected_failure_rate": f"{int(rate * 100)}%",
            "success_rate_pct": round(succ, 1),
            "mean_latency_ms": round(statistics.mean(lat), 2),
            "p99_latency_ms": round(percentile(lat, 99), 2),
        })

    with open(os.path.join(OUT, "fault_injection_150.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        w.writeheader()
        w.writerows(all_rows)
    with open(os.path.join(OUT, "fault_injection_summary.json"), "w") as f:
        json.dump({"verify_seed": VERIFY_SEED, "summary": summary}, f, indent=2)

    print("\n| Injected failure rate | Success rate | Mean latency (ms) | p99 latency (ms) |")
    print("|---|---|---|---|")
    for s in summary:
        print(f"| {s['injected_failure_rate']} | {s['success_rate_pct']}% | "
              f"{s['mean_latency_ms']} | {s['p99_latency_ms']} |")
    print(f"\nrows written: {len(all_rows)} (expected 150)")


if __name__ == "__main__":
    main()