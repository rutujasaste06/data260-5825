"""
HW8 Part 1 - Worker

Kitchen analogy: watches <PREFIX>_entity_requests for orders
(CREATE_TRIAL / GET_TRIAL), does the work, and sends the result back on
the topic named in "reply_to", carrying the same correlation_id (ticket
number) so the client knows which response is its own.

HW8 Part 3 (Duplicate Delivery): remembers every correlation_id it has
already finished, so a replayed/duplicate message doesn't redo the work.

HW8 Part 3 (Poison Message): if processing a message keeps raising an
error (a message that's permanently broken, not just a normal
validation failure), the worker retries it a bounded number of times
(MAX_RETRIES) by requeuing it onto the SAME request topic with an
incremented retry_count. Requeuing instead of retrying in a tight loop
means other, later, good messages still get a turn in between retries -
so one bad message does not block everything behind it. After
MAX_RETRIES attempts, the worker gives up and moves the message to
<PREFIX>_dead_letter instead of retrying forever.
"""

import json
import os
import uuid
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

    print("Consumer is ready and listening...")

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

        try:
            response = process_operation(correlation_id, operation, data)
            processed_requests[correlation_id] = response

            reply_to = request.get("reply_to", RESPONSE_TOPIC)
            producer.send(reply_to, value=response)
            producer.flush()
            print(f"[worker] Sent response to {reply_to}: {response}")

        except Exception as e:
            new_retry_count = retry_count + 1
            print(f"[worker] ERROR processing correlation_id={correlation_id} "
                  f"(attempt {new_retry_count}/{MAX_RETRIES}): {e}")

            if new_retry_count <= MAX_RETRIES:
                retried_request = dict(request)
                retried_request["retry_count"] = new_retry_count
                producer.send(REQUEST_TOPIC, value=retried_request)
                producer.flush()
                print(f"[worker] Requeued correlation_id={correlation_id} for retry "
                      f"{new_retry_count}/{MAX_RETRIES} (other messages can be processed "
                      f"in between - this does not block the queue)")
            else:
                dead_letter_message = {
                    "correlation_id": correlation_id,
                    "original_request": request,
                    "error": str(e),
                    "failed_attempts": new_retry_count,
                }
                producer.send(DEAD_LETTER_TOPIC, value=dead_letter_message)
                producer.flush()
                print(f"[worker] GIVING UP after {new_retry_count} attempts - sent "
                      f"correlation_id={correlation_id} to {DEAD_LETTER_TOPIC}")


if __name__ == "__main__":
    main()
