"""
HW9 Part 2 - the normal HW8 agent path, called as plain functions.

On a cache miss the semantic cache must send the question down the same
Planner -> Writer -> Reviewer path built in HW8 (local qwen3:8b through the
ModelClient adapter). Those three agents normally talk over Kafka; here we
reuse their own functions (make_plan, write_answer, review) so the cache does
not need the broker and three worker processes running just to be tested.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "pipeline")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from planner import make_plan  # noqa: E402
from reviewer import review  # noqa: E402
from writer import write_answer  # noqa: E402


def run_hw8_agent(question):
    """Planner -> Writer -> Reviewer. Returns (final_answer, reviewer_status)."""
    plan = make_plan(question)
    draft = write_answer(question, plan)
    status = review(draft)
    return draft, status
