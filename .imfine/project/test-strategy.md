# Test Strategy

Status: updated after implementation.

Primary verification command:

```bash
python3 -m unittest discover -s tests -v
```

The API tests use an in-process `ThreadingHTTPServer` on an ephemeral localhost port and cover:

- Health and CORS.
- Seeded floor/room/seat catalog with pagination and filters.
- User registration/login and admin authorization.
- Admin floor/room/seat management.
- Reservation create/list/detail/check-in/cancel/conflict prevention/auto-release.
- Seat availability by time range.
- Violation report creation/list/detail/admin review and repeat-review rejection.
- Utilization statistics.
- `/api` prefix and camelCase/snake_case compatibility for the static frontends.

Frontend JavaScript syntax checks:

```bash
node --check frontend/user-miniapp/app.js
node --check frontend/admin/admin.js
```

Note: the local sandbox may block localhost socket binding; elevated execution was required during this run for the API tests.

Evidence: `tests/test_api.py`, `.imfine/runs/20260519-从零搭建一个校园自习室预约管理系统-包含用户端注册登录-自习室楼层与座位管理-座位分时预约-预约/qa/`, `.imfine/runs/20260519-从零搭建一个校园自习室预约管理系统-包含用户端注册登录-自习室楼层与座位管理-座位分时预约-预约/review/`.
