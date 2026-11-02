"""
HW8 Part 3.II - BEFORE FIX (demo only, not part of the real pipeline).

Same as writer.py, except the offset is committed IMMEDIATELY when a message
arrives - BEFORE the LLM work is done. This is the naive pattern the
assignment's "Consumer Death" test is about: if the Writer dies mid-work,
Kafka already believes the message was handled, so it is never redelivered.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))            # code/pipeline (topics.py)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "src"))  # src (model_client.py)

from kafka import KafkaConsumer, KafkaProducer
from model_client import ModelClient
from topics import TASKS_TOPIC, DRAFTS_TOPIC

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")
client = ModelClient()


def write_answer(question, plan):
    messages = [
        {"role": "system", "content": "You are a Writer agent. Given a question and a "
                                       "plan, write a clear, well-organized answer "
                                       "following that plan. Keep it under 150 words."},
        {"role": "user", "content": f"Question: {question}\n\nPlan:\n{plan}"},
    ]
    return client.complete(messages)


def main():
    consumer = KafkaConsumer(
        TASKS_TOPIC,
        bootstrap_servers=KAFKA_BROKER,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        auto_offset_reset="earliest",
        group_id="s5825-writer-group",
        enable_auto_commit=False,
        max_poll_records=1,
    )
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    print("[writer-BEFORE-FIX] Ready and listening on", TASKS_TOPIC)

    for msg in consumer:
        task = msg.value
        correlation_id = task.get("correlation_id")
        print(f"[writer-BEFORE-FIX] Received plan (correlation_id={correlation_id}) "
              f"partition={msg.partition} offset={msg.offset}")

        consumer.commit()   # <-- THE BUG: committed BEFORE the work is done
        print(f"[writer-BEFORE-FIX] Offset committed IMMEDIATELY (before work) "
              f"for correlation_id={correlation_id}")

        print("[writer-BEFORE-FIX] Starting LLM work ...")
        draft = write_answer(task.get("question"), task.get("plan"))
        print(f"[writer-BEFORE-FIX] Generated draft: {draft}")

        producer.send(DRAFTS_TOPIC, value={"correlation_id": correlation_id,
                                           "question": task.get("question"),
                                           "draft": draft})
        producer.flush()
        print(f"[writer-BEFORE-FIX] Sent draft to {DRAFTS_TOPIC}")


if __name__ == "__main__":
    main()
