# Technical Summary

## Implementation Summary

The project implements a campus study room reservation demo with a Python standard-library backend and static browser frontends.

- Backend entry: `backend/server.py` starts `ThreadingHTTPServer` on the configured host, port, and SQLite database path.
- API layer: `backend/api.py` handles REST routes, JSON responses, CORS, bearer-token authorization, and `/api` prefix normalization.
- Data layer: `backend/database.py` creates SQLite tables for users, floors, rooms, seats, reservations, and violation reports, then seeds admin and catalog data.
- Business logic: `backend/services.py` covers registration/login, catalog pagination, admin resource management, seat availability, reservation conflict checks, check-in, cancellation, overdue auto-release, reports, and utilization statistics.
- Security helpers: `backend/security.py` uses PBKDF2 password hashes and HMAC-signed tokens from the Python standard library.
- User frontend: `frontend/user-miniapp/index.html`, `app.js`, and `styles.css` provide login/register, seat browsing, reservation, active reservation, and report flows.
- Admin frontend: `frontend/admin/index.html`, `admin.js`, and `styles.css` provide resource management, report review, and utilization views.
- Tests: `tests/test_api.py` runs integration-style API coverage against an in-process HTTP server.

## Verification Commands

Backend start command:

```bash
python3 -m backend.server --host 127.0.0.1 --port 8000 --db study_rooms.sqlite3
```

API test command:

```bash
python3 -m unittest discover -s tests
```

Observed result on 2026-05-19: 5 tests passed. The first sandboxed attempt failed because local socket binding to `127.0.0.1` was denied; rerunning with localhost bind permission passed.

## Notable Constraints

- Backend uses only Python standard-library HTTP, SQLite, crypto, and unittest modules.
- Persistence is local SQLite; no external database service is required.
- Frontends are static HTML/CSS/JavaScript files; no bundler or package install is required.
- API base URL defaults to `http://localhost:8000/api` in both frontends.
- Default admin credentials are `admin` / `admin123`.
- There is no heavy middleware stack, web framework, ORM, build pipeline, or frontend framework.
- Token secret defaults to a development value unless `STUDY_ROOM_TOKEN_SECRET` is set.
