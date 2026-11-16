"""HW10 Part 1.2 - Evaluation page."""

import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import data  # noqa: E402
import judge_stats  # noqa: E402

st.set_page_config(page_title="Ops dashboard - Evaluation", layout="wide")
st.title("Evaluation")

# ---------------------------------------------------------------- Part 2
st.header("Pipeline evaluation (Part 2)")
latest = {}
for row in data.get_jsonl("evaluations.jsonl"):
    latest[row["trace_id"]] = row  # the newest evaluation of a trace wins
ok_rows = [r for r in latest.values() if r["status"] == "ok"]
failed_rows = [r for r in latest.values() if r["status"] != "ok"]
if not latest:
    st.info("No evaluations yet. Run code/hw10/evaluator.py.")
else:
    table = pd.DataFrame([{
        "trace_id": r["trace_id"][:8], "question": r["question"],
        "Plan Quality": r["plan_quality"]["score"], "Writer Helpfulness": r["writer_helpfulness"]["score"],
        "Final Answer Helpfulness": r["final_helpfulness"]["score"],
        "Final - Draft": r["improvement"]["difference"], "final = draft": r["improvement"]["final_equals_draft"],
    } for r in ok_rows])
    st.caption("Scores are on the 1-5 scale (1 very poor, 5 excellent). Source: reports/hw10/raw/evaluations.jsonl "
               f"({len(ok_rows)} evaluated traces, {len(failed_rows)} evaluations that ended in an error).")
    if not table.empty:
        stages = ["Plan Quality", "Writer Helpfulness", "Final Answer Helpfulness"]
        st.subheader("Mean score by pipeline stage")
        means = table[stages].mean()
        st.bar_chart(means)
        st.subheader("Scores by case")
        st.dataframe(table, hide_index=True, width="stretch")

        same = table["final = draft"].mean() * 100
        mean_diff = table["Final - Draft"].mean()
        st.subheader("Interpretation of Planner / Writer / Reviewer coordination")
        st.write(
            f"Mean scores: plan {means['Plan Quality']:.2f}, draft {means['Writer Helpfulness']:.2f}, final answer "
            f"{means['Final Answer Helpfulness']:.2f}. The final answer equals the draft in {same:.0f}% of the cases "
            f"and the mean final-minus-draft difference is {mean_diff:+.2f}. "
            + ("The Reviewer passes the Writer's text through unchanged, so the final answer is not improved "
               "by the pipeline: answer quality is set by the Planner's plan and the Writer."
               if same >= 90 else "In some cases the final answer differs from the draft; see the case details below."))

        pick = st.selectbox("Case details", [r["trace_id"] for r in ok_rows],
                            format_func=lambda t: f"{t[:8]}  {latest[t]['question']}")
        r = latest[pick]
        st.write(f"**trace_id:** `{r['trace_id']}`")
        st.write(f"**Plan Quality {r['plan_quality']['score']}/5:** {r['plan_quality']['reason']}")
        st.write(f"**Writer Helpfulness {r['writer_helpfulness']['score']}/5:** {r['writer_helpfulness']['reason']}")
        st.write(f"**Final Answer Helpfulness {r['final_helpfulness']['score']}/5:** "
                 f"{r['final_helpfulness']['reason']}")
        imp = r["improvement"]
        st.write(f"**Final-vs-Draft:** draft {imp['draft_score']}, final {imp['final_score']}, difference "
                 f"{imp['difference']}. {imp['interpretation']}")
        st.write("**Final answer:**")
        st.write(r["final_answer"])
        st.caption(f"Judge: {r['judge']['model']}, temperature {r['judge']['temperature']}, seed {r['judge']['seed']}")
    if failed_rows:
        with st.expander(f"{len(failed_rows)} evaluation(s) that ended in an error"):
            st.dataframe(pd.DataFrame([{"trace_id": r["trace_id"], "error": r["error"]} for r in failed_rows]),
                         hide_index=True, width="stretch")

# ---------------------------------------------------------------- Part 3
st.header("Judge validation (Part 3)")
validation = data.get_json("judge_validation.json")
if not validation:
    st.info("No judge validation yet. Run code/hw10/validate_judge.py.")
else:
    stats = judge_stats.compute(validation)
    st.caption("Source: reports/hw10/raw/judge_validation.json (raw per-case data; these numbers are recomputed from "
               "it). Human labels: code/hw10/human_labels.csv, committed before any judge score existed.")
    if stats["n_usable"]:
        a, b = st.columns(2)
        rho = stats["spearman_rho"]
        a.metric("Spearman correlation (judge vs human)", "undefined" if rho is None else f"{rho:.3f}",
                 None if rho is None else f"p = {stats['spearman_p']:.4f}", delta_color="off")
        b.metric("Mean absolute difference", f"{stats['mean_abs_diff']:.2f}")
        rep = stats["repeat"]
        st.subheader("Repeatability (3 runs, same 20 drafts, same settings)")
        c, d, e = st.columns(3)
        c.metric("Cases whose score changed", f"{rep['cases_with_any_change']} of {rep['n_cases']}",
                 f"{rep['pct_cases_changed']:.0f}%", delta_color="off")
        d.metric("Mean absolute change", f"{rep['mean_abs_change']:.2f}")
        e.metric("Maximum absolute change", rep["max_abs_change"])
        st.caption(f"Judge settings: {validation['settings']}")
    if stats["n_judge_errors"]:
        st.warning(f"{stats['n_judge_errors']} case(s) have a judge error and are left out of the statistics.")
    per_case = pd.DataFrame([{
        "case": c["case_id"], "question": c["question"], "human": c["human"],
        **{f"judge run {i + 1}": r["score"] for i, r in enumerate(c["runs"])}} for c in validation["cases"]])
    st.dataframe(per_case, hide_index=True, width="stretch", height=35 * (len(per_case) + 1) + 3)
    if "judge run 1" in per_case:
        import altair as alt
        st.caption("Human score (x) against judge score, run 1 (y). Each dot is one case; overlapping cases share a dot.")
        st.altair_chart(alt.Chart(per_case.dropna(subset=["judge run 1"])).mark_circle(size=140, opacity=0.6).encode(
            x=alt.X("human:Q", scale=alt.Scale(domain=[0.5, 5.5]), title="human score"),
            y=alt.Y("judge run 1:Q", scale=alt.Scale(domain=[0.5, 5.5]), title="judge score (run 1)"),
            tooltip=["case", "human", "judge run 1"]), width="stretch")
