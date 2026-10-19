import time
import uuid
from typing import Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import ollama
import config
import memory
from mem_db import messages, summaries, episodes

app = FastAPI(title="Memory Chat API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatIn(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    message: str

@app.post("/api/chat")
def chat(body: ChatIn):
    t0 = time.perf_counter()
    sid = body.session_id or str(uuid.uuid4())
    messages.insert_one({"user_id": body.user_id, "session_id": sid, "role": "user",
                         "content": body.message, "created_at": memory.now()})
    window = memory.short_term(body.user_id, sid, config.SHORT_TERM_N + 1)[:-1]
    sess = memory.latest_summary(body.user_id, "session", sid)
    life = memory.latest_summary(body.user_id, "user")
    facts = memory.retrieve_episodes(body.user_id, body.message, config.TOP_K_EPISODES)
    system, msgs = memory.build_prompt(sess, life, window, body.message, facts)

    resp = ollama.chat(model=config.CHAT_MODEL, messages=msgs, think=False)
    reply = resp["message"]["content"].strip()
    messages.insert_one({"user_id": body.user_id, "session_id": sid, "role": "assistant",
                         "content": reply, "created_at": memory.now()})

    memory.extract_episodes(body.user_id, sid, body.message)
    summarized = memory.maybe_summarize(body.user_id, sid)
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    return {
        "session_id": sid, "reply": reply,
        "memory_used": {
            "short_term_count": len(window), "short_term": window,
            "session_summary": sess, "lifetime_summary": life,
            "episodic_facts": facts,
        },
        "summary_updated": summarized,
        "metrics": {
            "prompt_tokens": resp.get("prompt_eval_count"),
            "completion_tokens": resp.get("eval_count"),
            "system_tokens_est": memory.count_tokens(config.SYSTEM_PRIMER),
            "long_term_tokens_est": memory.count_tokens(sess + life),
            "short_term_tokens_est": sum(memory.count_tokens(m["content"]) for m in window),
            "episodic_tokens_est": sum(memory.count_tokens(f["fact"]) for f in facts),
            "latency_ms": latency_ms,
        },
    }

def clean(d):
    d["id"] = str(d.pop("_id"))
    d.pop("embedding", None)
    return d

@app.get("/api/memory/{user_id}")
def get_memory(user_id: str):
    msgs = [clean(d) for d in messages.find({"user_id": user_id}).sort("created_at", -1).limit(16)]
    sess = summaries.find_one({"user_id": user_id, "scope": "session"}, sort=[("created_at", -1)])
    life = summaries.find_one({"user_id": user_id, "scope": "user"}, sort=[("created_at", -1)])
    eps = [clean(d) for d in episodes.find({"user_id": user_id}).sort("created_at", -1).limit(20)]
    return {"messages": list(reversed(msgs)),
            "latest_session_summary": clean(sess) if sess else None,
            "latest_lifetime_summary": clean(life) if life else None,
            "episodes": eps}

@app.get("/api/aggregate/{user_id}")
def aggregate(user_id: str):
    daily = list(messages.aggregate([
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}]))
    recent = [clean(d) for d in summaries.find({"user_id": user_id}).sort("created_at", -1).limit(5)]
    return {"daily_message_counts": [{"date": d["_id"], "count": d["count"]} for d in daily],
            "recent_summaries": recent}