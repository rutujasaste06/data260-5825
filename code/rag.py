import glob, os, sys
import faiss
import numpy as np
import ollama

CORPUS = "data/hw04_corpus"
EMBED_MODEL = "nomic-embed-text"
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50


def load_docs():
    docs = []
    for path in sorted(glob.glob(os.path.join(CORPUS, "*.txt"))):
        docs.append((os.path.basename(path), open(path).read()))
    return docs


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Cut text into pieces of about `size` characters that overlap by `overlap`."""
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):                      # try to end on a space, not mid-word
            space = text.rfind(" ", start, end)
            if space > start + size // 2:
                end = space
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - overlap
    return [c for c in chunks if c]


def embed(texts):
    resp = ollama.embed(model=EMBED_MODEL, input=texts)
    vecs = np.array(resp["embeddings"], dtype="float32")
    faiss.normalize_L2(vecs)                     # so inner product = cosine similarity
    return vecs


def build_index(size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    chunks = []
    for source, text in load_docs():
        for i, piece in enumerate(chunk_text(text, size, overlap)):
            chunks.append({"chunk_id": f"{source}#{i}", "source": source, "text": piece})
    vecs = embed([c["text"] for c in chunks])
    index = faiss.IndexFlatIP(vecs.shape[1])
    index.add(vecs)
    return index, chunks


def retrieve(index, chunks, question, k=3):
    scores, ids = index.search(embed([question]), k)
    return [dict(chunks[i], score=float(s)) for s, i in zip(scores[0], ids[0])]


def print_retrieval(question, hits):
    print(f"\nQUESTION: {question}")
    for rank, h in enumerate(hits, 1):
        print(f"  [{rank}] score={h['score']:.4f} source={h['source']} chunk_id={h['chunk_id']}")
        print("      " + h["text"][:200].replace("\n", " ") + "...")


if __name__ == "__main__":
    index, chunks = build_index()
    print(f"documents: {len(load_docs())}  chunks: {len(chunks)}  "
          f"(chunk_size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    q = sys.argv[1] if len(sys.argv) > 1 else "How long does a HW4 session last?"
    print_retrieval(q, retrieve(index, chunks, q, k=3))