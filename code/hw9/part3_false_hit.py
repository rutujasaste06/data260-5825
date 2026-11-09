"""
HW9 Part 3.3 - one false hit in full.

Takes the false hit with the highest similarity from the sweep (case D01), and shows:
the cached query, the incoming query, the similarity, the cached answer that the cache
would have returned, and the correct answer (a fresh run of the HW8 agent on the
incoming query).

Run from the repo root:   python code/hw9/part3_false_hit.py
"""

import json
import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_path import run_hw8_agent  # noqa: E402

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "reports", "hw09", "raw")
CASE_ID = "D01"


def show(label, text):
    print(f"{label}")
    print(textwrap.indent(textwrap.fill(text, 100, replace_whitespace=False), "    "))
    print()


def main():
    with open(os.path.join(RAW_DIR, "part3_sweep.json")) as f:
        sweep = json.load(f)
    with open(os.path.join(RAW_DIR, "seed_answers.json")) as f:
        seeds = json.load(f)

    case = next(c for c in sweep["cases"] if c["id"] == CASE_ID)
    cached_answer = seeds[case["matched_seed"]]["answer"]

    print(f"=== Part 3.3 False hit: case {CASE_ID} ===\n")
    show("Cached query (saved earlier):", case["matched_query"])
    show("Incoming query (a different question):", case["query"])
    print(f"Similarity score: {case['similarity']:.3f}  (above every threshold up to 0.95)\n")
    show("Cached answer returned (WRONG - it answers the cached question):", cached_answer)

    print("Running the HW8 agent on the incoming query to get the correct answer ...\n")
    correct_answer, _status = run_hw8_agent(case["query"])
    show("Correct answer (fresh agent run for the incoming query):", correct_answer)

    with open(os.path.join(RAW_DIR, "part3_false_hit.json"), "w") as f:
        json.dump({
            "case": CASE_ID,
            "cached_query": case["matched_query"],
            "incoming_query": case["query"],
            "similarity": case["similarity"],
            "cached_answer": cached_answer,
            "correct_answer": correct_answer,
        }, f, indent=2)
    print("Saved details to reports/hw09/raw/part3_false_hit.json")


if __name__ == "__main__":
    main()
