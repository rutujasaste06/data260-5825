import json
import agent

SCENARIOS = [
    "How many trials does sponsor 1 have, and how many slots in total?",
    "Find trials about Diabetes and tell me the first one's NCT number.",
    "Look up trial 5001 and name its sponsor.",
    "Give me 100 trials about Metformin.",
]

rows = []
for q in SCENARIOS:
    out = agent.run_agent(q)
    rows.append({"question": q, "steps": out["steps"],
                 "stop_reason": out["stop_reason"],
                 "tool_calls": out["tool_calls"],
                 "safety_blocked": out["safety_blocked"]})
    print(json.dumps(rows[-1]))

print("\n| Scenario | Steps | Stop reason | Tool calls | Safety blocked |")
print("|---|---|---|---|---|")
for r in rows:
    print(f"| {r['question']} | {r['steps']} | {r['stop_reason']} | {r['tool_calls']} | {r['safety_blocked']} |")