"""
HW9 Part 3.2 - threshold sweep over the 40 labeled cases in cache_cases.yaml.

Step 1: fill the cache with the 10 seed questions (answered by the HW8 agent once;
        answers are saved in reports/hw09/raw/seed_answers.json and reused on re-runs).
Step 2: for each of the 40 cases, find the closest saved question in Redis and record
        its cosine similarity and how long the lookup took.
Step 3: for each threshold (0.75 ... 0.95) decide hit/miss from the recorded similarity.

Why not re-run the whole thing 5 times? Whether a query hits depends only on its
similarity score and the threshold, so one measured similarity per case is enough to
decide hit/miss at every threshold. A miss costs one agent run; its latency is the mean
of the 10 agent runs we actually measured while building the seeds.

Run from the repo root:   python code/hw9/part3_sweep.py
"""

import json
import os
import sys
import time

import redis
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_path import run_hw8_agent  # noqa: E402
from semantic_cache import SemanticCache  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CASES_PATH = os.path.join(HERE, "cache_cases.yaml")
RAW_DIR = os.path.join(HERE, "..", "..", "reports", "hw09", "raw")
SEED_PATH = os.path.join(RAW_DIR, "seed_answers.json")
OUT_PATH = os.path.join(RAW_DIR, "part3_sweep.json")
THRESHOLDS = [0.75, 0.80, 0.85, 0.90, 0.95]
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")


def build_seeds(cache, seeds):
    """Answer each seed with the HW8 agent (or load saved answers) and store it in Redis."""
    if os.path.exists(SEED_PATH):
        with open(SEED_PATH) as f:
            saved = json.load(f)
        print(f"[seeds] loaded {len(saved)} saved answers from reports/hw09/raw/seed_answers.json")
    else:
        saved = {}
        for seed in seeds:
            t0 = time.perf_counter()
            answer, status = run_hw8_agent(seed["query"])
            agent_ms = (time.perf_counter() - t0) * 1000
            saved[seed["id"]] = {
                "query": seed["query"], "answer": answer, "agent_ms": agent_ms, "reviewer": status,
            }
            print(f"[seeds] {seed['id']} answered in {agent_ms / 1000:.1f} s")
        os.makedirs(RAW_DIR, exist_ok=True)
        with open(SEED_PATH, "w") as f:
            json.dump(saved, f, indent=2)
    for seed in seeds:
        entry = saved[seed["id"]]
        cache.store(entry["query"], cache.embed(entry["query"]), entry["answer"], cache.current_version())
    return saved


def measure_cases(cache, cases, seed_by_query):
    """Closest saved question for every case: similarity, matched seed, lookup time."""
    rows = []
    for case in cases:
        t0 = time.perf_counter()
        vec = cache.embed(case["query"])
        match = cache.lookup(vec)
        lookup_ms = (time.perf_counter() - t0) * 1000
        rows.append({
            "id": case["id"],
            "type": case["type"],
            "query": case["query"],
            "expected_seed": case["seed"],
            "should_hit": case["should_hit"],
            "similarity": match["similarity"],
            "matched_query": match["query"],
            "matched_seed": seed_by_query[match["query"]],
            "lookup_ms": lookup_ms,
        })
    return rows


def summarize(rows, thresholds, mean_agent_ms):
    """Hit rate, false-hit rate and mean latency per threshold."""
    should_miss = [r for r in rows if not r["should_hit"]]
    table = []
    for threshold in thresholds:
        hits = [r for r in rows if r["similarity"] >= threshold]
        false_hits = [r for r in should_miss if r["similarity"] >= threshold]
        missed_hits = [r for r in rows if r["should_hit"] and r["similarity"] < threshold]
        latencies = [r["lookup_ms"] + (0 if r["similarity"] >= threshold else mean_agent_ms) for r in rows]
        table.append({
            "threshold": threshold,
            "hits": len(hits),
            "hit_rate_percent": 100 * len(hits) / len(rows),
            "false_hits": len(false_hits),
            "false_hit_rate_percent": 100 * len(false_hits) / len(should_miss),
            "missed_hits": len(missed_hits),
            "mean_latency_ms": sum(latencies) / len(latencies),
        })
    return table


def main():
    with open(CASES_PATH) as f:
        spec = yaml.safe_load(f)
    client = redis.Redis(host=REDIS_HOST, port=6379)
    try:
        client.ping()
    except redis.exceptions.ConnectionError:
        sys.exit("Redis is not running. Start it with: docker compose up -d redis")

    cache = SemanticCache(client, run_hw8_agent)
    cache.reset()
    cache.embed("warm up")  # load the embedding model before timing starts

    print("=== Part 3.2 threshold sweep ===\n")
    saved = build_seeds(cache, spec["seeds"])
    mean_agent_ms = sum(s["agent_ms"] for s in saved.values()) / len(saved)
    seed_by_query = {s["query"]: sid for sid, s in saved.items()}
    print(f"[seeds] mean agent latency (one cache miss) = {mean_agent_ms:.1f} ms\n")

    rows = measure_cases(cache, spec["cases"], seed_by_query)
    print("Case  Type               Similarity  Closest seed  Expected  Should hit")
    for r in rows:
        print(f"{r['id']:<5} {r['type']:<18} {r['similarity']:>9.3f}   {r['matched_seed']:<12}  "
              f"{str(r['expected_seed']):<8}  {r['should_hit']}")

    table = summarize(rows, THRESHOLDS, mean_agent_ms)
    print("\nThreshold  Hit rate  False-hit rate  Mean latency (ms)")
    for t in table:
        print(f"  {t['threshold']:.2f}     {t['hit_rate_percent']:>5.1f}%     "
              f"{t['false_hit_rate_percent']:>5.1f}% ({t['false_hits']}/20)   {t['mean_latency_ms']:>10.1f}")
    print("\nHit rate = hits / 40 cases.  False-hit rate = hits on should-miss cases / 20.")
    print("Mean latency = lookup time measured per case + mean agent time for each miss.")

    os.makedirs(RAW_DIR, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump({"mean_agent_ms": mean_agent_ms, "cases": rows, "table": table}, f, indent=2)
    print("\nSaved details to reports/hw09/raw/part3_sweep.json")


if __name__ == "__main__":
    main()
