"""HW10 Part 1.1 - Summary page.   Run:  streamlit run code/hw10/dashboard/Summary.py --server.port 8426"""

import os
import sys
import time

import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import data  # noqa: E402
import latency_stats  # noqa: E402

st.set_page_config(page_title="Ops dashboard - Summary", layout="wide")
st.title("Operations dashboard - Summary")

all_spans = data.get_spans()
requests_all = [s for s in all_spans if s["stage"] == "request"]
if not requests_all:
    st.info("No spans yet. Run code/hw10/trace_examples.py first (it writes reports/hw10/raw/spans.jsonl).")
    st.stop()

window = st.selectbox("Time window", ["All recorded data", "Last 1 hour", "Last 24 hours", "Last 7 days"])
seconds = {"Last 1 hour": 3600, "Last 24 hours": 86400, "Last 7 days": 7 * 86400}.get(window)
cutoff = time.time() - seconds if seconds else 0
reqs = [s for s in requests_all if s["start_time"] >= cutoff]
if not reqs:
    st.warning("No requests in this window.")
    st.stop()
ids = {s["trace_id"] for s in reqs}
window_text = (f"{window}: {data.fmt_time(min(s['start_time'] for s in reqs))} to "
               f"{data.fmt_time(max(s['end_time'] for s in reqs))}")
SRC_REQ = "Source: `request` spans in reports/hw10/raw/spans.jsonl"
SRC_CACHE = "Source: `cache_lookup` spans (attrs.cache = hit / miss) in reports/hw10/raw/spans.jsonl"


def pct(values, q):
    return f"{np.percentile(values, q):,.0f} ms" if values else "n/a"


st.subheader("Requests")
col1, col2 = st.columns(2)
col1.metric("Recent request count", len(reqs))
col1.caption(f"Window: {window_text}. {SRC_REQ}.")
errors = [s for s in reqs if s["status"] == "error"]
col2.metric("Error rate", f"{100 * len(errors) / len(reqs):.1f}%", f"{len(errors)} of {len(reqs)} requests",
            delta_color="off")
col2.caption(f"Window: {window_text}. A request is an error if its `request` span has status error. {SRC_REQ}.")
if errors:
    st.dataframe(pd.DataFrame([{"trace_id": s["trace_id"], "error": s["error"]} for s in errors]),
                 hide_index=True, width="stretch")

st.subheader("Semantic-cache hit rate")
lookups = [s for s in all_spans if s["stage"] == "cache_lookup" and s["trace_id"] in ids]
hits = sum(1 for s in lookups if (s.get("attrs") or {}).get("cache") == "hit")
misses = sum(1 for s in lookups if (s.get("attrs") or {}).get("cache") == "miss")
c1, c2, c3 = st.columns(3)
c1.metric("Hit rate", f"{100 * hits / max(hits + misses, 1):.1f}%")
c2.metric("Cache hits", hits)
c3.metric("Cache misses", misses)
st.caption(f"Window: {window_text}. {SRC_CACHE}. Hit = similarity at or above the 0.95 threshold.")

st.subheader("End-to-end latency (hits and misses kept separate)")
ok = [s for s in reqs if s["status"] == "ok"]
hit_ms = [s["duration_ms"] for s in ok if (s.get("attrs") or {}).get("cache") == "hit"]
miss_ms = [s["duration_ms"] for s in ok if (s.get("attrs") or {}).get("cache") == "miss"]
a, b, c, d = st.columns(4)
a.metric("Cache-HIT p50", pct(hit_ms, 50))
b.metric("Cache-HIT p95", pct(hit_ms, 95))
c.metric("Cache-MISS p50", pct(miss_ms, 50))
d.metric("Cache-MISS p95", pct(miss_ms, 95))
st.caption(f"Window: {window_text}. End-to-end = duration of the `request` span (cache lookup through the final "
           f"result), successful requests only: {len(hit_ms)} hits, {len(miss_ms)} misses. {SRC_REQ}.")

st.subheader("Stage latency, cache-miss requests")
rows, summary = latency_stats.miss_table(all_spans, ids)
if summary["n_requests"]:
    st.dataframe(pd.DataFrame([{"Stage": r["stage"], "p50 (ms)": r["p50_ms"], "p95 (ms)": r["p95_ms"],
                                "% of cache-miss end-to-end": r["pct_of_e2e"]} for r in rows]).round(1),
                 hide_index=True, width="stretch")
    st.caption(f"Window: {window_text}. {summary['n_requests']} successful cache-miss requests. Source: all span "
               f"stages in reports/hw10/raw/spans.jsonl. Queue wait = queue_inbox + queue_tasks + queue_drafts + "
               f"queue_final. Evaluation runs after the answer is returned.")
else:
    st.info("No successful cache-miss requests in this window yet.")
