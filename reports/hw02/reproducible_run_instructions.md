# Reproducible Run Instructions — HW2

## Prerequisites

- Python 3.11 
- Ollama installed and running, with `qwen3:8b` pulled
- Virtual environment activated with all dependencies installed:
  ```
  python3.11 -m venv venv
  source venv/bin/activate
  pip install langchain langchain-ollama fastapi uvicorn pydantic langgraph requests
  ```

## 1. Start the FastAPI backend

```
cd code/api
uvicorn main:app --reload --port 8425
```

Runs on `http://localhost:8425`. Verified by visiting `http://localhost:8425/docs`.

## 2. Open the frontend

 open the html file directly in any browser. The page connects to the backend automatically via `http://localhost:8425`.

## 3. Run the LangGraph agent (single run)

```
cd code
python agents_demo.py
```

Requires Ollama running in the background. Produces Planner → Reviewer → Finalized Publish Output, along with latency in milliseconds.

## 4. Run the full Part 4 experiment suite (30 + 20 + 20 + 5 = 75 runs)

```
cd code
python run_experiments_hw2.py
```

Note: this takes approximately 45–90 minutes to complete, since each run takes 30–90+ seconds depending on retries. Requires `reports/hw02/cases/schema_input.json` to exist. Results are saved automatically as CSV/JSON files in `reports/hw02/raw/`.

## 5. Run the smoke test / verification script

```
cd code
python verify_hw2.py
```

Requires the FastAPI backend (step 1) to be running. Writes `reports/hw02/verification.json` with pass/fail results for all three checks (FastAPI responds, POST succeeds, LangGraph finishes with 3 tags).

## Configuration values (Section 0)

| Value | Result |
| SID4 | 5825 |
| PORT_BASE | 8425 |
| PREFIX | s5825 |
| SEED | 5825 |
| VERIFY_SEED | 265825 |
| DOMAIN_ID | 1 (Clinical trial listings) |

## Model configuration

- Model: `qwen3:8b`
- Served via: Ollama (local)
- Temperature: 0.7
- All model calls route through `src/model_client.py`'s `complete()` adapter