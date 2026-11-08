"""HW9 Part 1 - Redis-backed view counter for the primary entity (Trial).

Analogy: Redis is a tally sheet taped to the front desk (fast to mark).
MySQL is the filing cabinet (slow, permanent). Every visit gets a quick tick on the
tally sheet; every 10th visit, the front desk copies the total into the cabinet.
"""
import logging

from sqlalchemy import text

PREFIX = "s5825"
SYNC_EVERY = 10

logger = logging.getLogger("trial_cache")


class TrialCache:
    """Database/cache class: Redis (fast counter) in front of MySQL (permanent copy)."""

    def __init__(self, redis_client, engine):
        self.redis_client = redis_client
        self.engine = engine

    def increment_trial_views(self, trial_id):
        """Count one access to a trial; save the total to MySQL on every 10th access."""
        key = f"{PREFIX}:views:trial:{trial_id}"
        count = self.redis_client.incr(key)

        if count % SYNC_EVERY == 0:
            with self.engine.begin() as conn:
                conn.execute(
                    text("UPDATE trials SET view_count = :count WHERE id = :id"),
                    {"count": count, "id": trial_id},
                )
            logger.info("Synced views to database")

        return count
