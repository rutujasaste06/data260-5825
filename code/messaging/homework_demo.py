"""
HW8 Part 1 - homework_demo.py

Demonstrates the complete CREATE_TRIAL -> GET_TRIAL request/response flow
over Kafka, with each stage logged separately as required by the
assignment:

 1. Create one correlation_id
 2. Send CREATE_TRIAL request to s5825_entity_requests
 3. Log the message sent to the request topic
 4. Log the worker receiving and processing the request
 5. Log the worker sending the response to s5825_entity_responses
 6. Log the response received by the client
 7. Extract the generated entity_id from the CREATE_TRIAL response
 8. Send a GET_TRIAL request using that entity_id
 9. Log the complete GET_TRIAL send/receive/process/reply/response sequence
10. Display the retrieved entity and confirm correlation_id is preserved

NOTE: worker.py must already be running in another terminal before you
run this script - this script is only the client side. The worker's own
terminal is where steps 4 and 5 (and their GET_TRIAL equivalents) show up.
"""

import json
import time
import uuid
from kafka import KafkaConsumer, KafkaProducer, TopicPartition
from topics import REQUEST_TOPIC, RESPONSE_TOPIC

import os

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")


def send_and_wait(operation: str, data: dict, timeout_seconds: int = 15) -> dict:
    # Step 1: create one correlation_id for this request
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

    # Step 2 + 3: send the request, log what was sent
    print(f"\n[STEP] Sending {operation} request to '{REQUEST_TOPIC}'")
    print(f"[SENT]  {request}")
    producer.send(REQUEST_TOPIC, value=request)
    producer.flush()

    print("[STEP] (worker receives/processes this - see worker.py terminal for that log)")

    # Step 6: log the response received by the client
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        records = consumer.poll(timeout_ms=500)
        for _tp, messages in records.items():
            for msg in messages:
                response = msg.value
                if response.get("correlation_id") == correlation_id:
                    print(f"[RECEIVED BY CLIENT] {response}")
                    consumer.close()
                    producer.close()
                    return response

    consumer.close()
    producer.close()
    raise TimeoutError(f"No response received for correlation_id {correlation_id} within {timeout_seconds}s")


def main():
    print("=" * 70)
    print("HW8 Part 1 Demonstration - CREATE_TRIAL -> GET_TRIAL over Kafka")
    print("=" * 70)

    # Steps 1-6: CREATE_TRIAL
    create_response = send_and_wait("CREATE_TRIAL", {
        "trialTitle": "Phase II Study of Metformin",
        "nctNumber": "NCT00000001",
        "trialPhase": "Phase II",
    })

    # Step 7: extract the generated entity_id
    assert create_response.get("success") is True, "CREATE_TRIAL did not succeed"
    trial_id = create_response["entity_id"]
    print(f"\n[STEP] Extracted generated entity_id: {trial_id}")

    # Steps 8-9: GET_TRIAL using that entity_id
    get_response = send_and_wait("GET_TRIAL", {"trial_id": trial_id})

    # Step 10: display the retrieved entity and confirm correlation_id preserved
    assert get_response.get("success") is True, "GET_TRIAL did not succeed"
    print("\n[STEP] Final retrieved entity:")
    print(json.dumps(get_response["entity"], indent=2))
    print(f"\n[CHECK] correlation_id on this response: {get_response['correlation_id']}")
    print("[CHECK] This confirms the response is matched to its own request, not any other message.")

    print("\n" + "=" * 70)
    print("Demonstration complete - CREATE_TRIAL and GET_TRIAL both succeeded.")
    print("=" * 70)


if __name__ == "__main__":
    main()
