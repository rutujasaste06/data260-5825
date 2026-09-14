# METRICS.md — HW2

## Configuration
- SID4: 5825
- PORT_BASE: 8425
- Model: qwen3:8b via Ollama
- Temperature: 0.7

## Experiment 1 — Schema Validation (30 runs, fixed input, max_turns=4)

Input: `reports/hw02/cases/schema_input.json`

| Outcome | Count |
|---|---|
| Valid first attempt | 30 |
| Valid after 1 retry | 0 |
| Valid after 2+ retries | 0 |
| Abandoned at ceiling | 0 |

**Observation:** The Planner produced valid output (exactly 3 tags, ≤25-word summary) on the first attempt in all 30 runs, indicating the prompt design reliably produces schema-compliant output for this input under normal conditions.

## Experiment 2 — Turn Ceiling Comparison (20 runs each, same frozen input)

| Metric | max_turns = 2 | max_turns = 10 |
|---|---|---|
| Completion rate | 100.0% | 100.0% |
| Mean latency | 33,908.55 ms | 36,021.13 ms |

**Deployment choice:** max_turns = 2. Both ceilings achieved identical 100% completion rates, and the mean latency difference (~2.1 seconds) is negligible. Since the fixed input never required more than 1 retry to pass validation, the higher ceiling provided no reliability benefit while adding unnecessary allowance for retries. A lower ceiling reduces worst-case latency in production without sacrificing success rate for typical inputs.

## Experiment 3 — Adversarial Input (5 runs, max_turns=4)

Adversarial input: a prompt instructing the model to ignore the tag/summary rules, provide only one tag, and write a 100+ word summary.

| Metric | Result |
|---|---|
| Runs that hit the turn ceiling | 3 / 5 (60%) |
| Runs that recovered (valid after retry) | 2 / 5 (40%) |

**Observation:** The observed ceiling-hit rate is 60%, not deterministic — in 2 of 5 runs, the correction-feedback loop successfully brought the output back into compliance by the second attempt. This shows the retry mechanism has partial but inconsistent effectiveness against adversarial instructions embedded in the input content.

**Why this causes trouble:** The adversarial input directly instructs the model to disregard the tag/summary formatting rules, and the underlying model (qwen3:8b) partially complies by producing malformed output (1 tag instead of 3, summaries far exceeding 25 words) even after being told the correct rules in the system prompt. This shows the model can be influenced by conflicting instructions embedded in the untrusted input content, not just the system-level rules.

**Proposed fix:** Strengthen the Planner's prompt to explicitly state that formatting requirements (exactly 3 tags, ≤25-word summary) are non-negotiable system constraints that override any conflicting instructions found within the input title or content, rather than presenting them as one set of instructions among several.