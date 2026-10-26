"""Smoke test for HW7: starts the API, runs basic checks, writes reports/hw07/verification.json."""
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import httpx

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENT_DIR = os.path.join(ROOT, "code", "hw7_agent")
P4_DIR = os.path.join(AGENT_DIR, "part4")
API_DIR = os.path.join(ROOT, "code", "api")
SID4, SEED, VERIFY_SEED = 5825, 5825, 265825
PORT_BASE = 8000 + (SID4 % 900)
API = f"http://127.0.0.1:{PORT_BASE}"
MODEL = "qwen3:8b"
results, state = [], {}
for d in (API_DIR, AGENT_DIR, P4_DIR, os.path.join(ROOT, "src")):
    sys.path.insert(0, d)


def check(name, fn):
    """Run one check, record pass/fail and a short detail."""
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"
    results.append({"check": name, "passed": bool(ok), "detail": str(detail)})
    print(("PASS  " if ok else "FAIL  ") + name + " - " + str(detail))


def up():
    """Return True if the API answers on PORT_BASE."""
    try:
        return httpx.get(API + "/docs", timeout=2).status_code == 200
    except Exception:
        return False


def start(log):
    """Start uvicorn unless a server already runs on the port; return the process or None."""
    if up():
        return None
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--app-dir", API_DIR,
                             "--port", str(PORT_BASE)], stdout=log, stderr=subprocess.STDOUT, cwd=API_DIR)
    for _ in range(60):
        if up():
            break
        time.sleep(1)
    return proc


def git(*args):
    """Return the output of a git command run in the repo root."""
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()


def login(user, password):
    return httpx.post(API + "/auth/login", json={"username": user, "password": password}, timeout=10)


def token(user, password):
    return {"Authorization": "Bearer " + login(user, password).json()["access_token"]}


def login_ok():
    r = login("reader1", "reader123")
    return r.status_code == 200 and bool(r.json().get("access_token")), f"valid login -> {r.status_code}, token returned"


def login_bad():
    r = login("reader1", "wrong-password")
    return r.status_code == 401, f"wrong password -> {r.status_code}"


def me_no_token():
    r = httpx.get(API + "/auth/me", timeout=10)
    return r.status_code == 401, f"no token -> {r.status_code}"


def me_bad_token():
    r = httpx.get(API + "/auth/me", headers={"Authorization": "Bearer not.a.token"}, timeout=10)
    return r.status_code == 401, f"invalid token -> {r.status_code}"


def trial_body():
    return {"trial_title": "Verify HW7 trial", "nct_number": f"NCT{int(time.time())}", "available_slots": 3}


def reader_forbidden():
    r = httpx.post(API + "/trials", json=trial_body(), headers=token("reader1", "reader123"), timeout=10)
    return r.status_code == 403, f"reader POST /trials -> {r.status_code}"


def writer_creates():
    r = httpx.post(API + "/trials", json=trial_body(), headers=token("writer1", "writer123"), timeout=10)
    state["trial_id"] = r.json().get("id") if r.status_code == 201 else None
    return r.status_code == 201 and bool(state["trial_id"]), f"writer POST /trials -> {r.status_code}"


def writer_delete_forbidden():
    r = httpx.delete(f"{API}/trials/{state.get('trial_id')}", headers=token("writer1", "writer123"), timeout=10)
    return r.status_code == 403, f"writer DELETE -> {r.status_code}"


def moderator_deletes():
    r = httpx.delete(f"{API}/trials/{state.get('trial_id')}", headers=token("mod1", "mod123"), timeout=10)
    return r.status_code == 200, f"moderator DELETE -> {r.status_code}"


def password_hashed():
    import models
    from database import SessionLocal
    with SessionLocal() as db:
        users = db.query(models.User).all()
    bad = [u.username for u in users if not str(u.password_hash).startswith("$2")]
    return bool(users) and not bad, f"{len(users)} users, all bcrypt hashes: {not bad}"


def sql_boundary():
    import tools
    csv_path = os.path.join(tempfile.gettempdir(), "verify_hw7_trips.csv")
    with open(csv_path, "w") as f:
        f.write("ride_id,rideable_type,started_at,ended_at,member_casual\n"
                "r1,classic_bike,2026-01-01 10:00:00,2026-01-01 10:20:00,casual\n")
    good = tools.csv_sql("SELECT COUNT(*) AS n FROM trips", csv_path)
    bad = [tools.csv_sql(q, csv_path)["success"] for q in
           ("DROP TABLE trips", "SELECT 1; DELETE FROM trips", "SELECT * FROM trips", "UPDATE trips SET rideable_type='x'")]
    return good["success"] and not any(bad), f"SELECT ok={good['success']}, 4 unsafe queries all rejected={not any(bad)}"


def calculator_ok():
    import tools
    r = tools.calculator("500*1 + 100*0.19")
    bad = tools.calculator("__import__('os').system('ls')")
    return r["success"] and abs(r["data"]["value"] - 519.0) < 1e-6 and not bad["success"], \
        f"calculator -> {r.get('data')}, code injection rejected={not bad['success']}"


def safety_gate():
    import file_tools as ft
    safe = ["ls -la", "cat app.py", "echo hello"]
    blocked = ["rm -rf /tmp/demo", "ls && rm -rf build", "sudo cat /etc/shadow", "chmod 777 app.py"]
    safe_ok = all(not ft.is_destructive(c) for c in safe)
    block_ok = all(ft.is_destructive(c) for c in blocked)
    return safe_ok and block_ok, f"3 safe commands allowed={safe_ok}, 4 destructive commands flagged={block_ok}"


def agent_loop_case():
    import agent_loop
    import verifiers
    cases = json.load(open(os.path.join(ROOT, "reports", "hw07", "raw", "verification_cases.json")))
    case = next(c for c in cases if c["id"] == "E")
    run = agent_loop.run_agent(case["prompt"], seed=VERIFY_SEED)
    verdict = verifiers.verify(case, run)
    return verdict["success"], (f"case E (missing trial): stop={run['stop_reason']}, tool_calls={run['tool_calls']}, "
                                f"verifier success={verdict['success']}")


def main():
    procs = []
    log_path = os.path.join(tempfile.gettempdir(), "verify_hw07_servers.log")
    with open(log_path, "w") as log:
        try:
            procs.append(start(log))
            check("API responds on PORT_BASE", lambda: (up(), f"GET /docs on port {PORT_BASE}"))
            check("Auth: valid login returns a token", login_ok)
            check("Auth: wrong password gives 401", login_bad)
            check("Auth: /auth/me without token gives 401", me_no_token)
            check("Auth: invalid token gives 401", me_bad_token)
            check("Roles: reader cannot create a trial (403)", reader_forbidden)
            check("Roles: writer can create a trial (201)", writer_creates)
            check("Roles: writer cannot delete (403)", writer_delete_forbidden)
            check("Roles: moderator can delete (200)", moderator_deletes)
            check("Passwords are stored as bcrypt hashes in MySQL", password_hashed)
            check("csv_sql allows one SELECT and rejects unsafe SQL", sql_boundary)
            check("calculator evaluates arithmetic and rejects code", calculator_ok)
            check("Part 6 gate allows safe and flags destructive commands", safety_gate)
            check("Hand-written agent loop completes a verification case", agent_loop_case)
        finally:
            for p in procs:
                if p:
                    p.terminate()
    if not all(r["passed"] for r in results):
        print("---- last lines of server log ----")
        print("".join(open(log_path).readlines()[-25:]))
    try:
        tag_commit = git("rev-parse", "hw7^{commit}")
    except Exception:
        tag_commit = None
    out = {"homework": "HW7", "sid4": SID4, "commit_hash": git("rev-parse", "HEAD"), "tag_hw7_commit": tag_commit,
           "model_configuration": {"chat_model": MODEL, "embed_model": "nomic-embed-text", "framework_agent": "langgraph create_react_agent"},
           "seed": SEED, "verify_seed": VERIFY_SEED, "port_base": PORT_BASE,
           "run_at_utc": datetime.now(timezone.utc).isoformat(), "checks": results,
           "all_passed": all(r["passed"] for r in results)}
    path = os.path.join(ROOT, "reports", "hw07", "verification.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("wrote", path, "| all_passed =", out["all_passed"])
    sys.exit(0 if out["all_passed"] else 1)


if __name__ == "__main__":
    main()
