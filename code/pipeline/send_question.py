"""
HW8 Part 2 - send_question.py

Sends one question to <PREFIX>_inbox with a fresh correlation_id, then
waits on <PREFIX>_final until it sees the matching final result - which
only appears after Planner, Writer, and Reviewer have each done their
part, in order, over Kafka.
"""

import json
import os
import time
import uuid

from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from topics import INBOX_TOPIC, FINAL_TOPIC

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")

# LLM calls in Planner + Writer take real time, so allow a generous window
TIMEOUT_SECONDS = 120


def main():
    question = "What should a patient know before joining a Phase II clinical trial?"
    correlation_id = str(uuid.uuid4())

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    partitions = consumer.partitions_for_topic(FINAL_TOPIC) or {0}
    topic_partitions = [TopicPartition(FINAL_TOPIC, p) for p in partitions]
    consumer.assign(topic_partitions)
    consumer.seek_to_beginning(*topic_partitions)

    request = {"correlation_id": correlation_id, "question": question}
    print(f"[send_question] Sending question to {INBOX_TOPIC} (correlation_id={correlation_id})")
    print(f"[send_question] Question: {question}")
    producer.send(INBOX_TOPIC, value=request)
    producer.flush()

    print(f"[send_question] Waiting on {FINAL_TOPIC} for the matching result ...")
    deadline = time.time() + TIMEOUT_SECONDS
    while time.time() < deadline:
        records = consumer.poll(timeout_ms=500)
        for _tp, messages in records.items():
            for msg in messages:
                result = msg.value
                if result.get("correlation_id") == correlation_id:
                    print("\n=== FINAL RESULT ===")
                    print(json.dumps(result, indent=2))
                    consumer.close()
                    producer.close()
                    return

    consumer.close()
    producer.close()
    raise TimeoutError(f"No final result received for correlation_id {correlation_id} within {TIMEOUT_SECONDS}s")


if __name__ == "__main__":
    main()
