import subprocess
import json
import time
import statistics
import csv
import os
import sys

RESULTS_DIR = "reports/hw01/raw"
os.makedirs(RESULTS_DIR, exist_ok=True)

def run_single(temp, run_number):
    start = time.time()
    result = subprocess.run(
        [sys.executable, "agents_demo.py", "--temp", str(temp)],
        capture_output=True, text=True
    )
    end = time.time()
    latency_ms = (end - start) * 1000

    output = result.stdout
    try:
        marker = " Finalized Publish Output "
        json_start = output.index(marker) + len(marker)
        json_text = output[json_start:].split("Latency:")[0].strip()
        parsed = json.loads(json_text)
        tags = parsed.get("tags", [])
        summary = parsed.get("summary", "")
    except Exception as e:
        tags = []
        summary = ""
        print(f"  [Warning] Failed to parse run {run_number} at temp={temp}: {e}")
        print(f"  [DEBUG] STDOUT: {output}")
        print(f"  [DEBUG] STDERR: {result.stderr}")

    return {
        "run_number": run_number,
        "temperature": temp,
        "tags": tags,
        "summary": summary,
        "latency_ms": round(latency_ms, 2)
    }

def run_batch(temp, count):
    results = []
    for i in range(1, count + 1):
        print(f"Running temp={temp}, run {i}/{count}...")
        r = run_single(temp, i)
        results.append(r)
        print(f"  Tags: {r['tags']}, Latency: {r['latency_ms']}ms")
    return results

if __name__ == "__main__":
    all_results = []

    print("=== Starting 20 runs at temperature 0.7 ===")
    results_07 = run_batch(0.7, 20)
    all_results.extend(results_07)

    print("\n=== Starting 20 runs at temperature 0.0 ===")
    results_00 = run_batch(0.0, 20)
    all_results.extend(results_00)

    with open(f"{RESULTS_DIR}/all_runs.json", "w") as f:
        json.dump(all_results, f, indent=2)

    with open(f"{RESULTS_DIR}/all_runs.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["run_number", "temperature", "tags", "summary", "latency_ms"])
        writer.writeheader()
        for r in all_results:
            writer.writerow({**r, "tags": "; ".join(r["tags"])})

    print("\nAll 40 runs complete. Results saved to reports/hw01/raw/")