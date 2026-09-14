import json
import argparse
import time
import sys
sys.path.append("../src")
from pydantic import BaseModel, field_validator, ValidationError
from typing import List
from model_client import ModelClient
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END


# -- Step 2: AgentState (shared memory for all agents) 

class AgentState(TypedDict):
    title: str
    content: str
    planner_proposal: Dict[str, Any]
    reviewer_feedback: Dict[str, Any]
    turn_count: int
    max_turns: int
    #force_issue: bool  # used for testing the correction loop


client = ModelClient()

class PlannerOutput(BaseModel):
    tags: List[str]
    summary: str

    @field_validator("tags")
    @classmethod
    def check_tags(cls, v):
        if len(v) != 3:
            raise ValueError(f"Expected exactly 3 tags, got {len(v)}")
        for tag in v:
            if not (3 <= len(tag) <= 30):
                raise ValueError(f"Tag '{tag}' must be 3-30 characters (got {len(tag)})")
        return v

    @field_validator("summary")
    @classmethod
    def check_summary(cls, v):
        word_count = len(v.split())
        if word_count > 25:
            raise ValueError(f"Summary has {word_count} words, must be at most 25")
        return v

    
def _call_model(prompt: str) -> str:
    """All model calls go through src/model_client.py, per HW2 Part 3 requirement."""
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]
    return client.complete(messages)


def _parse_json(text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to salvage JSON if the model wrapped it in extra text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        return {"tags": [], "summary": ""}


# --Step 3: Agent nodes

def planner_node(state: AgentState) -> Dict[str, Any]:
    print("--- NODE: Planner ---")

    correction_note = ""
    feedback = state.get("reviewer_feedback", {})
    if feedback.get("has_issues"):
        correction_note = f"\n\nYour previous attempt failed validation for this reason: {feedback.get('reason')}. Fix this specific problem."
    if correction_note:
        print(f"(RETRYING WITH CORRECTION: {correction_note.strip()})")

    prompt = f"""You are a Planner agent. Given a title and content, propose:
1. Exactly 3 topical tags (short phrases, each 3-30 characters) that best describe the content.
2. A summary of AT MOST 25 words. Count your words carefully - do not exceed 25 words under any circumstances.

Respond ONLY in valid JSON format like this:
{{"tags": ["tag1", "tag2", "tag3"], "summary": "your summary here"}}

Title: {state['title']}
Content: {state['content']}{correction_note}
"""
    raw = _call_model(prompt)
    proposal = _parse_json(raw)
    print(json.dumps(proposal, indent=2))
    return {"planner_proposal": proposal, "reviewer_feedback": {}}


def reviewer_node(state: AgentState) -> Dict[str, Any]:
    print("--- NODE: Reviewer ---")
    proposal = state.get("planner_proposal", {})

    try:
        validated = PlannerOutput(**proposal)
        print(f"(VALID: {validated.model_dump()})")
        return {"reviewer_feedback": {"has_issues": False, "tags": validated.tags, "summary": validated.summary}}
    except ValidationError as e:
        reason = "; ".join(err["msg"] for err in e.errors())
        print(f"(VALIDATION FAILED: {reason})")
        return {"reviewer_feedback": {"has_issues": True, "reason": reason}}

# -- Step 4:Building Supervisor 

def supervisor_node(state: AgentState) -> Dict[str, Any]:
    print(f"--- NODE: Supervisor (turn {state['turn_count'] + 1}) ---")
    return {"turn_count": state["turn_count"] + 1}


def router_logic(state: AgentState) -> str:
    # No proposal yet -> go to Planner
    if not state.get("planner_proposal"):
        return "planner"

    # Have a proposal but no review yet -> go to Reviewer
    if not state.get("reviewer_feedback"):
        return "reviewer"

    # Reviewer found issues and we still have turns left -> back to Planner
    if state["reviewer_feedback"].get("has_issues") and state["turn_count"] < state["max_turns"]:
        return "planner"

    # Otherwise, we're done
    return END


# ---------- Step 5: Assembling the graph ----------
def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("planner", planner_node)
    graph.add_node("reviewer", reviewer_node)

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges("supervisor", router_logic, {
        "planner": "planner",
        "reviewer": "reviewer",
        END: END,
    })
    graph.add_edge("planner", "supervisor")
    graph.add_edge("reviewer", "supervisor")

    return graph.compile()


# ---------- Step 6: Running and testing ----------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="../reports/hw01/cases/nondeterminism_input.json")
    parser.add_argument("--max-turns", type=int, default=4)
   # parser.add_argument("--force-issue", action="store_true",
   #                      help="Force the Reviewer to report an issue once, to demonstrate the loop-back.")
    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = json.load(f)

    initial_state: AgentState = {
        "title": data["title"],
        "content": data["content"],
        "planner_proposal": {},
        "reviewer_feedback": {},
        "turn_count": 0,
        "max_turns": args.max_turns,
    #    "force_issue": args.force_issue,
    }

    app = build_graph()

    start_time = time.time()
    final_values = dict(initial_state)
    for step in app.stream(initial_state):
        for node_name, node_output in step.items():
            final_values.update(node_output)

    end_time = time.time()
    latency_ms = (end_time - start_time) * 1000

    print("\n=== Finalized Publish Output ===")
    final_output = {
        "tags": final_values.get("planner_proposal", {}).get("tags", [])[:3],
        "summary": final_values.get("planner_proposal", {}).get("summary", ""),
    }
    print(json.dumps(final_output, indent=2))
    print(f"\nLatency: {latency_ms:.2f} ms")