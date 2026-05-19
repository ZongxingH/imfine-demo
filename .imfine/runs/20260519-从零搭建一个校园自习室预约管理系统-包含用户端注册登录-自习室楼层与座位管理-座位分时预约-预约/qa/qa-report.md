# QA Report

Run: `20260519-从零搭建一个校园自习室预约管理系统-包含用户端注册登录-自习室楼层与座位管理-座位分时预约-预约`

## Verdict

Not ready for acceptance.

The backend has a working standard-library REST implementation with SQLite schema, seeded data, authentication, reservation conflict checks, timeout release, admin resource mutation, report review, and utilization statistics covered by the included unit suite. However, the frontend is not functionally wired to the backend contract, and several requested REST/user flows are missing or incomplete.

## Verification Commands

| Command | Result | Notes |
| --- | --- | --- |
| `python -m unittest discover -s tests -v` | Pass with elevated localhost binding | Default sandbox run failed in every test setup with `PermissionError: [Errno 1] Operation not permitted` when binding `ThreadingHTTPServer(("127.0.0.1", 0), ...)`. Re-run with approved elevated execution passed: 5 tests, 2.863s, OK. |
| `node --check frontend/user-miniapp/app.js` | Pass | Syntax check only; no runtime API contract validation. |
| `node --check frontend/admin/admin.js` | Pass | Syntax check only; no runtime API contract validation. |

## Requirement Coverage Notes

Covered or partially covered:

- Backend layered modules exist: `backend/api.py`, `backend/services.py`, `backend/database.py`, `backend/security.py`.
- SQLite schema includes users, roles, floors, rooms, seats, reservations, and violation reports.
- Backend REST paths cover registration/login, floor/room/seat listing, reservation create/list/check-in, timeout auto-release, report create/admin list/admin review, and utilization stats.
- Unit tests cover health/catalog pagination, registration/login/admin authz, admin floor/room/seat mutation, reservation conflict/check-in/auto-release, report review, and utilization response.
- Frontend pages exist for user login/register, seat browse, reservation form, active reservations, report form, admin resources, reports, and utilization.

Gaps and risks:

- Frontend default API bases are `http://localhost:8000/api`, but backend routes are mounted at root paths such as `/auth/login`, `/floors`, and `/admin/statistics/utilization`; no `/api` prefix is handled.
- User frontend request names do not match backend contracts: it sends `email`, `name`, `seatId`, `startTime`, `endTime`, `type`, and `description`, while the backend expects `username`, `seat_id`, `start_time`, `end_time`, `reason`, and `details`.
- Admin frontend request names and endpoints do not match backend contracts: it calls `GET /admin/seats` and `/admin/stats/utilization`, while the backend exposes public `GET /seats` and `GET /admin/statistics/utilization`; forms send `number`, `floorId`, `roomId`, `code`, and `status`, while backend expects `level`, `floor_id`, `room_id`, `label`, `seat_type`, `has_power`, or `active`.
- Pagination/filter parameters are inconsistent: frontend uses `pageSize`, `floorId`, and `roomId`; backend expects `page_size`, `floor_id`, and `room_id`.
- User frontend calls `/reservations/active`, but backend only implements `GET /reservations`.
- Required flows are missing or incomplete: cancel reservation, available time-slot query, reservation detail, user "my reports" list/detail, current-user/session endpoint, logout endpoint if session-based, admin reservation detail route, and explicit available-by-time-slot seat status.
- Report review status differs from the product plan: backend accepts `reviewed` or `rejected`; frontend and acceptance language expect approve/approved or reject/rejected. Backend also allows a report to be reviewed repeatedly.
- Report validation is not robust: invalid referenced seat/reservation IDs can surface as server errors instead of predictable validation errors because the service inserts directly without prechecking related records.
- Expired/past reservation handling is loose: the service can create reservations that already started or ended, relying on later auto-release rather than rejecting expired slots as required.
- Occupancy statistics return reserved minutes/capacity/utilization, but do not include the requested reservation count, completed/in-use count, timeout count, and use rate split by room or seat.
- "All interfaces introduced have unit tests" is not satisfied because several implemented or required endpoints/branches lack coverage, especially frontend-backend contract paths and negative validation cases.

## QA Conclusion

Backend unit-level verification passes after the localhost sandbox blocker is bypassed, but end-to-end requirement coverage is blocked by frontend/backend contract mismatches and missing REST flows. The run should return to development before acceptance or archive.
