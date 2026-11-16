"""HW10 Part 1.3 - Trace lookup page."""

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import data  # noqa: E402
from tracing import trace_spans  # noqa: E402

st.set_page_config(page_title="Ops dashboard - Trace lookup", layout="wide")
st.title("Trace lookup")

examples = data.get_json("trace_examples.json") or {}
if examples:
    labels = {"hit": "cache-hit example", "miss": "cache-miss (success) example", "failed": "failed example"}
    st.write("Saved example traces (Part 4.2):")
    for key in ("hit", "miss", "failed"):
        if key in examples:
            st.write(f"- {labels[key]}: `{examples[key]['trace_id']}`")

trace_id = st.text_input("trace_id (the HW8 correlation_id)").strip()
if not trace_id:
    st.info("Paste a trace_id above to see its full request journey.")
    st.stop()

mine = trace_spans(trace_id, data.get_spans())
if not mine:
    st.error("No spans found for this trace_id.")
    st.stop()

lookup = next((s for s in mine if s["stage"] == "cache_lookup"), None)
request = next((s for s in mine if s["stage"] == "request"), None)
cache = (lookup.get("attrs") or {}).get("cache") if lookup else None
if cache == "hit":
    st.success("CACHE HIT path: answered from the semantic cache, the agents were not called.")
elif cache == "miss":
    st.warning("CACHE MISS path: the question went through inbox -> Planner -> Writer -> Reviewer -> final.")
if request:
    if request["status"] == "error":
        failing = [s for s in mine if s["status"] == "error" and s["stage"] != "request"]
        where = failing[0]["stage"] if failing else "unknown stage"
        st.error(f"FAILED request. Failing stage: {where}. Error: {request['error']}")
    else:
        st.write(f"Request completed in {request['duration_ms']:,.1f} ms.")

st.subheader("Request journey (stage order)")
st.dataframe(pd.DataFrame([{
    "stage": s["stage"], "start": data.fmt_time(s["start_time"]), "end": data.fmt_time(s["end_time"]),
    "duration (ms)": s["duration_ms"], "status": s["status"], "error": s["error"] or "",
} for s in mine]), hide_index=True, width="stretch")
st.caption("Source: reports/hw10/raw/spans.jsonl. queue_* stages = time a message waited in a Kafka topic; "
           "request = end to end; evaluation runs after the answer.")
