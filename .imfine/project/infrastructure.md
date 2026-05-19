# Infrastructure

Status: updated after implementation.

Local runtime infrastructure:

- Python HTTP server started via `python3 -m backend.server --host 127.0.0.1 --port 8000 --db study_rooms.sqlite3`.
- SQLite database file created and seeded on first server/service use.
- Static frontend files opened directly in a browser.

No CI/CD, container, cache, queue, or external service is configured.

Environment:

- Optional `STUDY_ROOM_TOKEN_SECRET` controls bearer-token signing secret.

Evidence: `backend/server.py`, `backend/database.py`, `README.md`.
