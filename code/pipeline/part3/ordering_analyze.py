"""HW8 Part 3.IV - Ordering: analyze a run.  Usage: python ordering_analyze.py nokey | key"""
import csv, json, os, sys
mode = sys.argv[1]
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "..", "..", "reports", "hw08", "raw")
rows = [json.loads(l) for l in open(os.path.join(RAW, f"ordering_{mode}_log.jsonl")) if l.strip()]
rows.sort(key=lambda r: r["t_end"])               # order in which processing finished
print(f"Run: {mode}   messages processed: {len(rows)} / 20\n")
by_entity = {}
for r in rows:
    by_entity.setdefault(r["entity_id"], []).append(r)
all_ok = True
for e, rs in by_entity.items():
    seqs = [r["seq"] for r in rs]
    parts = sorted({r["partition"] for r in rs})
    writers = sorted({r["writer"] for r in rs})
    ok = seqs == sorted(seqs)
    all_ok &= ok
    print(f"entity {e[:8]}: processed seq order = {seqs}")
    print(f"   partitions = {parts}   writers = {writers}   -> {'IN ORDER' if ok else 'OUT OF ORDER'}")
print("\nRESULT:", "all entities processed in order" if all_ok else "ORDER BROKEN for at least one entity")
with open(os.path.join(RAW, f"ordering_{mode}.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["processed_pos","writer","partition","offset","entity_id","seq","msg_no"])
    for i, r in enumerate(rows, 1):
        w.writerow([i, r["writer"], r["partition"], r["offset"], r["entity_id"], r["seq"], r["msg_no"]])
print(f"saved reports/hw08/raw/ordering_{mode}.csv")
