# Architecture Plan

## Scope and Assumptions

This run starts from an empty implementation baseline. The project evidence reports no detected source layout, package manager, framework, entrypoints, middleware, database, or tests. The architecture therefore recommends a small, explicit structure rather than adapting an existing application.

Assumptions:

- Use Python standard library only for the backend runtime: `http.server`, `sqlite3`, `json`, `urllib.parse`, `hashlib`, `hmac`, `secrets`, `datetime`, and `unittest`.
- Use SQLite as the local relational database.
- Use static HTML, CSS, and JavaScript for both frontend surfaces.
- Keep the frontend/backend separated by REST JSON APIs.
- Do not introduce Flask, Django, FastAPI, SQLAlchemy, Celery, Redis, frontend build tools, or other heavy middleware.
- Implement enough authentication for this local demo: password hashing with stdlib PBKDF2 and opaque session tokens stored in SQLite.

Success criteria:

- Backend exposes complete REST resources for auth, study rooms, floors, seats, time slots, reservations, reports, and utilization reports.
- Database migrations and seed data create a complete relational model with associations and constraints.
- User miniapp pages support registration/login, seat browsing, reservation, own reservations, and violation reports.
- Admin pages support login, room/floor/seat management, report review, reservation management, and utilization reports.
- API behavior is covered with `unittest` integration tests.

## Recommended Repository Structure

```text
backend/
  app.py
  config.py
  db/
    connection.py
    migrate.py
    seed.py
    migrations/
      001_initial.sql
    study_room.sqlite3
  domain/
    errors.py
    models.py
    validation.py
  repositories/
    users.py
    sessions.py
    rooms.py
    floors.py
    seats.py
    time_slots.py
    reservations.py
    violation_reports.py
  services/
    auth_service.py
    room_service.py
    reservation_service.py
    report_service.py
    utilization_service.py
  http/
    router.py
    request.py
    response.py
    handlers/
      auth.py
      rooms.py
      floors.py
      seats.py
      time_slots.py
      reservations.py
      violation_reports.py
      utilization.py
  tests/
    test_auth_api.py
    test_rooms_api.py
    test_seats_api.py
    test_reservations_api.py
    test_violation_reports_api.py
    test_utilization_api.py
frontend/
  user-miniapp/
    index.html
    styles.css
    app.js
    api.js
    pages/
      login.js
      rooms.js
      seats.js
      reservations.js
      reports.js
  admin/
    index.html
    styles.css
    app.js
    api.js
    pages/
      dashboard.js
      login.js
      rooms.js
      seats.js
      reservations.js
      reports.js
      utilization.js
```

Entrypoints:

- `python -m backend.db.migrate`: apply SQLite migrations.
- `python -m backend.db.seed`: insert demo admin, demo user, rooms, floors, seats, and time slots.
- `python -m backend.app`: start the stdlib HTTP API server.
- `python -m unittest discover backend/tests`: run API tests.
- Open `frontend/user-miniapp/index.html` and `frontend/admin/index.html` in a browser, or serve them as static files separately.

## Backend Layers

HTTP layer:

- Parse request method, path, query string, JSON body, and auth token.
- Route to handlers.
- Convert service results to JSON responses.
- Map domain errors to HTTP status codes.

Service layer:

- Enforce use cases and transactional rules.
- Own validation that crosses repository boundaries, such as double-booking checks.
- Release expired reservations before availability reads or reservation writes.
- Coordinate repository calls inside SQLite transactions.

Repository layer:

- Own SQL statements for each aggregate/table group.
- Return plain dictionaries or small dataclasses.
- Avoid business decisions beyond query shape.

Domain layer:

- Shared status constants, validation helpers, and typed application errors.
- No database or HTTP dependencies.

Database layer:

- Provide SQLite connections with `PRAGMA foreign_keys = ON`.
- Apply migrations in filename order.
- Seed deterministic demo data.

## Database Entities and Associations

Core tables:

- `users`
  - `id` primary key
  - `username` unique
  - `password_hash`
  - `role` enum-like text: `student`, `admin`
  - `status` text: `active`, `disabled`
  - `created_at`

- `sessions`
  - `id` primary key
  - `user_id` references `users(id)`
  - `token` unique
  - `expires_at`
  - `created_at`

- `study_rooms`
  - `id` primary key
  - `name`
  - `building`
  - `description`
  - `status` text: `open`, `closed`
  - `created_at`

- `floors`
  - `id` primary key
  - `room_id` references `study_rooms(id)`
  - `floor_no`
  - `name`
  - unique `(room_id, floor_no)`

- `seats`
  - `id` primary key
  - `floor_id` references `floors(id)`
  - `seat_no`
  - `type` text: `normal`, `power`, `silent`
  - `status` text: `available`, `maintenance`, `disabled`
  - unique `(floor_id, seat_no)`

- `time_slots`
  - `id` primary key
  - `label`
  - `start_time` text in `HH:MM`
  - `end_time` text in `HH:MM`
  - unique `(start_time, end_time)`

- `reservations`
  - `id` primary key
  - `user_id` references `users(id)`
  - `seat_id` references `seats(id)`
  - `slot_id` references `time_slots(id)`
  - `reservation_date` text in `YYYY-MM-DD`
  - `status` text: `pending_checkin`, `checked_in`, `completed`, `cancelled`, `released`, `no_show`
  - `expires_at` timestamp for check-in timeout
  - `checked_in_at`
  - `cancelled_at`
  - `released_at`
  - `created_at`
  - unique active booking guard: service must prevent more than one active reservation for `(seat_id, reservation_date, slot_id)`.

- `violation_reports`
  - `id` primary key
  - `reporter_id` references `users(id)`
  - `reservation_id` nullable references `reservations(id)`
  - `seat_id` references `seats(id)`
  - `reason`
  - `description`
  - `status` text: `pending`, `approved`, `rejected`
  - `admin_id` nullable references `users(id)`
  - `review_note`
  - `reviewed_at`
  - `created_at`

Associations:

- One study room has many floors.
- One floor has many seats.
- One seat has many reservations and reports.
- One time slot has many reservations.
- One user has many reservations and submitted reports.
- One admin reviews many violation reports.

Recommended indexes:

- `sessions(token)`
- `reservations(user_id, reservation_date)`
- `reservations(seat_id, reservation_date, slot_id, status)`
- `violation_reports(status, created_at)`
- `seats(floor_id, status)`

## REST Resource Design

Conventions:

- All endpoints return JSON.
- Request body uses JSON.
- Auth uses `Authorization: Bearer <token>`.
- Pagination uses `page` and `page_size`.
- List responses use `{ "items": [], "page": 1, "page_size": 20, "total": 0 }`.
- Error responses use `{ "error": { "code": "...", "message": "..." } }`.

Authentication:

- `POST /api/auth/register`
  - Public student registration.
  - Body: `username`, `password`.

- `POST /api/auth/login`
  - Body: `username`, `password`.
  - Returns user summary and token.

- `POST /api/auth/logout`
  - Requires auth.
  - Invalidates current token.

- `GET /api/auth/me`
  - Requires auth.
  - Returns current user.

Study rooms and floors:

- `GET /api/rooms`
  - User/admin list, supports `status`, `page`, `page_size`.

- `POST /api/admin/rooms`
  - Admin create room.

- `PUT /api/admin/rooms/{room_id}`
  - Admin update room.

- `DELETE /api/admin/rooms/{room_id}`
  - Admin soft delete by setting `closed` or `disabled` equivalent.

- `GET /api/rooms/{room_id}/floors`
  - List floors under a room.

- `POST /api/admin/rooms/{room_id}/floors`
  - Admin create floor.

- `PUT /api/admin/floors/{floor_id}`
  - Admin update floor.

- `DELETE /api/admin/floors/{floor_id}`
  - Admin delete floor only when no seats exist, or reject with conflict.

Seats and availability:

- `GET /api/floors/{floor_id}/seats`
  - Supports `date`, `slot_id`, `status`, `page`, `page_size`.
  - When `date` and `slot_id` are present, includes `availability`.

- `POST /api/admin/floors/{floor_id}/seats`
  - Admin create seat.

- `PUT /api/admin/seats/{seat_id}`
  - Admin update seat status/type.

- `DELETE /api/admin/seats/{seat_id}`
  - Admin disables seat if historical reservations exist.

Time slots:

- `GET /api/time-slots`
  - Public list.

- `POST /api/admin/time-slots`
  - Admin create slot.

- `PUT /api/admin/time-slots/{slot_id}`
  - Admin update slot if not used by future active reservations.

- `DELETE /api/admin/time-slots/{slot_id}`
  - Admin delete when unused; otherwise reject with conflict.

Reservations:

- `GET /api/reservations`
  - Student sees own reservations.
  - Admin may pass `user_id`, `date`, `status`, `seat_id`.

- `POST /api/reservations`
  - Student creates reservation.
  - Body: `seat_id`, `slot_id`, `reservation_date`.
  - Service rejects seat maintenance/disabled, past slot, and active double booking.

- `POST /api/reservations/{reservation_id}/check-in`
  - Student checks in before `expires_at`.

- `POST /api/reservations/{reservation_id}/cancel`
  - Student cancels own active reservation.

- `POST /api/admin/reservations/{reservation_id}/release`
  - Admin manually releases a reservation.

Violation reports:

- `GET /api/violation-reports`
  - Student sees own submitted reports.
  - Admin lists all reports with `status`, `page`, `page_size`.

- `POST /api/violation-reports`
  - Student reports seat occupation.
  - Body: `seat_id`, optional `reservation_id`, `reason`, `description`.

- `POST /api/admin/violation-reports/{report_id}/review`
  - Admin approves or rejects.
  - Body: `decision`, `review_note`.
  - On approval, optionally release linked active reservation if the report is tied to a reservation.

Utilization reports:

- `GET /api/admin/reports/utilization`
  - Admin only.
  - Query: `start_date`, `end_date`, optional `room_id`, `floor_id`, `group_by=day|room|floor`.
  - Returns reservation counts, active seat count, total available seat-slot capacity, occupied seat-slot count, and utilization rate.

- `GET /api/admin/reports/violations`
  - Admin only.
  - Query: `start_date`, `end_date`, optional `status`.
  - Returns counts by status and reason.

## Reservation Timeout Release Strategy

No background worker should be introduced for the initial version. Use lazy release with a small explicit admin endpoint.

Rules:

- New reservations start as `pending_checkin`.
- `expires_at` is computed as the earlier of:
  - slot start time plus a configured check-in grace period, default 15 minutes
  - slot end time
- `release_expired_reservations(now)` updates reservations from `pending_checkin` to `released` where `expires_at < now`.
- The service calls `release_expired_reservations` before:
  - listing seat availability
  - creating a reservation
  - listing reservations
  - generating utilization reports
- Provide `POST /api/admin/reservations/release-expired` for manual admin maintenance and tests.

This strategy is deterministic, testable with stdlib tools, and avoids Celery/Redis/cron dependencies. If the project later needs production scheduling, the same service method can be called by a system cron without changing business logic.

## Reporting Aggregation

Seat utilization should be calculated from normalized entities rather than denormalized counters.

Definitions:

- Active seats: seats whose status is `available`.
- Capacity seat-slots: active seats multiplied by matching time slots and dates in the requested range.
- Occupied seat-slots: reservations with status in `pending_checkin`, `checked_in`, or `completed`.
- Released, cancelled, and no-show reservations do not count as occupied.
- Utilization rate: `occupied_seat_slots / capacity_seat_slots`, rounded to four decimal places.

Implementation notes:

- Generate date ranges in Python for small local demo ranges.
- Query reservation aggregates with `GROUP BY` based on `day`, `room`, or `floor`.
- For `group_by=day`, compute capacity as active seat count times number of slots per day.
- For room/floor grouping, join `reservations -> seats -> floors -> study_rooms`.
- Validate `start_date <= end_date` and cap report ranges to a reasonable demo limit such as 90 days.

## Frontend Design

Shared frontend approach:

- Static HTML shell per surface.
- Plain JavaScript page modules.
- Shared `api.js` wrapper for `fetch`, JSON parsing, auth token storage, and error display.
- Client-side form validation for required fields, date formats, password length, pagination bounds, and admin status fields.
- Server remains the source of truth for all authorization and conflict checks.

User miniapp pages:

- Login/register view.
- Room list with pagination.
- Floor and seat availability view with date and time slot filters.
- Reservation form and reservation history list.
- Violation report form and submitted report list.

Admin pages:

- Login view.
- Dashboard with summary counts.
- Room/floor/seat CRUD forms and paginated lists.
- Reservation list with filters and manual release action.
- Violation report review queue with approve/reject form.
- Utilization report filters and table output.

The "miniapp" implementation is a responsive static web approximation, not a platform-specific WeChat/Alipay package. This keeps the initial repo simple and avoids app-specific build tooling.

## Test Strategy

Use `unittest` only.

Test harness:

- Create a temporary SQLite database per test module or test case.
- Apply migrations and seed only the data needed by each test.
- Start the stdlib HTTP server on an ephemeral local port in a background thread.
- Use `urllib.request` for HTTP calls.
- Keep tests black-box at the REST boundary where practical.

Required API coverage:

- Auth:
  - register success
  - duplicate username rejection
  - login success/failure
  - token-required endpoint rejection

- Room/floor/seat management:
  - admin can create/list/update rooms, floors, and seats
  - student cannot access admin mutations
  - seat availability reflects active reservations

- Reservations:
  - create reservation success
  - double booking rejected for same seat/date/slot
  - cancelled or released reservations free the seat
  - check-in succeeds before timeout
  - expired pending reservation is released and no longer blocks availability

- Violation reports:
  - student can submit a report
  - admin can list pending reports
  - admin approval/rejection updates status and reviewer fields

- Reports:
  - utilization endpoint computes expected capacity, occupied count, and rate
  - date validation rejects invalid or reversed ranges
  - grouping by day, room, and floor returns stable shapes

Non-goals for this run:

- Browser automation tests.
- Load tests.
- Cross-origin deployment configuration beyond simple CORS headers if static pages are served from another local port.

## Risk Notes

- The stdlib HTTP server is intentionally lightweight and suitable for this demo, but not a production web server.
- SQLite write concurrency is limited. Keep transactions short and use constraints plus service-level conflict checks.
- Without a background worker, timeout release occurs on reads/writes or admin trigger. This is acceptable for the requested lightweight implementation.
- Frontend pages should stay simple and avoid a build step unless a later requirement explicitly calls for a framework.
