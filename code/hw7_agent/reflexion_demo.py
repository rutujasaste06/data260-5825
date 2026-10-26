"""HW7 Part 3 demo: force a failed first attempt (iteration ceiling of 2), then let Reflexion recover."""
import json
import os

import agent_loop
import cases
import reflexion
import run_cases
from model_client import ModelClient


def handicapped_agent(prompt, model, seed, extra_system):
    """First attempt only gets 2 model calls, so it cannot finish; retries get the normal ceiling."""
    limit = 2 if not extra_system else agent_loop.MAX_ITERATIONS
    return agent_loop.run_agent(prompt, model=model, seed=seed, extra_system=extra_system,
                                max_iterations=limit)


def main():
    """Run case A with a forced first failure and print each attempt."""
    run_cases.setup_logging(os.path.join(cases.RAW, "..", "RUN_LOG.txt"))
    case = next(c for c in cases.load_cases() if c["id"] == "A")
    rec = reflexion.reflexion_run(case, cases.SEED, ModelClient(), agent=handicapped_agent)
    print("\nREFLEXION DEMO (Rutuja Saste) - forced failure on attempt 1")
    for a in rec["attempts"]:
        v = a["verdict"]
        print(f"attempt {a['attempt']}: stop={a['run']['stop_reason']} success={v['success']} reason={v['reason']}")
    print("stored reflections:", json.dumps(
        reflexion.MEMORY.get(("rutuja", f"A-{cases.SEED}"), []), indent=2))
    print("final stop_reason:", rec["stop_reason"], "| budget used:", rec["used"])
    with open(os.path.join(cases.RAW, "part3_forced_failure_demo.json"), "w") as f:
        json.dump(rec, f, indent=2, default=str)


if __name__ == "__main__":
    main()
