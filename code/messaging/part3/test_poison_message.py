"""
HW8 Part 3.III - Poison Message test

Sends, in order:
  1. A normal CREATE_TRIAL request (should succeed quickly)
  2. A "poison" CREATE_TRIAL request (trialTitle=POISON_TEST_TRIGGER_CRASH,
     which the worker is deliberately rigged to always fail on - see
     worker.py's process_operation)
  3. Another normal CREATE_TRIAL request, sent right after the poison one

This proves two things at once:
  - The normal messages (#1 and #3) both get a successful response -
    message #3 is NOT stuck waiting behind the poison message's retries.
  - The poison message (#2) is retried a bounded number of times and then
    ends up on the dead-letter topic instead of retrying forever.
"""

import json
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from topics import REQUEST_TOPIC, RESPONSE_TOPIC, DEAD_LETTER_TOPIC

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")


def make_trial_request(correlation_id: str, title: str) -> dict:
    return {
        "correlation_id": correlation_id,
        "reply_to": RESPONSE_TOPIC,
        "operation": "CREATE_TRIAL",
        "data": {
            "trialTitle": title,
            "nctNumber": "NCT00000077",
            "trialPhase": "Phase I",
        },
    }


def wait_for_message(consumer, topic_name, correlation_id, timeout_seconds=30):
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        records = consumer.poll(timeout_ms=500)
        for _tp, messages in records.items():
            for msg in messages:
                if msg.value.get("correlation_id") == correlation_id:
                    return msg.value
    return None  # not found within timeout - caller decides what that means


def main():
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    response_consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    resp_partitions = response_consumer.partitions_for_topic(RESPONSE_TOPIC) or {0}
    resp_tps = [TopicPartition(RESPONSE_TOPIC, p) for p in resp_partitions]
    response_consumer.assign(resp_tps)
    response_consumer.seek_to_beginning(*resp_tps)

    dead_letter_consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    dl_partitions = dead_letter_consumer.partitions_for_topic(DEAD_LETTER_TOPIC) or {0}
    dl_tps = [TopicPartition(DEAD_LETTER_TOPIC, p) for p in dl_partitions]
    dead_letter_consumer.assign(dl_tps)
    dead_letter_consumer.seek_to_beginning(*dl_tps)

    normal_id_1 = str(uuid.uuid4())
    poison_id = str(uuid.uuid4())
    normal_id_2 = str(uuid.uuid4())

    print(f"[test] normal_id_1 = {normal_id_1}")
    print(f"[test] poison_id   = {poison_id}")
    print(f"[test] normal_id_2 = {normal_id_2}")

    print("\n[test] Sending normal request #1 ...")
    producer.send(REQUEST_TOPIC, value=make_trial_request(normal_id_1, "Normal Trial A"))

    print("[test] Sending POISON request (trialTitle=POISON_TEST_TRIGGER_CRASH) ...")
    producer.send(REQUEST_TOPIC, value=make_trial_request(poison_id, "POISON_TEST_TRIGGER_CRASH"))

    print("[test] Sending normal request #2 (right after the poison message) ...")
    producer.send(REQUEST_TOPIC, value=make_trial_request(normal_id_2, "Normal Trial B"))
    producer.flush()

    print("\n[test] Waiting for responses to the two NORMAL requests ...")
    result_1 = wait_for_message(response_consumer, RESPONSE_TOPIC, normal_id_1, timeout_seconds=15)
    result_2 = wait_for_message(response_consumer, RESPONSE_TOPIC, normal_id_2, timeout_seconds=15)

    print(f"[test] Normal request #1 response: {result_1}")
    print(f"[test] Normal request #2 response: {result_2}")

    if result_1 and result_1.get("success") and result_2 and result_2.get("success"):
        print("[test] BOTH normal requests succeeded -> poison message did NOT block later messages. GOOD.")
    else:
        print("[test] One of the normal requests did not get a successful response - investigate.")

    print("\n[test] Waiting for the poison message to appear on the dead-letter topic "
          "(it must retry and fail a bounded number of times first, so this takes a few seconds) ...")
    dead_letter_result = wait_for_message(dead_letter_consumer, DEAD_LETTER_TOPIC, poison_id, timeout_seconds=30)

    print(f"\n[test] Dead-letter result for poison_id: {dead_letter_result}")
    if dead_letter_result:
        print("[test] Poison message correctly ended up on the dead-letter topic after retries. GOOD.")
    else:
        print("[test] Poison message was NOT found on the dead-letter topic within the timeout.")

    response_consumer.close()
    dead_letter_consumer.close()
    producer.close()


if __name__ == "__main__":
    main()
