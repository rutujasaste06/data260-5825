import os, re, datetime as dt
import ollama

HERE = os.path.dirname(os.path.abspath(__file__))
AGENT_PATH = os.path.join(HERE, "..", "..", "AGENT.md")
MEMORY_PATH = os.path.join(HERE, "MEMORY.md")
MODEL = "qwen3:8b"
MAX_LINES = 40
MAX_AGE_HOURS = 24
STAMP_RE = re.compile(r"<!--\s*last_consolidated:\s*(\S+?)\s*-->")

CONSOLIDATE_PROMPT = """You are cleaning a memory file called MEMORY.md.
Rewrite it with FEWER THAN 35 lines in total. Rules:
1. Merge duplicate or near-duplicate facts into one line.
2. If two facts contradict each other, keep the one with the LATER date. Do NOT
   silently drop the other: add a line under the heading '## Resolved contradictions'
   in this form: '- KEPT: <fact> (date) | REPLACED: <old fact> (date) | WHY: later date'.
3. Every line is a short bullet starting with '- '. Keep the dates in parentheses.
4. Do not invent new facts. Output ONLY the new file content, no explanations."""


# ---------- loading ----------
def read_file(path):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()
    return ""


def write_file(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def load_memory_files():
    return read_file(AGENT_PATH), read_file(MEMORY_PATH)


def build_system_prompt():
    agent, memory = load_memory_files()
    return ("You are a helpful assistant for a clinical trial listings project.\n\n"
            "## AGENT.md (standing instructions)\n" + agent +
            "\n\n## MEMORY.md (facts learned earlier)\n" + memory)


def show_memory():
    agent, memory = load_memory_files()
    return "=== AGENT.md ===\n" + agent + "\n=== MEMORY.md ===\n" + memory


# ---------- consolidation checks ----------
def count_memory_lines(text):
    """Non-empty lines that are not <!-- comments -->."""
    return sum(1 for ln in text.splitlines()
               if ln.strip() and not ln.strip().startswith("<!--"))


def read_last_consolidated(text=None):
    text = read_file(MEMORY_PATH) if text is None else text
    m = STAMP_RE.search(text)
    if not m:
        return None
    try:
        t = dt.datetime.fromisoformat(m.group(1))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)


def set_last_consolidated(text, when=None):
    stamp = f"<!-- last_consolidated: {(when or now_utc()).isoformat()} -->"
    if STAMP_RE.search(text):
        return STAMP_RE.sub(lambda m: stamp, text, count=1)
    return stamp + "\n" + text


def needs_consolidation():
    text = read_file(MEMORY_PATH)
    n = count_memory_lines(text)
    if n == 0:
        return False, "MEMORY.md is empty"
    if n > MAX_LINES:
        return True, f"{n} lines > {MAX_LINES}"
    last = read_last_consolidated(text)
    if last is None:
        return True, "no consolidation time recorded"
    age = (now_utc() - last).total_seconds() / 3600
    if age > MAX_AGE_HOURS:
        return True, f"last consolidated {age:.1f} h ago (> {MAX_AGE_HOURS} h)"
    return False, f"{n} lines, last consolidated {age:.1f} h ago"


# ---------- model helper ----------
def llm(prompt):
    client = ollama.Client(timeout=180)
    out = client.chat(model=MODEL, think=False,
                      messages=[{"role": "user", "content": prompt}],
                      options={"temperature": 0.2, "seed": 5825,
                               "num_predict": 1200, "repeat_penalty": 1.1})["message"]["content"]
    out = re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip()
    out = re.sub(r"^```[a-z]*\n|\n```$", "", out).strip()
    return out


# ---------- commands ----------
def _norm(line: str) -> str:
    """Return a lowercase letters-and-digits version of a line for duplicate checks."""
    return "".join(ch for ch in line.lower() if ch.isalnum())


def remove_exact_duplicates(text: str):
    """Drop repeated lines (keep the first one) and return the new text plus the removed lines."""
    seen, kept, removed = set(), [], []
    for line in text.splitlines():
        key = _norm(line)
        if line.strip() and not line.strip().startswith("<!--") and key in seen:
            removed.append(line)
            continue
        seen.add(key)
        kept.append(line)
    return "\n".join(kept), removed


def _date_of(line: str) -> str:
    """Return the (YYYY-MM-DD) date at the start of a memory line, or empty text."""
    import re
    m = re.match(r"- \((\d{4}-\d{2}-\d{2})\)", line)
    return m.group(1) if m else ""


def _cos(a: list, b: list) -> float:
    """Return the cosine similarity of two vectors."""
    import math
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def _verdict(a: str, b: str) -> str:
    """Ask the model if two memory lines are SAME, CONFLICT or DIFFERENT."""
    prompt = (
        "Compare two memory lines. Answer with ONE word:\n"
        "SAME = they state the same fact in different words.\n"
        "CONFLICT = they answer the same question but give different values.\n"
        "DIFFERENT = they are about different things. Things that only sound alike "
        "stay DIFFERENT (for example 'API port' and 'memory API port').\n\n"
        f"A: {a}\nB: {b}\nAnswer:")
    word = llm(prompt).upper()
    for v in ("SAME", "CONFLICT", "DIFFERENT"):
        if v in word:
            return v
    return "DIFFERENT"


def _plan(items: list):
    """Find groups of lines: embeddings pick candidate pairs, the model judges each pair."""
    texts = [re.sub(r"^- (\(\d{4}-\d{2}-\d{2}\) )?", "", t) for t in items]
    vecs = ollama.Client(timeout=180).embed(model="nomic-embed-text", input=texts)["embeddings"]
    parent = list(range(len(items)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    conflict = set()
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if _cos(vecs[i], vecs[j]) < 0.72:
                continue
            v = _verdict(texts[i], texts[j])
            if v != "DIFFERENT":
                parent[find(i)] = find(j)
                if v == "CONFLICT":
                    conflict.update((i, j))
    members = {}
    for i in range(len(items)):
        members.setdefault(find(i), []).append(i)
    return [(idx, "contradiction" if conflict & set(idx) else "duplicate")
            for idx in members.values() if len(idx) > 1]

def consolidate():
    """Merge duplicates, resolve contradictions (newest date wins), save only if under MAX_LINES."""
    old = read_file(MEMORY_PATH)
    before = count_memory_lines(old)
    items = [l for l in old.splitlines() if l.strip() and not l.strip().startswith("<!--")]
    groups = []
    for _ in range(3):
        try:
            groups = _plan(items)
            break
        except Exception:
            groups = []
    drop, notes, dup_log, n_dup = set(), [], [], 0
    for idx, kind in groups:
        keep = max(idx, key=lambda i: (_date_of(items[i]), i))
        others = [i for i in idx if i != keep]
        drop.update(others)
        if kind == "contradiction":
            replaced = "; ".join(items[i].lstrip("- ") for i in others)
            notes.append(f"- KEPT: {items[keep].lstrip('- ')} | REPLACED: {replaced} | WHY: later date")
        else:
            n_dup += len(others)
            dup_log += [f"line {i + 1} merged into line {keep + 1}: {items[i]}" for i in others]
    result = [t for i, t in enumerate(items) if i not in drop]
    if n_dup:
        result.append(f"- Merged {n_dup} duplicate lines (details in dedupe_log.txt)")
    if notes:
        result += ["## Resolved contradictions"] + notes
    if dup_log:
        write_file(os.path.join(HERE, "dedupe_log.txt"), "\n".join(dup_log) + "\n")
    new = "\n".join(result)
    if count_memory_lines(new) >= MAX_LINES:
        return before, before
    new = set_last_consolidated(new)
    write_file(MEMORY_PATH, new + "\n")
    return before, count_memory_lines(new)


def _convo(history, last=10):
    return "\n".join(f"{m['role']}: {m['content']}" for m in history[-last:])


def compact(history):
    """Consolidate MEMORY.md and shrink the chat history to one summary message."""
    msgs_before = len(history)
    lines_before, lines_after = consolidate()
    if history:
        summary = llm("Summarize this chat in 3 short bullets:\n" + _convo(history, 50))
        history[:] = [{"role": "assistant", "content": "Summary of earlier chat:\n" + summary}]
    return msgs_before, len(history), lines_before, lines_after


def dream(history):
    """Pick durable long-term facts from the recent chat and append them to MEMORY.md."""
    if not history:
        return []
    out = llm("From this conversation list up to 5 durable long-term facts about the "
              "user or project (names, preferences, deadlines, decisions). Skip small "
              "talk. One per line, each starting with '- '. If none, reply NONE.\n\n"
              + _convo(history))
    existing = read_file(MEMORY_PATH)
    today = now_utc().date().isoformat()
    added = []
    for ln in out.splitlines():
        ln = ln.strip()
        if ln.startswith("- ") and ln[2:].lower() not in existing.lower():
            added.append(f"- ({today}) {ln[2:]}")
    if added:
        write_file(MEMORY_PATH, existing.rstrip("\n") + "\n" + "\n".join(added) + "\n")
    return added