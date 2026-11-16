"""
HW10 Part 2 - the LLM judge (DeepEval GEval with a local Ollama model).

Judge model : qwen3:8b through Ollama (local, same model family as the agents)
Settings    : temperature 0, seed 5825, thinking off (reasoning=False), JSON output, max 512 output tokens,
              120 s per model call and 300 s per score (a slow or missing judge cannot hang the run)
Scale       : GEval returns 0-1 (the judge writes 0-10, DeepEval divides by 10).
              It is mapped to the same 1-5 scale as the human labels:  1 + 4 * score, rounded.
              1 = very poor ... 5 = excellent.
"""

import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

from deepeval.metrics import GEval  # noqa: E402
from deepeval.models import DeepEvalBaseLLM  # noqa: E402
from deepeval.test_case import LLMTestCase  # noqa: E402

try:
    from deepeval.test_case import SingleTurnParams as Params  # noqa: E402
except ImportError:  # older DeepEval
    from deepeval.test_case import LLMTestCaseParams as Params  # noqa: E402

JUDGE_MODEL = "qwen3:8b"
TEMPERATURE = 0.0
SEED = 5825
CALL_TIMEOUT_S = 120
MAX_TOKENS = 512       # a judge answer is a short JSON; this stops a runaway generation blocking the model
SCORE_TIMEOUT_S = 300
SETTINGS = {"model": JUDGE_MODEL, "temperature": TEMPERATURE, "seed": SEED, "thinking": "off (reasoning=False)",
            "output": "JSON", "max_output_tokens": MAX_TOKENS, "call_timeout_s": CALL_TIMEOUT_S, "score_timeout_s": SCORE_TIMEOUT_S,
            "scale": "GEval 0-1 mapped to 1-5 (1 + 4*score, rounded)"}


def _first_json(text):
    start, end = text.find("{"), text.rfind("}")
    return text[start:end + 1] if start != -1 and end > start else text


class OllamaJudge(DeepEvalBaseLLM):
    def __init__(self):
        from langchain_ollama import ChatOllama

        self.llm = ChatOllama(model=JUDGE_MODEL, temperature=TEMPERATURE, seed=SEED, format="json",
                              num_predict=MAX_TOKENS, reasoning=False, client_kwargs={"timeout": CALL_TIMEOUT_S})
        super().__init__(model=f"ollama/{JUDGE_MODEL}")

    def load_model(self):
        return self.llm

    def generate(self, prompt, schema=None, *args, **kwargs):
        reply = self.llm.invoke(prompt + "\n/no_think").content
        text = re.sub(r"<think>.*?</think>", "", reply, flags=re.S).strip()
        if schema is None:
            return text
        return schema(**json.loads(_first_json(text)))

    async def a_generate(self, prompt, schema=None, *args, **kwargs):
        return self.generate(prompt, schema)

    def get_model_name(self):
        return f"ollama/{JUDGE_MODEL}"


# One criterion = a short list of steps the judge follows. Same 1-5 meaning for all three.
CRITERIA = {
    "plan_quality": [
        "Read the question and the plan (the plan is the 'actual output').",
        "Check that the plan is relevant to the question and covers what a good answer needs.",
        "Check that the steps are specific and actionable, not vague or generic.",
        "Check that following the plan would lead to a correct, complete answer.",
    ],
    "helpfulness": [
        "Read the question and the answer (the answer is the 'actual output').",
        "Check that the answer directly addresses what the question asks.",
        "Check that it is accurate and does not invent specific facts (for example slot counts, "
        "sponsors, NCT numbers or trial status) that it could not know.",
        "Check that it is clear, complete and appropriately short.",
        "An answer that ignores the question, refuses without reason or invents details is poor.",
    ],
}

_judge = None


def _get_judge():
    global _judge
    if _judge is None:
        _judge = OllamaJudge()
    return _judge


def to_five(raw):
    return max(1, min(5, int(round(1 + 4 * raw))))


def _measure(criterion, question, output):
    metric = GEval(
        name=criterion,
        evaluation_steps=CRITERIA[criterion],
        evaluation_params=[Params.INPUT, Params.ACTUAL_OUTPUT],
        model=_get_judge(),
        async_mode=False,
        verbose_mode=False,
    )
    metric.measure(LLMTestCase(input=question, actual_output=output))
    return float(metric.score), metric.reason


def run_judge(criterion, question, output):
    """Score one text. Never raises and never hangs: a failure comes back as score=None + error."""
    result = {"criterion": criterion, "score": None, "raw": None, "reason": None, "error": None,
              "seconds": None}
    t0 = time.time()
    if not output or not str(output).strip():
        result["error"] = "empty or malformed text"
        return result
    pool = ThreadPoolExecutor(max_workers=1)
    future = pool.submit(_measure, criterion, question, str(output))
    try:
        raw, reason = future.result(timeout=SCORE_TIMEOUT_S)
        result.update(raw=raw, reason=reason, score=to_five(raw))
    except FutureTimeout:
        result["error"] = f"judge timed out after {SCORE_TIMEOUT_S}s"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    result["seconds"] = round(time.time() - t0, 2)
    return result
