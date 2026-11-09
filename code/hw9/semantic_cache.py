"""
HW9 Part 2 - Semantic response cache.

Analogy: a receptionist with a notebook of questions already answered. When a
new question arrives she does not look for the exact same words - she looks for
a question that MEANS the same thing. If she finds one that is close enough
(similarity >= threshold) she reads out the saved answer. If not, she sends the
question to the expert (the HW8 agent pipeline) and writes the new question
and answer in the notebook.

"Closeness" = cosine similarity between sentence embeddings (1.0 = same
meaning, 0.0 = unrelated). The embeddings live in Redis, in a RediSearch vector
index, so Redis does the nearest-neighbour search for us.
"""

import logging
import time
import uuid
from datetime import datetime

import numpy as np
from redis.commands.search.field import TextField, VectorField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError

PREFIX = "s5825"
INDEX_NAME = f"{PREFIX}:cache_idx"
KEY_PREFIX = f"{PREFIX}:cache:"
VERSION_KEY = f"{PREFIX}:data_version"
EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384
DEFAULT_THRESHOLD = 0.85

logger = logging.getLogger("semantic_cache")


def _now():
    return datetime.now().isoformat(timespec="milliseconds")


class SemanticCache:
    def __init__(self, redis_client, agent_fn, threshold=DEFAULT_THRESHOLD):
        # redis_client must NOT use decode_responses (embeddings are raw bytes)
        self.redis_client = redis_client
        self.agent_fn = agent_fn
        self.threshold = threshold
        self._model = None

    # ---------- setup ----------
    def _embedder(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(EMBED_MODEL_NAME)
        return self._model

    def embed(self, text):
        vec = self._embedder().encode(text, normalize_embeddings=True)
        return np.asarray(vec, dtype=np.float32).tobytes()

    def reset(self):
        """Empty the notebook: drop the index and all cached entries, then rebuild it."""
        try:
            self.redis_client.ft(INDEX_NAME).dropindex(delete_documents=True)
        except ResponseError:
            pass  # index did not exist yet
        self.redis_client.ft(INDEX_NAME).create_index(
            [
                TextField("query"),
                VectorField(
                    "embedding",
                    "FLAT",
                    {"TYPE": "FLOAT32", "DIM": EMBED_DIM, "DISTANCE_METRIC": "COSINE"},
                ),
            ],
            definition=IndexDefinition(prefix=[KEY_PREFIX], index_type=IndexType.HASH),
        )

    def current_version(self):
        """The data-version marker: bumped whenever the underlying data changes."""
        value = self.redis_client.get(VERSION_KEY)
        return value.decode() if value else "1"

    # ---------- cache operations ----------
    def lookup(self, vec):
        """Nearest cached query to vec, or None if the cache is empty."""
        query = (
            Query("*=>[KNN 1 @embedding $vec AS dist]")
            .sort_by("dist")
            .return_fields("query", "answer", "data_version", "dist")
            .dialect(2)
        )
        result = self.redis_client.ft(INDEX_NAME).search(query, query_params={"vec": vec})
        if not result.docs:
            return None
        doc = result.docs[0]
        return {
            "key": doc.id,
            "query": doc.query,
            "answer": doc.answer,
            "data_version": doc.data_version,
            "similarity": 1.0 - float(doc.dist),  # Redis returns cosine DISTANCE
        }

    def bump_version(self):
        """Call whenever the underlying data changes: marks every older cached answer as outdated."""
        return int(self.redis_client.incr(VERSION_KEY))

    def store(self, question, vec, answer, data_version):
        self.redis_client.hset(
            f"{KEY_PREFIX}{uuid.uuid4().hex}",
            mapping={
                "query": question,
                "answer": answer,
                "data_version": data_version,
                "created_at": _now(),
                "embedding": vec,
            },
        )

    # ---------- the query handler ----------
    def handle_query(self, question, threshold=None, check_version=False):
        threshold = self.threshold if threshold is None else threshold
        t_start = time.perf_counter()
        started_at = _now()

        t0 = time.perf_counter()
        vec = self.embed(question)
        embed_ms = (time.perf_counter() - t0) * 1000

        t0 = time.perf_counter()
        match = self.lookup(vec)
        search_ms = (time.perf_counter() - t0) * 1000

        best = match["similarity"] if match else None

        # Part 3.5 invalidation: a hit whose stored data_version is older than the current
        # marker is outdated - delete it and fall through to the miss path (re-run, re-store).
        stale = False
        if match and best >= threshold and check_version:
            current = self.current_version()
            if match["data_version"] != current:
                stale = True
                self.redis_client.delete(match["key"])
                logger.info(
                    "CACHE STALE saved data_version=%s but current=%s - entry removed, treating as a miss | %s",
                    match["data_version"], current, question,
                )

        if match and best >= threshold and not stale:
            latency_ms = (time.perf_counter() - t_start) * 1000
            logger.info(
                "CACHE HIT  similarity=%.3f (threshold %.2f) embed=%.1fms search=%.1fms | %s",
                best, threshold, embed_ms, search_ms, question,
            )
            return {
                "question": question,
                "answer": match["answer"],
                "is_cached": True,
                "similarity": best,
                "matched_query": match["query"],
                "latency_ms": latency_ms,
                "started_at": started_at,
                "finished_at": _now(),
            }

        shown = "n/a (cache empty)" if best is None else f"{best:.3f}"
        logger.info(
            "CACHE MISS best_similarity=%s (threshold %.2f) - running HW8 agent | %s",
            shown, threshold, question,
        )
        t0 = time.perf_counter()
        answer, status = self.agent_fn(question)
        agent_ms = (time.perf_counter() - t0) * 1000
        self.store(question, vec, answer, self.current_version())
        latency_ms = (time.perf_counter() - t_start) * 1000
        logger.info(
            "STORED     agent=%.1fms reviewer=%s total=%.1fms",
            agent_ms, status, latency_ms,
        )
        return {
            "question": question,
            "answer": answer,
            "is_cached": False,
            "similarity": best,
            "matched_query": match["query"] if match else None,
            "latency_ms": latency_ms,
            "started_at": started_at,
            "finished_at": _now(),
        }
