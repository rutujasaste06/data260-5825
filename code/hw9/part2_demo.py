"""
HW9 Part 2 demo - run 12 queries through the semantic cache and report the
hit rate and the average latency of cached vs non-cached answers.

Run from the repo root:   python code/hw9/part2_demo.py
(needs: Redis Stack running, Ollama running with qwen3:8b)
"""

import json
import logging
import os
import sys

import redis

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_path import run_hw8_agent  # noqa: E402
from semantic_cache import DEFAULT_THRESHOLD, SemanticCache  # noqa: E402

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
RESULTS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "reports", "hw09", "raw", "part2_results.json"
)

# (type, question): new = never seen, exact = repeat of an earlier question,
# paraphrase = same meaning in different words
QUERIES = [
    ("new", "What should a patient know before joining a Phase II clinical trial?"),
    ("new", "What are the eligibility requirements for a Phase III trial?"),
    ("new", "How is informed consent obtained in a clinical trial?"),
    ("exact", "What should a patient know before joining a Phase II clinical trial?"),
    ("paraphrase", "Before enrolling in a Phase 2 clinical trial, what should a patient be aware of?"),
    ("exact", "How is informed consent obtained in a clinical trial?"),
    ("new", "What does Phase I testing of a new drug focus on?"),
    ("paraphrase", "How does informed consent work when joining a clinical trial?"),
    ("paraphrase", "Who can qualify to participate in a Phase 3 trial?"),
    ("new", "What is the NCT number on a trial listing?"),
    ("exact", "What does Phase I testing of a new drug focus on?"),
    ("new", "What is the capital of France?"),
]


def main():
    logging.basicConfig(level=logging.WARNING)
    cache_logger = logging.getLogger("semantic_cache")
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))
    cache_logger.addHandler(handler)
    cache_logger.setLevel(logging.INFO)
    cache_logger.propagate = False

    client = redis.Redis(host=REDIS_HOST, port=6379)
    try:
        client.ping()
    except redis.exceptions.ConnectionError:
        sys.exit("Redis is not running. Start it with: docker compose up -d redis")

    cache = SemanticCache(client, run_hw8_agent, threshold=DEFAULT_THRESHOLD)
    cache.reset()
    cache.embed("warm up")  # load the embedding model before timing starts

    print(f"=== Semantic cache test (threshold {DEFAULT_THRESHOLD}) ===\n")
    results = []
    for number, (kind, question) in enumerate(QUERIES, start=1):
        print(f"[{number}/{len(QUERIES)}] ({kind})")
        out = cache.handle_query(question)
        out["type"] = kind
        results.append(out)
        sim = "n/a" if out["similarity"] is None else f"{out['similarity']:.3f}"
        print(f"    is_cached={out['is_cached']}  similarity={sim}  latency={out['latency_ms']:.1f} ms\n")

    hits = [r for r in results if r["is_cached"]]
    misses = [r for r in results if not r["is_cached"]]
    hit_rate = 100 * len(hits) / len(results)
    avg_hit = sum(r["latency_ms"] for r in hits) / len(hits) if hits else 0.0
    avg_miss = sum(r["latency_ms"] for r in misses) / len(misses) if misses else 0.0

    print("=== Summary ===")
    print(f"Queries: {len(results)}   Hits: {len(hits)}   Misses: {len(misses)}")
    print(f"Cache hit rate: {hit_rate:.1f}%")
    print(f"Average latency, cached:     {avg_hit:.1f} ms")
    print(f"Average latency, non-cached: {avg_miss:.1f} ms")

    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(
            {
                "threshold": DEFAULT_THRESHOLD,
                "hit_rate_percent": hit_rate,
                "avg_latency_cached_ms": avg_hit,
                "avg_latency_non_cached_ms": avg_miss,
                "results": results,
            },
            f,
            indent=2,
        )
    print("\nSaved details to reports/hw09/raw/part2_results.json")


if __name__ == "__main__":
    main()
