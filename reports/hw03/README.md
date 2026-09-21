# HW3 — Reproducible Run Instructions

Repository: data260-5825
SID4: 5825 | PORT_BASE: 8425 | PREFIX: s5825 | SEED: 5825 | DOMAIN_ID: 1 (Clinical Trial Listings)

## Setup

1. Activate the virtual environment:
source venv/bin/activate

2. Install dependencies:
pip install fastapi uvicorn starlette itsdangerous jinja2 python-multipart requests pyyaml
pip install llama-index llama-index-embeddings-huggingface sentence-transformers faiss-cpu numpy pandas


## Part 1 — Auth System

Run the FastAPI server:
cd code/api
uvicorn main:app --reload --port 8425


Then open `http://127.0.0.1:8425/` in a browser.

Demo credentials:
- `admin` / `password123`
- `researcher1` / `trial2026`
- `coordinator` / `sjsu2026`

Routes:
- `/` — home page
- `/login` — login form
- `/dashboard` — protected route (requires login)
- `/logout` — clears session, redirects home

Session idle timeout: 5 minutes (configurable via "max_age" in `main.py` in "SessionMiddleware").

## Part 2 — Chunking Comparison

Run these from the repo root, in order:

1. Build the corpus (fetches 55 real Type 2 Diabetes trials from the official ClinicalTrials.gov API):
python code/corpus/fetch_corpus.py

   Generates `data/corpus/*.txt`, `reports/hw03/SOURCES.md`, and `reports/hw03/CORPUS_MANIFEST.json`.

2. Sanity-check the corpus and embedding model load correctly:
python code/rag/common.py


3. Tested each chunking technique individually with a sample query:

python code/rag/token_chunking.py
python code/rag/semantic_chunking.py
python code/rag/sentence_window_chunking.py


4. Run the full comparison (all 5 questions from `questions.yaml` x all 3 techniques):

python code/rag/run_comparison.py | tee reports/hw03/RUN_LOG.txt

   Produces `reports/hw03/raw/retrieval_token.csv`, `retrieval_semantic.csv`,
   `retrieval_sentence_window.csv`, `retrieval_all.json`, and `reports/hw03/METRICS.md`.

5. Run the self-check script to verify all deliverables are present:

python code/verify_hw03.py

   Produces `reports/hw03/verification.json`.


6. Recompute METRICS.md purely from saved raw/ data,
   without re-running any embeddings:
   python code/rag/compute_metrics.py
   (This is an optional step)

## File locations

- `code/api/` — FastAPI app (main.py, auth.py, templates/)
- `code/corpus/fetch_corpus.py` — corpus builder
- `code/rag/` — common.py, token_chunking.py, semantic_chunking.py, sentence_window_chunking.py, run_comparison.py
- `code/verify_hw03.py` — self-check script
- `data/corpus/` — 55 clinical trial .txt files
- `reports/hw03/` — questions.yaml, SOURCES.md, CORPUS_MANIFEST.json, METRICS.md, RUN_LOG.txt, AI_USE.md, verification.json, raw/, report.pdf
