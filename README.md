# Campus Study Room Reservation

Small campus study room reservation demo with a Python standard-library backend, SQLite persistence, and static user/admin frontends.

## Project Structure

- `backend/server.py` - HTTP server entry point.
- `backend/api.py` - REST routing, JSON responses, CORS, token checks, and `/api` path normalization.
- `backend/services.py` - reservation, resource, report, and utilization business logic.
- `backend/database.py` - SQLite schema creation and seed data.
- `backend/security.py` - password hashing and signed bearer tokens using the standard library.
- `frontend/user-miniapp/index.html` - student-facing static app entry.
- `frontend/admin/index.html` - admin static console entry.
- `tests/test_api.py` - API integration tests using `unittest` and an in-process HTTP server.

## Backend

Start the API from the repository root:

```bash
python3 -m backend.server --host 127.0.0.1 --port 8000 --db study_rooms.sqlite3
```

The server creates and seeds the SQLite database on first use. The default admin account is:

- Username: `admin`
- Password: `admin123`

Tokens are signed with `STUDY_ROOM_TOKEN_SECRET` when set, otherwise a development default is used.

## Frontend

Open the static entry files directly in a browser:

- User miniapp: `frontend/user-miniapp/index.html`
- Admin console: `frontend/admin/index.html`

Both frontends default to this API base URL:

```text
http://localhost:8000/api
```

The backend also accepts bare paths such as `/health`, because `/api/*` is normalized internally.

## Tests

Run the API test suite:

```bash
python3 -m unittest discover -s tests
```

The tests cover health/CORS, seeded catalog pagination, registration/login, admin authorization, floor/room/seat management, reservation conflict/check-in/cancel/auto-release flows, violation report review, and utilization statistics.

## Key Features

- Student registration and login with bearer-token authentication.
- Seeded floors, rooms, and seats with pagination and filters.
- Seat availability checks for time ranges.
- Seat reservations with conflict prevention, check-in, cancellation, and overdue auto-release.
- Admin management for floors, rooms, and seats.
- Violation report submission and admin review.
- Utilization statistics by room and overall capacity.
