import csv, os, time
import numpy as np
import requests

BASE = "http://localhost:8425"
OUT = "reports/hw04/raw"
os.makedirs(OUT, exist_ok=True)

s = requests.Session()
r = s.post(f"{BASE}/auth/login", json={"email": "user1@gmail.com", "password": "secret123"})
assert r.status_code == 200, r.text

rows, summary = [], []
for size in (10, 50, 200):
    for version in ("naive", "fixed"):
        url = f"{BASE}/trials-{version}?limit={size}"
        s.get(url)                                   # 1 warm-up call, not recorded
        lat, counts = [], []
        for i in range(1, 31):
            t0 = time.perf_counter()
            resp = s.get(url)
            ms = (time.perf_counter() - t0) * 1000
            assert resp.status_code == 200 and len(resp.json()) == size
            sql = int(resp.headers["X-SQL-Count"])
            lat.append(ms); counts.append(sql)
            rows.append([size, version, i, sql, round(ms, 2)])
        p50, p95, p99 = np.percentile(lat, [50, 95, 99])
        summary.append([size, version, counts[0], round(p50, 2), round(p95, 2), round(p99, 2)])

with open(f"{OUT}/requests_180.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["page_size", "version", "request_no", "sql_stmts", "latency_ms"])
    w.writerows(rows)

lines = ["| Page size | Version | SQL stmts/req | p50 (ms) | p95 (ms) | p99 (ms) |",
         "|---|---|---|---|---|---|"]
lines += [f"| {a} | {b} | {c} | {d} | {e} | {g} |" for a, b, c, d, e, g in summary]
lines.append("")
lines.append("Speed-up (naive p50 / fixed p50):")
for size in (10, 50, 200):
    n = next(x for x in summary if x[0] == size and x[1] == "naive")[3]
    fx = next(x for x in summary if x[0] == size and x[1] == "fixed")[3]
    lines.append(f"- size {size}: {n / fx:.1f}x")
open("reports/hw04/METRICS.md", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))