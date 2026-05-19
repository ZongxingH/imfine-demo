# Architecture

Status: updated after implementation.

The system uses a lightweight front/back separated architecture.

Backend layers:

- `backend/server.py`: server entrypoint and CLI flags.
- `backend/api.py`: REST routing, request normalization, CORS, auth checks, and JSON responses.
- `backend/services.py`: business rules for users, rooms, seats, reservations, reports, and statistics.
- `backend/database.py`: SQLite schema initialization and seed data.
- `backend/security.py`: password hashing and token signing.

Frontend boundaries:

- `frontend/user-miniapp/`: student-facing static pages for auth, seat browsing, reservations, active reservations, and reports.
- `frontend/admin/`: admin static console for resources, report review, and utilization.

Database entities:

- `users`, `floors`, `rooms`, `seats`, `reservations`, `violation_reports`.

Evidence: `backend/`, `frontend/`, `README.md`, `.imfine/runs/20260519-从零搭建一个校园自习室预约管理系统-包含用户端注册登录-自习室楼层与座位管理-座位分时预约-预约/architecture/architecture-plan.md`.
