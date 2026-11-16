"""
HW10 Part 4 - tiny span logger.

Analogy: a delivery parcel with a tracking number. Every station that handles
the parcel writes one line in a logbook: "parcel X, station Y, arrived at, left
at, ok or broken". The tracking number (trace_id) is the HW8 correlation_id -
there is no second identifier.

One span = one JSON line in reports/hw10/raw/spans.jsonl:
  trace_id, stage, start_time, end_time (epoch seconds), duration_ms, status, error
  (+ optional "attrs", e.g. {"cache": "hit"} on the cache_lookup span)
"""

import json
import os
import time
from contextlib import contextmanager

_DEFAULT_RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "reports", "hw10", "raw")


def raw_dir():
    return os.path.abspath(os.environ.get("HW10_RAW_DIR", _DEFAULT_RAW))


def spans_path():
    return os.path.join(raw_dir(), "spans.jsonl")


def write_span(trace_id, stage, start, end, status="ok", error=None, **attrs):
    span = {
        "trace_id": trace_id,
        "stage": stage,
        "start_time": start,
        "end_time": end,
        "duration_ms": round((end - start) * 1000, 2),
        "status": status,
        "error": error,
    }
    if attrs:
        span["attrs"] = attrs
    os.makedirs(raw_dir(), exist_ok=True)
    with open(spans_path(), "a") as f:
        f.write(json.dumps(span) + "\n")  # one line per span, appended
    return span


@contextmanager
def traced(trace_id, stage, **attrs):
    """with traced(trace_id, "planner"): ...  -> writes one span, status ok or error."""
    start = time.time()
    info = dict(attrs)
    try:
        yield info
    except Exception as exc:
        write_span(trace_id, stage, start, time.time(), "error", f"{type(exc).__name__}: {exc}", **info)
        raise
    write_span(trace_id, stage, start, time.time(), "ok", None, **info)


def queue_span(trace_id, stage, sent_at):
    """Time a message waited in a Kafka topic: from when it was sent until this consumer got it."""
    if sent_at:
        write_span(trace_id, stage, sent_at, time.time())


def error_message(trace_id, stage, exc):
    """What an agent puts on the final topic when its own stage failed (so the caller is not left waiting)."""
    return {
        "correlation_id": trace_id,
        "status": "error",
        "stage": stage,
        "error": f"{type(exc).__name__}: {exc}",
        "answer": None,
        "sent_at": time.time(),
    }


def load_spans(path=None):
    spans = []
    try:
        with open(path or spans_path()) as f:
            for line in f:
                try:
                    spans.append(json.loads(line))
                except ValueError:
                    pass  # ignore a half-written line
    except FileNotFoundError:
        pass
    return spans


STAGE_ORDER = ["request", "cache_lookup", "queue_inbox", "planner", "queue_tasks", "writer",
               "queue_drafts", "reviewer", "queue_final", "evaluation"]


def trace_spans(trace_id, spans=None):
    """All spans of one trace in stage order."""
    spans = load_spans() if spans is None else spans
    rank = {s: i for i, s in enumerate(STAGE_ORDER)}
    mine = [s for s in spans if s.get("trace_id") == trace_id]
    return sorted(mine, key=lambda s: (s["start_time"], rank.get(s["stage"], 99)))
