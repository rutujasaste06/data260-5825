import time
import random
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

from domain_core import ok, err

log = logging.getLogger("resilience")

MAX_RETRIES = 3          # retries after the first attempt (4 attempts total)
BASE_DELAY = 0.05        # seconds; doubles each retry: 0.05, 0.1, 0.2
TIMEOUT = 2.0            # seconds per attempt


class TransientError(Exception):
    """A temporary failure that is worth retrying."""


def call_with_retry(fn, *args, max_retries=MAX_RETRIES, base_delay=BASE_DELAY,
                    timeout=TIMEOUT, **kwargs):
    """Run fn with a timeout and bounded exponential-backoff retries.
    Always returns an {ok, data, error} envelope and never raises."""
    attempts = 0
    last_error = "unknown error"
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        for attempt in range(max_retries + 1):
            attempts = attempt + 1
            try:
                future = pool.submit(fn, *args, **kwargs)
                result = future.result(timeout=timeout)
                return result, attempts
            except FutureTimeout:
                last_error = f"timed out after {timeout}s"
            except TransientError as e:
                last_error = str(e)
            except Exception as e:
                last_error = f"unexpected error: {e}"
            log.warning("attempt %d failed: %s", attempts, last_error)
            if attempt < max_retries:
                time.sleep(base_delay * (2 ** attempt))
        return err(f"failed after {attempts} attempts: {last_error}"), attempts
    finally:
        pool.shutdown(wait=False)


class FlakyInjector:
    """Seeded failure injector. Same seed gives the same fail/succeed sequence."""

    def __init__(self, rate, seed):
        self.rate = rate
        self.rng = random.Random(seed)

    def wrap(self, fn):
        def inner(*args, **kwargs):
            if self.rng.random() < self.rate:
                raise TransientError("injected failure")
            return fn(*args, **kwargs)
        return inner


class ScriptedInjector:
    """Fails or succeeds in an exact, pre-written order (for the 3 demos)."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)   # e.g. [False, True] = fail then succeed
        self.i = 0

    def wrap(self, fn):
        def inner(*args, **kwargs):
            should_fail = self.outcomes[min(self.i, len(self.outcomes) - 1)]
            self.i += 1
            if should_fail:
                raise TransientError("injected failure")
            return fn(*args, **kwargs)
        return inner