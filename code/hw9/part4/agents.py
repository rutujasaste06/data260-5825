"""
HW9 Part 4 - Answering Agent, Evaluator Agent, lesson store and the revise-once workflow.

Analogy: a student (Answering Agent) answers from an old copy of the class notes
(listing_snapshot.json). A teacher (Evaluator Agent) marks the answer against the
answer key (reference_data.json = the current, correct listing data). If the answer
is wrong, the teacher says what is wrong and the student gets ONE more try. Mistakes
that were fixed become "lessons" the student reads before answering similar questions.
"""

import json
import os
import re
import sys
import time
from datetime import date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "src")))

from langchain_ollama import ChatOllama  # noqa: E402
from model_client import ModelClient  # noqa: E402

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
SEED = 5825
FIELD_LABELS = {
    "available_slots": "available slots", "status": "status", "phase": "phase",
    "sponsor": "sponsor", "nct_number": "NCT number",
}
DECLINE_MARKERS = [
    "no information", "not listed", "not in the", "cannot find", "can't find", "don't have",
    "do not have", "unable to", "no record", "not found", "not able to", "isn't listed",
]


def load_json(name):
    with open(os.path.join(DATA_DIR, name)) as f:
        return json.load(f)


def save_json(name, obj):
    with open(os.path.join(DATA_DIR, name), "w") as f:
        json.dump(obj, f, indent=2)


def make_model():
    """Local qwen3:8b through the ModelClient adapter, fixed seed and temperature 0."""
    client = ModelClient(temperature=0.0)
    client.llm = ChatOllama(model=client.model, temperature=0.0, seed=SEED)
    return client


def strip_think(text):
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()


# ---------------------------------------------------------------- Answering Agent
class AnsweringAgent:
    def __init__(self, snapshot, client=None):
        self.snapshot = snapshot
        self.client = client or make_model()

    def listing_text(self):
        return "\n".join(
            f"- {t['title']} | NCT {t['nct_number']} | {t['phase']} | available slots: "
            f"{t['available_slots']} | sponsor: {t['sponsor']} | status: {t['status']}"
            for t in self.snapshot
        )

    def answer(self, question, lessons=None, previous_answer=None, feedback=None):
        system = (
            "You are the Answering Agent for a clinical trial listings service. Answer using ONLY "
            "the listing snapshot below. If the trial is not in the snapshot, say you have no "
            "information about that trial. Reply in one short sentence.\n\n"
            f"Listing snapshot:\n{self.listing_text()}"
        )
        if lessons:
            system += ("\n\nLessons from earlier mistakes. They are more recent than the listing "
                       "snapshot, so they override it:\n" + "\n".join(
                           f"- {lesson['correction']}" for lesson in lessons))
        if previous_answer:
            # Revision: the Evaluator checked the last answer against current records. Its feedback
            # is newer than the snapshot, so it overrides it. (The wrong answer is not repeated back,
            # because the model tends to anchor on it.)
            system += ("\n\nYour previous answer was marked wrong by the Evaluator, which checked "
                       "the current records. Its correction overrides the listing snapshot:\n"
                       f"{feedback}")
        user = question + " /no_think"
        reply = self.client.complete([{"role": "system", "content": system},
                                      {"role": "user", "content": user}])
        return strip_think(reply)


# ---------------------------------------------------------------- Evaluator Agent
class Evaluator:
    """Checks an answer against the reference dataset (ground truth). Returns PASS or REVISE."""

    def __init__(self, reference):
        self.trials = reference

    def find_trial(self, question):
        q = question.lower()
        for t in self.trials:
            if t["title"].lower() in q or t["nct_number"].lower() in q:
                return t
        return None

    @staticmethod
    def field_of(question):
        q = question.lower()
        for word, field in (("nct", "nct_number"), ("sponsor", "sponsor"), ("phase", "phase"),
                            ("status", "status"), ("slots", "available_slots")):
            if word in q:
                return field
        return None

    @staticmethod
    def matches(field, expected, answer):
        text = answer.lower()
        if field == "available_slots":
            numbers = set(re.findall(r"\d+", re.sub(r"nct\d+", "", text)))
            return numbers == {str(expected)}
        if field == "phase":
            found = set(re.findall(r"phase\s+(iv|iii|ii|i)\b", text))
            return found == {expected.lower().replace("phase ", "")}
        if field == "status":
            if expected == "Closed":
                return "closed" in text
            return "recruiting" in text and not any(
                w in text for w in ("closed", "not recruiting", "no longer recruiting"))
        return expected.lower() in text

    def evaluate(self, question, answer):
        trial = self.find_trial(question)
        if trial is None:
            if any(m in answer.lower() for m in DECLINE_MARKERS):
                return {"result": "PASS", "trial": None, "field": None, "expected": None,
                        "explanation": "The trial is not in the reference dataset and the answer correctly says so.",
                        "feedback": ""}
            return {"result": "REVISE", "trial": None, "field": None, "expected": None,
                    "explanation": "The trial is not in the reference dataset, but the answer gives a value anyway.",
                    "feedback": "That trial is not in the listings. Say you have no information about it "
                                "instead of giving a value."}
        field = self.field_of(question)
        expected = trial[field]
        label = FIELD_LABELS[field]
        base = {"trial": trial["title"], "nct": trial["nct_number"], "field": field, "expected": expected}
        if self.matches(field, expected, answer):
            return {**base, "result": "PASS", "feedback": "",
                    "explanation": f"The {label} matches the reference dataset ({expected})."}
        return {**base, "result": "REVISE",
                "explanation": f"The {label} in the answer does not match the reference dataset.",
                "feedback": f"The correct {label} of the {trial['title']} is {expected}. "
                            f"The listing snapshot is outdated for this value. Answer with {expected}."}


# ---------------------------------------------------------------- Lessons
class LessonStore:
    def __init__(self, filename="lessons.json", persist=True):
        self.filename = filename
        self.persist = persist
        path = os.path.join(DATA_DIR, filename)
        self.lessons = load_json(filename) if os.path.exists(path) else []

    def save(self):
        if self.persist:
            save_json(self.filename, self.lessons)

    def relevant(self, question, trials):
        """Lessons about a trial named in the question, plus general lessons (no trial named)."""
        q = question.lower()
        mentioned = {t["title"] for t in trials if t["title"].lower() in q or t["nct_number"].lower() in q}
        chosen = []
        for lesson in self.lessons:
            text = (lesson["failure_pattern"] + " " + lesson["correction"]).lower()
            named = {t["title"] for t in trials if t["title"].lower() in text}
            if not named or named & mentioned:
                chosen.append(lesson)
        return chosen

    def mark_used(self, lessons):
        for lesson in lessons:
            lesson["use_count"] += 1
        self.save()

    def add(self, failure_pattern, correction):
        lesson = {
            "lesson_id": f"lesson_{len(self.lessons) + 1:03d}",
            "failure_pattern": failure_pattern,
            "correction": correction,
            "created_at": date.today().isoformat(),
            "use_count": 0,
        }
        self.lessons.append(lesson)
        self.save()
        return lesson


def lesson_from_failure(store, evaluation):
    """A fixed failure becomes a lesson built from the evaluator's finding."""
    label = FIELD_LABELS[evaluation["field"]]
    return store.add(
        f"The listing snapshot's {label} for the {evaluation['trial']} is outdated, so the first answer was wrong.",
        f"The current {label} of the {evaluation['trial']} ({evaluation['nct']}) is "
        f"{evaluation['expected']}. Use this value, not the listing snapshot's value.",
    )


# ---------------------------------------------------------------- Workflow (4.1)
def run_workflow(question, answerer, evaluator, store=None, max_attempts=2, forced_first=None):
    """Answer -> evaluate -> (if REVISE and attempts left) revise -> evaluate. Max two attempts."""
    t0 = time.perf_counter()
    lessons = store.relevant(question, evaluator.trials) if store else []
    if lessons:
        store.mark_used(lessons)
    attempts = []
    previous = feedback = None
    for number in range(1, max_attempts + 1):
        if number == 1 and forced_first is not None:
            answer = forced_first
        else:
            answer = answerer.answer(question, lessons, previous, feedback)
        verdict = evaluator.evaluate(question, answer)
        attempts.append({"attempt": number, "answer": answer, **verdict})
        if verdict["result"] == "PASS":
            break
        previous, feedback = answer, verdict["feedback"]
    return {
        "question": question,
        "attempts": attempts,
        "final_answer": attempts[-1]["answer"],
        "final_result": attempts[-1]["result"],
        "n_attempts": len(attempts),
        "lessons_used": [lesson["lesson_id"] for lesson in lessons],
        "latency_s": time.perf_counter() - t0,
    }
