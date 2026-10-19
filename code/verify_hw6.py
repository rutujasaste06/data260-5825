"""Smoke test for HW6: starts the APIs, runs basic checks, writes reports/hw06/verification.json."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone

import httpx

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SID4, SEED, VERIFY_SEED = 5825, 5825, 265825
PORT_BASE = 8000 + (SID4 % 900)
DOC_PORT, MEM_PORT = PORT_BASE, PORT_BASE + 2
DOC, MEM = f"http://127.0.0.1:{DOC_PORT}", f"http://127.0.0.1:{MEM_PORT}"
DOC_DIR = os.path.join(ROOT, "code", "doc_api")
MEM_DIR = os.path.join(ROOT, "code", "memory_api")
FM_DIR = os.path.join(ROOT, "code", "file_memory")
results, state = [], {}


def check(name, fn):
    """Run one check, record pass/fail and a short detail."""
    try:
        ok, detail = fn()
    except Exception as e:
        ok, detail = False, f"{type(e).__name__}: {e}"
    results.append({"check": name, "passed": bool(ok), "detail": str(detail)})
    print(("PASS  " if ok else "FAIL  ") + name + " - " + str(detail))


def up(port):
    """Return True if a FastAPI server answers on this port."""
    try:
        return httpx.get(f"http://127.0.0.1:{port}/docs", timeout=2).status_code == 200
    except Exception:
        return False


def start(app_dir, port, log):
    """Start uvicorn unless a server already runs on the port; return the process or None."""
    if up(port):
        return None
    proc = subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--app-dir", app_dir,
                             "--port", str(port)], stdout=log, stderr=subprocess.STDOUT, cwd=app_dir)
    for _ in range(60):
        if up(port):
            break
        time.sleep(1)
    return proc


def git(*args):
    """Return the output of a git command run in the repo root."""
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True,
                                   stderr=subprocess.DEVNULL).strip()


def mongo_ok():
    from pymongo import MongoClient
    MongoClient(serverSelectionTimeoutMS=3000).admin.command("ping")
    return True, "MongoDB answered ping"


def doc_root():
    r = httpx.get(DOC + "/", timeout=10)
    return r.status_code == 200, f"GET / -> {r.status_code} on port {DOC_PORT}"


def doc_create():
    body = {"trial_title": "Verify HW6 trial", "phase": "phase2", "status": "recruiting",
            "start_date": "2026-01-01T00:00:00"}
    r = httpx.post(DOC + "/trials-doc", json=body, timeout=10)
    state["trial_id"] = r.json().get("id") if r.status_code == 201 else None
    return r.status_code == 201 and bool(state["trial_id"]), f"POST -> {r.status_code}"


def doc_get():
    r = httpx.get(f"{DOC}/trials-doc/{state.get('trial_id')}", timeout=10)
    return r.status_code == 200, f"GET by id -> {r.status_code}"


def doc_422():
    r = httpx.post(DOC + "/trials-doc", json={"trial_title": "", "phase": "phase1",
                                              "start_date": "2026-01-01T00:00:00"}, timeout=10)
    return r.status_code == 422, f"empty title -> {r.status_code}"


def doc_404():
    r = httpx.get(DOC + "/trials-doc/000000000000000000000000", timeout=10)
    return r.status_code == 404, f"unknown id -> {r.status_code}"


def doc_delete():
    r = httpx.delete(f"{DOC}/trials-doc/{state.get('trial_id')}", timeout=10)
    return r.status_code == 200, f"DELETE -> {r.status_code}"


def mem_up():
    return up(MEM_PORT), f"memory API answers on port {MEM_PORT}"


def mem_chat():
    body = {"user_id": state["uid"], "message": "Reply in one short sentence: what is a Phase 2 trial?"}
    r = httpx.post(MEM + "/api/chat", json=body, timeout=300)
    data = r.json() if r.status_code == 200 else {}
    reply = next((data[k] for k in ("reply", "response", "answer", "message")
                  if isinstance(data.get(k), str)), "")
    return r.status_code == 200 and len(reply.strip()) > 0, f"POST /api/chat -> {r.status_code}, keys {sorted(data)}"


def mem_read():
    r = httpx.get(f"{MEM}/api/memory/{state['uid']}", timeout=30)
    return r.status_code == 200, f"GET /api/memory -> {r.status_code}"


def file_memory():
    text = open(os.path.join(FM_DIR, "MEMORY.md"), encoding="utf-8").read()
    n = sum(1 for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("<!--"))
    stamp = "last_consolidated" in text
    agent = os.path.exists(os.path.join(ROOT, "AGENT.md"))
    return n < 40 and stamp and agent, f"MEMORY.md {n} lines (<40), stamp={stamp}, AGENT.md exists={agent}"


def cleanup_memory_data():
    """Delete the test chat data created by this script."""
    try:
        sys.path.insert(0, MEM_DIR)
        import mem_db
        for coll in (mem_db.messages, mem_db.summaries, mem_db.episodes):
            coll.delete_many({"user_id": state["uid"]})
    except Exception as e:
        print("cleanup note:", e)


def model_config():
    spec = importlib.util.spec_from_file_location("memcfg", os.path.join(MEM_DIR, "config.py"))
    cfg = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cfg)
    return {"chat_model": cfg.CHAT_MODEL, "embed_model": cfg.EMBED_MODEL,
            "short_term_n": cfg.SHORT_TERM_N, "top_k_episodes": cfg.TOP_K_EPISODES}


def main():
    state["uid"] = "verify_hw06_" + uuid.uuid4().hex[:8]
    procs = []
    log_path = os.path.join(tempfile.gettempdir(), "verify_hw06_servers.log")
    with open(log_path, "w") as log:
        try:
            check("MongoDB reachable", mongo_ok)
            procs.append(start(DOC_DIR, DOC_PORT, log))
            procs.append(start(MEM_DIR, MEM_PORT, log))
            check("Doc API responds on PORT_BASE", doc_root)
            check("Doc API: POST creates a trial (201)", doc_create)
            check("Doc API: GET by id returns it (200)", doc_get)
            check("Doc API: empty title rejected (422)", doc_422)
            check("Doc API: unknown id gives 404", doc_404)
            check("Doc API: DELETE removes the trial (200)", doc_delete)
            check("Memory API is up", mem_up)
            check("Memory API: POST /api/chat returns a reply", mem_chat)
            check("Memory API: GET /api/memory/{user} works", mem_read)
            check("File memory: MEMORY.md < 40 lines with stamp, AGENT.md exists", file_memory)
        finally:
            cleanup_memory_data()
            for p in procs:
                if p:
                    p.terminate()
    if not all(r["passed"] for r in results):
        print("---- last lines of server log ----")
        print("".join(open(log_path).readlines()[-25:]))                    
    try:
        tag_commit = git("rev-parse", "hw6^{commit}")
    except Exception:
        tag_commit = None
    out = {"homework": "HW6", "sid4": SID4, "commit_hash": git("rev-parse", "HEAD"),
           "tag_hw6_commit": tag_commit, "model_configuration": model_config(),
           "seed": SEED, "verify_seed": VERIFY_SEED, "port_base": PORT_BASE,
           "run_at_utc": datetime.now(timezone.utc).isoformat(), "checks": results,
           "all_passed": all(r["passed"] for r in results)}
    path = os.path.join(ROOT, "reports", "hw06", "verification.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print("wrote", path, "| all_passed =", out["all_passed"])
    sys.exit(0 if out["all_passed"] else 1)


if __name__ == "__main__":
    main()