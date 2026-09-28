import csv, json

REFUSAL = "I cannot answer this question from the provided documents"
results = json.load(open("reports/hw04/raw/three_config_results.json"))

# Chunks that must be in the top 3 for the question to be answerable (None = nothing to find)
NEEDED = {
    "Q1": ["01_session_auth_hw4.txt#2"],
    "Q2": ["02_session_hw3_legacy.txt#0", "01_session_auth_hw4.txt#0"],
    "Q3": ["02_session_hw3_legacy.txt#0", "03_database_setup.txt#0"],
    "Q4": ["01_session_auth_hw4.txt#2", "02_session_hw3_legacy.txt#0"],
    "Q5": None, "Q6": None,
}

# Manual judgments from the final run: (correct_answer, grounded, refused_when_needed)
# refused_when_needed is None for Q1-Q4 (no refusal needed)
J = {
    ("Q1", "A"): (0, 0, None), ("Q1", "B"): (1, 1, None), ("Q1", "C"): (1, 1, None),
    ("Q2", "A"): (0, 0, None), ("Q2", "B"): (1, 1, None), ("Q2", "C"): (1, 1, None),
    ("Q3", "A"): (0, 0, None), ("Q3", "B"): (1, 1, None), ("Q3", "C"): (1, 1, None),
    ("Q4", "A"): (0, 0, None), ("Q4", "B"): (1, 1, None), ("Q4", "C"): (1, 1, None),
    ("Q5", "A"): (1, 1, 1),    ("Q5", "B"): (0, 0, 0),    ("Q5", "C"): (1, 1, 1),
    ("Q6", "A"): (0, 0, 0),    ("Q6", "B"): (0, 0, 0),    ("Q6", "C"): (1, 1, 1),
}

def fmt_ok(cfg, answer):
    if cfg == "C":
        return int(REFUSAL in answer or "[" in answer)   # cited or exact refusal
    return 0                                             # A and B have no citation rule

rows = []
for r in results:
    got = [c["chunk_id"] for c in r["retrieved"]]
    need = NEEDED[r["id"]]
    retr = "n/a" if need is None else int(all(n in got for n in need))
    for cfg in "ABC":
        ans, grd, ref = J[(r["id"], cfg)]
        rows.append([r["id"], cfg, retr if cfg != "A" else "n/a", ans, grd,
                     "n/a" if ref is None else ref, fmt_ok(cfg, r[cfg])])

hdr = ["question", "config", "correct_retrieval", "correct_answer", "grounded",
       "refused_when_needed", "format_ok"]
with open("reports/hw04/raw/evaluation_table.csv", "w", newline="") as f:
    csv.writer(f).writerows([hdr] + rows)

lines = ["| Q | Config | Correct retrieval | Correct answer | Grounded | Refused when needed | Format OK |",
         "|---|---|---|---|---|---|---|"]
lines += ["| " + " | ".join(str(x) for x in row) + " |" for row in rows]

def rate(cfg, col, only=None):
    vals = [row[col] for row in rows if row[1] == cfg and row[col] != "n/a"
            and (only is None or row[0] in only)]
    return f"{sum(vals)}/{len(vals)}"

lines += ["", "| Config | Accuracy (correct answer) | Faithfulness (grounded) | Format compliance | Robustness (Q5+Q6 refused) |",
          "|---|---|---|---|---|"]
for cfg in "ABC":
    lines.append(f"| {cfg} | {rate(cfg,3)} | {rate(cfg,4)} | {rate(cfg,6)} | {rate(cfg,5)} |")

open("reports/hw04/raw/evaluation_table.md", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))