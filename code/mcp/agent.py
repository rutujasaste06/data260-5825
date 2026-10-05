import json
import time
import ollama
import executor

MODEL = "qwen3:8b"
MAX_STEPS = 5
LOG_FILE = "agent_runs.jsonl"

TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "search_trials", "description": "Search clinical trials by title.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}, "limit": {"type": "integer"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "get_trial", "description": "Get one trial and its sponsor by id.",
        "parameters": {"type": "object", "properties": {
            "trial_id": {"type": "integer"}}, "required": ["trial_id"]}}},
    {"type": "function", "function": {
        "name": "count_trials_by_sponsor",
        "description": "Count trials and total slots for a sponsor id.",
        "parameters": {"type": "object", "properties": {
            "sponsor_id": {"type": "integer"}}, "required": ["sponsor_id"]}}},
]


class OllamaModel:
    def chat(self, messages):
        return ollama.chat(model=MODEL, messages=messages, tools=TOOL_SPECS)


def log(entry, path=LOG_FILE):
    with open(path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def _get(obj, key, default=None):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def run_agent(user_input, model=None, db=None, max_steps=MAX_STEPS, log_path=LOG_FILE):
    model = model or OllamaModel()
    messages = [
        {"role": "system", "content": "You answer questions about clinical trials. "
         "Use the tools to get real data. Answer briefly."},
        {"role": "user", "content": user_input},
    ]
    tool_calls_made = 0
    blocked = False
    run_id = int(time.time() * 1000)
    for step in range(1, max_steps + 1):
        resp = model.chat(messages)
        msg = _get(resp, "message")
        calls = _get(msg, "tool_calls") or []
        content = _get(msg, "content") or ""
        if not calls:
            log({"run": run_id, "step": step, "event": "final",
                 "answer": content, "stop_reason": "completed"}, log_path)
            return {"answer": content, "steps": step, "stop_reason": "completed",
                    "tool_calls": tool_calls_made, "safety_blocked": blocked}
        messages.append({"role": "assistant", "content": content})
        for c in calls:
            fn = _get(c, "function")
            name = _get(fn, "name")
            args = dict(_get(fn, "arguments") or {})
            result = executor.execute_tool(name, args, db=db)
            tool_calls_made += 1
            if "safety rule" in result:
                blocked = True
            log({"run": run_id, "step": step, "event": "tool_call", "tool": name,
                 "input": args, "result": json.loads(result)}, log_path)
            messages.append({"role": "tool", "content": result, "name": name})
    log({"run": run_id, "step": max_steps, "event": "stop",
         "stop_reason": "max_steps"}, log_path)
    return {"answer": None, "steps": max_steps, "stop_reason": "max_steps",
            "tool_calls": tool_calls_made, "safety_blocked": blocked}