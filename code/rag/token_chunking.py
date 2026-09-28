"""
Technique 1: Token-based chunking.

Cuts every document into fixed-size pieces by counting tokens (roughly,
word-pieces), with a small overlap between consecutive chunks so we don't
lose context right at the cut point. This is the crudest of the three
techniques -- it doesn't know or care where sentences or paragraphs end.

Run directly to test retrieval for one sample query:
    python code/rag/token_chunking.py
"""

import time

import numpy as np
from llama_index.core.node_parser import TokenTextSplitter
from llama_index.core import VectorStoreIndex

from common import configure_global_settings, load_documents, get_embed_model

# Chunk size and overlap, in tokens (word-piece units, not raw characters)
CHUNK_SIZE = 256
CHUNK_OVERLAP = 20


def build_index():
    """Splits all documents into token-based chunks and builds an
    in-memory vector index over them."""
    splitter = TokenTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    documents = load_documents()
    nodes = splitter.get_nodes_from_documents(documents)
    index = VectorStoreIndex(nodes)
    return index, nodes


def cosine_similarity(vec_a, vec_b):

    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def retrieve(index, query, k=3):
    
    embed_model = get_embed_model()
    query_embedding = embed_model.get_query_embedding(query)

    print(f"\n=== TOKEN CHUNKING === Query: {query!r}")
    print(f"Query embedding dimension: {len(query_embedding)}")
    print(f"Query embedding (first 8 values): {query_embedding[:8]}")

    start = time.perf_counter()
    retriever = index.as_retriever(similarity_top_k=k)
    results = retriever.retrieve(query)
    latency_ms = (time.perf_counter() - start) * 1000

    doc_embeddings = []
    rows = []
    for rank, node_with_score in enumerate(results, start=1):
        node = node_with_score.node
        chunk_text = node.get_content()
        store_score = node_with_score.score

        chunk_embedding = embed_model.get_text_embedding(chunk_text)
        doc_embeddings.append(chunk_embedding)
        cosine_sim = cosine_similarity(query_embedding, chunk_embedding)

        preview = chunk_text[:160].replace("\n", " ")
        rows.append({
            "technique": "token",
            "query": query,
            "rank": rank,
            "store_score": round(store_score, 4) if store_score is not None else None,
            "cosine_sim": round(cosine_sim, 4),
            "chunk_len": len(chunk_text),
            "preview": preview,
            "latency_ms": round(latency_ms, 2),
        })
        print(f"  rank={rank} store_score={store_score:.4f} cosine_sim={cosine_sim:.4f} "
              f"chunk_len={len(chunk_text)} preview={preview!r}")

    doc_matrix = np.array(doc_embeddings)
    query_vec = np.array(query_embedding)
    print(f"Query vector shape: {query_vec.shape}")
    print(f"Stacked doc vectors shape: {doc_matrix.shape}")
    print(f"Retrieval latency: {latency_ms:.2f} ms")

    return rows


if __name__ == "__main__":
    configure_global_settings()
    index, nodes = build_index()
    print(f"Token chunking produced {len(nodes)} chunks from the corpus")
    avg_len = sum(len(n.get_content()) for n in nodes) / len(nodes)
    print(f"Average chunk length: {avg_len:.1f} characters")

    # Sample query for a quick sanity check -- full 5-question run comes later
    sample_query = "What daily dose of cinnamon was tested for lowering HbA1c in type 2 diabetics?"
    retrieve(index, sample_query, k=3)