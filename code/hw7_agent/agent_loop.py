"""Hand-written agent loop for HW7 Part 2.

run_agent(user_input) sends the question to the model, executes each tool call through
executor.execute_tool, appends the result as a tool-role message, and repeats until the
model gives a final answer or a hard iteration ceiling is reached.
"""
import json
import logging
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "mcp"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "src"))

import executor  # noqa: E402
from agent import TOOL_SPECS  # noqa: E402  (the three HW5 tool schemas)
from model_client import ModelClient  # noqa: E402

MAX_ITERATIONS = 6  # hard ceiling on model calls per run
MAX_REPAIRS = 2  # failed repairs allowed before a clean stop
SYSTEM_PROMPT = (
    "You answer questions about clinical trials. Always use the tools to get real data and "
    "never guess. For multi-step questions keep calling tools until you have everything, "
    "then answer briefly using only what the tools returned. search_trials only returns a "
    "short list: when the question asks for details (NCT number, slots, title, comparisons), "
    "call get_trial for each trial you need before answering."
)
TYPES = {"string": str, "integer": int}

log = logging.getLogger("agent_loop")
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(asctime)s [agent] %(message)s", "%H:%M:%S"))
log.addHandler(_handler)
log.setLevel(logging.INFO)
log.propagate = False


def _get(obj, key, default=None):
    """Read a key from a dict or an attribute from an object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def parse_args(raw):
    """Arguments may arrive as a dict or a JSON string; return a dict or the raw value."""
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return dict(raw) if hasattr(raw, "items") else (raw if raw is not None else {})


def _check_arg(name, key, value, props):
    """Return a problem string for one argument, or None."""
    if key not in props:
        return f"unexpected argument '{key}' for '{name}'"
    want = props[key]["type"]
    if not isinstance(value, TYPES[want]) or isinstance(value, bool):
        return f"argument '{key}' for '{name}' must be of type {want}"
    return None


def validate_call(name, args):
    """Return (failure_type, problem) for a bad call, or None when it is well-formed."""
    spec = next((s["function"] for s in TOOL_SPECS if s["function"]["name"] == name), None)
    if spec is None:
        known = ", ".join(s["function"]["name"] for s in TOOL_SPECS)
        return "unknown_tool", f"unknown tool '{name}'. Available tools: {known}"
    params = spec["parameters"]
    if not isinstance(args, dict):
        return "malformed_arguments", f"arguments for '{name}' must be a JSON object"
    for key in params.get("required", []):
        if key not in args:
            return "malformed_arguments", f"missing required argument '{key}' for '{name}'"
    for key, value in args.items():
        problem = _check_arg(name, key, value, params["properties"])
        if problem:
            return "malformed_arguments", problem
    return None


def _new_state():
    """Fresh counters for one run."""
    return {"tool_calls": 0, "invalid": [], "repairs": 0, "failed_repairs": 0,
            "awaiting_repair": False, "text_reprompted": False, "trace": [],
            "prompt_tokens": 0, "completion_tokens": 0}


def _add_usage(state, resp):
    """Add the token counts reported by Ollama for this model call."""
    state["prompt_tokens"] += _get(resp, "prompt_eval_count", 0) or 0
    state["completion_tokens"] += _get(resp, "eval_count", 0) or 0


def _execute(messages, state, name, args, db):
    """Execute one valid call and append the result as a tool-role message."""
    result = executor.execute_tool(name, args, db=db)
    state["tool_calls"] += 1
    log.info("tool_call #%d %s inputs=%s -> %s", state["tool_calls"], name,
             json.dumps(args), result[:90])
    state["trace"].append({"tool": name, "inputs": args, "result": json.loads(result)})
    messages.append({"role": "tool", "content": result, "name": name})


def _reject(messages, state, name, bad):
    """Record a rejected call and tell the model why through a tool-role message."""
    kind, problem = bad
    state["invalid"].append({"type": kind, "problem": problem})
    log.info("REJECTED call %s: %s", name, problem)
    error = json.dumps({"ok": False, "data": None, "error": problem})
    messages.append({"role": "tool", "content": error, "name": str(name or "unknown")})
    return problem


def _reprompt(messages, state, problems, max_repairs):
    """Reprompt with the specific problem; stop cleanly when repairs keep failing."""
    if state["awaiting_repair"]:
        state["failed_repairs"] += 1
    if state["failed_repairs"] >= max_repairs:
        return "repair_failed", None
    state["awaiting_repair"] = True
    state["repairs"] += 1
    text = "Your tool call was rejected: " + "; ".join(problems) + ". Call it again correctly."
    messages.append({"role": "user", "content": text})
    return None


def _handle_calls(messages, content, calls, state, db, max_repairs):
    """Run or reject every tool call in one model message; return a stop tuple or None."""
    parsed = []
    for c in calls:
        fn = _get(c, "function")
        parsed.append((_get(fn, "name"), parse_args(_get(fn, "arguments"))))
    shown = [{"function": {"name": str(n), "arguments": a if isinstance(a, dict) else {}}}
             for n, a in parsed]
    messages.append({"role": "assistant", "content": content, "tool_calls": shown})
    problems = []
    for name, args in parsed:
        bad = validate_call(name, args)
        if bad:
            problems.append(_reject(messages, state, name, bad))
        else:
            _execute(messages, state, name, args, db)
    if not problems:
        state["awaiting_repair"] = False
        return None
    return _reprompt(messages, state, problems, max_repairs)


def _handle_text(messages, content, state):
    """The model answered in text: finish if tools were used, otherwise reprompt once."""
    if state["tool_calls"] > 0:
        return "completed", content
    if state["text_reprompted"]:
        return "repair_failed", None
    state["text_reprompted"] = True
    state["repairs"] += 1
    state["invalid"].append({"type": "text_instead_of_tool", "problem": "answered with text"})
    log.info("REJECTED: model answered with text when a tool was required")
    messages.append({"role": "assistant", "content": content})
    messages.append({"role": "user", "content": "You must call a tool to get real data "
                     "before answering. Call the right tool now."})
    return None


def run_agent(user_input, model=None, max_iterations=MAX_ITERATIONS,
              max_repairs=MAX_REPAIRS, extra_system="", seed=None, db=None):
    """Run one question through the tool loop and return the answer plus run statistics."""
    model = model or ModelClient()
    messages = [{"role": "system", "content": SYSTEM_PROMPT + extra_system},
                {"role": "user", "content": user_input}]
    state = _new_state()
    started = time.time()
    stop_reason, answer, iteration = "max_iterations", None, 0
    for iteration in range(1, max_iterations + 1):
        resp = model.chat_with_tools(messages, TOOL_SPECS, seed=seed)
        _add_usage(state, resp)
        msg = _get(resp, "message")
        calls = _get(msg, "tool_calls") or []
        content = _get(msg, "content") or ""
        if calls:
            stop = _handle_calls(messages, content, calls, state, db, max_repairs)
        else:
            stop = _handle_text(messages, content, state)
        if stop:
            stop_reason, answer = stop
            break
    return _finish(state, answer, stop_reason, started, iteration)


def _finish(state, answer, stop_reason, started, iteration):
    """Build the result dict and log the total number of tool calls."""
    log.info("run finished: total_tool_calls=%d stop_reason=%s iterations=%d",
             state["tool_calls"], stop_reason, iteration)
    return {"answer": answer, "stop_reason": stop_reason, "tool_calls": state["tool_calls"],
            "trace": state["trace"], "invalid": state["invalid"], "repairs": state["repairs"],
            "iterations": iteration, "prompt_tokens": state["prompt_tokens"],
            "completion_tokens": state["completion_tokens"],
            "latency_ms": round((time.time() - started) * 1000, 1)}
