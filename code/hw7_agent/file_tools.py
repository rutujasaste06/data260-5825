"""HW7 Part 6: six file tools and a bash safety gate (pure Python, no model needed)."""
import difflib
import fnmatch
import glob
import os
import re
import subprocess

SANDBOX = os.path.realpath(os.getcwd())

# Commands that may run without asking (every chained part must match one of these).
SAFE_PREFIXES = ("ls", "cat", "pwd", "echo", "grep", "head", "tail", "wc", "find",
                 "git status", "git diff", "git log")

# Independent deny-list: these need explicit confirmation even if a SAFE_PREFIX matches.
DESTRUCTIVE_PATTERNS = {
    "recursive deletion": r"\brm\s+(?:-\S+\s+)*(?:-\w*[rR]\w*|--recursive)\b",
    "privilege escalation": r"\b(?:sudo|su|doas)\b",
    "permission or ownership change": r"\b(?:chmod|chown|chgrp)\b",
    "raw-device write": r"\bdd\b[^|;&]*\bof=/dev/|>\s*/dev/(?!null\b)",
    "filesystem creation": r"\b(?:mkfs(?:\.\w+)?|mke2fs|newfs)\b",
    "redirection to a root path": r">>?\s*/(?!dev/null\b)",
}


def set_sandbox(path):
    """Point every file tool at one sandbox directory."""
    global SANDBOX
    SANDBOX = os.path.realpath(path)


def _inside(path):
    """Resolve a path and refuse anything outside the sandbox."""
    full = os.path.realpath(os.path.join(SANDBOX, path))
    if full != SANDBOX and not full.startswith(SANDBOX + os.sep):
        raise ValueError(f"path outside sandbox: {path}")
    return full


def read_file(path, max_lines=None):
    """Return the file text, limited to max_lines lines when given."""
    with open(_inside(path), encoding="utf-8") as f:
        lines = f.read().splitlines()
    return "\n".join(lines if max_lines is None else lines[:max_lines])


def write_file(path, content):
    """Create or overwrite a file inside the sandbox."""
    full = _inside(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return f"wrote {len(content)} characters to {path}"


def edit_file(path, old, new):
    """Replace the first occurrence of old with new and return a short diff."""
    full = _inside(path)
    with open(full, encoding="utf-8") as f:
        before = f.read()
    if old not in before:
        return "edit failed: old text not found"
    after = before.replace(old, new, 1)
    with open(full, "w", encoding="utf-8") as f:
        f.write(after)
    diff = difflib.unified_diff(before.splitlines(), after.splitlines(),
                                "before", "after", lineterm="", n=0)
    return "\n".join(list(diff)[:12])


def glob_files(pattern):
    """List sandbox files matching a glob pattern (relative paths)."""
    found = glob.glob(os.path.join(SANDBOX, pattern), recursive=True)
    return sorted(os.path.relpath(p, SANDBOX) for p in found if os.path.isfile(p))


def search_in_files(pattern, file_pattern="*"):
    """Search file contents; returns 'path:line:text' for each match."""
    hits = []
    for root, _dirs, files in os.walk(SANDBOX):
        for name in sorted(files):
            if not fnmatch.fnmatch(name, file_pattern):
                continue
            full = os.path.join(root, name)
            with open(full, encoding="utf-8", errors="ignore") as f:
                for number, line in enumerate(f, 1):
                    if re.search(pattern, line):
                        hits.append(f"{os.path.relpath(full, SANDBOX)}:{number}:{line.strip()}")
    return hits


def destructive_reason(command):
    """Name of the first destructive category the command falls in, else None."""
    for reason, regex in DESTRUCTIVE_PATTERNS.items():
        if re.search(regex, command):
            return reason
    return None


def is_destructive(command):
    """True when the command is recursive deletion, sudo, chmod/chown, raw-device write, etc."""
    return destructive_reason(command) is not None


def _matches_safe_prefix(command):
    """True only when every chained part starts with an allow-listed prefix."""
    parts = [p.strip() for p in re.split(r"&&|\|\||;|\|", command) if p.strip()]
    return bool(parts) and all(
        any(p == s or p.startswith(s + " ") for s in SAFE_PREFIXES) for p in parts)


def confirm_bash(command, auto_approve=False):
    """Allow/block decision with a short reason. auto_approve stands for explicit confirmation."""
    reason = destructive_reason(command)
    if reason:
        if auto_approve:
            return {"allowed": True, "reason": f"destructive ({reason}) but explicitly confirmed"}
        return {"allowed": False, "reason": f"blocked: {reason} needs confirmation"}
    if _matches_safe_prefix(command):
        return {"allowed": True, "reason": "matches SAFE_PREFIXES"}
    if auto_approve:
        return {"allowed": True, "reason": "not allow-listed but explicitly confirmed"}
    return {"allowed": False, "reason": "blocked: not in SAFE_PREFIXES, needs confirmation"}


def bash(command, auto_approve=False):
    """Run a shell command inside the sandbox, but only after the safety gate allows it."""
    gate = confirm_bash(command, auto_approve)
    if not gate["allowed"]:
        return {"ok": False, "output": gate["reason"]}
    done = subprocess.run(command, shell=True, cwd=SANDBOX, capture_output=True,
                          text=True, timeout=10)
    return {"ok": done.returncode == 0, "output": (done.stdout + done.stderr).strip()}
