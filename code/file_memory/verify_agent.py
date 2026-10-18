import ast
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "trial_utils.py")
TEST = os.path.join(HERE, "tests", "test_trial_utils.py")


def main() -> None:
    """Check trial_utils.py against the rules written in AGENT.md."""
    print("Rutuja Saste - checking trial_utils.py against AGENT.md")
    source = open(SRC, encoding="utf-8").read()
    tree = ast.parse(source)
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    test_src = open(TEST, encoding="utf-8").read() if os.path.exists(TEST) else ""
    checks = {
        "has at least one function": len(funcs) > 0,
        "type hints on all args and return": all(
            f.returns is not None and all(a.annotation is not None for a in f.args.args)
            for f in funcs),
        "one-line docstring": all(
            ast.get_docstring(f) and "\n" not in ast.get_docstring(f).strip() for f in funcs),
        "snake_case names": all(re.fullmatch(r"[a-z_][a-z0-9_]*", f.name) for f in funcs),
        "under 20 lines": all(f.end_lineno - f.lineno + 1 < 20 for f in funcs),
        "no print()": not any(isinstance(n, ast.Call) and getattr(n.func, "id", "") == "print"
                              for n in ast.walk(tree)),
        "no hard-coded secrets": not re.search(r"(password|api_key|secret)\s*=", source, re.I),
        "pytest test exists": "def test_" in test_src,
    }
    for name, ok in checks.items():
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    sys.exit(0 if all(checks.values()) else 1)


if __name__ == "__main__":
    main()