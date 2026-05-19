# Conventions

Status: updated after implementation.

- Keep the backend dependency-free and based on Python standard-library modules unless a future requirement explicitly justifies dependencies.
- Keep REST handlers in `backend/api.py`, business rules in `backend/services.py`, persistence/schema in `backend/database.py`, and auth helpers in `backend/security.py`.
- Preserve `/api/*` compatibility for frontend calls while allowing bare REST paths for tests and direct API usage.
- Support both snake_case backend fields and camelCase frontend aliases at API boundaries.
- Add or update `tests/test_api.py` coverage whenever changing an endpoint or business rule.

Evidence: `backend/api.py`, `backend/services.py`, `tests/test_api.py`, `README.md`.
