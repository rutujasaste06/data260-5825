"""HW7 Part 1 demo: run while the API is up. Prints the status code of every auth case."""
import json
import time
import urllib.error
import urllib.request

BASE = "http://localhost:8425"


def call(method, path, body=None, token=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def show(label, status, body):
    print(f"{label:<42} -> {status}  {str(body)[:80]}")


def token_of(username, password):
    status, body = call("POST", "/auth/login", {"username": username, "password": password})
    return status, body


print("HW7 Part 1 - JWT demo - Rutuja Saste")
s, b = token_of("reader1", "reader123")
show("POST /auth/login reader1 (valid)", s, b)
reader = b["access_token"]
writer = token_of("writer1", "writer123")[1]["access_token"]
mod = token_of("mod1", "mod123")[1]["access_token"]
show("POST /auth/login reader1 (wrong password)", *token_of("reader1", "wrong"))
print()
show("GET /auth/me (no token)", *call("GET", "/auth/me"))
show("GET /auth/me (invalid token)", *call("GET", "/auth/me", token="not.a.valid.token"))
show("GET /auth/me (reader token)", *call("GET", "/auth/me", token=reader))
print()
trial = {
    "trial_title": "HW7 demo trial",
    "nct_number": f"NCT{int(time.time())}",
    "available_slots": 5,
}
show("POST /trials as reader", *call("POST", "/trials", trial, reader))
s, b = call("POST", "/trials", trial, writer)
show("POST /trials as writer", s, b)
trial_id = b["id"]
print()
show("DELETE /trials/{id} as writer", *call("DELETE", f"/trials/{trial_id}", token=writer))
show("DELETE /trials/{id} as moderator", *call("DELETE", f"/trials/{trial_id}", token=mod))
print()
s, b = call("GET", "/trials", token=reader)
show("GET /trials as reader", s, f"{len(b)} trials returned")