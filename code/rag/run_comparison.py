import csv
import json
import os
import time

import numpy as np
import yaml

from common import configure_global_settings, get_embed_model
import token_chunking
import semantic_chunking
import sentence_window_chunking

QUESTIONS_PATH = os.path.join("reports", "hw03", "questions.yaml")
RAW_DIR = os.path.join("reports", "hw03", "raw")
METRICS_PATH = os.path.join("reports", "hw03", "METRICS.md")

K = 3

TECHNIQUES = {
    "token": token_chunking,
    "semantic": semantic_chunking,
    "sentence_window": sentence_window_chunking,
}


def cosine_similarity(vec_a, vec_b):
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def load_questions():
    with open(QUESTIONS_PATH, "r") as f:
        return yaml.safe_load(f)


def run_technique(name, module, questions, embed_model):
    print(f"\n{'=' * 60}\nBuilding index for: {name}\n{'=' * 60}")
    index, nodes = module.build_index()
    num_chunks = len(nodes)
    avg_chunk_len = sum(len(n.get_content()) for n in nodes) / num_chunks
    print(f"{name}: {num_chunks} chunks, avg length {avg_chunk_len:.1f} chars")

    all_rows = []
    per_query_stats = []

    for q in questions:
        query = q["question"]
        expected_source = q.get("expected_source", "")

        query_embedding = embed_model.get_query_embedding(query)

        start = time.perf_counter()
        retriever = index.as_retriever(similarity_top_k=K)
        results = retriever.retrieve(query)
        latency_ms = (time.perf_counter() - start) * 1000

        cosine_sims = []
        found_expected = False

        for rank, node_with_score in enumerate(results, start=1):
            node = node_with_score.node
            chunk_text = node.get_content()
            store_score = node_with_score.score
            file_name = node.metadata.get("file_name", "")

            if expected_source and expected_source in file_name:
                found_expected = True

            chunk_embedding = embed_model.get_text_embedding(chunk_text)
            cosine_sim = cosine_similarity(query_embedding, chunk_embedding)
            cosine_sims.append(cosine_sim)

            all_rows.append({
                "technique": name,
                "question_id": q["id"],
                "query": query,
                "rank": rank,
                "store_score": round(store_score, 4) if store_score is not None else None,
                "cosine_sim": round(cosine_sim, 4),
                "chunk_len": len(chunk_text),
                "file_name": file_name,
                "preview": chunk_text[:160].replace("\n", " "),
                "latency_ms": round(latency_ms, 2),
            })

        top1_cosine = cosine_sims[0] if cosine_sims else 0.0
        mean_at_k_cosine = sum(cosine_sims) / len(cosine_sims) if cosine_sims else 0.0

        per_query_stats.append({
            "question_id": q["id"],
            "top1_cosine": top1_cosine,
            "mean_at_k_cosine": mean_at_k_cosine,
            "latency_ms": latency_ms,
            "recall_hit": found_expected,
        })

        print(f"  {q['id']}: top1_cosine={top1_cosine:.4f} mean@{K}_cosine={mean_at_k_cosine:.4f} "
              f"recall_hit={found_expected} latency={latency_ms:.2f}ms")

    summary = {
        "technique": name,
        "num_chunks": num_chunks,
        "avg_chunk_len": avg_chunk_len,
        "avg_top1_cosine": sum(s["top1_cosine"] for s in per_query_stats) / len(per_query_stats),
        "avg_mean_at_k_cosine": sum(s["mean_at_k_cosine"] for s in per_query_stats) / len(per_query_stats),
        "recall_at_k": sum(1 for s in per_query_stats if s["recall_hit"]) / len(per_query_stats),
        "avg_latency_ms": sum(s["latency_ms"] for s in per_query_stats) / len(per_query_stats),
    }

    return all_rows, summary


def save_raw(all_rows_by_technique, chunk_stats):
    os.makedirs(RAW_DIR, exist_ok=True)
    combined = []
    for name, rows in all_rows_by_technique.items():
        combined.extend(rows)

        csv_path = os.path.join(RAW_DIR, f"retrieval_{name}.csv")
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {csv_path}")

    json_path = os.path.join(RAW_DIR, "retrieval_all.json")
    with open(json_path, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"Wrote {json_path}")

    stats_path = os.path.join(RAW_DIR, "chunk_stats.json")
    with open(stats_path, "w") as f:
        json.dump(chunk_stats, f, indent=2)
    print(f"Wrote {stats_path}")


def write_metrics_md(summaries):
    lines = [
        "# METRICS.md",
        "",
        "Retrieval quality comparison across Token / Semantic / Sentence-window "
        "chunking techniques, averaged over all 5 questions in questions.yaml "
        f"(top-{K} retrieval).",
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
    lines.append("*(Observations and conclusion to be added after reviewing raw/ retrieval output.)*")

    with open(METRICS_PATH, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"Wrote {METRICS_PATH}")


if __name__ == "__main__":
    configure_global_settings()
    embed_model = get_embed_model()
    questions = load_questions()
    print(f"Loaded {len(questions)} questions from {QUESTIONS_PATH}")

    all_rows_by_technique = {}
    summaries = []
    chunk_stats = {}

    for name, module in TECHNIQUES.items():
        rows, summary = run_technique(name, module, questions, embed_model)
        all_rows_by_technique[name] = rows
        summaries.append(summary)
        chunk_stats[name] = {
            "num_chunks": summary["num_chunks"],
            "avg_chunk_len": summary["avg_chunk_len"],
        }

    save_raw(all_rows_by_technique, chunk_stats)
    write_metrics_md(summaries)