"""
HW8 Part 2 - Reviewer

Reads a draft from <PREFIX>_drafts, checks it's a reasonable answer
(not empty, not too short), and sends the final verdict to
<PREFIX>_final. Never talks to Planner or Writer directly - only
through Kafka.
"""

import json
import os
from kafka import KafkaConsumer, KafkaProducer
from topics import DRAFTS_TOPIC, FINAL_TOPIC

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")

MIN_LENGTH = 20  # characters


def review(draft: str) -> str:
    """Returns 'approved' or 'needs_revision'."""
    if not draft or len(draft.strip()) < MIN_LENGTH:
        return "needs_revision"
    return "approved"


def main():
    consumer = KafkaConsumer(
        DRAFTS_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="s5825-reviewer-group",
    )
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    print("[reviewer] Ready and listening on", DRAFTS_TOPIC)

    for msg in consumer:
        draft_msg = msg.value
        correlation_id = draft_msg.get("correlation_id")
        draft = draft_msg.get("draft")
        print(f"[reviewer] Received draft (correlation_id={correlation_id})")

        status = review(draft)
        print(f"[reviewer] Verdict: {status}")

        output = {
            "correlation_id": correlation_id,
            "status": status,
            "answer": draft,
        }
        producer.send(FINAL_TOPIC, value=output)
        producer.flush()
        print(f"[reviewer] Sent final result to {FINAL_TOPIC}")


if __name__ == "__main__":
    main()
