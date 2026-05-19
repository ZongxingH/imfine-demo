# QA Recheck Report

Run: `20260519-从零搭建一个校园自习室预约管理系统-包含用户端注册登录-自习室楼层与座位管理-座位分时预约-预约`

## Verdict

Conditionally ready for the previously reported API contract fixes.

The backend compatibility patch resolves the specific frontend/backend contract blockers called out in the prior QA report: `/api` paths are accepted, camelCase request fields and query params are normalized, `/reservations/active` exists, `/admin/seats` exists, `/admin/stats/utilization` exists, CORS preflight/response headers are emitted, and frontend `approved` report actions map to backend `reviewed` status.

There are still minor frontend-facing semantic issues listed below, but they are narrower than the original API contract blockers.

## Verification Commands

| Command | Result | Notes |
| --- | --- | --- |
| `python -m unittest discover -s tests -v` | Pass with elevated localhost binding | Default sandbox run failed with `PermissionError: [Errno 1] Operation not permitted` while binding `ThreadingHTTPServer(("127.0.0.1", 0), ...)`. Re-run with approved elevated execution passed: 5 tests, 2.871s, OK. |
| `node --check frontend/user-miniapp/app.js` | Pass | Syntax check completed with exit code 0. |
| `node --check frontend/admin/admin.js` | Pass | Syntax check completed with exit code 0. |

## Rechecked Contract Items

| Item | Status | Evidence |
| --- | --- | --- |
| `/api` prefix | Resolved | `backend/api.py` normalizes `/api` and `/api/...` before routing. Tests cover `/api/health`, `/api/rooms`, `/api/seats`, `/api/reservations`, `/api/reports`, `/api/admin/...`. |
| camelCase request fields | Resolved for patched fields | `backend/api.py` maps `email`, `seatId`, `reservationId`, `startTime`, `endTime`, `floorId`, `roomId`, `number`, `code`, `type`, and `description` to backend snake_case/service fields. Tests cover `floorId`, `roomId`, `number`, `code`, `seatId`, `startTime`, `endTime`, `type`, and `description`. |
| camelCase query params | Resolved for patched params | `pageSize`, `floorId`, and `roomId` are accepted via query aliases. Tests cover these through catalog/admin/reservation calls. |
| `/reservations/active` | Route resolved | Backend routes `GET /reservations/active` to reservation listing, and the user frontend calls that path with `pageSize`. Unit tests cover `GET /api/reservations/active`. |
| `/admin/seats` | Resolved | Backend supports admin `GET/POST/PATCH/DELETE /admin/seats...`, frontend admin calls `GET /admin/seats` and resource creation through `/admin/seats`, and tests cover admin seat create/list/delete. |
| `/admin/stats/utilization` | Resolved | Backend supports both `/admin/statistics/utilization` and `/admin/stats/utilization`; frontend admin calls `/admin/stats/utilization`; tests cover `/api/admin/stats/utilization`. |
| CORS | Resolved | `OPTIONS` returns 204 with CORS headers, and JSON responses include CORS headers. Tests cover `OPTIONS /api/floors` and `Access-Control-Allow-Origin: *`. |
| `approved` -> `reviewed` mapping | Resolved | Request bodies and report status query filtering map `approved` to `reviewed`. Tests cover PATCH `/api/admin/reports/{id}` with `status: approved` returning `reviewed`. |

## Remaining Issues

1. `POST /admin/seats` does not honor frontend `status=disabled` on creation.
   The API normalizer converts `status: "disabled"` to `active: 0`, but `StudyRoomService.create_seat()` ignores `active` and always inserts a default active seat. The admin frontend exposes a disabled option in the create-seat form, so creating a disabled seat will incorrectly appear available.

2. `/reservations/active` is only an alias for `/reservations`.
   The route exists, which fixes the original 404 contract mismatch, but it does not filter out non-active statuses. After released/completed reservations exist, the user frontend's Active tab can show inactive historical reservations.

3. Frontend seat filters/search are only partially backed by the API.
   The user frontend sends `status` on `/seats`, and the admin frontend sends `keyword` on `/admin/seats`; the backend currently ignores both. This does not block the rechecked compatibility paths, but those visible UI controls will not behave as users expect.

## QA Conclusion

The original high-impact API contract mismatches are fixed and verified by the updated unit tests plus frontend syntax checks. Remaining issues are functional/semantic follow-ups rather than the broad frontend/backend incompatibility found in the first QA pass.
