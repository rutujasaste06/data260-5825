import ollama
import file_memory as fm

HELP = """Commands:
/memory   show AGENT.md and MEMORY.md
/compact  consolidate MEMORY.md and shrink the chat (prints counts before/after)
/dream    save useful long-term facts from the recent chat into MEMORY.md
/help     show this help
/quit     exit"""


def main():
    history = []
    print("File-memory chat - Rutuja Saste. Type /help for commands.")
    need, why = fm.needs_consolidation()
    print(f"[memory check] consolidation needed: {need} ({why})")
    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user:
            continue
        if user == "/quit":
            break
        if user == "/help":
            print(HELP)
            continue
        if user == "/memory":
            print(fm.show_memory())
            continue
        if user == "/compact":
            mb, ma, lb, la = fm.compact(history)
            print(f"[compact] chat messages: {mb} -> {ma} | MEMORY.md lines: {lb} -> {la}")
            continue
        if user == "/dream":
            added = fm.dream(history)
            print("[dream] added:" if added else "[dream] nothing new to add")
            for a in added:
                print("  " + a)
            continue
        need, why = fm.needs_consolidation()
        if need:
            lb, la = fm.consolidate()
            print(f"[auto-consolidate] {why}: {lb} -> {la} lines")
        history.append({"role": "user", "content": user})
        msgs = [{"role": "system", "content": fm.build_system_prompt()}] + history
        reply = ollama.chat(model=fm.MODEL, messages=msgs, think=False)["message"]["content"]
        history.append({"role": "assistant", "content": reply})
        print("bot>", reply)


if __name__ == "__main__":
    main()