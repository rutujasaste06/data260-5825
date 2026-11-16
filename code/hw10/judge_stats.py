"""
HW10 Part 3 - the statistics, computed from the raw per-case data in judge_validation.json
(so anyone can recompute them). Used by validate_judge.py and the dashboard.
"""

from itertools import combinations

from scipy.stats import spearmanr


def spearman(human, judge):
    if len(set(human)) < 2 or len(set(judge)) < 2:
        return None, None  # one of them never changes: rank correlation is undefined
    rho, p = spearmanr(human, judge)
    return float(rho), float(p)


def mean_abs_diff(human, judge):
    return sum(abs(h - j) for h, j in zip(human, judge)) / len(human)


def repeatability(runs):
    """runs = [[scores of run 1], [scores of run 2], [scores of run 3]] for the same cases."""
    n = len(runs[0])
    changes = [abs(a[i] - b[i]) for a, b in combinations(runs, 2) for i in range(n)]
    cases_changed = sum(1 for i in range(n) if len({r[i] for r in runs}) > 1)
    return {
        "n_cases": n,
        "cases_with_any_change": cases_changed,
        "pct_cases_changed": 100 * cases_changed / n,
        "pct_pairs_changed": 100 * sum(1 for c in changes if c > 0) / len(changes),
        "mean_abs_change": sum(changes) / len(changes),
        "max_abs_change": max(changes),
    }


def compute(validation):
    """validation = the dict saved in judge_validation.json."""
    cases = validation["cases"]
    usable = [c for c in cases if all(r["score"] is not None for r in c["runs"])]
    human = [c["human"] for c in usable]
    runs = [[c["runs"][k]["score"] for c in usable] for k in range(len(usable[0]["runs"]))] if usable else []
    out = {"n_cases": len(cases), "n_usable": len(usable), "n_judge_errors": len(cases) - len(usable)}
    if usable:
        rho, p = spearman(human, runs[0])
        out.update(spearman_rho=rho, spearman_p=p, mean_abs_diff=mean_abs_diff(human, runs[0]),
                   mean_abs_diff_by_run=[mean_abs_diff(human, r) for r in runs],
                   repeat=repeatability(runs) if len(runs) > 1 else None)
    return out
