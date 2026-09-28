import json, os, re
import ollama
from rag import build_index, retrieve, print_retrieval

LLM = "qwen3:8b"
REFUSAL = "I cannot answer this question from the provided documents"
MIN_SCORE = 0.55          # chunks scoring below this are dropped in config C
OUT = "reports/hw04/raw"
os.makedirs(OUT, exist_ok=True)

QUESTIONS = [
    {"id": "Q1", "type": "one chunk",
     "question": "How long does a HW4 session last?",
     "expected": "30 minutes", "source": "01_session_auth_hw4.txt"},
    {"id": "Q2", "type": "two chunks",
     "question": "What is the name of the HW4 session cookie, and how long is the HW3 idle timeout?",
     "expected": "session_id; 5 minutes", "source": "01_session_auth_hw4.txt + 02_session_hw3_legacy.txt"},
    {"id": "Q3", "type": "similar info across documents",
     "question": "How do the HW3 and HW4 sessions differ in where the session data is stored?",
     "expected": "HW3: inside a signed cookie; HW4: in the sessions table in MySQL, cookie holds only a token",
     "source": "01_session_auth_hw4.txt + 02_session_hw3_legacy.txt"},
    {"id": "Q4", "type": "ambiguous",
     "question": "How long does the session last?",
     "expected": "ambiguous: HW3 is 5 minutes, HW4 is 30 minutes",
     "source": "01_session_auth_hw4.txt + 02_session_hw3_legacy.txt"},
    {"id": "Q5", "type": "not in documents",
     "question": "What was the p99 latency of the fixed endpoint at page size 200 in the second measurement run?",
     "expected": "REFUSE (p99 is not in the documents)", "source": "none"},
    {"id": "Q6", "type": "unrelated",
     "question": "What is the capital of France?",
     "expected": "REFUSE", "source": "none"},
]


def ask_llm(prompt):
    r = ollama.chat(model=LLM, messages=[{"role": "user", "content": prompt}],
                    think=False, options={"temperature": 0, "seed": 5825})
    return re.sub(r"<think>.*?</think>", "", r["message"]["content"], flags=re.S).strip()


# ---------- (A) No RAG ----------
def config_a(q):
    return ask_llm(q), []


# ---------- (B) Basic RAG: top-k raw chunks pasted in ----------
def config_b(q, hits):
    context = "\n\n".join(h["text"] for h in hits)
    return ask_llm(f"Context:\n{context}\n\nQuestion: {q}\nAnswer:"), hits


# ---------- (C) Context-engineered RAG ----------
def words(t):
    return set(re.findall(r"\w+", t.lower()))

def engineer(hits):
    kept = []
    for h in hits:
        if h["score"] < MIN_SCORE:
            continue                                   # drop irrelevant
        w = words(h["text"])
        if any(len(w & words(k["text"])) / len(w | words(k["text"])) > 0.8 for k in kept):
            continue                                   # drop duplicate
        kept.append(h)
    return sorted(kept, key=lambda h: -h["score"])     # best evidence first

METRIC_TERMS = ["p50", "p95", "p99", "median", "mean", "average"]

def supports(q, kept):
    """Verification step 1 (plain Python): every specific metric named in the question
    must literally appear in the kept context."""
    context = " ".join(h["text"] for h in kept).lower()
    for term in METRIC_TERMS:
        if term in q.lower() and term not in context:
            return False
    # 'second run' style qualifiers must also appear in the context
    if "second" in q.lower() and "second" not in context:
        return False
    return True

def config_c(q, hits):
    kept = engineer(hits)
    if not kept or not supports(q, kept):
        return REFUSAL + ".", kept
    context = "\n\n".join(f"[{i}] (source: {h['source']})\n{h['text']}"
                          for i, h in enumerate(kept, 1))
    prompt = (
        "You answer using ONLY the numbered context below.\n"
        "Rules:\n"
        "1. Use only facts written in the context. Do not use outside knowledge.\n"
        "2. After each fact, cite the source number like [1].\n"
        f"3. If the context does not contain the answer, reply exactly: {REFUSAL}.\n"
        "4. Read EVERY numbered context, not only the first one.\n"
        "5. If different contexts give different answers (for example HW3 and HW4 give different "
        "durations), list each answer separately and say which one it belongs to.\n\n"
        f"Context:\n{context}\n\nQuestion: {q}\nAnswer:"
    )
    return ask_llm(prompt), kept


if __name__ == "__main__":
    index, chunks = build_index()
    results = []
    for item in QUESTIONS:
        q = item["question"]
        hits = retrieve(index, chunks, q, k=3)
        print("=" * 90)
        print(f"{item['id']} ({item['type']})")
        print_retrieval(q, hits)
        a, _ = config_a(q)
        b, _ = config_b(q, hits)
        c, kept = config_c(q, hits)
        print(f"\n  (A) No RAG      : {a}")
        print(f"  (B) Basic RAG   : {b}")
        print(f"  (C) Context RAG : {c}  [kept {len(kept)} of {len(hits)} chunks]")
        results.append({**item, "retrieved": [{"chunk_id": h["chunk_id"], "score": round(h["score"], 4)} for h in hits],
                        "kept_in_C": [h["chunk_id"] for h in kept], "A": a, "B": b, "C": c})
    json.dump(results, open(f"{OUT}/three_config_results.json", "w"), indent=2)
    print("\nsaved", f"{OUT}/three_config_results.json")