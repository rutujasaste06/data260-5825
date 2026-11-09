"""
HW9 Part 4.1 and 4.2 demo.

  4.1  One controlled revision: the first answer is forced to be wrong, so the
       Answering Agent -> Evaluator -> revised answer -> Evaluator sequence shows reliably.
  Training run: the 6 training questions go through the workflow; every failure that
       the revision fixes becomes a lesson in lessons.json.
  4.2  A later, related question loads that lesson and reuses it.

Run from the repo root:   python code/hw9/part4/part4_demo.py
"""

import json
import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import (  # noqa: E402
    AnsweringAgent, Evaluator, LessonStore, lesson_from_failure, load_json, run_workflow, save_json,
)

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "reports", "hw09", "raw")


def wrap(text, indent="    "):
    return textwrap.indent(textwrap.fill(text, 100), indent)


def show_sequence(result):
    print(f"Question: {result['question']}\n")
    for attempt in result["attempts"]:
        print(f"Attempt {attempt['attempt']} answer:")
        print(wrap(attempt["answer"]))
        print(f"Evaluator result: {attempt['result']}")
        print(wrap(attempt["explanation"]))
        if attempt["feedback"]:
            print("Evaluator feedback:")
            print(wrap(attempt["feedback"]))
        print()
    print(f"Final evaluation: {result['final_result']}   Attempts used: {result['n_attempts']} (max 2)")
    print("Final response:")
    print(wrap(result["final_answer"]))


def main():
    reference = load_json("reference_data.json")
    evaluator = Evaluator(reference)
    answerer = AnsweringAgent(load_json("listing_snapshot.json"))
    save_json("lessons.json", [])  # every demo run starts with no lessons
    log = {}

    print("=== 4.1 Controlled revision test (first answer deliberately wrong) ===\n")
    controlled = run_workflow(
        "How many available slots does the NeuroCalm Migraine Trial have?",
        answerer, evaluator, store=None,
        forced_first="The NeuroCalm Migraine Trial has 12 available slots.",
    )
    show_sequence(controlled)
    log["controlled_revision"] = controlled

    print("\n=== Training run (lessons start empty) ===\n")
    store = LessonStore()
    log["training"] = []
    for item in load_json("training_data.json"):
        result = run_workflow(item["question"], answerer, evaluator, store)
        first = result["attempts"][0]
        print(f"[{item['id']}] {item['question']}")
        print(f"      attempt 1: {first['result']}   final: {result['final_result']}   "
              f"attempts: {result['n_attempts']}   lessons loaded: {result['lessons_used'] or 'none'}")
        if first["result"] == "REVISE" and result["final_result"] == "PASS" and first["trial"]:
            lesson = lesson_from_failure(store, first)
            print(f"      -> lesson saved: {lesson['lesson_id']}")
            print(wrap(f"failure_pattern: {lesson['failure_pattern']}", "         "))
            print(wrap(f"correction: {lesson['correction']}", "         "))
        log["training"].append(result)

    print("\n=== 4.2 Lesson reuse on a later, related question ===\n")
    question = load_json("validation_data.json")[0]["question"]
    store = LessonStore()
    print(f"Question: {question}")
    loaded = store.relevant(question, reference)
    print(f"Lessons loaded before answering: {[lesson['lesson_id'] for lesson in loaded]}")
    for lesson in loaded:
        print(wrap(f"{lesson['lesson_id']}: {lesson['correction']}", "    "))
    reused = run_workflow(question, answerer, evaluator, store)
    print(f"\nAnswer (attempt 1): {reused['attempts'][0]['answer']}")
    print(f"Evaluation: {reused['final_result']}   Attempts used: {reused['n_attempts']}")
    saved = {lesson["lesson_id"]: lesson["use_count"] for lesson in load_json("lessons.json")}
    print(f"use_count in lessons.json now: {saved}")
    log["lesson_reuse"] = reused

    os.makedirs(RAW_DIR, exist_ok=True)
    with open(os.path.join(RAW_DIR, "part4_demo.json"), "w") as f:
        json.dump(log, f, indent=2)
    print("\nSaved details to reports/hw09/raw/part4_demo.json and code/hw9/part4/lessons.json")


if __name__ == "__main__":
    main()
