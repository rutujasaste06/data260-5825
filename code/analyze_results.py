import json
from collections import Counter
import statistics

with open("../reports/hw01/raw/all_runs.json", "r") as f:
    all_results = json.load(f)

def analyze_temp(results, temp_label):
    tag_sets = [frozenset(r["tags"]) for r in results]
    distinct_sets = set(tag_sets)

    tag_counts = Counter()
    for r in results:
        for tag in set(r["tags"]):
            tag_counts[tag] += 1

    total_runs = len(results)
    tags_in_all = [tag for tag, count in tag_counts.items() if count == total_runs]
    tags_in_exactly_one = [tag for tag, count in tag_counts.items() if count == 1]

    latencies = sorted(r["latency_ms"] for r in results)
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies) * 0.95) - 1]
    p99 = latencies[int(len(latencies) * 0.99) - 1]

    print(f"\n=== Temperature {temp_label} ===")
    print(f"Distinct tag sets: {len(distinct_sets)}")
    print(f"Tags in all {total_runs} runs: {tags_in_all}")
    print(f"Tags in exactly 1 run: {tags_in_exactly_one}")
    print(f"Latency p50: {p50:.2f} ms")
    print(f"Latency p95: {p95:.2f} ms")
    print(f"Latency p99: {p99:.2f} ms")

    return {
        "distinct_tag_sets": len(distinct_sets),
        "tags_in_all_runs": tags_in_all,
        "tags_in_exactly_one_run": tags_in_exactly_one,
        "latency_p50_ms": round(p50, 2),
        "latency_p95_ms": round(p95, 2),
        "latency_p99_ms": round(p99, 2)
    }

results_07 = [r for r in all_results if r["temperature"] == 0.7]
results_00 = [r for r in all_results if r["temperature"] == 0.0]

summary_07 = analyze_temp(results_07, "0.7")
summary_00 = analyze_temp(results_00, "0.0")

with open("../reports/hw01/METRICS.md", "w") as f:
    f.write("# Non-Determinism Metrics\n\n")
    f.write("## Temperature 0.7\n\n")
    f.write(f"- Distinct tag sets: {summary_07['distinct_tag_sets']}\n")
    f.write(f"- Tags in all 20 runs: {summary_07['tags_in_all_runs']}\n")
    f.write(f"- Tags in exactly 1 run: {summary_07['tags_in_exactly_one_run']}\n")
    f.write(f"- Latency p50: {summary_07['latency_p50_ms']} ms\n")
    f.write(f"- Latency p95: {summary_07['latency_p95_ms']} ms\n")
    f.write(f"- Latency p99: {summary_07['latency_p99_ms']} ms\n\n")
    f.write("## Temperature 0.0\n\n")
    f.write(f"- Distinct tag sets: {summary_00['distinct_tag_sets']}\n")
    f.write(f"- Tags in all 20 runs: {summary_00['tags_in_all_runs']}\n")
    f.write(f"- Tags in exactly 1 run: {summary_00['tags_in_exactly_one_run']}\n")
    f.write(f"- Latency p50: {summary_00['latency_p50_ms']} ms\n")
    f.write(f"- Latency p95: {summary_00['latency_p95_ms']} ms\n")
    f.write(f"- Latency p99: {summary_00['latency_p99_ms']} ms\n")

print("\nMETRICS.md written to reports/hw01/METRICS.md")