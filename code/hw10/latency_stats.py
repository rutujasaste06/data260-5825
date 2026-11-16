"""
HW10 Part 4.3 - per-stage latency (p50, p95) and each stage's share of cache-miss end-to-end time,
computed from the spans in reports/hw10/raw/spans.jsonl.

Queue wait (total) = queue_inbox + queue_tasks + queue_drafts + queue_final (time messages waited in Kafka).
% of end-to-end = total time spent in the stage / total end-to-end time, over the same requests.
Evaluation runs after the answer is returned, so its % is relative to the request but not part of it.
"""

import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pipeline"))

QUEUES = ["queue_inbox", "queue_tasks", "queue_drafts", "queue_final"]
ROWS = [("Cache lookup", ["cache_lookup"]), ("Planner", ["planner"]), ("Writer", ["writer"]),
        ("Reviewer", ["reviewer"]), ("Queue wait (total)", QUEUES), ("Evaluation", ["evaluation"])]


def by_trace(spans, trace_ids=None):
    """{trace_id: {stage: summed duration_ms}, plus 'status' and 'cache' of the request span}."""
    traces = defaultdict(lambda: defaultdict(float))
    meta = {}
    for s in spans:
        t = s["trace_id"]
        if trace_ids is not None and t not in trace_ids:
            continue
        traces[t][s["stage"]] += s["duration_ms"]
        if s["stage"] == "request":
            meta[t] = {"status": s["status"], "cache": (s.get("attrs") or {}).get("cache")}
    return traces, meta


def miss_table(spans, trace_ids=None):
    """Rows for the 4.3 table, over successful cache-miss requests. Returns (rows, n_requests, e2e)."""
    traces, meta = by_trace(spans, trace_ids)
    ids = [t for t, m in meta.items() if m["cache"] == "miss" and m["status"] == "ok"
           and "planner" in traces[t] and "reviewer" in traces[t]]
    e2e = [traces[t]["request"] for t in ids]
    rows = []
    for label, stages in ROWS:
        have = [t for t in ids if any(s in traces[t] for s in stages)]
        values = [sum(traces[t].get(s, 0.0) for s in stages) for t in have]
        total_e2e = sum(traces[t]["request"] for t in have)
        rows.append({"stage": label, "n": len(values),
                     "p50_ms": float(np.percentile(values, 50)) if values else None,
                     "p95_ms": float(np.percentile(values, 95)) if values else None,
                     "pct_of_e2e": 100 * sum(values) / total_e2e if values else None})
    summary = {"n_requests": len(ids),
               "e2e_p50_ms": float(np.percentile(e2e, 50)) if e2e else None,
               "e2e_p95_ms": float(np.percentile(e2e, 95)) if e2e else None}
    return rows, summary


def hit_summary(spans, trace_ids=None):
    """Cache-hit latency is its own metric (end-to-end time of requests answered from the cache)."""
    traces, meta = by_trace(spans, trace_ids)
    values = [traces[t]["request"] for t, m in meta.items() if m["cache"] == "hit" and m["status"] == "ok"]
    return {"n_requests": len(values),
            "p50_ms": float(np.percentile(values, 50)) if values else None,
            "p95_ms": float(np.percentile(values, 95)) if values else None}


def format_table(rows, summary):
    lines = [f"{'Stage':<22}{'p50 (ms)':>12}{'p95 (ms)':>12}{'% of cache-miss e2e':>22}"]
    for r in rows:
        if r["p50_ms"] is None:
            lines.append(f"{r['stage']:<22}{'-':>12}{'-':>12}{'-':>22}")
        else:
            lines.append(f"{r['stage']:<22}{r['p50_ms']:>12,.0f}{r['p95_ms']:>12,.0f}{r['pct_of_e2e']:>21.1f}%")
    if summary["n_requests"]:
        lines.append(f"{'End-to-end (miss)':<22}{summary['e2e_p50_ms']:>12,.0f}{summary['e2e_p95_ms']:>12,.0f}"
                     f"{'100%':>22}")
    return "\n".join(lines)
