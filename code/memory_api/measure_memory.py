import argparse, csv, json, os, re, sys, time, uuid, datetime as dt
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import config
import memory
import ollama
from pymongo import MongoClient
from fastapi.testclient import TestClient
import main

OUT = os.path.abspath(os.path.join(HERE, "..", "..", "reports", "hw06"))
RAW = os.path.join(OUT, "raw")
LOG = os.path.join(OUT, "RUN_LOG.txt")
PRICE_IN, PRICE_OUT = 1.0, 5.0           # dollars per 1M tokens
CONVERSATIONS, TURNS_PER_CONV = 10_000, 30
SEED = 5825
KEEP_FULL, TRUNC = 5, 80                 # policy: keep 5 newest in full, cut older to 80 chars
client = TestClient(main.app)
db = MongoClient("mongodb://localhost:27017")["s5825_doc"]
_orig_short_term = memory.short_term

LABELS = {"n4": "SHORT_TERM_N=4", "n12": "SHORT_TERM_N=12", "n30": "SHORT_TERM_N=30",
          "policy": "Eviction/compression policy (N=12, older messages cut to 80 chars)"}


def log(msg):
    line = f"{dt.datetime.now().isoformat(timespec='seconds')} {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def compressed_short_term(user_id, session_id, n):
    w = _orig_short_term(user_id, session_id, n)
    out = []
    for i, m in enumerate(w):
        m = dict(m)
        if i < len(w) - KEEP_FULL and len(m["content"]) > TRUNC:
            m["content"] = m["content"][:TRUNC] + "..."
        out.append(m)
    return out


def clean(uid):
    for c in ("messages", "summaries", "episodes"):
        db[c].delete_many({"user_id": uid})


def chat(uid, sid, text):
    r = client.post("/api/chat", json={"user_id": uid, "session_id": sid, "message": text})
    r.raise_for_status()
    return r.json()


def judge(question, expected, answer, rubric):
    rub = "\n".join(f"{k}: {v}" for k, v in rubric.items())
    prompt = (f"Score the ANSWER from 1 to 5 using this rubric:\n{rub}\n\n"
              f"Question: {question}\nExpected: {expected}\nAnswer: {answer}\n"
              "Reply with ONLY one digit (1-5).")
    out = ollama.chat(model=config.CHAT_MODEL, think=False,
                      messages=[{"role": "user", "content": prompt}],
                      options={"temperature": 0, "seed": SEED})["message"]["content"]
    m = re.search(r"[1-5]", out)
    return int(m.group(0)) if m else 1


def run(label, n, spec, quick, policy=False):
    config.SHORT_TERM_N = n
    memory.short_term = compressed_short_term if policy else _orig_short_term
    uid, sid = f"probe_{label}", str(uuid.uuid4())
    clean(uid)
    setup = spec["setup"][:8] if quick else spec["setup"]
    turns, probes = [], []
    log(f"START {label} N={n} policy={policy} user={uid} session={sid}")

    def record(phase, i, text, d):
        m = d["metrics"]
        row = {"setting": label, "phase": phase, "turn": i,
               "prompt_tokens": m.get("prompt_tokens") or 0,
               "completion_tokens": m.get("completion_tokens") or 0,
               "system_tokens_est": m.get("system_tokens_est"),
               "long_term_tokens_est": m.get("long_term_tokens_est"),
               "short_term_tokens_est": m.get("short_term_tokens_est"),
               "episodic_tokens_est": m.get("episodic_tokens_est"),
               "latency_ms": m.get("latency_ms") or 0, "message": text}
        turns.append(row)
        return row

    for i, msg in enumerate(setup, 1):
        r = record("setup", i, msg, chat(uid, sid, msg))
        log(f"{label} setup {i}/{len(setup)} prompt={r['prompt_tokens']} latency_ms={r['latency_ms']}")
    for j, p in enumerate(spec["probes"], 1):
        d = chat(uid, sid, p["question"])
        r = record("probe", len(setup) + j, p["question"], d)
        score = judge(p["question"], p["expected"], d["reply"], spec["rubric"])
        hit = (all if p.get("need_all") else any)(k in d["reply"].lower() for k in p["keywords"])
        if not hit:
            score = min(score, 2)
        probes.append({"setting": label, "id": p["id"], "reply": d["reply"],
                       "score": score, "keyword_hit": hit})
        log(f"{label} {p['id']}: score={score} hit={hit} prompt={r['prompt_tokens']}")
    memory.short_term = _orig_short_term

    k = len(turns)
    mp = sum(t["prompt_tokens"] for t in turns) / k
    mc = sum(t["completion_tokens"] for t in turns) / k
    ml = sum(t["latency_ms"] for t in turns) / k
    q = sum(p["score"] for p in probes) / len(probes)
    cost = CONVERSATIONS * TURNS_PER_CONV * (mp * PRICE_IN + mc * PRICE_OUT) / 1e6
    res = {"setting": label, "name": LABELS[label], "short_term_n": n, "turns": k,
           "mean_prompt_tokens": round(mp, 1), "mean_completion_tokens": round(mc, 1),
           "mean_latency_ms": round(ml, 1), "avg_quality": round(q, 2),
           "cost_usd": round(cost, 2)}
    log(f"DONE {label}: {res}")
    return res, turns, probes


def write_outputs(results, all_turns, all_probes):
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, "per_turn.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(all_turns[0].keys()))
        w.writeheader(); w.writerows(all_turns)
    json.dump(all_probes, open(os.path.join(RAW, "probe_scores.json"), "w"), indent=2)
    json.dump(results, open(os.path.join(RAW, "summary.json"), "w"), indent=2)
    with open(os.path.join(RAW, "summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader(); w.writerows(results)

    by = {r["setting"]: r for r in results}
    top_q = max(r["avg_quality"] for r in results)
    ok = [r for r in results if r["avg_quality"] >= top_q - 0.5]
    best = min(ok, key=lambda r: r["cost_usd"])
    worst = max(results, key=lambda r: r["cost_usd"])
    L = ["# METRICS - HW6 Part 3", "", "## Memory sweep and policy", "",
         "| Setting | Mean prompt tokens/turn | Mean latency (ms) | Probe quality (1-5) |",
         "|---|---|---|---|"]
    for r in results:
        L.append(f"| {r['name']} | {r['mean_prompt_tokens']} | {r['mean_latency_ms']} | {r['avg_quality']} |")
    if "policy" in by and "n12" in by:
        a, b = by["n12"], by["policy"]
        sav = (1 - b["mean_prompt_tokens"] / a["mean_prompt_tokens"]) * 100
        L += ["", "## Policy vs plain N=12", "",
              f"- Prompt-token savings: {sav:.1f}% ({a['mean_prompt_tokens']} -> {b['mean_prompt_tokens']} per turn)",
              f"- Latency change: {b['mean_latency_ms'] - a['mean_latency_ms']:+.1f} ms",
              f"- Probe quality change: {b['avg_quality'] - a['avg_quality']:+.2f}"]
    L += ["", "## Cost estimate: 10,000 conversations x 30 turns ($1/M input, $5/M output)", "",
          "| Setting | Mean prompt tokens/turn | Mean completion tokens/turn | Estimated cost |",
          "|---|---|---|---|"]
    for r in results:
        L.append(f"| {r['name']} | {r['mean_prompt_tokens']} | {r['mean_completion_tokens']} | ${r['cost_usd']} |")
    L += ["", f"- Best setting: {best['name']} (cheapest among settings within 0.5 quality points of the top score)",
          f"- Worst setting: {worst['name']} (highest estimated cost)",
          "- Cost counts chat tokens only (not summary / fact-extraction calls)."]
    open(os.path.join(OUT, "METRICS.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\n" + "\n".join(L))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ns", type=int, nargs="+", default=[4, 12, 30])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--no-policy", action="store_true")
    a = ap.parse_args()
    os.makedirs(RAW, exist_ok=True)
    open(LOG, "w").close()
    print("Rutuja Saste - HW6 Part 3 measurement")
    spec = yaml.safe_load(open(os.path.join(HERE, "memory_probes.yaml")))
    results, all_turns, all_probes = [], [], []
    plan = [(f"n{n}", n, False) for n in a.ns]
    if not a.no_policy:
        plan.append(("policy", 12, True))
    for label, n, pol in plan:
        res, turns, probes = run(label, n, spec, a.quick, pol)
        results.append(res); all_turns += turns; all_probes += probes
    write_outputs(results, all_turns, all_probes)