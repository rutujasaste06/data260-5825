# METRICS.md

Retrieval quality comparison across Token / Semantic / Sentence-window chunking techniques, averaged over all 5 questions in questions.yaml (top-3 retrieval).

Recomputed by code/rag/compute_metrics.py directly from reports/hw03/raw/ -- no embeddings or retrieval were re-run to produce this table.

| Technique | Chunks | Avg chunk length | Top-1 cosine | Mean@k cosine | Recall@k | Mean retrieval latency (ms) |
|---|---|---|---|---|---|---|
| token | 258 | 935.0 | 0.6954 | 0.6246 | 0.80 | 4.93 |
| semantic | 135 | 1650.8 | 0.7147 | 0.6102 | 1.00 | 4.17 |
| sentence_window | 1063 | 209.7 | 0.7125 | 0.6760 | 1.00 | 10.92 |

