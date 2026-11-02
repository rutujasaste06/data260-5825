"""
HW8 Part 3.I - Duplicate Delivery test

Sends ONE CREATE_TRIAL request, then sends the EXACT SAME message again
(same correlation_id, same data) to simulate a replayed/duplicate
delivery - something that can genuinely happen in real systems (a
network retry, a consumer re-reading a message it already saw, etc.).

If the worker is NOT idempotent: the two responses will contain two
DIFFERENT entity_id values -> a duplicate trial was created. BUG.

If the worker IS idempotent: the two responses will contain the SAME
entity_id value -> the replay had no extra effect. FIXED.
"""

import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from topics import REQUEST_TOPIC, RESPONSE_TOPIC

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")


def wait_for_response(consumer, correlation_id, timeout_seconds=30) -> dict:
    deadline = time.time() + timeout_seconds
    scanned = 0
    while time.time() < deadline:
        records = consumer.poll(timeout_ms=1000)
        for _tp, messages in records.items():
            for msg in messages:
                scanned += 1
                if msg.value.get("correlation_id") == correlation_id:
                    print(f"[test] (scanned {scanned} messages on this topic before finding the match)")
                    return msg.value
    raise TimeoutError(f"No response for correlation_id {correlation_id} after scanning {scanned} messages")


def main():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    partitions = consumer.partitions_for_topic(RESPONSE_TOPIC) or {0}
    tps = [TopicPartition(RESPONSE_TOPIC, p) for p in partitions]
    consumer.assign(tps)
    consumer.seek_to_beginning(*tps)

    correlation_id = str(uuid.uuid4())
    request = {
        "correlation_id": correlation_id,
        "reply_to": RESPONSE_TOPIC,
        "operation": "CREATE_TRIAL",
        "data": {
            "trialTitle": "Duplicate Delivery Test Trial",
            "nctNumber": "NCT00000099",
            "trialPhase": "Phase I",
        },
    }

    print(f"[test] correlation_id for this test: {correlation_id}")

    print("\n[test] Sending CREATE_TRIAL request (1st time, original)")
    producer.send(REQUEST_TOPIC, value=request)
    producer.flush()
    response1 = wait_for_response(consumer, correlation_id)
    print(f"[test] Response #1: {response1}")

    print("\n[test] Replaying the EXACT SAME message (same correlation_id) - simulating a duplicate delivery")
    producer.send(REQUEST_TOPIC, value=request)
    producer.flush()
    response2 = wait_for_response(consumer, correlation_id)
    print(f"[test] Response #2: {response2}")

    entity_id_1 = response1.get("entity_id")
    entity_id_2 = response2.get("entity_id")

    print("\n=== RESULT ===")
    print(f"entity_id from response #1: {entity_id_1}")
    print(f"entity_id from response #2: {entity_id_2}")
    if entity_id_1 == entity_id_2:
        print("SAME entity_id both times -> idempotent. No duplicate trial was created.")
    else:
        print("DIFFERENT entity_id each time -> NOT idempotent. A duplicate trial was created. BUG.")

    consumer.close()
    producer.close()


if __name__ == "__main__":
    main()
