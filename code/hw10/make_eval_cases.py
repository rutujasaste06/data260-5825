"""
HW10 Part 3.1 - make the 20 Writer drafts (eval_cases.json).

Each question goes through the domain system's own Planner and Writer functions
(code/pipeline/planner.py and writer.py, local qwen3:8b). The questions are a deliberate mix, so
the drafts differ in quality: general trial questions, questions about listing data the Writer
cannot know (it has no data, so it may invent answers), vague questions and off-topic ones.

This only creates the drafts. No judge runs here. Next: label them by hand (label_cases.py),
then COMMIT eval_cases.json and human_labels.csv BEFORE any judge scores exist.

Run from the repo root:   python code/hw10/make_eval_cases.py
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "src"))

from planner import make_plan  # noqa: E402
from writer import write_answer  # noqa: E402

OUT = os.path.join(HERE, "eval_cases.json")

QUESTIONS = [
    # general clinical-trial questions
    "What should a patient know before joining a Phase II clinical trial?",
    "What is the difference between a Phase I and a Phase III trial?",
    "What does it mean when a trial's status is Recruiting?",
    "How is a placebo used in a clinical trial?",
    "What is an NCT number and where can I find it?",
    "What are common eligibility criteria for a clinical trial?",
    "What is informed consent in a clinical trial?",
    "Can a participant leave a clinical trial after enrolling?",
    "What are the risks of joining a Phase I trial compared with a Phase III trial?",
    # questions about listing data the Writer cannot know
    "How many available slots does the NeuroCalm Migraine Trial have?",
    "What is the current status of the CardioShield Heart Study?",
    "Which trials are currently recruiting for type 2 diabetes?",
    "What is the NCT number of the NeuroCalm Migraine Trial?",
    "List all Phase III trials sponsored by Meridian Pharma.",
    "Is the OncoBridge Lung Study still accepting participants?",
    # vague questions
    "Tell me about the trial.",
    "Is it safe?",
    "How long does it take?",
    # off-topic
    "What is the best pizza topping?",
    "Write a short poem about clouds.",
]


def main():
    cases = []
    for i, question in enumerate(QUESTIONS, start=1):
        plan = make_plan(question)
        draft = write_answer(question, plan)
        cases.append({"case_id": f"c{i:02d}", "question": question, "plan": plan, "draft": draft,
                      "model": "qwen3:8b", "temperature": 0.7,
                      "generated_at": time.strftime("%Y-%m-%d %H:%M:%S")})
        print(f"[{i}/{len(QUESTIONS)}] {question}")
    with open(OUT, "w") as f:
        json.dump(cases, f, indent=2)
    print(f"\nSaved {len(cases)} drafts to code/hw10/eval_cases.json")


if __name__ == "__main__":
    main()
