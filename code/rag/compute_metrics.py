import csv
import json
import os

import yaml

QUESTIONS_PATH = os.path.join("reports", "hw03", "questions.yaml")
RAW_DIR = os.path.join("reports", "hw03", "raw")
CHUNK_STATS_PATH = os.path.join(RAW_DIR, "chunk_stats.json")
METRICS_PATH = os.path.join("reports", "hw03", "METRICS.md")

TECHNIQUES = ["token", "semantic", "sentence_window"]
K = 3


def load_questions():
    with open(QUESTIONS_PATH) as f:
        return {q["id"]: q for q in yaml.safe_load(f)}


def load_chunk_stats():
    with open(CHUNK_STATS_PATH) as f:
        return json.load(f)


def load_technique_rows(technique):
    path = os.path.join(RAW_DIR, f"retrieval_{technique}.csv")
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def recompute_summary(technique, rows, chunk_stats, questions):
    by_question = {}
    for row in rows:
        by_question.setdefault(row["question_id"], []).append(row)

    top1_cosines = []
    mean_at_k_cosines = []
    latencies = []
    recall_hits = []

    for qid, qrows in by_question.items():
        qrows_sorted = sorted(qrows, key=lambda r: int(r["rank"]))
        cosines = [float(r["cosine_sim"]) for r in qrows_sorted]
        top1_cosines.append(cosines[0])
        mean_at_k_cosines.append(sum(cosines) / len(cosines))
        latencies.append(float(qrows_sorted[0]["latency_ms"]))

        expected_source = questions[qid]["expected_source"]
        found = any(expected_source in r["file_name"] for r in qrows_sorted)
        recall_hits.append(found)

    stats = chunk_stats[technique]
    return {
        "technique": technique,
        "num_chunks": stats["num_chunks"],
        "avg_chunk_len": stats["avg_chunk_len"],
        "avg_top1_cosine": sum(top1_cosines) / len(top1_cosines),
        "avg_mean_at_k_cosine": sum(mean_at_k_cosines) / len(mean_at_k_cosines),
        "recall_at_k": sum(recall_hits) / len(recall_hits),
        "avg_latency_ms": sum(latencies) / len(latencies),
    }


def write_metrics_md(summaries):
    lines = [
        "# METRICS.md",
        "",
        "Retrieval quality comparison across Token / Semantic / Sentence-window "
        "chunking techniques, averaged over all 5 questions in questions.yaml "
        f"(top-{K} retrieval).",
        "",
        "Recomputed by code/rag/compute_metrics.py directly from reports/hw03/raw/ "
        "-- no embeddings or retrieval were re-run to produce this table.",
        "",
        "| Technique | Chunks | Avg chunk length | Top-1 cosine | Mean@k cosine | Recall@k | Mean retrieval latency (ms) |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in summaries:
        lines.append(
            f"| {s['technique']} | {s['num_chunks']} | {s['avg_chunk_len']:.1f} | "
            f"{s['avg_top1_cosine']:.4f} | {s['avg_mean_at_k_cosine']:.4f} | "
            f"{s['recall_at_k']:.2f} | {s['avg_latency_ms']:.2f} |"
        )
    lines.append("")

    with open(METRICS_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {METRICS_PATH}")


if __name__ == "__main__":
    questions = load_questions()
    chunk_stats = load_chunk_stats()

    summaries = []
    for technique in TECHNIQUES:
        rows = load_technique_rows(technique)
        summary = recompute_summary(technique, rows, chunk_stats, questions)
        summaries.append(summary)
        print(summary)

    write_metrics_md(summaries)