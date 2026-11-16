"""
HW10 Part 2 - evaluator for the Kafka pipeline.

Given a trace_id (= correlation_id) it reads the plan (<PREFIX>_tasks), the draft
(<PREFIX>_drafts) and the final message (<PREFIX>_final) that share that id, keeps the
original messages with their Kafka metadata, and scores with the judge in judge.py:
  Plan Quality, Writer Helpfulness, Final Answer Helpfulness, Final-vs-Draft Improvement.
Bounded: Kafka reading stops after COLLECT_TIMEOUT_S, malformed messages are skipped and
counted, and a judge that fails or times out gives score=None + an error (the run goes on).

Run from the repo root:   python code/hw10/evaluator.py [trace_id]
(no trace_id = the successful cache-miss trace saved by trace_examples.py)
"""

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pipeline"))
sys.path.insert(0, HERE)

from judge import SETTINGS, run_judge  # noqa: E402
from kafka import KafkaConsumer, TopicPartition  # noqa: E402
from topics import DRAFTS_TOPIC, FINAL_TOPIC, TASKS_TOPIC  # noqa: E402
from tracing import raw_dir, write_span  # noqa: E402

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "localhost:9092")
COLLECT_TIMEOUT_S = 15
EVALS_FILE = "evaluations.jsonl"
TOPICS = {"plan": TASKS_TOPIC, "draft": DRAFTS_TOPIC, "final": FINAL_TOPIC}


def _safe_json(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return None  # malformed message: skipped and counted


def collect(trace_id, timeout_s=COLLECT_TIMEOUT_S):
    """Find the plan, draft and final message with this correlation_id. Stops after timeout_s."""
    consumer = KafkaConsumer(bootstrap_servers=KAFKA_BROKER, value_deserializer=_safe_json)
    found, malformed = {}, 0
    try:
        tps = []
        for topic in TOPICS.values():
            tps += [TopicPartition(topic, p) for p in (consumer.partitions_for_topic(topic) or {0})]
        consumer.assign(tps)
        consumer.seek_to_beginning(*tps)
        by_topic = {topic: name for name, topic in TOPICS.items()}
        deadline = time.time() + timeout_s
        while len(found) < 3 and time.time() < deadline:
            for messages in consumer.poll(timeout_ms=500).values():
                for msg in messages:
                    if not isinstance(msg.value, dict):
                        malformed += 1
                        continue
                    name = by_topic[msg.topic]
                    if msg.value.get("correlation_id") == trace_id and name not in found:
                        found[name] = {"topic": msg.topic, "partition": msg.partition,
                                       "offset": msg.offset, "kafka_timestamp_ms": msg.timestamp,
                                       "value": msg.value}
    finally:
        consumer.close()
    return found, malformed


def interpret(draft_score, final_score, same_text):
    if draft_score is None or final_score is None:
        return "Not computed: a judge score is missing."
    diff = final_score - draft_score
    if diff >= 1:
        return f"The final answer scored {diff} point(s) higher than the draft: the Reviewer stage improved it."
    if diff <= -1:
        return f"The final answer scored {-diff} point(s) lower than the draft: the Reviewer made it worse."
    if same_text:
        return ("No improvement: the final answer is the same text as the draft. The Reviewer only "
                "approves or rejects and never rewrites, so it cannot raise quality.")
    return "No meaningful change: the scores differ by less than one point."


def evaluate_trace(trace_id, save=True):
    start = time.time()
    record = {"trace_id": trace_id, "status": "ok", "error": None, "judge": SETTINGS,
              "evaluated_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        found, malformed = collect(trace_id)
        record["malformed_messages_skipped"] = malformed
        record["messages"] = found  # original content + Kafka metadata, so the run can be reproduced
        missing = [name for name in TOPICS if name not in found]
        if missing:
            raise RuntimeError(f"missing {', '.join(missing)} message(s) for this trace")
        final = found["final"]["value"]
        if final.get("status") == "error":
            raise RuntimeError(f"pipeline failed at {final.get('stage')}: {final.get('error')}")
        question = found["plan"]["value"].get("question")
        plan = found["plan"]["value"].get("plan")
        draft = found["draft"]["value"].get("draft")
        final_answer = final.get("answer")
        record.update(question=question, plan=plan, draft=draft, final_answer=final_answer,
                      final_status=final.get("status"))

        plan_q = run_judge("plan_quality", question, plan)
        writer_h = run_judge("helpfulness", question, draft)
        final_h = run_judge("helpfulness", question, final_answer)
        same = (draft or "").strip() == (final_answer or "").strip()
        record["plan_quality"] = plan_q
        record["writer_helpfulness"] = writer_h
        record["final_helpfulness"] = final_h
        record["improvement"] = {
            "draft_score": writer_h["score"], "final_score": final_h["score"],
            "difference": None if None in (writer_h["score"], final_h["score"])
            else final_h["score"] - writer_h["score"],
            "final_equals_draft": same,
            "interpretation": interpret(writer_h["score"], final_h["score"], same),
        }
        failed = [r["error"] for r in (plan_q, writer_h, final_h) if r["error"]]
        if failed:
            raise RuntimeError(f"judge problem: {failed[0]}")
    except Exception as exc:
        record["status"], record["error"] = "error", f"{type(exc).__name__}: {exc}"
    write_span(trace_id, "evaluation", start, time.time(), record["status"], record["error"])
    if save:
        os.makedirs(raw_dir(), exist_ok=True)
        with open(os.path.join(raw_dir(), EVALS_FILE), "a") as f:
            f.write(json.dumps(record) + "\n")
    return record


def main():
    if len(sys.argv) > 1:
        trace_id = sys.argv[1]
    else:
        with open(os.path.join(raw_dir(), "trace_examples.json")) as f:
            trace_id = json.load(f)["miss"]["trace_id"]
    print(f"Evaluating trace {trace_id} (judge {SETTINGS['model']}, temperature {SETTINGS['temperature']}) ...")
    r = evaluate_trace(trace_id)
    if r["status"] == "error":
        print(f"Evaluation error: {r['error']}")
    else:
        print(f"Question: {r['question']}")
        for key, label in (("plan_quality", "Plan Quality"), ("writer_helpfulness", "Writer Helpfulness"),
                           ("final_helpfulness", "Final Answer Helpfulness")):
            print(f"{label}: {r[key]['score']}/5  - {r[key]['reason']}")
        imp = r["improvement"]
        print(f"Final-vs-Draft: draft {imp['draft_score']}, final {imp['final_score']}, "
              f"difference {imp['difference']}")
        print(f"Interpretation: {imp['interpretation']}")
        print(f"Final answer: {r['final_answer']}")
    print(f"Saved to {os.path.join('reports', 'hw10', 'raw', EVALS_FILE)}")


if __name__ == "__main__":
    main()
