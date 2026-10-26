"""Create the HW7 users table and one demo user per role (passwords are stored hashed)."""
from sqlalchemy import text

import models
from database import Base, SessionLocal, db_session_basede26
from jwt_auth import hash_password

DEMO_USERS = [
    ("reader1", "reader123", "reader"),
    ("writer1", "writer123", "writer"),
    ("mod1", "mod123", "moderator"),
]

with db_session_basede26.begin() as conn:
    conn.execute(text("DROP TABLE IF EXISTS sessions"))
    conn.execute(text("DROP TABLE IF EXISTS users"))
Base.metadata.create_all(bind=db_session_basede26)

db = SessionLocal()
for username, password, role in DEMO_USERS:
    db.add(models.User(username=username, password_hash=hash_password(password), role=role))
db.commit()
print(db.query(models.User).count(), "users created")
db.close()