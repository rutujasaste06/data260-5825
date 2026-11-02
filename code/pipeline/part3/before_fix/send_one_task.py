"""Sends ONE plan message straight to <PREFIX>_tasks (for the Consumer Death demos)."""
import json, os, sys, uuid
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from kafka import KafkaProducer
from topics import TASKS_TOPIC

producer = KafkaProducer(bootstrap_servers=os.environ.get("KAFKA_BROKER", "localhost:9092"),
                         value_serializer=lambda v: json.dumps(v).encode("utf-8"))
cid = str(uuid.uuid4())
md = producer.send(TASKS_TOPIC, value={
    "correlation_id": cid,
    "question": "What should a patient know before joining a Phase II clinical trial?",
    "plan": "- Explain what Phase II means\n- Mention risks and benefits\n- Suggest questions to ask the study team",
}).get(timeout=10)
producer.flush()
print(f"[send_one_task] sent correlation_id={cid}  -> partition {md.partition}, offset {md.offset}")
