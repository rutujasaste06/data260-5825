"""
HW8 Part 1 - Client

Customer analogy: sends an order (CREATE_TRIAL / GET_TRIAL) to
<PREFIX>_entity_requests with a unique ticket number (correlation_id),
then watches <PREFIX>_entity_responses until it sees the response with
that same ticket number.
"""

import json
import time
import uuid
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from topics import REQUEST_TOPIC, RESPONSE_TOPIC

import os

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")


def send_request(operation: str, data: dict, timeout_seconds: int = 15) -> dict:
    """Sends one request and waits for its matching response."""
    correlation_id = str(uuid.uuid4())

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
    partitions = consumer.partitions_for_topic(RESPONSE_TOPIC) or {0}
    topic_partitions = [TopicPartition(RESPONSE_TOPIC, p) for p in partitions]
    consumer.assign(topic_partitions)
    consumer.seek_to_beginning(*topic_partitions)  # scan all responses, filter by correlation_id below

    request = {
        "correlation_id": correlation_id,
        "reply_to": RESPONSE_TOPIC,
        "operation": operation,
        "data": data,
    }

    print(f"[client] Sending {operation} (correlation_id={correlation_id}): {request}")
    producer.send(REQUEST_TOPIC, value=request)
    producer.flush()

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        records = consumer.poll(timeout_ms=500)
        for _tp, messages in records.items():
            for msg in messages:
                response = msg.value
                if response.get("correlation_id") == correlation_id:
                    print(f"[client] Received response: {response}")
                    consumer.close()
                    producer.close()
                    return response

    consumer.close()
    producer.close()
    raise TimeoutError(f"No response received for correlation_id {correlation_id} within {timeout_seconds}s")


if __name__ == "__main__":
    # Demo: create a trial, then fetch it back by its generated trial_id
    created = send_request("CREATE_TRIAL", {
        "trialTitle": "Phase II Study of Metformin",
        "nctNumber": "NCT00000001",
        "trialPhase": "Phase II",
    })

    trial_id = created["entity_id"]
    fetched = send_request("GET_TRIAL", {"trial_id": trial_id})
