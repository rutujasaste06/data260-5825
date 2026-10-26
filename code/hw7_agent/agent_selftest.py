"""Model-free self-test of the agent loop's repair path (scripted fake model, no database)."""
import json

import agent_loop


class ScriptedModel:
    """Returns one scripted reply per call, so every failure type can be triggered on demand."""

    def __init__(self, replies):
        self.replies = list(replies)

    def chat_with_tools(self, messages, tools, seed=None):
        """Pop the next scripted reply."""
        return self.replies.pop(0)


def call(name, args):
    """Build a scripted reply that contains one tool call."""
    return {"message": {"content": "", "tool_calls": [{"function": {"name": name, "arguments": args}}]},
            "prompt_eval_count": 10, "eval_count": 5}


def text(answer):
    """Build a scripted plain-text reply."""
    return {"message": {"content": answer, "tool_calls": []},
            "prompt_eval_count": 10, "eval_count": 5}


def fake_execute(name, args, db=None):
    """Stand-in for executor.execute_tool so no database is needed."""
    return json.dumps({"ok": True, "data": [{"id": 1}], "error": None})


def check(label, run, stop_reason, tool_calls, failures):
    """Print one PASS/FAIL line for a scripted scenario."""
    kinds = [i["type"] for i in run["invalid"]]
    good = run["stop_reason"] == stop_reason and run["tool_calls"] == tool_calls
    print(f"{'PASS' if good else 'FAIL'}  {label}: stop={run['stop_reason']} "
          f"tool_calls={run['tool_calls']} failures={kinds}")
    return good


def main():
    """Run the four repair-path scenarios."""
    agent_loop.executor.execute_tool = fake_execute
    print("Agent loop self-test - Rutuja Saste")
    good = [
        check("unknown tool, then repaired",
              agent_loop.run_agent("q", ScriptedModel([
                  call("find_trials", {"query": "x"}), call("search_trials", {"query": "x"}),
                  text("done")])), "completed", 1, None),
        check("malformed arguments, then repaired",
              agent_loop.run_agent("q", ScriptedModel([
                  call("get_trial", {"trial_id": "7"}), call("get_trial", {"trial_id": 7}),
                  text("done")])), "completed", 1, None),
        check("text instead of a tool, then repaired",
              agent_loop.run_agent("q", ScriptedModel([
                  text("I think so"), call("search_trials", {"query": "x"}),
                  text("done")])), "completed", 1, None),
        check("repairs keep failing -> clean stop",
              agent_loop.run_agent("q", ScriptedModel([
                  call("get_trial", {}), call("get_trial", {}), call("get_trial", {})])),
              "repair_failed", 0, None),
    ]
    print("ALL PASS" if all(good) else "SOME FAILED")
    return 0 if all(good) else 1


if __name__ == "__main__":
    raise SystemExit(main())
