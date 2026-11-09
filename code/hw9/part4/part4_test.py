"""
HW9 Part 4.4 - final evaluation on test_data.json for the four system variants.

  1. Baseline            - Answering Agent only, one attempt, no lessons
  2. Evaluator Repair    - + Evaluator feedback and one revision (max 2 attempts)
  3. Lesson Memory       - + every saved lesson (lessons.json), loaded before answering
  4. Validated Improvement - + only the lessons that passed validation (lessons_validated.json)

test_data.json was not used to create or choose any lesson. Lessons are loaded read-only here.

Run from the repo root:   python code/hw9/part4/part4_test.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents import AnsweringAgent, Evaluator, LessonStore, load_json, run_workflow  # noqa: E402

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "reports", "hw09", "raw")


def main():
    if not os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "lessons_validated.json")):
        sys.exit("Run part4_validate.py first (it creates lessons_validated.json).")
    reference = load_json("reference_data.json")
    evaluator = Evaluator(reference)
    answerer = AnsweringAgent(load_json("listing_snapshot.json"))
    questions = load_json("test_data.json")
    answerer.answer("warm up")  # load the model before timing starts

    variants = [
        ("Baseline", 1, None),
        ("Evaluator Repair", 2, None),
        ("Lesson Memory", 2, "lessons.json"),
        ("Validated Improvement", 2, "lessons_validated.json"),
    ]
    summary, details = [], {}
    print("=== 4.4 Final test (test_data.json, 8 questions) ===")
    for name, max_attempts, lesson_file in variants:
        store = LessonStore(lesson_file, persist=False) if lesson_file else None
        print(f"\n--- {name} ---")
        results = []
        for item in questions:
            result = run_workflow(item["question"], answerer, evaluator, store, max_attempts=max_attempts)
            results.append(result)
            print(f"[{item['id']}] {result['final_result']:<6} attempts={result['n_attempts']} "
                  f"lessons={result['lessons_used'] or '-'}  {result['latency_s']:.1f}s | {result['final_answer']}")
        correct = sum(r["final_result"] == "PASS" for r in results)
        summary.append({
            "variant": name,
            "correct": correct,
            "incorrect": len(results) - correct,
            "avg_attempts": sum(r["n_attempts"] for r in results) / len(results),
            "avg_latency_s": sum(r["latency_s"] for r in results) / len(results),
        })
        details[name] = results

    print("\n=== Results table (8 test questions) ===")
    print(f"{'Variant':<24}{'Correct':>8}{'Incorrect':>11}{'Avg attempts':>14}{'Avg latency (s)':>17}")
    for row in summary:
        print(f"{row['variant']:<24}{row['correct']:>8}{row['incorrect']:>11}"
              f"{row['avg_attempts']:>14.2f}{row['avg_latency_s']:>17.1f}")

    os.makedirs(RAW_DIR, exist_ok=True)
    with open(os.path.join(RAW_DIR, "part4_test_results.json"), "w") as f:
        json.dump({"summary": summary, "details": details}, f, indent=2)
    print("\nSaved details to reports/hw09/raw/part4_test_results.json")


if __name__ == "__main__":
    main()
