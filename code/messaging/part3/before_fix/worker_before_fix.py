"""
HW8 Part 3.III - BEFORE FIX (demo only, not part of the real system).

Same as worker.py but WITHOUT the bounded-retry / dead-letter handling:
a message that makes process_operation() raise is not caught.
"""

import json
import os
import sys
import uuid
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from kafka import KafkaConsumer, KafkaProducer
from topics import REQUEST_TOPIC, RESPONSE_TOPIC, DEAD_LETTER_TOPIC

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")

REQUIRED_FIELDS = ["trialTitle", "nctNumber", "trialPhase"]
MAX_RETRIES = 3

# Plain Python dictionary, as the assignment requires for this exercise
trials_db = {}

# Idempotency store: correlation_id -> the response we already sent for it.
processed_requests = {}


def validate_data(data) -> str | None:
    """Returns an error message if invalid, or None if the data is OK."""
    if not isinstance(data, dict):
        return "data must be an object"
    for field in REQUIRED_FIELDS:
        value = data.get(field)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            return f"Missing or empty required field: {field}"
    return None


def process_operation(correlation_id, operation, data) -> dict:
    """Does the actual work. May raise an exception for a 'poison' message -
    see the deliberate trigger below, used only to demonstrate Part 3.III."""

    # Deliberate poison-message trigger for the Part 3.III demonstration:
    # a message with this exact sentinel title always fails, simulating a
    # permanently broken/corrupted message (not a normal validation error).
    if isinstance(data, dict) and data.get("trialTitle") == "POISON_TEST_TRIGGER_CRASH":
        raise RuntimeError("Simulated processing crash (poison message test)")

    if operation == "CREATE_TRIAL":
        error = validate_data(data)
        if error:
            return {
                "correlation_id": correlation_id,
                "success": False,
                "error": error,
            }
        trial_id = str(uuid.uuid4())
        record = {"trial_id": trial_id, **data}
        trials_db[trial_id] = record
        return {
            "correlation_id": correlation_id,
            "success": True,
            "entity_id": trial_id,
            "message": "Trial created",
        }

    elif operation == "GET_TRIAL":
        trial_id = data.get("trial_id") if isinstance(data, dict) else None
        record = trials_db.get(trial_id)
        if record is None:
            return {
                "correlation_id": correlation_id,
                "success": False,
                "error": "Entity not found",
            }
        return {
            "correlation_id": correlation_id,
            "success": True,
            "entity": record,
        }

    else:
        return {
            "correlation_id": correlation_id,
            "success": False,
            "error": "Unknown operation",
        }


def main():
    consumer = KafkaConsumer(
        REQUEST_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="s5825-worker-group",
    )
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    print("[worker-BEFORE-FIX] Consumer is ready and listening...")

    for msg in consumer:
        request = msg.value
        print(f"[worker] Received request: {request}")

        correlation_id = request.get("correlation_id")
        operation = request.get("operation")
        data = request.get("data", {})
        retry_count = request.get("retry_count", 0)

        # Duplicate delivery check (Part 3.I)
        if correlation_id in processed_requests:
            response = processed_requests[correlation_id]
            print(f"[worker] DUPLICATE detected for correlation_id={correlation_id} "
                  f"- returning cached response, no new trial created")
            reply_to = request.get("reply_to", RESPONSE_TOPIC)
            producer.send(reply_to, value=response)
            producer.flush()
            print(f"[worker] Sent response to {reply_to}: {response}")
            continue

        # BEFORE FIX: no try/except, no retries, no dead-letter topic.
        # If process_operation() raises, the exception is unhandled.
        response = process_operation(correlation_id, operation, data)
        processed_requests[correlation_id] = response

        reply_to = request.get("reply_to", RESPONSE_TOPIC)
        producer.send(reply_to, value=response)
        producer.flush()
        print(f"[worker] Sent response to {reply_to}: {response}")


if __name__ == "__main__":
    main()
