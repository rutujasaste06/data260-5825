"""
HW9 Part 3.5 - stale answers and invalidation.

The cached query: "How many available slots does the trial '<title>' have?"
Its answer depends on one s5825_rel record: trials.available_slots for that trial.

  1. Ask the question      -> miss, answer read from MySQL, saved with data_version 1
  2. Update the record     -> available_slots changes in MySQL (cache not told)
  3. Ask again             -> STALE HIT: the cache still returns the old number
  4. Turn on invalidation  -> the update path now bumps the data-version marker; a hit
                              with an older version is deleted and answered fresh
  5. Ask again             -> fresh answer; ask once more -> normal hit

For this demo the answering function reads the trial row from MySQL. (The HW8 LLM agent has
no database access, so it cannot show an answer that depends on a record.)

Run from the repo root:   python code/hw9/part3_stale.py
"""

import logging
import os
import sys

import redis
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from semantic_cache import VERSION_KEY, SemanticCache  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, "..", "api", ".env"))


def main():
    engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
    client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379)
    try:
        client.ping()
    except redis.exceptions.ConnectionError:
        sys.exit("Redis is not running. Start it with: docker compose up -d redis")

    with engine.begin() as conn:
        trial_id, title, slots = conn.execute(
            text("SELECT id, trial_title, available_slots FROM trials ORDER BY id LIMIT 1")).first()
        conn.execute(text("UPDATE trials SET available_slots = 10 WHERE id = :id"), {"id": trial_id})

    def db_agent(question):
        """Answer from the live database record (stands in for the agent for this demo)."""
        with engine.begin() as conn:
            now = conn.execute(text("SELECT available_slots FROM trials WHERE id = :id"),
                               {"id": trial_id}).scalar()
        return f"The trial '{title}' currently has {now} available slots.", "approved"

    def update_slots(new_value, bump):
        """The write path. With bump=True it also bumps the data-version marker."""
        with engine.begin() as conn:
            conn.execute(text("UPDATE trials SET available_slots = :v WHERE id = :id"),
                         {"v": new_value, "id": trial_id})
        if bump:
            return cache.bump_version()
        return None

    def db_truth():
        with engine.begin() as conn:
            return conn.execute(text("SELECT available_slots FROM trials WHERE id = :id"),
                                {"id": trial_id}).scalar()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("    %(message)s"))
    log = logging.getLogger("semantic_cache")
    log.addHandler(handler)
    log.setLevel(logging.INFO)
    log.propagate = False

    cache = SemanticCache(client, db_agent)
    cache.reset()
    client.set(VERSION_KEY, 1)
    cache.embed("warm up")
    question = f"How many available slots does the trial '{title}' have?"

    def ask(label, check_version):
        print(f"\n--- {label} ---")
        out = cache.handle_query(question, check_version=check_version)
        print(f"    is_cached={out['is_cached']}  answer: {out['answer']}")
        print(f"    (MySQL right now says available_slots = {db_truth()})")

    print("=== Part 3.5 Stale answers and invalidation ===")
    print(f"Cached query: {question}")
    print(f"Depends on: s5825_rel.trials.available_slots for trial id {trial_id} (starts at 10)")

    ask("1. First ask (miss, saved with data_version 1)", check_version=False)

    print("\n--- 2. Someone enrolls patients: available_slots 10 -> 3 (cache is not told) ---")
    update_slots(3, bump=False)

    ask("3. Ask again, no invalidation: STALE HIT", check_version=False)

    print("\n=== Invalidation strategy: data-version marker ===")
    print("The write path now bumps the marker. A hit is trusted only if its saved version "
          "equals the current one.")
    print("\n--- 4. Enrollment again: available_slots 3 -> 2, and the update bumps the marker ---")
    new_version = update_slots(2, bump=True)
    print(f"    data_version marker is now {new_version}")

    ask("5. Ask again, with invalidation: stale entry detected, fresh answer", check_version=True)
    ask("6. Ask once more: normal hit, now with the fresh answer", check_version=True)


if __name__ == "__main__":
    main()
