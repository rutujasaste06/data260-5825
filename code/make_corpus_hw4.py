import os

OUT = "data/hw04_corpus"
os.makedirs(OUT, exist_ok=True)

DOCS = {
"01_session_auth_hw4.txt": """Session authentication in the Clinical Trial Registry (HW4)

When a user logs in with an email and a password, the FastAPI backend checks the password against a bcrypt hash stored in the users table. The plain password is never stored. If the password matches, the server creates a random 64-character session token and saves it in the sessions table together with the user id, the creation time and an expiry time.

The token is sent to the browser in an HTTP-only cookie named session_id. The cookie holds only the opaque token and never any user data. Because the cookie is HttpOnly, JavaScript running in the page cannot read it.

Every protected route runs a function called require_session. It reads the session_id cookie and looks the token up in the sessions table. If no cookie is sent, the server answers 401 with the message Not logged in. If the token is unknown or has expired, the server answers 401 with the message Session expired or invalid, and an expired row is deleted.

A HW4 session lasts 30 minutes on the server. Logging out deletes the session row and clears the cookie.
""",

"02_session_hw3_legacy.txt": """Session handling in the HW3 login pages

The HW3 pages (/login, /dashboard and /logout) use Starlette SessionMiddleware. The session data is stored inside a signed cookie named s5825_session instead of in a database table. The cookie is signed with a secret key so that tampering can be detected, but it is not encrypted, so its contents can be read by the browser user.

The HW3 idle timeout is 5 minutes (max_age of 300 seconds). The cookie is marked HttpOnly, SameSite=lax and Secure. The dashboard page sends the header Cache-Control: no-store, and a small pageshow script reloads the page when the browser back-forward cache restores it, so a logged-out user cannot see a stale dashboard by pressing Back.

The HW3 users are a small hard-coded list in auth.py. These pages were kept in HW4 so that the earlier work still runs.
""",

"03_database_setup.txt": """Database setup for HW4

The application stores its data in a MySQL database named s5825_rel, where s5825 is the student prefix. The connection object in database.py is named db_session_basede26, and SQLAlchemy is used to talk to MySQL.

There are four tables. The trials table holds the primary entity, with an auto-increment id, a trial_title and an nct_number. The users table holds id, name, a unique email and a password_hash. The sessions table holds the session token as its id, the user_id, created_at and expires_at. The trial_sites table holds test data, with an id, a trial_id that points to a trial, a site_name and a city.

The database was seeded with SEED 5825 so the data is identical on every run. It contains 5000 trials and 200 trial_sites rows, and each site row belongs to one trial.

One index was added: idx_trials_nct_number on the nct_number column of the trials table. Before the index, EXPLAIN showed a table scan with an estimated cost of 514 over about 5077 rows. After the index, EXPLAIN showed an index lookup with an estimated cost of 0.35 and 1 row.
""",

"04_n_plus_one.txt": """The N+1 problem and its fix

A list endpoint has the N+1 problem when it runs one query to load the list and then one extra query for every record to load that record's related data. The naive endpoint /trials-naive works this way. It loads the trials with one query and then, inside a loop, runs a separate SELECT on trial_sites for each trial.

The fixed endpoint /trials-fixed uses SQLAlchemy joinedload. The trials and their sites are loaded together in a single JOIN query, so the number of SQL statements does not depend on the page size.

Both endpoints return the same JSON. Each trial has a list called sites, which is empty for trials that have no site row. Both endpoints require a valid session cookie.

How it was measured. A script logged in once and then sent 30 timed requests for each combination of page size (10, 50 and 200) and version (naive and fixed), which makes 180 measured requests. The number of SQL statements per request was read from the X-SQL-Count response header, which does not count the one session check query. Latency was measured with a timer around each request, and p50, p95 and p99 were computed from the 30 values.

Results. The naive endpoint used 11, 51 and 201 SQL statements at page sizes 10, 50 and 200. The fixed endpoint used 1 statement at every page size. The median latency was 3.78 ms for naive and 1.67 ms for fixed at size 10, 7.38 ms and 1.56 ms at size 50, and 25.13 ms and 2.43 ms at size 200. The speed-up was 2.3 times, 4.7 times and 10.3 times. The speed-up grows because every extra record adds one more database round trip to the naive version.
""",

"05_react_client.txt": """React client for the Clinical Trial Registry

The frontend is a React app built with Vite and React Router. It has five pages: Login.jsx, Home.jsx, CreateRecord.jsx, UpdateRecord.jsx and DeleteRecord.jsx. The routes are / for the list, /login, /create, /update/:id and /delete/:id.

App.jsx is the hub. It keeps the login state and the list of trials with useState, loads data with useEffect, and passes the functions onAdd, onUpdate and onDelete down to the pages as props. After each change it calls navigate to return to the home page.

The React dev server runs on port 5173 by default, or on the next free port such as 5174. It calls the FastAPI backend on port 8425 through axios with withCredentials set to true, so the browser sends the session_id cookie. When the user is not logged in, Home.jsx shows the message Login required and the Add Trial link is hidden. On page load, App.jsx calls /auth/me to find out whether the cookie is still valid.
""",
}

for name, text in DOCS.items():
    with open(os.path.join(OUT, name), "w") as f:
        f.write(text)
    print("wrote", name, len(text), "characters")