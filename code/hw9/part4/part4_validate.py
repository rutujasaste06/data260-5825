"""
HW9 Part 4.3 - validate each lesson on validation_data.json before keeping it.

A lesson is KEPT only if, compared with the same questions answered without it:
  - failure cases improve or stay the same,
  - previously correct answers stay correct,
  - unrelated questions (trials not in the listings) do not get unsupported answers.
In other words: no question may go from correct to incorrect.

Candidates lesson_004 and lesson_005 are deliberately risky rules added to test the gate.
Lessons that pass are written to lessons_validated.json. test_data.json is not touched here.

Run from the repo root:   python code/hw9/part4/part4_validate.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import AnsweringAgent, Evaluator, LessonStore, load_json, run_workflow, save_json  # noqa: E402

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "reports", "hw09", "raw")
# Two deliberately risky candidates, added to test the validation gate (not learned from a failure):
#   lesson_004: an over-broad rule     lesson_005: a lesson over-generalized from one example
CANDIDATES = [
    ("The answer refuses when the listing snapshot does not contain the requested value.",
     "If the listing snapshot does not contain the requested value, give your best "
     "estimate instead of saying you have no information."),
    ("Slot counts in the listing snapshot are too high, as the NeuroCalm failure showed.",
     "Available slot counts in the listing snapshot are always out of date: every trial "
     "currently has 4 available slots."),
]


def run_set(answerer, evaluator, questions, lessons):
    """One attempt per question (no revision), so we measure the lesson's own effect."""
    store = LessonStore(persist=False)
    store.lessons = [dict(lesson) for lesson in lessons]
    out = {}
    for item in questions:
        result = run_workflow(item["question"], answerer, evaluator, store, max_attempts=1)
        out[item["id"]] = {"correct": result["final_result"] == "PASS", "answer": result["final_answer"]}
    return out


def main():
    reference = load_json("reference_data.json")
    evaluator = Evaluator(reference)
    answerer = AnsweringAgent(load_json("listing_snapshot.json"))
    questions = load_json("validation_data.json")

    store = LessonStore()
    for pattern, rule in CANDIDATES:
        if not any(lesson["correction"] == rule for lesson in store.lessons):
            store.add(pattern, rule)
    lessons = store.lessons

    print("=== 4.3 Validation (validation_data.json, 7 questions) ===\n")
    baseline = run_set(answerer, evaluator, questions, [])
    print(f"Without any lesson: {sum(v['correct'] for v in baseline.values())}/{len(questions)} correct")
    print("  wrong: " + ", ".join(q for q, v in baseline.items() if not v["correct"]) + "\n")

    report, kept = [], []
    for lesson in lessons:
        with_lesson = run_set(answerer, evaluator, questions, [lesson])
        fixed = [q for q in baseline if not baseline[q]["correct"] and with_lesson[q]["correct"]]
        regressed = [q for q in baseline if baseline[q]["correct"] and not with_lesson[q]["correct"]]
        decision = "KEEP" if not regressed else "REMOVE"
        print(f"{lesson['lesson_id']}: {lesson['correction']}")
        print(f"   correct with lesson: {sum(v['correct'] for v in with_lesson.values())}/{len(questions)}   "
              f"improved: {fixed or 'none'}   regressed: {regressed or 'none'}   -> {decision}")
        for q in regressed:
            print(f"   regression {q}: {with_lesson[q]['answer']}")
        print()
        report.append({"lesson_id": lesson["lesson_id"], "improved": fixed, "regressed": regressed,
                       "decision": decision, "answers_with_lesson": with_lesson})
        if decision == "KEEP":
            kept.append(lesson)

    save_json("lessons_validated.json", kept)
    print(f"Kept {len(kept)} of {len(lessons)} lessons -> lessons_validated.json "
          f"({[lesson['lesson_id'] for lesson in kept]})")
    os.makedirs(RAW_DIR, exist_ok=True)
    with open(os.path.join(RAW_DIR, "part4_validation.json"), "w") as f:
        json.dump({"baseline": baseline, "lessons": report}, f, indent=2)
    print("Saved details to reports/hw09/raw/part4_validation.json")


if __name__ == "__main__":
    main()
