"""Smoke test for HW8: needs Kafka + worker running. Writes reports/hw08/verification.json.
Only sends test messages through Kafka; it never changes application code."""
import json
import os
import subprocess
import sys
import time
import uuid
import warnings
from datetime import datetime, timezone

warnings.filterwarnings("ignore", category=DeprecationWarning)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "code", "messaging"))
from kafka import KafkaConsumer, KafkaProducer, TopicPartition  # noqa: E402
from client import KAFKA_BROKER, send_request  # noqa: E402
from topics import REQUEST_TOPIC, RESPONSE_TOPIC  # noqa: E402

SID4, SEED, VERIFY_SEED = 5825, 5825, 265825
MODEL = "qwen3:8b"
results, state = [], {}
TRIAL = {"trialTitle": "Verify HW8 trial", "nctNumber": "NCT00000008", "trialPhase": "Phase II"}


def check(name, fn):
    """Run one check, record pass/fail and a short detail."""
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"
    results.append({"check": name, "passed": bool(ok), "detail": str(detail)})
    print(("PASS  " if ok else "FAIL  ") + name + " - " + str(detail))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()


def kafka_up():
    c = KafkaConsumer(bootstrap_servers=KAFKA_BROKER)
    topics = c.topics()
    c.close()
    ok = REQUEST_TOPIC in topics and RESPONSE_TOPIC in topics
    return ok, f"broker {KAFKA_BROKER} answered; {REQUEST_TOPIC} and {RESPONSE_TOPIC} exist={ok}"


def create_ok():
    r = send_request("CREATE_TRIAL", TRIAL)
    state["id"] = r.get("entity_id")
    valid = False
    try:
        valid = str(uuid.UUID(state["id"])) == state["id"]
    except Exception:
        pass
    return r.get("success") is True and valid, f"success={r.get('success')}, entity_id is a UUID={valid}"


def get_ok():
    r = send_request("GET_TRIAL", {"trial_id": state.get("id")})
    same = r.get("entity", {}).get("trial_id") == state.get("id")
    return r.get("success") is True and same, f"success={r.get('success')}, same entity returned={same}"


def get_missing():
    r = send_request("GET_TRIAL", {"trial_id": "does-not-exist"})
    return r.get("success") is False and bool(r.get("error")) and bool(r.get("correlation_id")), \
        f"success={r.get('success')}, error present={bool(r.get('error'))}, correlation_id present"


def unknown_op():
    r = send_request("DELETE_EVERYTHING", {})
    return r.get("success") is False and bool(r.get("error")), f"success={r.get('success')}, error present"


def missing_field():
    r = send_request("CREATE_TRIAL", {"trialTitle": "", "nctNumber": "NCT1", "trialPhase": "Phase I"})
    return r.get("success") is False, f"empty trialTitle rejected: success={r.get('success')}"


def duplicate_replay():
    """Send the SAME correlation_id twice; an idempotent worker returns the same entity_id."""
    cid = str(uuid.uuid4())
    c = KafkaConsumer(bootstrap_servers=KAFKA_BROKER, value_deserializer=lambda v: json.loads(v.decode()))
    tps = [TopicPartition(RESPONSE_TOPIC, p) for p in (c.partitions_for_topic(RESPONSE_TOPIC) or {0})]
    c.assign(tps)
    c.seek_to_end(*tps)
    p = KafkaProducer(bootstrap_servers=KAFKA_BROKER, value_serializer=lambda v: json.dumps(v).encode())
    req = {"correlation_id": cid, "reply_to": RESPONSE_TOPIC, "operation": "CREATE_TRIAL", "data": TRIAL}
    p.send(REQUEST_TOPIC, value=req)
    p.send(REQUEST_TOPIC, value=req)
    p.flush()
    got, end = [], time.time() + 20
    while time.time() < end and len(got) < 2:
        for msgs in c.poll(timeout_ms=500).values():
            got += [m.value for m in msgs if m.value.get("correlation_id") == cid]
    c.close()
    p.close()
    ids = {g.get("entity_id") for g in got}
    return len(got) == 2 and len(ids) == 1, f"{len(got)} responses, distinct entity_ids={len(ids)}"


def main():
    check("Kafka broker reachable", kafka_up)
    check("CREATE_TRIAL succeeds with a UUID entity_id", create_ok)
    check("GET_TRIAL returns the created trial", get_ok)
    check("GET_TRIAL with unknown id returns a clean error", get_missing)
    check("Unknown operation returns a clean error", unknown_op)
    check("Empty required field is rejected", missing_field)
    check("Duplicate correlation_id returns the same entity_id (idempotent)", duplicate_replay)
    try:
        tag_commit = git("rev-parse", "hw8^{commit}")
    except Exception:
        tag_commit = None
    out = {"homework": "HW8", "sid4": SID4, "commit_hash": git("rev-parse", "HEAD"), "tag_hw8_commit": tag_commit,
           "model_configuration": {"chat_model": MODEL, "note": "model used by the Part 2 pipeline; this smoke test checks Part 1/3 messaging only"},
           "seed": SEED, "verify_seed": VERIFY_SEED, "run_at_utc": datetime.now(timezone.utc).isoformat(),
           "checks": results, "all_passed": all(r["passed"] for r in results)}
    path = os.path.join(ROOT, "reports", "hw08", "verification.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("Wrote", path, "| all_passed =", out["all_passed"])
    sys.exit(0 if out["all_passed"] else 1)


if __name__ == "__main__":
    main()
