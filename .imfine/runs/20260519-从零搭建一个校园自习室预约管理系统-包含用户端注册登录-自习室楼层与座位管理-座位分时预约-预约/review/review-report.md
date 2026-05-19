# Review Report

## Verdict

Blocking issues found. Backend happy-path tests pass, but the delivered frontend cannot reliably call the backend, and several required reservation/report behaviors are either missing or violate the stated contract.

## Findings

### P0 - Frontend and backend REST contracts do not match, making the user and admin pages unusable against this API

Evidence:

- Backend routes are registered at root paths such as `/auth/login`, `/floors`, `/rooms`, `/seats`, `/reservations`, `/admin/reports`, and `/admin/statistics/utilization` (`backend/api.py:59`, `backend/api.py:69`, `backend/api.py:82`, `backend/api.py:92`, `backend/api.py:149`, `backend/api.py:157`).
- Both frontends default to `http://localhost:8000/api` (`frontend/user-miniapp/app.js:4`, `frontend/admin/admin.js:4`), so every default request is sent to non-existent `/api/...` endpoints.
- The user frontend sends camelCase query/body fields (`pageSize`, `floorId`, `roomId`, `seatId`, `startTime`, `endTime`) while the backend reads snake_case fields (`page_size`, `floor_id`, `room_id`, `seat_id`, `start_time`, `end_time`) (`frontend/user-miniapp/app.js:104`, `frontend/user-miniapp/app.js:113`, `frontend/user-miniapp/app.js:143`, `frontend/user-miniapp/app.js:292`; `backend/api.py:77`, `backend/api.py:87`, `backend/services.py:214`, `backend/services.py:215`, `backend/services.py:216`).
- Login/register forms submit `email` and `name`, but the backend requires `username` (`frontend/user-miniapp/index.html:46`, `frontend/user-miniapp/index.html:55`, `frontend/user-miniapp/index.html:58`; `backend/api.py:61`, `backend/api.py:66`).
- The user frontend loads `/reservations/active`, which is not implemented (`frontend/user-miniapp/app.js:176`; implemented reservation list route is `backend/api.py:92`).
- The admin frontend loads `/admin/seats` and `/admin/stats/utilization`, but the backend has no `GET /admin/seats` route and exposes stats as `/admin/statistics/utilization` (`frontend/admin/admin.js:121`, `frontend/admin/admin.js:180`; `backend/api.py:138`, `backend/api.py:157`).
- Admin report approval sends `approved`, but backend only accepts `reviewed` or `rejected` (`frontend/admin/admin.js:135`, `frontend/admin/admin.js:274`; `backend/services.py:376`).

Impact:

The submitted frontend pages fail common core flows: login/register, browsing filtered seats, creating reservations, viewing reservations, listing admin seats, viewing utilization, and approving reports. This violates the requirement for working user mini-program pages and admin pages.

### P1 - Reservation creation accepts expired/past time slots and stores them as active reservations

Evidence:

- `create_reservation` validates only `end_time > start_time`; it does not reject slots that are already expired or whose end time is in the past (`backend/services.py:213` through `backend/services.py:252`).
- Auto-release runs before the insert (`backend/services.py:220`), so a newly inserted reservation from two hours ago is saved as `reserved` until a later release pass.
- The current test suite codifies this behavior by creating a reservation entirely in the past and expecting `201` with status `reserved` (`tests/test_api.py:194` through `tests/test_api.py:205`).

Impact:

Users can create already-expired reservations. These reservations are counted as active until another release call runs, which breaks availability semantics, usage statistics, and the acceptance criterion that expired slots return predictable errors.

### P1 - Report review status model and review rules do not satisfy the requirement

Evidence:

- The requirement expects report statuses including pending, approved, and rejected, and states reviewed reports cannot be reviewed again unless reopened.
- The database permits `pending`, `reviewed`, and `rejected`, not `approved` (`backend/database.py:82`).
- `review_report` accepts only `reviewed` or `rejected` and updates any report without checking that it is still pending (`backend/services.py:374` through `backend/services.py:390`).
- The admin frontend exposes "Approve" with status `approved`, which backend rejects (`frontend/admin/admin.js:135`, `frontend/admin/admin.js:274`).

Impact:

Admin approval from the UI fails, and even API clients that use `reviewed` can repeatedly change already-reviewed reports. This violates the admin review workflow and audit expectations.

### P1 - Violation report creation does not validate required seat/reservation context and can return 500 for bad references

Evidence:

- `create_report` only requires either `reservation_id` or `seat_id`; it does not require a time context, validate that the referenced seat/reservation exists before insert, or verify reservation ownership/context (`backend/services.py:333` through `backend/services.py:352`).
- Foreign key failures from invalid `seat_id` or `reservation_id` are not converted into `ServiceError`, so the top-level dispatcher returns a generic `500` (`backend/api.py:43` through `backend/api.py:48`).

Impact:

Invalid report submissions do not get predictable client errors, and reports can be filed without the valid seat/time context required by the product plan.

### P2 - Required reservation/report APIs are missing

Evidence:

- There is no reservation cancel endpoint, reservation detail endpoint, or available-slots endpoint in `backend/api.py`.
- There is no user "my reports" list/detail endpoint; only `POST /reports` and admin report listing/review are implemented (`backend/api.py:116`, `backend/api.py:149`, `backend/api.py:154`).
- Admin reservation list/detail is not exposed under the admin namespace, despite being in scope. Admins can incidentally call `GET /reservations`, but there is no detail route and the UI does not use it (`backend/api.py:92`).

Impact:

Several required user and admin workflows cannot be completed through the REST API: canceling a future reservation, viewing reservation details, querying report status as a student, and reviewing reservation details as an admin.

### P2 - Pagination contract is inconsistent between backend, tests, and frontend

Evidence:

- Backend reads `page_size` and responds with `page_size` (`backend/api.py:221`, `backend/services.py:453`).
- Frontends send and read `pageSize` (`frontend/user-miniapp/app.js:95`, `frontend/user-miniapp/app.js:104`, `frontend/user-miniapp/app.js:145`; `frontend/admin/admin.js:69`, `frontend/admin/admin.js:117`, `frontend/admin/admin.js:150`).

Impact:

List page sizes are silently ignored by the backend, and next-page detection can be wrong because the UI looks for a response field that never exists.

### P2 - Tests do not cover the required API surface or the known failure modes

Evidence:

- The suite contains five backend HTTP tests (`tests/test_api.py`) and no frontend contract tests.
- Missing coverage includes expired reservation rejection, reservation cancel/detail, own report list/detail, invalid report references, repeated report review, frontend/backend route compatibility, admin statistics route compatibility, and snake_case/camelCase payload compatibility.

Impact:

The passing test suite does not prove correctness against the requested system behavior. Several blocking regressions above would pass the current tests.

## Verification

- `python -m unittest -v tests/test_api.py`
- Result: passed after allowing local HTTP socket binding. The first sandboxed run failed with `PermissionError: [Errno 1] Operation not permitted` while binding `127.0.0.1`.

## Residual Risks

- No browser/e2e tests were run, so layout and runtime fetch behavior were reviewed statically.
- No concurrency stress test was run for simultaneous reservations. The current SQLite conflict check is not protected by an explicit transaction/lock around check-and-insert, so concurrent double-booking remains a risk even though the sequential conflict test passes.
