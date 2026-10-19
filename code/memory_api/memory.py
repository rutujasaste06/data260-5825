import json
import re
from datetime import datetime, timezone
import numpy as np
import ollama
import config
from mem_db import messages, summaries, episodes

def now():
    return datetime.now(timezone.utc)

def count_tokens(text):
    return max(1, len(text) // 4)  # rough estimate (about 4 characters per token)

def llm(prompt, system=None):
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    r = ollama.chat(model=config.CHAT_MODEL, messages=msgs, think=False)
    return r["message"]["content"].strip(), r

def embed(text):
    return ollama.embeddings(model=config.EMBED_MODEL, prompt=text)["embedding"]

# ---- short-term memory ----
def short_term(user_id, session_id, n):
    rows = list(messages.find({"user_id": user_id, "session_id": session_id})
                .sort("created_at", -1).limit(n))
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

# ---- long-term summaries ----
def latest_summary(user_id, scope, session_id=None):
    q = {"user_id": user_id, "scope": scope}
    if scope == "session":
        q["session_id"] = session_id
    d = summaries.find_one(q, sort=[("created_at", -1)])
    return d["text"] if d else ""

def maybe_summarize(user_id, session_id):
    """Summarization trigger: every M user messages."""
    n_user = messages.count_documents({"user_id": user_id, "session_id": session_id, "role": "user"})
    if n_user == 0 or n_user % config.SUMMARIZE_EVERY_USER_MSGS != 0:
        return False
    recent = short_term(user_id, session_id, config.SUMMARIZE_EVERY_USER_MSGS * 2)
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in recent)
    prev = latest_summary(user_id, "session", session_id)
    text, _ = llm(f"Previous summary:\n{prev}\n\nRecent conversation:\n{convo}\n\n"
                  "Write an updated summary as 3-5 concise bullets.")
    summaries.insert_one({"user_id": user_id, "session_id": session_id,
                          "scope": "session", "text": text, "created_at": now()})
    maybe_lifetime(user_id)
    return True

def maybe_lifetime(user_id):
    """Condense several session summaries into one lifetime summary."""
    sess = list(summaries.find({"user_id": user_id, "scope": "session"}).sort("created_at", -1).limit(6))
    if len(sess) < config.LIFETIME_EVERY_N_SESSION_SUMMARIES:
        return
    joined = "\n---\n".join(s["text"] for s in reversed(sess))
    text, _ = llm(f"Session summaries:\n{joined}\n\nCondense into 3-5 bullets of lasting facts about this user.")
    summaries.insert_one({"user_id": user_id, "session_id": None,
                          "scope": "user", "text": text, "created_at": now()})

# ---- episodic memory ----
def extract_episodes(user_id, session_id, user_msg):
    """Extract up to 3 short facts with an importance score (0..1)."""
    prompt = ("Extract up to 3 short facts worth remembering from this message. "
              'Reply ONLY with JSON: [{"fact": "...", "importance": 0.0-1.0}]. '
              "If nothing is worth remembering reply [].\n\nMessage: " + user_msg)
    raw, _ = llm(prompt)
    m = re.search(r"\[.*\]", raw, re.S)
    try:
        items = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        items = []
    saved = []
    for it in items[:3]:
        fact = str(it.get("fact", "")).strip()
        if not fact:
            continue
        imp = min(1.0, max(0.0, float(it.get("importance", 0.5))))
        doc = {"user_id": user_id, "session_id": session_id, "fact": fact,
               "importance": imp, "embedding": embed(fact), "created_at": now()}
        episodes.insert_one(doc)
        saved.append({"fact": fact, "importance": imp})
    return saved

def retrieve_episodes(user_id, message, k):
    """Top-k episodes by cosine similarity to the current message."""
    docs = list(episodes.find({"user_id": user_id}))
    if not docs:
        return []
    q = np.array(embed(message))
    scored = []
    for d in docs:
        e = np.array(d["embedding"])
        sim = float(np.dot(q, e) / (np.linalg.norm(q) * np.linalg.norm(e) + 1e-9))
        scored.append((sim, d["fact"]))
    scored.sort(reverse=True)
    return [{"fact": f, "similarity": round(s, 3)} for s, f in scored[:k]]

# ---- prompt assembly ----
def build_prompt(session_summary, lifetime_summary, window, message, facts):
    parts = [config.SYSTEM_PRIMER]
    if lifetime_summary:
        parts.append("Lifetime summary:\n" + lifetime_summary)
    if session_summary:
        parts.append("Session summary:\n" + session_summary)
    if facts:
        parts.append("Relevant facts:\n" + "\n".join("- " + f["fact"] for f in facts))
    system = "\n\n".join(parts)
    msgs = [{"role": "system", "content": system}] + window + [{"role": "user", "content": message}]
    return system, msgs