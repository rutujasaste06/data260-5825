import asyncio, json, os, subprocess, sys, datetime
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCP = os.path.join(ROOT, "code", "mcp")
checks = []

def record(name, passed, detail=""):
    checks.append({"check": name, "passed": bool(passed), "detail": str(detail)})
    print(("PASS" if passed else "FAIL"), name, detail)

async def call(server_file, tool, args):
    env = os.environ.copy()
    params = StdioServerParameters(command=sys.executable, args=[server_file],
                                   cwd=MCP, env=env)
    async with stdio_client(params) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            tools = await s.list_tools()
            res = await s.call_tool(tool, args)
            return [t.name for t in tools.tools], res.content[0].text

def main():
    try:
        r = httpx.get("http://127.0.0.1:8425/docs", timeout=5)
        record("FastAPI backend responds on port 8425", r.status_code == 200)
    except Exception as e:
        record("FastAPI backend responds on port 8425", False, e)
    try:
        names, text = asyncio.run(call(os.path.join(MCP, "trials_server.py"),
                                       "get_trial", {"trial_id": 1}))
        record("trials MCP server lists 3 tools and answers a call",
               len(names) == 3 and json.loads(text)["ok"] is True, names)
    except Exception as e:
        record("trials MCP server lists 3 tools and answers a call", False, e)
    try:
        names, text = asyncio.run(call(os.path.join(MCP, "meals_server.py"),
                                       "search_meals_by_name", {"query": "Arrabiata"}))
        record("meals MCP server lists 4 tools and answers a call",
               len(names) == 4 and "results" in text, names)
    except Exception as e:
        record("meals MCP server lists 4 tools and answers a call", False, e)
    p = subprocess.run([sys.executable, "test_runner.py"], cwd=MCP,
                       capture_output=True, text=True, env=os.environ.copy())
    record("offline tests all pass", p.returncode == 0, p.stdout.strip().splitlines()[-1:])
    csv_path = os.path.join(ROOT, "reports", "hw05", "raw", "fault_injection_150.csv")
    n = sum(1 for _ in open(csv_path)) - 1 if os.path.exists(csv_path) else 0
    record("150 fault-injection records saved", n == 150, n)
    record("agent_runs.jsonl exists",
           os.path.exists(os.path.join(ROOT, "reports", "hw05", "raw", "agent_runs.jsonl")))
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    out = {"homework": 5, "sid4": 5825, "commit_hash": commit,
           "model": "qwen3:8b (Ollama)", "seed": 5825, "verify_seed": 265825,
           "run_at": datetime.datetime.now().isoformat(timespec="seconds"),
           "checks": checks, "all_passed": all(c["passed"] for c in checks)}
    with open(os.path.join(ROOT, "reports", "hw05", "verification.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("all passed:", out["all_passed"])

if __name__ == "__main__":
    main()