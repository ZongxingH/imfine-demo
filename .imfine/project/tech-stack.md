# Tech Stack

Status: updated after implementation.

## Backend

- Language: Python 3.
- HTTP: standard-library `http.server.ThreadingHTTPServer`.
- Persistence: SQLite via standard-library `sqlite3`.
- Tests: standard-library `unittest`.
- Auth: signed bearer tokens and password hashing implemented with standard-library modules.

## Frontend

- Static HTML/CSS/JavaScript.
- User app: `frontend/user-miniapp/`.
- Admin console: `frontend/admin/`.
- No package manager, bundler, or third-party frontend dependency is required.

## Middleware / External Services

- No heavy third-party middleware.
- No external services are required for local operation.

Evidence: `backend/server.py`, `backend/api.py`, `backend/database.py`, `backend/security.py`, `frontend/user-miniapp/app.js`, `frontend/admin/admin.js`, `tests/test_api.py`, `README.md`.
