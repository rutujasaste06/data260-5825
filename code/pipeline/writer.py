"""
HW8 Part 2 - Writer

Reads a plan from <PREFIX>_tasks, asks the local LLM to write an actual
answer following that plan, and sends the draft to <PREFIX>_drafts for
the Reviewer to check. Never talks to Planner or Reviewer directly -
only through Kafka.

HW8 Part 3 (Consumer Death): offset auto-commit is turned OFF
(enable_auto_commit=False). We only tell Kafka "I'm done with this
message" (consumer.commit()) AFTER the draft has actually been written
AND successfully sent to the drafts topic. This means: if Writer is
killed mid-processing (e.g. while the LLM is still thinking), Kafka
still considers that message unread, and the next time Writer starts
up, it will receive that same message again instead of silently
losing it.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from kafka import KafkaConsumer, KafkaProducer
from model_client import ModelClient
from topics import TASKS_TOPIC, DRAFTS_TOPIC

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")

client = ModelClient()

# Optional instance name, e.g. "python writer.py writer-A" (used in ordering logs)
WRITER_NAME = sys.argv[1] if len(sys.argv) > 1 else "writer"
ORDERING_RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "..", "reports", "hw08", "raw")


def write_answer(question: str, plan: str) -> str:
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
        enable_auto_commit=False,  # we commit manually, only after success - see docstring
        max_poll_records=1,        # hand me ONE message at a time so a commit covers only it
    )
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BROKER,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    print(f"[{WRITER_NAME}] Ready and listening on", TASKS_TOPIC)

    last_assignment = None
    while True:
        records = consumer.poll(timeout_ms=500)

        # show which partitions this Writer instance currently owns
        assigned = sorted(tp.partition for tp in consumer.assignment())
        if assigned and assigned != last_assignment:
            print(f"[{WRITER_NAME}] assigned partitions: {assigned}")
            last_assignment = assigned

        for _tp, msgs in records.items():
            for msg in msgs:
                task = msg.value
                correlation_id = task.get("correlation_id")
                question = task.get("question")
                plan = task.get("plan")
                t_start = time.time()
                print(f"[{WRITER_NAME}] Received plan (correlation_id={correlation_id}) "
                      f"partition={msg.partition} offset={msg.offset} - starting work "
                      f"(offset NOT committed yet - if I die right now, this message is NOT lost)")

                draft = write_answer(question, plan)
                print(f"[{WRITER_NAME}] Generated draft: {draft}")

                output = {
                    "correlation_id": correlation_id,
                    "question": question,
                    "draft": draft,
                }
                producer.send(DRAFTS_TOPIC, value=output)
                producer.flush()
                print(f"[{WRITER_NAME}] Sent draft to {DRAFTS_TOPIC}")

                # Only now - after the work is actually done and sent downstream -
                # do we tell Kafka this message is handled.
                consumer.commit()
                print(f"[{WRITER_NAME}] Offset committed for correlation_id={correlation_id} - now safe")

                # Part 3.IV (ordering test only): messages carrying a run_id also
                # record where/when they were processed. Normal messages skip this.
                if task.get("run_id"):
                    print(f"[{WRITER_NAME}] ORDER partition {msg.partition} offset {msg.offset} "
                          f"entity {task['entity_id'][:8]} seq {task['seq']} (msg {task['msg_no']})")
                    log_path = os.path.join(ORDERING_RAW, f"ordering_{task['run_id']}_log.jsonl")
                    with open(log_path, "a") as f:
                        f.write(json.dumps({
                            "writer": WRITER_NAME, "partition": msg.partition,
                            "offset": msg.offset, "entity_id": task["entity_id"],
                            "seq": task["seq"], "msg_no": task["msg_no"],
                            "t_start": t_start, "t_end": time.time()}) + "\n")


if __name__ == "__main__":
    main()
