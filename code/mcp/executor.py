import json
import domain_core as core

TOOLS = {
    "search_trials": core.search_trials,
    "get_trial": core.get_trial,
    "count_trials_by_sponsor": core.count_trials_by_sponsor,
}

MAX_AGENT_LIMIT = 25  # safety rule: an agent may not pull more than 25 records


def check_safety(name, inputs):
    """Return an error message if the call breaks the safety rule, else None."""
    if name == "search_trials" and isinstance(inputs, dict):
        limit = inputs.get("limit", 10)
        if isinstance(limit, int) and limit > MAX_AGENT_LIMIT:
            return (f"safety rule: search_trials limit {limit} exceeds "
                    f"the maximum of {MAX_AGENT_LIMIT} records per call")
    return None


def execute_tool(name, inputs, db=None):
    
    try:
        if name not in TOOLS:
            return json.dumps(core.err(f"unknown tool: {name}"))
        if not isinstance(inputs, dict):
            return json.dumps(core.err("inputs must be an object"))
        violation = check_safety(name, inputs)
        if violation:
            return json.dumps(core.err(violation))
        result = TOOLS[name](**inputs, db=db)
        return json.dumps(result)
    except TypeError as e:
        return json.dumps(core.err(f"bad arguments: {e}"))
    except Exception as e:
        return json.dumps(core.err(f"internal error: {e}"))