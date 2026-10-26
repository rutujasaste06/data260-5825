"""HW7 Part 4: small web server for the bike-share agent UI (run: uvicorn server:app --port 8426)."""
import os
import threading
import uuid

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse

import agent

HERE = os.path.dirname(os.path.abspath(__file__))
UPLOADS = os.path.join(HERE, "uploads")
DEFAULT_URL = "https://www.lyft.com/bikes/bay-wheels/pricing"
JOBS = {}

app = FastAPI(title="HW7 bike-share ReAct agent")


@app.get("/")
def index():
    """Serve the single-page UI."""
    return FileResponse(os.path.join(HERE, "static", "index.html"))


def worker(job_id, path, url):
    """Run the agent in a thread and keep its timeline events for polling."""
    job = JOBS[job_id]
    try:
        job["result"] = agent.run(path, url, emit=job["events"].append)
    except Exception as e:  # report a crash in the UI instead of hanging
        job["error"] = f"{e.__class__.__name__}: {e}"
    job["done"] = True


@app.post("/api/run")
async def start_run(csv_file: UploadFile = File(...), url: str = Form(DEFAULT_URL)):
    """Save the uploaded CSV and start a background run."""
    os.makedirs(UPLOADS, exist_ok=True)
    path = os.path.join(UPLOADS, os.path.basename(csv_file.filename or "uploaded.csv"))
    with open(path, "wb") as f:
        f.write(await csv_file.read())
    job_id = uuid.uuid4().hex[:8]
    JOBS[job_id] = {"events": [], "done": False, "result": None, "error": None, "file": csv_file.filename}
    threading.Thread(target=worker, args=(job_id, path, url), daemon=True).start()
    return {"job_id": job_id}


@app.get("/api/job/{job_id}")
def job_status(job_id: str):
    """Timeline so far, plus the result when finished."""
    return JOBS.get(job_id, {"error": "unknown job", "done": True, "events": []})
