"""
HW10 Part 3.1 - hand-label the drafts in eval_cases.json (1-5 helpfulness) into human_labels.csv.
Type q to quit; running it again continues where you stopped.

Run from the repo root:   python code/hw10/label_cases.py
"""

import csv
import json
import os
import textwrap

HERE = os.path.dirname(os.path.abspath(__file__))
CASES = os.path.join(HERE, "eval_cases.json")
LABELS = os.path.join(HERE, "human_labels.csv")


def load_labels():
    if not os.path.exists(LABELS):
        return {}
    with open(LABELS, newline="") as f:
        return {row["case_id"]: row["human_label"] for row in csv.DictReader(f)}


def save_labels(labels):
    with open(LABELS, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "human_label"])
        for case_id, label in labels.items():
            writer.writerow([case_id, label])


def main():
    with open(CASES) as f:
        cases = json.load(f)
    labels = load_labels()
    for case in cases:
        if case["case_id"] in labels:
            continue
        print("=" * 80)
        print(f"{case['case_id']}  ({len(labels)}/{len(cases)} labelled)")
        print(f"QUESTION: {case['question']}\n")
        print("DRAFT:")
        print(textwrap.indent(textwrap.fill(case["draft"], 90, replace_whitespace=False), "  "))
        while True:
            value = input("\nLabel 1-5 (q to quit): ").strip().lower()
            if value == "q":
                save_labels(labels)
                print(f"Saved {len(labels)} labels.")
                return
            if value in {"1", "2", "3", "4", "5"}:
                labels[case["case_id"]] = value
                save_labels(labels)
                break
            print("Type 1, 2, 3, 4 or 5.")
    print(f"\nDone: {len(labels)} labels saved to code/hw10/human_labels.csv")


if __name__ == "__main__":
    main()
