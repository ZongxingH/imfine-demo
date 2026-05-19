# Project Overview

Status: updated after run `20260519-从零搭建一个校园自习室预约管理系统-包含用户端注册登录-自习室楼层与座位管理-座位分时预约-预约`.

This project is a campus study room reservation management demo. It provides a REST backend, SQLite persistence, a student-facing mini-program-style static frontend, and a static admin console.

Core capabilities:

- Student registration/login and bearer-token authentication.
- Floor, room, and seat browsing with pagination and filters.
- Seat time-slot availability checks, reservations, check-in, cancellation, conflict prevention, and overdue auto-release.
- Violation report submission and admin review.
- Admin management for floors, rooms, and seats.
- Utilization statistics by room and overall capacity.

Evidence: `README.md`, `backend/`, `frontend/`, `tests/test_api.py`, `.imfine/runs/20260519-从零搭建一个校园自习室预约管理系统-包含用户端注册登录-自习室楼层与座位管理-座位分时预约-预约/docs/technical-summary.md`.
