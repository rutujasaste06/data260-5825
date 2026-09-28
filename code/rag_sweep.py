import json
from rag import build_index, retrieve, print_retrieval
from rag_run import QUESTIONS, config_b, config_c

SWEEP_QUESTIONS = ["Q2", "Q3"]      # Q2 needs two chunks, Q3 needs facts from two documents
KS = [1, 3, 5]

if __name__ == "__main__":
    index, chunks = build_index()
    results = []
    for item in QUESTIONS:
        if item["id"] not in SWEEP_QUESTIONS:
            continue
        q = item["question"]
        for k in KS:
            hits = retrieve(index, chunks, q, k=k)
            print("=" * 90)
            print(f"{item['id']}  k={k}")
            print_retrieval(q, hits)
            b, _ = config_b(q, hits)
            c, kept = config_c(q, hits)
            print(f"\n  (B) Basic RAG   : {b}")
            print(f"  (C) Context RAG : {c}  [kept {len(kept)} of {len(hits)} chunks]")
            results.append({
                "id": item["id"], "k": k,
                "retrieved": [{"chunk_id": h["chunk_id"], "score": round(h["score"], 4)} for h in hits],
                "kept_in_C": [h["chunk_id"] for h in kept],
                "B": b, "C": c,
            })
    json.dump(results, open("reports/hw04/raw/k_sweep_results.json", "w"), indent=2)
    print("\nsaved reports/hw04/raw/k_sweep_results.json")