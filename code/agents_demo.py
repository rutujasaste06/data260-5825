import json
import argparse
import time
from langchain_ollama import ChatOllama

# Sample input — clinical trial domain (used only if run without --input)
sample_title = "Phase II Study of Metformin for Type 2 Diabetes"
sample_content = (
    "This trial evaluates the efficacy and safety of Metformin in managing "
    "blood glucose levels among adult patients diagnosed with Type 2 Diabetes. "
    "Participants will be monitored over a 12-week period, with primary "
    "endpoints focused on HbA1c reduction and secondary endpoints assessing "
    "adverse events and patient-reported outcomes."
)


def planner_agent(title, content):
    prompt = f"""You are a Planner agent. Given a title and content, propose:
1. Exactly 3 topical tags (short phrases) that best describe the content.
2. A summary of AT MOST 25 words. Count your words carefully - do not exceed 25 words under any circumstances. Prioritize a complete, grammatically correct sentence within that limit..

Respond ONLY in valid JSON format like this:
{{"tags": ["tag1", "tag2", "tag3"], "summary": "your summary here"}}

Title: {title}
Content: {content}
"""
    response = llm.invoke(prompt)
    return response.content


def reviewer_agent(title, content, planner_output):
    prompt = f"""You are a Reviewer agent. You will review the Planner's proposed 
tags and summary for accuracy and quality, given the original title and content.

If the tags or summary need improvement, provide corrected versions.
If they are already good, you may keep them the same.
The summary must be AT MOST 25 words - count carefully and do not exceed this limit.

Respond ONLY in valid JSON format like this:
{{"tags": ["tag1", "tag2", "tag3"], "summary": "your summary here"}}

Title: {title}
Content: {content}

Planner's proposal: {planner_output}
"""
    response = llm.invoke(prompt)
    return response.content


def finalizer_agent(reviewer_output):
    try:
        parsed = json.loads(reviewer_output)
    except json.JSONDecodeError:
        parsed = {"tags": [], "summary": ""}

    summary = parsed.get("summary", "")
    words = summary.split()
    if len(words) > 25:
        summary = " ".join(words[:25])

    final_output = {
        "tags": parsed.get("tags", [])[:3],
        "summary": summary
    }
    return final_output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="../reports/hw01/cases/nondeterminism_input.json")
    parser.add_argument("--temp", type=float, default=0.7)
    args = parser.parse_args()

    with open(args.input, "r") as f:
        data = json.load(f)
    title = data["title"]
    content = data["content"]

    llm = ChatOllama(model="qwen3:8b", temperature=args.temp)

    start_time = time.time()

    print("=== Planner Agent ===")
    planner_output = planner_agent(title, content)
    print(planner_output)
    print()

    print("=== Reviewer Agent ===")
    reviewer_output = reviewer_agent(title, content, planner_output)
    print(reviewer_output)
    print()

    print("=== Finalized Publish Output ===")
    final_output = finalizer_agent(reviewer_output)
    print(json.dumps(final_output, indent=2))

    end_time = time.time()
    latency_ms = (end_time - start_time) * 1000

    print(f"\nLatency: {latency_ms:.2f} ms")