"""
HW8 Part 2 - Planner

Reads a question from <PREFIX>_inbox, asks the local LLM to produce a
short plan for answering it, and sends that plan to <PREFIX>_tasks for
the Writer to pick up. Never talks to Writer or Reviewer directly -
only through Kafka.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from kafka import KafkaConsumer, KafkaProducer
from model_client import ModelClient
from topics import INBOX_TOPIC, TASKS_TOPIC

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")

client = ModelClient()


def make_plan(question: str) -> str:
    messages = [
        {"role": "system", "content": "You are a Planner agent. Given a question, "
                                       "write a short 2-4 bullet plan for how to answer "
                                       "it well. Output only the plan, no extra text."},
        {"role": "user", "content": question},
    ]
    return client.complete(messages)


def main():
    consumer = KafkaConsumer(
        INBOX_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="s5825-planner-group",
    )
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8"),
    )

    print("[planner] Ready and listening on", INBOX_TOPIC)

    for msg in consumer:
        request = msg.value
        correlation_id = request.get("correlation_id")
        question = request.get("question")
        print(f"[planner] Received question (correlation_id={correlation_id}): {question}")

        plan = make_plan(question)
        print(f"[planner] Generated plan: {plan}")

        output = {
            "correlation_id": correlation_id,
            "question": question,
            "plan": plan,
        }
        # Part 3.IV: message key = the related entity (falls back to correlation_id),
        # so all messages about the same entity go to the same partition, in order.
        entity_id = request.get("entity_id") or correlation_id
        output["entity_id"] = entity_id
        producer.send(TASKS_TOPIC, key=entity_id, value=output)
        producer.flush()
        print(f"[planner] Sent plan to {TASKS_TOPIC}")


if __name__ == "__main__":
    main()
