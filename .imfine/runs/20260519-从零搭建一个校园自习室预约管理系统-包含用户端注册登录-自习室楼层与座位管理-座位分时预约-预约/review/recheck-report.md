# Reviewer Recheck Report

## Verdict

Pass with non-blocking residual issues. The original blocking API/frontend contract failures and business-rule gaps are resolved by the current backend, service, database, and test changes. I found no remaining P0/P1 blocker in the rechecked surface.

Two P2 frontend behavior issues remain and should be tracked, but they do not reopen the prior blocking review.

## Findings

### P2 - User floor filter is still not honored by the seat list endpoint

Evidence:

- The user frontend sends `floorId` when loading seats (`frontend/user-miniapp/app.js:147` through `frontend/user-miniapp/app.js:153`).
- `GET /seats` accepts `roomId`, `status`, and `keyword`, but does not read `floor_id` or `floorId` (`backend/api.py:87` through `backend/api.py:95`).
- `StudyRoomService.list_seats` filters by `room_id`, status, and keyword only (`backend/services.py:86` through `backend/services.py:121`).

Impact:

Choosing a floor without also choosing a room can still show seats from every floor. Status filtering and admin keyword search are now implemented, but this user-facing floor filter remains a frontend/backend contract mismatch.

### P2 - Admin utilization summary cards can display incorrect utilization

Evidence:

- Backend utilization returns `reservedSeats` as `total_reserved`, which is reserved minutes, while `totalSeats` is a seat count (`backend/services.py:632` through `backend/services.py:643`).
- The admin frontend calculates the top-level utilization as `reservedSeats / totalSeats * 100` whenever `totalSeats > 0`, instead of using the backend's `utilizationRate` (`frontend/admin/admin.js:158` through `frontend/admin/admin.js:164`).

Impact:

The `/admin/stats/utilization` route now exists and returns correct utilization fields, but the admin summary UI can show an inflated percentage and labels reserved minutes as "Reserved now".

## Resolved Checks

- `/api` prefix mismatch: resolved by path normalization (`backend/api.py:262` through `backend/api.py:267`) and covered by `/api/health`, `/api/rooms`, `/api/seats`, and other `/api/...` test calls.
- CamelCase/snake_case request mismatch: resolved for the exercised body and query fields via `_normalize_body`, `_query_int`, and `_page_size` aliases (`backend/api.py:270` through `backend/api.py:326`).
- Pagination aliases: resolved; responses include both `page_size` and `pageSize` (`backend/services.py:660` through `backend/services.py:667`), and tests assert both.
- Missing `/reservations/active`: resolved (`backend/api.py:112` through `backend/api.py:123`), with active-list coverage in `tests/test_api.py:224` through `tests/test_api.py:232`.
- Missing `/admin/seats`: resolved (`backend/api.py:175` through `backend/api.py:191`), with create/list/delete coverage in `tests/test_api.py:167` through `tests/test_api.py:201`.
- Missing `/admin/stats/utilization`: resolved as an alias alongside `/admin/statistics/utilization` (`backend/api.py:211` through `backend/api.py:215`), with test coverage in `tests/test_api.py:384` through `tests/test_api.py:398`.
- Report approval status: resolved; database supports `approved`, service accepts `approved`/`rejected`, and admin JS sends `approved` (`backend/database.py:82`, `backend/services.py:573` through `backend/services.py:591`, `frontend/admin/admin.js:135` and `frontend/admin/admin.js:274` through `frontend/admin/admin.js:277`).
- Expired reservation creation: resolved for fully expired slots by `end_time <= now` rejection (`backend/services.py:261` through `backend/services.py:264`) and covered in `tests/test_api.py:288` through `tests/test_api.py:299`.
- Invalid report reference handling: resolved for missing seats/reservations through explicit `_seat`/`_reservation` lookup before insert (`backend/services.py:499` through `backend/services.py:506`), with invalid seat coverage in `tests/test_api.py:341` through `tests/test_api.py:347`.
- Repeated report review: resolved by requiring pending status before update (`backend/services.py:579` through `backend/services.py:581`), with coverage in `tests/test_api.py:376` through `tests/test_api.py:382`.
- Reservation cancel/detail/availability APIs: resolved (`backend/api.py:99` through `backend/api.py:143`) with coverage in `tests/test_api.py:234` through `tests/test_api.py:252` and `tests/test_api.py:310` through `tests/test_api.py:325`.
- User reports and admin reservations APIs: resolved (`backend/api.py:145` through `backend/api.py:155`, `backend/api.py:197` through `backend/api.py:201`). User report listing is covered in `tests/test_api.py:358` through `tests/test_api.py:365`.
- Status/search filters: resolved for supported seat status values, admin seat keyword search, and report status filters (`backend/services.py:99` through `backend/services.py:121`, `backend/services.py:545` through `backend/services.py:571`), with the floor-filter caveat listed above.

## Verification

- `python -m unittest discover -s tests -v`
  - First sandboxed run failed because localhost binding was blocked: `PermissionError: [Errno 1] Operation not permitted` at `ThreadingHTTPServer(("127.0.0.1", 0), handler)`.
  - Rerun with approved localhost binding passed: 5 tests, OK.
- `node --check frontend/user-miniapp/app.js`: passed.
- `node --check frontend/admin/admin.js`: passed.

## Residual Risk

No browser/e2e test was run. Frontend runtime behavior was reviewed statically plus `node --check`.
