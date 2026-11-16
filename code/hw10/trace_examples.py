"""
HW10 Part 4.2 - capture three example traces and save their trace_ids.

  hit    : a question answered from the semantic cache (asked twice: the first time is a miss)
  miss   : a successful cache miss that completes Planner -> Writer -> Reviewer
  failed : a request where the Writer is made to fail (fault injection) - shows the failing stage + error

Needs Redis, Kafka and the three agents (planner.py, writer.py, reviewer.py) running.
Run from the repo root:   python code/hw10/trace_examples.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
sys.path.insert(0, HERE)

from traced_request import TracedClient  # noqa: E402
from tracing import load_spans, raw_dir, trace_spans  # noqa: E402

Q_MISS = "What questions should I ask the study team before enrolling in a clinical trial?"
Q_FAIL = "How do clinical trial sponsors choose which hospitals will run a study?"


def show(label, trace_id):
    print(f"\n--- {label} trace {trace_id} ---")
    print(f"{'stage':<14}{'duration_ms':>12}  {'status':<7} error")
    for s in trace_spans(trace_id, load_spans()):
        attrs = s.get("attrs") or {}
        extra = f"[{attrs['cache']}]" if "cache" in attrs and s["stage"] == "cache_lookup" else ""
        print(f"{s['stage']:<14}{s['duration_ms']:>12,.1f}  {s['status']:<7} {s['error'] or ''} {extra}")


def main():
    client = TracedClient()
    print("1/3 cache MISS (full agent path) ...")
    miss = client.ask(Q_MISS)
    if miss["cache_hit"]:
        sys.exit("This question is already in the cache. Use a different Q_MISS or reset the cache.")
    print("2/3 same question again -> cache HIT ...")
    hit = client.ask(Q_MISS)
    print("3/3 failed request (Writer fault injection) ...")
    failed = client.ask(Q_FAIL, simulate_failure="writer")

    assert miss["status"] == "ok", miss["error"]
    assert hit["cache_hit"] and hit["status"] == "ok", "expected a cache hit"
    assert failed["status"] == "error", "expected a failed trace"
    show("cache HIT", hit["trace_id"])
    show("cache MISS (success)", miss["trace_id"])
    show("FAILED", failed["trace_id"])
    print(f"\nFailed trace: {failed['error']}")

    os.makedirs(raw_dir(), exist_ok=True)
    with open(os.path.join(raw_dir(), "trace_examples.json"), "w") as f:
        json.dump({"hit": hit, "miss": miss, "failed": failed}, f, indent=2)
    print("Saved trace ids to reports/hw10/raw/trace_examples.json")


if __name__ == "__main__":
    main()
