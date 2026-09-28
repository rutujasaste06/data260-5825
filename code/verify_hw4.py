import json, subprocess
import requests

BASE = "http://localhost:8425"
SID4 = "5825"
SEED = 5825
VERIFY_SEED = 265825

checks = []

def check(name, ok, detail=""):
    checks.append({"check": name, "pass": bool(ok), "detail": detail})
    print(("PASS" if ok else "FAIL"), "-", name, ("-", detail) if detail else "")

# 1. Backend responds on PORT_BASE
try:
    r = requests.get(f"{BASE}/docs", timeout=5)
    check("backend responds on port 8425", r.status_code == 200)
except Exception as e:
    check("backend responds on port 8425", False, str(e))

# 2. Login works with a real account
s = requests.Session()
r = s.post(f"{BASE}/auth/login", json={"email": "user1@gmail.com", "password": "secret123"})
check("login succeeds", r.status_code == 200, f"status={r.status_code}")

# 3. Naive endpoint returns data
r = s.get(f"{BASE}/trials-naive?limit=5")
ok = r.status_code == 200 and len(r.json()) == 5
check("naive endpoint returns 5 trials", ok, f"status={r.status_code}")

# 4. Fixed endpoint returns data
r = s.get(f"{BASE}/trials-fixed?limit=5")
ok = r.status_code == 200 and len(r.json()) == 5
check("fixed endpoint returns 5 trials", ok, f"status={r.status_code}")

# 5. Fixed endpoint uses far fewer SQL statements than naive at a larger page
r_naive = s.get(f"{BASE}/trials-naive?limit=50")
r_fixed = s.get(f"{BASE}/trials-fixed?limit=50")
n = int(r_naive.headers.get("X-SQL-Count", -1))
f = int(r_fixed.headers.get("X-SQL-Count", -1))
check("fixed endpoint uses fewer SQL statements than naive", 0 < f < n, f"naive={n} fixed={f}")

# 6. Unauthenticated request is rejected
r_anon = requests.get(f"{BASE}/trials")
check("unauthenticated request rejected", r_anon.status_code == 401, f"status={r_anon.status_code}")

# 7. Corpus and RAG output files exist
import os
check("corpus has 5 documents", len(os.listdir("data/hw04_corpus")) == 5)
check("three_config_results.json exists", os.path.exists("reports/hw04/raw/three_config_results.json"))
check("k_sweep_results.json exists", os.path.exists("reports/hw04/raw/k_sweep_results.json"))
check("evaluation_table.csv exists", os.path.exists("reports/hw04/raw/evaluation_table.csv"))

# Commit hash
try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode().strip()
except Exception:
    commit = "unknown"

report = {
    "homework": "HW4",
    "SID4": SID4,
    "commit_hash": commit,
    "SEED": SEED,
    "VERIFY_SEED": VERIFY_SEED,
    "checks": checks,
    "all_passed": all(c["pass"] for c in checks),
}
os.makedirs("reports/hw04", exist_ok=True)
json.dump(report, open("reports/hw04/verification.json", "w"), indent=2)
print("\nAll passed:", report["all_passed"])
print("saved reports/hw04/verification.json")