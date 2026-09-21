import csv
import json
import os
from datetime import datetime

import yaml

CORPUS_DIR = os.path.join("data", "corpus")
REPORTS_DIR = os.path.join("reports", "hw03")
QUESTIONS_PATH = os.path.join(REPORTS_DIR, "questions.yaml")
SOURCES_PATH = os.path.join(REPORTS_DIR, "SOURCES.md")
MANIFEST_PATH = os.path.join(REPORTS_DIR, "CORPUS_MANIFEST.json")
METRICS_PATH = os.path.join(REPORTS_DIR, "METRICS.md")
RAW_DIR = os.path.join(REPORTS_DIR, "raw")
RUN_LOG_PATH = os.path.join(REPORTS_DIR, "RUN_LOG.txt")
AI_USE_PATH = os.path.join(REPORTS_DIR, "AI_USE.md")
OUTPUT_PATH = os.path.join(REPORTS_DIR, "verification.json")

MIN_CORPUS_BYTES = 200_000
EXPECTED_TECHNIQUES = {"token", "semantic", "sentence_window"}


def check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" -- {detail}" if detail else ""))
    return {"check": label, "status": status, "detail": detail}


def main():
    results = []

    # 1. Corpus exists and clears the 200KB minimum
    corpus_files = [f for f in os.listdir(CORPUS_DIR) if f.endswith(".txt")] if os.path.isdir(CORPUS_DIR) else []
    total_bytes = sum(os.path.getsize(os.path.join(CORPUS_DIR, f)) for f in corpus_files)
    results.append(check(
        "Corpus directory exists with .txt files",
        len(corpus_files) > 0,
        f"{len(corpus_files)} files found"
    ))
    results.append(check(
        "Corpus size >= 200KB",
        total_bytes >= MIN_CORPUS_BYTES,
        f"{total_bytes / 1024:.1f} KB"
    ))

    # 2. SOURCES.md and CORPUS_MANIFEST.json exist
    results.append(check("SOURCES.md exists", os.path.isfile(SOURCES_PATH)))
    results.append(check("CORPUS_MANIFEST.json exists", os.path.isfile(MANIFEST_PATH)))

    if os.path.isfile(MANIFEST_PATH):
        with open(MANIFEST_PATH) as f:
            manifest = json.load(f)
        results.append(check(
            "Manifest file count matches corpus file count",
            manifest.get("total_files") == len(corpus_files),
            f"manifest says {manifest.get('total_files')}, found {len(corpus_files)}"
        ))

    # 3. questions.yaml has exactly 5 questions, each with required fields,
    #    and at least 2 marked single_source
    if os.path.isfile(QUESTIONS_PATH):
        with open(QUESTIONS_PATH) as f:
            questions = yaml.safe_load(f)
        results.append(check("questions.yaml has 5 questions", len(questions) == 5, f"found {len(questions)}"))
        required_fields = {"id", "question", "expected_answer", "expected_source"}
        all_fields_present = all(required_fields.issubset(q.keys()) for q in questions)
        results.append(check("All questions have required fields", all_fields_present))
        single_source_count = sum(1 for q in questions if q.get("single_source"))
        results.append(check(
            "At least 2 questions marked single_source",
            single_source_count >= 2,
            f"{single_source_count} found"
        ))
    else:
        results.append(check("questions.yaml exists", False))

    # 4. METRICS.md exists and mentions all three techniques
    if os.path.isfile(METRICS_PATH):
        with open(METRICS_PATH) as f:
            metrics_text = f.read().lower()
        results.append(check("METRICS.md exists", True))
        results.append(check(
            "METRICS.md mentions all 3 techniques",
            all(t.replace("_", "") in metrics_text.replace("-", "").replace("_", "") for t in EXPECTED_TECHNIQUES),
        ))
    else:
        results.append(check("METRICS.md exists", False))

    # 5. raw/ directory has all 3 per-technique CSVs + combined JSON
    if os.path.isdir(RAW_DIR):
        raw_files = os.listdir(RAW_DIR)
        for technique in EXPECTED_TECHNIQUES:
            expected_name = f"retrieval_{technique}.csv"
            results.append(check(f"raw/{expected_name} exists", expected_name in raw_files))
        results.append(check("raw/retrieval_all.json exists", "retrieval_all.json" in raw_files))

        # Spot-check: each CSV has 15 rows (5 questions x top-3) plus header
        for technique in EXPECTED_TECHNIQUES:
            path = os.path.join(RAW_DIR, f"retrieval_{technique}.csv")
            if os.path.isfile(path):
                with open(path) as f:
                    row_count = sum(1 for _ in csv.reader(f)) - 1  # minus header
                results.append(check(
                    f"retrieval_{technique}.csv has 15 data rows (5 questions x top-3)",
                    row_count == 15,
                    f"found {row_count} rows"
                ))
    else:
        results.append(check("raw/ directory exists", False))

    # 6. RUN_LOG.txt and AI_USE.md exist
    results.append(check("RUN_LOG.txt exists", os.path.isfile(RUN_LOG_PATH)))
    results.append(check("AI_USE.md exists", os.path.isfile(AI_USE_PATH)))

    passed = sum(1 for r in results if r["status"] == "PASS")
    total = len(results)

    output = {
        "run_timestamp": datetime.now().isoformat(),
        "checks_passed": passed,
        "checks_total": total,
        "all_passed": passed == total,
        "results": results,
    }

    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{passed}/{total} checks passed")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()