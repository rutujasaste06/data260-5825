"""HW9 Part 1 demo: 25 accesses to one trial, counted in Redis, saved to MySQL every 10th."""
import logging
import os

import redis
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text

from trial_views import PREFIX, TrialCache

HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, "..", "api", ".env"))


class LogCollector(logging.Handler):
    """Holds log messages so the demo can print them right after the 'Access' line."""

    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def prepare_database(engine):
    """Make sure trials has a view_count column and pick the trial to test."""
    with engine.begin() as conn:
        columns = [c["name"] for c in inspect(conn).get_columns("trials")]
        if "view_count" not in columns:
            conn.execute(text("ALTER TABLE trials ADD COLUMN view_count INT NOT NULL DEFAULT 0"))
            print("[setup] added column trials.view_count")
        row = conn.execute(text("SELECT id, trial_title FROM trials ORDER BY id LIMIT 1")).first()
        if row is None:
            conn.execute(text(
                "INSERT INTO trials (trial_title, nct_number, available_slots) "
                "VALUES ('HW9 View Counter Demo Trial', 'NCT00009001', 10)"))
            row = conn.execute(text("SELECT id, trial_title FROM trials ORDER BY id LIMIT 1")).first()
        conn.execute(text("UPDATE trials SET view_count = 0 WHERE id = :id"), {"id": row[0]})
    return row[0], row[1]


def main():
    engine = create_engine(os.getenv("DATABASE_URL"), pool_pre_ping=True)
    redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "localhost"), port=6379,
                               decode_responses=True)
    try:
        redis_client.ping()
    except redis.exceptions.ConnectionError:
        raise SystemExit("Redis is not running. Start it with: docker compose up -d redis")

    trial_id, title = prepare_database(engine)
    key = f"{PREFIX}:views:trial:{trial_id}"
    redis_client.delete(key)  # start every demo from zero

    collector = LogCollector()
    logging.getLogger("trial_cache").addHandler(collector)
    logging.getLogger("trial_cache").setLevel(logging.INFO)

    cache = TrialCache(redis_client, engine)
    print("=== Testing Counter ===")
    print(f"Trial id {trial_id}: {title}   (Redis key: {key})\n")

    for n in range(1, 26):
        total = cache.increment_trial_views(trial_id)
        print(f"Access #{n}: Total = {total}")
        for message in collector.messages:
            print(f"✓ {message}")
        collector.messages.clear()

    with engine.connect() as conn:
        saved = conn.execute(text("SELECT view_count FROM trials WHERE id = :id"),
                             {"id": trial_id}).scalar()
    print(f"\nRedis counter now: {redis_client.get(key)}")
    print(f"MySQL trials.view_count now: {saved}  (saved at the last 10th access)")


if __name__ == "__main__":
    main()
