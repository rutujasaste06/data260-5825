"""
HW10 Part 4.3 - stage-latency experiment: 50 confirmed cache-miss requests.

Every request goes through TracedClient. A request counts only if its cache_lookup span says
"miss" (so it was NOT served from the semantic cache) and the pipeline finished. Each counted
request is also evaluated (the evaluation span gives the Evaluation row). Questions that turn
out to be cache hits are recorded as skipped and replaced from the pool.
After the 50, the first 10 questions are asked again to get cache-HIT latency (a separate metric).
Progress is saved in reports/hw10/raw/latency_requests.jsonl, so if you stop it, running it
again continues where it stopped.

Needs Redis, Kafka, the three agents and Ollama running.   (This takes a while.)
Run from the repo root:   python code/hw10/latency_experiment.py
"""

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
sys.path.insert(0, HERE)

import latency_stats  # noqa: E402
from evaluator import evaluate_trace  # noqa: E402
from traced_request import TracedClient  # noqa: E402
from tracing import load_spans, raw_dir  # noqa: E402

TARGET_MISSES = 50
HIT_REPEATS = 10
CONDITIONS = [
    "type 2 diabetes", "asthma", "migraine", "breast cancer", "lung cancer", "heart failure",
    "hypertension", "rheumatoid arthritis", "psoriasis", "Crohn's disease", "multiple sclerosis",
    "Parkinson's disease", "Alzheimer's disease", "epilepsy", "depression", "schizophrenia",
    "chronic kidney disease", "COPD", "osteoporosis", "ulcerative colitis", "lupus", "hepatitis C",
    "HIV", "prostate cancer", "colorectal cancer", "melanoma", "leukemia", "sickle cell disease",
    "cystic fibrosis", "endometriosis", "obesity", "insomnia", "atrial fibrillation", "glaucoma",
    "macular degeneration", "eczema", "celiac disease", "fibromyalgia", "gout", "anxiety disorder",
]
TEMPLATES = [
    "What side effects do patients commonly report in clinical trials for {c}?",
    "How are participants selected for {c} studies?",
]
REQUESTS_FILE = os.path.join(raw_dir(), "latency_requests.jsonl")


def question_pool():
    pool = [t.format(c=c) for c in CONDITIONS for t in TEMPLATES]
    random.Random(5825).shuffle(pool)
    return pool


def load_records():
    if not os.path.exists(REQUESTS_FILE):
        return []
    with open(REQUESTS_FILE) as f:
        return [json.loads(line) for line in f if line.strip()]


def save_record(record):
    os.makedirs(raw_dir(), exist_ok=True)
    with open(REQUESTS_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")


def main():
    client = TracedClient()
    records = load_records()
    asked = {r["question"] for r in records if r["kind"] in ("miss", "skipped_hit", "failed")}
    confirmed = [r for r in records if r["kind"] == "miss"]

    for question in question_pool():
        if len(confirmed) >= TARGET_MISSES:
            break
        if question in asked:
            continue
        result = client.ask(question)
        if result["cache_hit"]:
            kind = "skipped_hit"
        elif result["status"] != "ok":
            kind = "failed"
        else:
            kind = "miss"
        record = {"kind": kind, "trace_id": result["trace_id"], "question": question,
                  "latency_ms": result["latency_ms"], "error": result["error"]}
        if kind == "miss":
            ev = evaluate_trace(result["trace_id"])
            record["evaluation_status"] = ev["status"]
            confirmed.append(record)
        save_record(record)
        print(f"[{len(confirmed)}/{TARGET_MISSES}] {kind:<11} {result['latency_ms']/1000:6.1f}s  {question}")

    hits_done = sum(1 for r in load_records() if r["kind"] == "hit")
    for r in confirmed[:HIT_REPEATS][hits_done:]:
        result = client.ask(r["question"])
        save_record({"kind": "hit" if result["cache_hit"] else "unexpected_miss", "trace_id": result["trace_id"],
                     "question": r["question"], "latency_ms": result["latency_ms"], "error": result["error"]})
        print(f"cache-hit check  {result['latency_ms']:7.1f} ms  hit={result['cache_hit']}")

    records = load_records()
    miss_ids = {r["trace_id"] for r in records if r["kind"] == "miss"}
    hit_ids = {r["trace_id"] for r in records if r["kind"] == "hit"}
    spans = load_spans()
    rows, summary = latency_stats.miss_table(spans, miss_ids)
    hits = latency_stats.hit_summary(spans, hit_ids)
    print(f"\n=== 4.3 Stage latency over {summary['n_requests']} confirmed cache-miss requests ===")
    print(latency_stats.format_table(rows, summary))
    if hits["n_requests"]:
        print(f"\nCache-hit latency ({hits['n_requests']} requests, separate metric): "
              f"p50 {hits['p50_ms']:,.0f} ms, p95 {hits['p95_ms']:,.0f} ms")
    ranked = sorted((r for r in rows if r["pct_of_e2e"] is not None and r["stage"] != "Evaluation"),
                    key=lambda r: r["pct_of_e2e"], reverse=True)
    if ranked:
        print(f"Dominant contributor: {ranked[0]['stage']} ({ranked[0]['pct_of_e2e']:.1f}% of cache-miss end-to-end)")
    with open(os.path.join(raw_dir(), "latency_table.json"), "w") as f:
        json.dump({"rows": rows, "summary": summary, "cache_hit": hits}, f, indent=2)
    print("Saved to reports/hw10/raw/latency_table.json")


if __name__ == "__main__":
    main()
