"""
HW8 Part 3.IV - Ordering: producer.
Generates 20 related plan messages (about 4 trials) using VERIFY_SEED, sends them to
<PREFIX>_tasks.  Usage:  python ordering_producer.py nokey   |   python ordering_producer.py key
"""
import json, os, random, sys, uuid
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from kafka import KafkaProducer
from topics import TASKS_TOPIC

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")
VERIFY_SEED = 265825
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "..", "..", "reports", "hw08", "raw")

mode = sys.argv[1] if len(sys.argv) > 1 else "nokey"
assert mode in ("nokey", "key")

rng = random.Random(VERIFY_SEED)
entities = [str(uuid.UUID(int=rng.getrandbits(128))) for _ in range(4)]
seq_counter = {e: 0 for e in entities}
messages = []
for n in range(1, 21):
    e = rng.choice(entities)
    seq_counter[e] += 1
    rng.randint(100, 700)   # (kept so the sequence matches the earlier draws)
    short = e[:8]
    messages.append({
        "correlation_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{mode}-{n}")),
        "run_id": mode, "msg_no": n, "entity_id": e, "seq": seq_counter[e],
        "question": f"In two sentences, what should a patient know about clinical trial {short}, update {seq_counter[e]}?",
        "plan": "- State one key fact\n- Keep it to two sentences",
    })

# fresh log for this run
open(os.path.join(RAW, f"ordering_{mode}_log.jsonl"), "w").close()

producer = KafkaProducer(
    bootstrap_servers=KAFKA_BROKER,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=lambda k: k.encode("utf-8") if k else None,
)

print(f"[producer] mode={mode}  topic={TASKS_TOPIC}  VERIFY_SEED={VERIFY_SEED}")
parts_per_entity = {e: set() for e in entities}
for m in messages:
    key = m["entity_id"] if mode == "key" else None   # <-- the partition key
    md = producer.send(TASKS_TOPIC, key=key, value=m).get(timeout=10)
    parts_per_entity[m["entity_id"]].add(md.partition)
    print(f"[producer] msg {m['msg_no']:>2}  entity {m['entity_id'][:8]}  seq {m['seq']}  -> partition {md.partition}")
producer.flush()

print("\n[producer] partitions used per entity:")
for e, p in parts_per_entity.items():
    print(f"   entity {e[:8]}: partitions {sorted(p)}")
