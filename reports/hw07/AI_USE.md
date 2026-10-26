# AI_USE.md - HW7 (Rutuja Saste, SID4 5825)

**1. What I used an AI assistant for and what I did myself.**
I used AI to understand and implement the hand-written agent loop, the Reflexion wrapper, the framework agent (LangGraph with csv_sql, policy_retriever and calculator).  I tried to implement the prompt-injection fixtures and defenses, the safety-gate code, chose the datasets and scenarios, checked the numbers against the saved data, and decided what to change when a run failed. I also ran Ruff and the pre-commit hook and made the commits.

**2. One AI-produced output that was wrong or unsuitable.**
The first version of the Part 4 agent prompt let the model answer without using the tools properly. In the UI runs the model skipped csv_sql or calculator, invented ride counts and minutes, or used a flat $29 as the membership total. Another run ended with the stop reason `unverified_after_repairs` because the model dropped the months part of a long SQL query and then stalled in the calculator step.

**3. How I detected the problem.**
I compared every answer with a deterministic cost model (`cost_model.compare`) that computes both totals directly from the CSV and the saved pricing page. The UI timeline also showed which tools were called, and the verification gate printed which tool was missing or which total did not match (more than 3% off). The timeline text and the saved `run.json` showed the missing calls.

**4. What I changed and why it works now.**
I replaced the long query with a short one and made csv_sql return `dataset_months` itself, so the model does not have to build that value. I made the prompt use one fixed SQL query and exactly two calculator calls (one per total), and raised the allowed repairs from 2 to 3 with more specific repair messages. After these changes Scenario 2 finished with `final_answer` and the cross-check agreed with the cost model. I also kept the cost-model cross-check and the gate, so a wrong answer is still caught instead of trusted.
