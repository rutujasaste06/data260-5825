"""
HW10 Part 4 - the front door: semantic cache lookup, then (on a miss) the Kafka pipeline.

One request = one trace. trace_id is the HW8 correlation_id, so the same id travels:
  cache lookup -> inbox -> Planner -> tasks -> Writer -> drafts -> Reviewer -> final -> evaluator.
Spans written here: request (end to end), cache_lookup, queue_final.
The Planner / Writer / Reviewer write their own spans (code/pipeline/*.py).
"""

import json
import os
import sys
import time
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
sys.path.insert(0, os.path.join(HERE, "..", "hw9"))

import redis  # noqa: E402
from kafka import KafkaConsumer, KafkaProducer, TopicPartition  # noqa: E402
from redis.exceptions import ResponseError  # noqa: E402
from semantic_cache import INDEX_NAME, SemanticCache  # noqa: E402
from topics import FINAL_TOPIC, INBOX_TOPIC  # noqa: E402
from tracing import queue_span, traced, write_span  # noqa: E402

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")
THRESHOLD = 0.95        # the threshold chosen in HW9 Part 3
TIMEOUT_SECONDS = 180   # a request that gets no final result in this time is a failed trace


def get_cache():
    """The HW9 semantic cache. Creates the index only if it does not exist (never wipes the cache)."""
    cache = SemanticCache(redis.Redis(host="localhost", port=6379), agent_fn=None, threshold=THRESHOLD)
    try:
        cache.redis_client.ft(INDEX_NAME).info()
    except ResponseError:
        cache.reset()
    return cache


class TracedClient:
    def __init__(self, cache=None):
        self.cache = cache or get_cache()
        self.cache.embed("warm up")  # load the embedding model now, so no request's timing includes it
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BROKER,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        self.consumer = KafkaConsumer(
            bootstrap_servers=KAFKA_BROKER,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        )
        partitions = self.consumer.partitions_for_topic(FINAL_TOPIC) or {0}
        self.final_tps = [TopicPartition(FINAL_TOPIC, p) for p in partitions]
        self.consumer.assign(self.final_tps)

    def _wait_for_final(self, trace_id):
        deadline = time.time() + TIMEOUT_SECONDS
        while time.time() < deadline:
            for messages in self.consumer.poll(timeout_ms=500).values():
                for msg in messages:
                    if msg.value.get("correlation_id") == trace_id:
                        return msg.value
        raise TimeoutError(f"no final result within {TIMEOUT_SECONDS}s")

    def ask(self, question, simulate_failure=None):
        """Returns {trace_id, question, answer, cache_hit, status, error, latency_ms}."""
        trace_id = str(uuid.uuid4())
        start = time.time()
        answer, hit, status, error = None, False, "ok", None
        try:
            with traced(trace_id, "cache_lookup") as info:
                vec = self.cache.embed(question)
                match = self.cache.lookup(vec)
                hit = bool(match and match["similarity"] >= THRESHOLD)
                info["cache"] = "hit" if hit else "miss"
                info["similarity"] = round(match["similarity"], 4) if match else None
            if hit:
                answer = match["answer"]
            else:
                for tp in self.final_tps:  # only read results that arrive from now on
                    self.consumer.seek_to_end(tp)
                    self.consumer.position(tp)
                request = {"correlation_id": trace_id, "question": question, "sent_at": time.time()}
                if simulate_failure:
                    request["simulate_failure"] = simulate_failure
                self.producer.send(INBOX_TOPIC, value=request)
                self.producer.flush()
                result = self._wait_for_final(trace_id)
                queue_span(trace_id, "queue_final", result.get("sent_at"))
                if result.get("status") == "error":
                    raise RuntimeError(f"{result.get('stage')} failed: {result.get('error')}")
                answer = result["answer"]
                if result["status"] == "approved":
                    self.cache.store(question, vec, answer, self.cache.current_version())
        except Exception as exc:
            status, error = "error", f"{type(exc).__name__}: {exc}"
        end = time.time()
        write_span(trace_id, "request", start, end, status, error, cache="hit" if hit else "miss")
        return {"trace_id": trace_id, "question": question, "answer": answer, "cache_hit": hit,
                "status": status, "error": error, "latency_ms": round((end - start) * 1000, 1)}
