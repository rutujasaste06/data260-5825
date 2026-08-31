import json
import os
import subprocess
import sys

checks = {}

# Check 1: Required files exist
required_files = [
    "index.html", "script.js", "Dockerfile", "agents_demo.py",
    "src/model_client.py", "hw1_client.py", "AGENT.md",
    "DOMAIN_SCHEMA.md", "reports/hw01/cases/nondeterminism_input.json",
    "reports/hw01/raw/all_runs.json", "reports/hw01/METRICS.md",
    "reports/hw01/AI_USE.md", "reports/hw01/RUN_LOG.txt"
]
missing_files = [f for f in required_files if not os.path.exists(f)]
checks["required_files_present"] = len(missing_files) == 0
checks["missing_files"] = missing_files

# Check 2: Python version
python_version = sys.version_info
checks["python_version"] = f"{python_version.major}.{python_version.minor}.{python_version.micro}"
checks["python_version_ok"] = python_version.major == 3 and python_version.minor in [11, 12]

# Check 3: Ollama model available
try:
    result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
    checks["ollama_available"] = "qwen3:8b" in result.stdout
except Exception:
    checks["ollama_available"] = False

# Check 4: 40 runs completed
if os.path.exists("reports/hw01/raw/all_runs.json"):
    with open("reports/hw01/raw/all_runs.json") as f:
        runs = json.load(f)
    checks["total_runs_count"] = len(runs)
    checks["forty_runs_complete"] = len(runs) == 40
else:
    checks["total_runs_count"] = 0
    checks["forty_runs_complete"] = False

checks["overall_status"] = "PASS" if (
    checks["required_files_present"] and
    checks["python_version_ok"] and
    checks["ollama_available"] and
    checks["forty_runs_complete"]
) else "FAIL"

with open("reports/hw01/verification.json", "w") as f:
    json.dump(checks, f, indent=2)

print(json.dumps(checks, indent=2))