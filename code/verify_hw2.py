import json
import subprocess
import time
import sys
import os
import requests

sys.path.append("../src")

SID4 = "5825"
PORT_BASE = 8425
SEED = 5825
VERIFY_SEED = 265825  # 260000 + 5825

OUTPUT_PATH = "../reports/hw02/verification.json"


def get_commit_hash():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=".."
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def check_fastapi_responds():
    """Check 1: does the FastAPI backend respond on PORT_BASE?"""
    try:
        resp = requests.get(f"http://localhost:{PORT_BASE}/trials", timeout=5)
        passed = resp.status_code == 200
        detail = f"GET /trials returned status {resp.status_code}"
    except Exception as e:
        passed = False
        detail = f"Request failed: {e}"
    return {"check": "fastapi_responds_on_port_base", "passed": passed, "detail": detail}


def check_post_trial_succeeds():
    """Check 2: does adding a record via POST succeed?"""
    try:
        payload = {
            "trialTitle": "Smoke Test Trial",
            "nctNumber": "NCT00000000",
            "submitterEmail": "smoketest@sjsu.edu",
            "trialDescription": "This is a smoke test record used only to verify the API works correctly end to end.",
            "trialPhase": "Phase I",
        }
        resp = requests.post(f"http://localhost:{PORT_BASE}/trials", json=payload, timeout=10)
        passed = resp.status_code == 200 and "trial" in resp.json()
        detail = f"POST /trials returned status {resp.status_code}"
    except Exception as e:
        passed = False
        detail = f"Request failed: {e}"
    return {"check": "post_trial_succeeds", "passed": passed, "detail": detail}


def check_langgraph_finishes_with_3_tags():
    """Check 3: does the LangGraph script finish (not hang) and return exactly 3 tags?"""
    try:
        from agents_demo import build_graph, AgentState

        initial_state: AgentState = {
            "title": "Smoke Test Title",
            "content": "This is smoke test content used to verify the LangGraph pipeline finishes and produces a valid structured output within a reasonable time.",
            "planner_proposal": {},
            "reviewer_feedback": {},
            "turn_count": 0,
            "max_turns": 4,
        }
        app = build_graph()

        start = time.time()
        final_values = dict(initial_state)
        for step in app.stream(initial_state):
            for node_name, node_output in step.items():
                final_values.update(node_output)
            if time.time() - start > 300:  # 5 minute hang guard
                raise TimeoutError("Graph did not finish within 5 minutes")
        elapsed = time.time() - start

        tags = final_values.get("planner_proposal", {}).get("tags", [])
        passed = len(tags) == 3
        detail = f"Graph finished in {elapsed:.1f}s, returned {len(tags)} tags"
    except Exception as e:
        passed = False
        detail = f"Graph run failed: {e}"
    return {"check": "langgraph_finishes_with_3_tags", "passed": passed, "detail": detail}


if __name__ == "__main__":
    checks = []

    print("Running smoke test checks...\n")

    print("[1/3] Checking FastAPI responds on PORT_BASE...")
    c1 = check_fastapi_responds()
    checks.append(c1)
    print(f"  {'PASS' if c1['passed'] else 'FAIL'}: {c1['detail']}")

    print("[2/3] Checking POST /trials succeeds...")
    c2 = check_post_trial_succeeds()
    checks.append(c2)
    print(f"  {'PASS' if c2['passed'] else 'FAIL'}: {c2['detail']}")

    print("[3/3] Checking LangGraph finishes and returns 3 tags (this will take ~30-90s)...")
    c3 = check_langgraph_finishes_with_3_tags()
    checks.append(c3)
    print(f"  {'PASS' if c3['passed'] else 'FAIL'}: {c3['detail']}")

    result = {
        "homework": "HW2",
        "sid4": SID4,
        "commit_hash": get_commit_hash(),
        "model_configuration": "qwen3:8b via Ollama, temperature=0.7",
        "seed": SEED,
        "verify_seed": VERIFY_SEED,
        "checks": checks,
        "all_passed": all(c["passed"] for c in checks),
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nWrote results to {OUTPUT_PATH}")
    print(f"All checks passed: {result['all_passed']}")