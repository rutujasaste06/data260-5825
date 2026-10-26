"""HW7 Part 6 test run: glob -> search -> read integration test plus the 10-command gate test."""
import json
import os
import tempfile

import file_tools as ft

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "..", "reports", "hw07", "raw")

SHOULD_PASS = ["ls -la", "cat app.py", "grep -n DEBUG app.py", "git status", "echo hello"]
SHOULD_BLOCK = ["rm -rf /tmp/demo", "sudo cat /etc/shadow", "chmod 777 app.py",
                "ls && rm -rf build", "echo hi > /etc/hosts"]


def prefix_only_gate(command):
    """Baseline gate that only looks at the first word (this is the one with false allows)."""
    first = command.split()[0]
    return any(first == s.split()[0] for s in ft.SAFE_PREFIXES)


def integration_test(sandbox):
    """Create three Python files, then chain glob -> search -> read to find DEBUG."""
    ft.set_sandbox(sandbox)
    ft.write_file("utils.py", "def add(a, b):\n    return a + b\n")
    ft.write_file("app.py", "import utils\nDEBUG = True\nprint(utils.add(1, 2))\n")
    ft.write_file("main.py", "def main():\n    return 'ok'\n")
    files = ft.glob_files("*.py")
    hits = ft.search_in_files("DEBUG", "*.py")
    found = hits[0].split(":")[0]
    print("glob_files('*.py')          ->", files)
    print("search_in_files('DEBUG')    ->", hits)
    print(f"read_file('{found}') contents:")
    print(ft.read_file(found))
    print("edit_file diff              ->", ft.edit_file("app.py", "DEBUG = True", "DEBUG = False"))
    print("read_file(max_lines=1)      ->", ft.read_file("app.py", max_lines=1))
    return found == "app.py"


def gate_test():
    """Run 5 should-pass and 5 should-block commands; flag any false allow."""
    rows = []
    for command, want_allowed in [(c, True) for c in SHOULD_PASS] + [(c, False) for c in SHOULD_BLOCK]:
        gate = ft.confirm_bash(command)
        baseline = prefix_only_gate(command)
        rows.append({"command": command, "expected_allowed": want_allowed,
                     "allowed": gate["allowed"], "reason": gate["reason"],
                     "prefix_only_baseline_allowed": baseline,
                     "correct": gate["allowed"] == want_allowed,
                     "baseline_false_allow": baseline and not want_allowed})
        flag = "OK " if rows[-1]["correct"] else "BAD"
        note = "  <- baseline would FALSE-ALLOW this; final gate blocks it" if rows[-1]["baseline_false_allow"] else ""
        print(f"{flag} {command:<24} allowed={gate['allowed']!s:<5} {gate['reason']}{note}")
    return rows


def main():
    """Run both tests, print a summary and save the gate results as raw data."""
    print("File tools and safety gate test - Rutuja Saste")
    sandbox = tempfile.mkdtemp(prefix="course_sandbox_")
    print("\n(a) glob -> search -> read integration test")
    found_ok = integration_test(sandbox)
    print("integration test:", "PASS" if found_ok else "FAIL")
    print("\n(b) safety-gate test: 5 should pass, 5 should be blocked")
    rows = gate_test()
    extra = ["dd if=/dev/zero of=/dev/sda", "mkfs.ext4 /dev/sdb1", "chown root app.py"]
    print("extra deny-list checks:", {c: ft.is_destructive(c) for c in extra})
    print("confirmed destructive:", ft.confirm_bash("rm -rf build", auto_approve=True))
    print("bash('ls') in sandbox:", ft.bash("ls"))
    good = all(r["correct"] for r in rows) and found_ok
    print("\nFINAL:", "ALL PASS (0 false allows)" if good else "FAILURES FOUND")
    os.makedirs(RAW, exist_ok=True)
    with open(os.path.join(RAW, "safety_gate_results.json"), "w") as f:
        json.dump(rows, f, indent=2)
    return 0 if good else 1


if __name__ == "__main__":
    raise SystemExit(main())
