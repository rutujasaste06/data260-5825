import json
import executor


class FakeTrial:
    def __init__(self, id, title, nct, slots, sponsor_id):
        self.id, self.trial_title, self.nct_number = id, title, nct
        self.available_slots, self.sponsor_id = slots, sponsor_id


class FakeSponsor:
    def __init__(self, id, name):
        self.id, self.sponsor_name = id, name


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
    def filter(self, *a, **k): return self
    def order_by(self, *a, **k): return self
    def limit(self, *a, **k): return self
    def all(self): return self.rows
    def first(self): return self.rows[0] if self.rows else None
    def one(self): return (len(self.rows), sum(r.available_slots for r in self.rows))


class FakeDB:
    """Offline stand-in for the database. No MySQL needed."""
    def __init__(self, trials=(), sponsors=()):
        self.trials, self.sponsors = list(trials), list(sponsors)
    def query(self, *cols):
        import models
        first = cols[0]
        if first is models.Sponsor:
            return FakeQuery(self.sponsors)
        return FakeQuery(self.trials)
    def close(self): pass


def run(name, inputs, db=None):
    return json.loads(executor.execute_tool(name, inputs, db=db))


def make_db():
    return FakeDB([FakeTrial(1, "Pfizer Diabetes", "NCT1", 25, 1)],
                  [FakeSponsor(1, "Pfizer Research")])


def t_search_valid():
    r = run("search_trials", {"query": "Diabetes", "limit": 5}, make_db())
    assert r["ok"] is True and r["error"] is None and len(r["data"]) == 1

def t_search_empty_query():
    r = run("search_trials", {"query": "", "limit": 5}, make_db())
    assert r["ok"] is False and "non-empty" in r["error"] and r["data"] is None

def t_search_bad_limit():
    r = run("search_trials", {"query": "x", "limit": 500}, make_db())
    assert r["ok"] is False and "limit" in r["error"]

def t_get_valid():
    r = run("get_trial", {"trial_id": 1}, make_db())
    assert r["ok"] is True and r["data"]["id"] == 1

def t_get_invalid_id():
    r = run("get_trial", {"trial_id": 0}, make_db())
    assert r["ok"] is False and "positive integer" in r["error"]

def t_count_invalid_sponsor_type():
    r = run("count_trials_by_sponsor", {"sponsor_id": "abc"}, make_db())
    assert r["ok"] is False and "positive integer" in r["error"]

def t_unknown_tool():
    r = run("delete_everything", {}, make_db())
    assert r["ok"] is False and "unknown tool" in r["error"]

def t_bad_arguments():
    r = run("get_trial", {"wrong_name": 1}, make_db())
    assert r["ok"] is False and "bad arguments" in r["error"]

def t_envelope_shape():
    r = run("get_trial", {"trial_id": 1}, make_db())
    assert set(r.keys()) == {"ok", "data", "error"}
def t_safety_blocks():
    r = run("search_trials", {"query": "x", "limit": 100}, make_db())
    assert r["ok"] is False and "safety rule" in r["error"] and r["data"] is None

def t_agent_max_steps():
    import agent

    class MockModel:
        def chat(self, messages):
            return {"message": {"role": "assistant", "content": "",
                    "tool_calls": [{"function": {"name": "get_trial",
                                                  "arguments": {"trial_id": 1}}}]}}

    out = agent.run_agent("loop forever", model=MockModel(), db=make_db(),
                          max_steps=3, log_path="test_agent_runs.jsonl")
    assert out["stop_reason"] == "max_steps" and out["steps"] == 3

TESTS = [t_search_valid, t_search_empty_query, t_search_bad_limit, t_get_valid,
         t_get_invalid_id, t_count_invalid_sponsor_type, t_unknown_tool,
         t_bad_arguments, t_envelope_shape, t_safety_blocks, t_agent_max_steps]


def main():
    passed = 0
    for t in TESTS:
        try:
            t()
            print(f"PASS  {t.__name__}")
            passed += 1
        except Exception as e:
            print(f"FAIL  {t.__name__}  ({e})")
    print(f"\n{passed}/{len(TESTS)} tests passed")
    return passed == len(TESTS)


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)