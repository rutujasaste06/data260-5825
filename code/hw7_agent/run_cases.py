"""Run the fixed cases A, B, C and the error-recovery case E once each (HW7 Part 2)."""
import json
import logging
import os
import sys

import agent_loop
import cases
import verifiers

RAW = cases.RAW


def setup_logging(log_path):
    """Log to the console and append to RUN_LOG.txt with timestamps."""
    fmt = logging.Formatter("%(asctime)s %(name)s %(message)s")
    root = logging.getLogger()
    root.handlers.clear()  # drop duplicate handlers added by other libraries
    root.setLevel(logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [agent] %(message)s"))
    logging.getLogger("agent_loop").addHandler(file_handler)  # tool-call lines go to the file too
    for h in (logging.StreamHandler(sys.stdout), logging.FileHandler(log_path)):
        h.setFormatter(fmt)
        root.addHandler(h)


def run_one(case, seed):
    """Run one case, verify it, return the record."""
    logging.info("=== case %s (%s) seed=%s ===", case["id"], case["kind"], seed)
    logging.info("prompt: %s", case["prompt"])
    run = agent_loop.run_agent(case["prompt"], seed=seed)
    verdict = verifiers.verify(case, run)
    logging.info("answer: %s", run["answer"])
    logging.info("verdict: success=%s reason=%s", verdict["success"], verdict["reason"])
    return {"case": case["id"], "seed": seed, "run": run, "verdict": verdict}


def main():
    """Run all fixed cases and save raw/part2_fixed_runs.json."""
    log_path = os.path.join(RAW, "..", "RUN_LOG.txt")
    os.makedirs(RAW, exist_ok=True)
    setup_logging(log_path)
    records = [run_one(c, cases.SEED) for c in cases.build_cases()]
    with open(os.path.join(RAW, "part2_fixed_runs.json"), "w") as f:
        json.dump(records, f, indent=2, default=str)
    print("\nCASE  TOOL CALLS  STOP       SUCCESS")
    for r in records:
        print(f"{r['case']:<5} {r['run']['tool_calls']:<11} {r['run']['stop_reason']:<10} {r['verdict']['success']}")


if __name__ == "__main__":
    main()
