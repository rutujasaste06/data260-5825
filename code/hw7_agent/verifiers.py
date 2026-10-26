"""Deterministic checks for the fixed verification cases (used by Parts 2 and 3)."""
import json
import re


def _gets(trace):
    """trial_ids passed to get_trial, in order."""
    return [t["inputs"].get("trial_id") for t in trace if t["tool"] == "get_trial"]


def _search_before_get(trace, term):
    """True when a search for the term happened before the first get_trial."""
    for t in trace:
        if t["tool"] == "get_trial":
            return False
        if t["tool"] == "search_trials" and term.lower() in str(t["inputs"].get("query", "")).lower():
            return True
    return False


def chain_reason(case, trace):
    """Why the tool chain is wrong (a short sentence), or None when it is complete."""
    kind = case["kind"]
    if kind == "search_then_detail":
        if not _search_before_get(trace, case["term"]):
            return f"no search_trials('{case['term']}') before the lookup"
        if case["first_id"] not in _gets(trace):
            return f"get_trial({case['first_id']}) was never called for the first search result"
    elif kind == "aggregate_plus_example":
        sponsors = [t["inputs"].get("sponsor_id") for t in trace if t["tool"] == "count_trials_by_sponsor"]
        if case["sponsor_id"] not in sponsors:
            return f"count_trials_by_sponsor({case['sponsor_id']}) was never called"
        if case["example_id"] not in _gets(trace):
            return f"get_trial({case['example_id']}) was never called for the example"
    elif kind == "compare_two":
        if not _search_before_get(trace, case["term"]):
            return f"no search_trials('{case['term']}') before the lookups"
        missing = [i for i in case["ids"] if i not in _gets(trace)]
        if missing:
            return f"get_trial was not called for result id(s) {missing}"
    elif kind == "error_recovery" and case["missing_id"] not in _gets(trace):
        return f"get_trial({case['missing_id']}) was never called"
    return None


def _contains(answer, *needles):
    """True when the answer contains every needle (case-insensitive)."""
    text = (answer or "").lower().replace(",", "")
    return all(str(n).lower().replace(",", "") in text for n in needles)


def answer_reason(case, answer):
    """Why the final answer is wrong, or None."""
    kind = case["kind"]
    ok = {
        "search_then_detail": _contains(answer, case.get("nct", ""), case.get("sponsor", "")),
        "aggregate_plus_example": _contains(answer, case.get("count", "")) and
                                  _contains(answer, case.get("example_title", "")),
        "compare_two": _contains(answer, *case.get("ncts", [""]), *case.get("sponsors", [])),
        "error_recovery": any(w in (answer or "").lower() for w in ("not found", "not be found", "does not exist", "no trial", "couldn't find", "could not find", "doesn't exist")),
    }[kind]
    return None if ok else "final answer does not contain the expected facts"


def lenient_ok(case, answer):
    """A looser, independent reading of the answer (used to detect verifier false rejections)."""
    kind = case["kind"]
    options = {
        "search_then_detail": [case.get("nct"), case.get("sponsor")],
        "aggregate_plus_example": [case.get("example_title"), case.get("example_nct")],
        "compare_two": [case.get("sponsors", [None])[0]],
        "error_recovery": ["not found", "not be found", "does not exist"],
    }[kind]
    return any(_contains(answer, o) for o in options if o)


def unsupported_claims(answer, prompt, trace):
    """NCT codes or 4+ digit numbers in the answer that no tool result (or the question) contains."""
    seen = prompt + json.dumps([t["result"] for t in trace])
    claims = set(re.findall(r"NCT[\w-]*\d|\b\d{4,}\b", answer or ""))
    return sorted(c for c in claims if c not in seen)


def verify(case, run):
    """Return the verdict for one run: success, reasons, unsupported claims, false rejection."""
    chain = chain_reason(case, run["trace"])
    answer = run["answer"]
    reason = chain or (answer_reason(case, answer) if run["stop_reason"] == "completed"
                       else f"run stopped with {run['stop_reason']}")
    success = reason is None
    return {"success": success, "chain_ok": chain is None, "reason": reason,
            "unsupported": unsupported_claims(answer, case["prompt"], run["trace"]),
            "false_rejection": (not success) and chain is None and lenient_ok(case, answer)}
