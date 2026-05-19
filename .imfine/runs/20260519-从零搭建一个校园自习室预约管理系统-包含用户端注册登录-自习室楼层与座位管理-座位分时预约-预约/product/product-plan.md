# Product Plan: Campus Study Room Reservation System

## Source Alignment

This plan is scoped to the run request: build a campus study room reservation management system from scratch with user registration/login, study room floor and seat management, time-slot seat reservations, timeout auto release, violation reports, admin review, occupancy reports, REST backend, mini-program-style user pages, admin pages, complete database design, API unit tests, frontend form validation, list pagination, layered architecture, and no unnecessary heavyweight middleware.

## Product Assumptions

- The first release serves a single campus or school tenant. Multi-campus tenancy is out of scope.
- "Timeout auto release" means a reserved seat is released when the user does not confirm use within a configurable grace period after the reservation start time.
- User-side pages are mini-program-style web pages or components, not a native mini-program SDK integration unless a later technical plan chooses one.
- Admin pages are internal management pages for school staff, not a public self-service portal.
- Reports are operational summaries and review lists. Advanced BI, chart drill-down, and export workflows are not required for the first release.

## Personas

### Student User

Students need to register or log in, browse available study rooms and seats by floor, reserve an available seat for a time slot, view or cancel their reservations, confirm use when they arrive, and report improper seat occupation.

### Room Administrator

Room administrators maintain floor, room, and seat data, monitor reservation and occupancy status, review violation reports, and keep seat availability accurate.

### System Operator

System operators need the system to release timed-out reservations automatically, keep reservation status consistent, and expose reliable REST APIs with unit test coverage.

## Roles and Permissions

| Role | Permissions |
| --- | --- |
| Guest | Register, log in, view public entry pages only. |
| Student User | View floors/rooms/seats, query available time slots, create/cancel own reservations, view own reservation history, confirm use for own reservations, submit violation reports, view own report status. |
| Admin | Manage floors, rooms, seats, and time-slot availability; view all reservations; review violation reports; view occupancy reports; paginate and filter management lists. |
| System Job | Auto-release timed-out reservations and update related seat availability/status records. |

Permission boundaries:

- Student users cannot modify room, floor, seat, reservation rule, report review, or statistics data directly.
- Admins can review reports but should not edit a student's password or impersonate users in the first release.
- System jobs only mutate reservation and seat availability state required for timeout release.

## Core Workflows

### 1. User Registration and Login

1. Guest opens the user-side entry page.
2. Guest registers with required account fields and valid credentials.
3. System validates required fields, uniqueness, and password format.
4. User logs in and receives an authenticated session or token.
5. Authenticated requests use the session/token to access reservation features.

Acceptance criteria:

- Registration rejects missing fields, duplicate account identifiers, and invalid password formats.
- Login rejects invalid credentials and returns a clear error response.
- Protected REST APIs reject unauthenticated requests.
- User-side forms show validation feedback before submission where practical.

### 2. Browse Floors, Rooms, Seats, and Time Slots

1. Student opens the reservation page.
2. Student selects a floor and study room.
3. System lists seats with availability by selected date and time slot.
4. Student can filter or paginate lists where the result set is large.

Acceptance criteria:

- Floors, rooms, seats, and time slots come from persisted database entities.
- Seat status distinguishes at least available, reserved, unavailable/disabled, and in use where applicable.
- Seat lists and admin management lists support pagination.
- Disabled seats cannot be reserved.

### 3. Time-Slot Seat Reservation

1. Student selects an available seat and time slot.
2. System validates that the seat is active and available for the selected slot.
3. System creates a reservation and marks the seat/slot as reserved.
4. Student can view the reservation in their reservation list.
5. Student can cancel a future reservation when cancellation is allowed.

Acceptance criteria:

- The same seat cannot be double-booked for overlapping time slots.
- A user cannot create duplicate active reservations for the same seat and time slot.
- Reservation creation, cancellation, query, and detail APIs have unit tests.
- Invalid seat IDs, invalid time slots, expired slots, and conflicts return predictable error responses.

### 4. Timeout Auto Release

1. Reservation reaches its start time.
2. User must confirm use within the configured grace period.
3. If no confirmation is recorded before timeout, the system marks the reservation as timed out or released.
4. The seat/slot becomes available again for valid remaining reservation rules, if applicable.

Acceptance criteria:

- Timeout release is deterministic and can be triggered by a scheduled job or service method.
- Released reservations are no longer counted as active reservations.
- Timeout transitions are covered by backend unit tests.
- Timeout behavior does not require heavy external middleware.

### 5. Violation Report Submission

1. Student finds a seat occupied in violation of the reservation rules.
2. Student submits a report with seat, room, reservation/time context, reason, and optional description.
3. System validates required fields and records the report as pending review.
4. Student can view the report status.

Acceptance criteria:

- Reports require a valid seat and time context.
- Report statuses include at least pending, approved, and rejected.
- Students can only view their own submitted reports.
- Report submission API and validation cases have unit tests.

### 6. Admin Report Review

1. Admin opens the violation report list.
2. Admin filters and paginates pending/reviewed reports.
3. Admin reviews report details and chooses approve or reject with review remarks.
4. System records reviewer, review result, review time, and final status.

Acceptance criteria:

- Only admins can review reports.
- Reviewed reports cannot be reviewed again unless explicitly reopened; reopening is out of scope for first release.
- Admin review actions are persisted and visible in report detail.
- Review list pages include pagination and basic filters.

### 7. Room, Floor, and Seat Management

1. Admin creates or updates floors.
2. Admin creates or updates study rooms under floors.
3. Admin creates, updates, disables, or enables seats under rooms.
4. Changes affect future availability and management views.

Acceptance criteria:

- Database design includes floor, room, and seat entities with clear relationships.
- Seat codes/names are unique within a room.
- Disabled seats are hidden from normal reservation availability or shown as unavailable.
- Admin create/update/list/detail APIs have unit tests.

### 8. Occupancy Reports

1. Admin opens occupancy report pages.
2. Admin selects date range, floor, room, or seat filters.
3. System returns seat usage metrics based on reservation and usage status.
4. Admin views paginated or summarized results in the management UI.

Acceptance criteria:

- Reports include at least reservations count, completed/in-use count, timeout count, and occupancy/use rate by room or seat.
- Report calculations are based on persisted reservation records.
- Report APIs handle empty ranges and invalid date ranges consistently.
- Advanced export, custom dashboards, and predictive analytics are out of scope.

## Data Scope

The database design should include complete entities and relationships for:

- Users and roles.
- Floors.
- Study rooms.
- Seats.
- Time slots or reservation periods.
- Reservations with status history fields sufficient for created, confirmed/in use, canceled, completed, and timed-out/released states.
- Violation reports and admin review metadata.
- Optional lightweight configuration for timeout grace period if needed.

Minimum relationship expectations:

- One floor has many rooms.
- One room has many seats.
- One user has many reservations and reports.
- One seat has many reservations over time.
- One report references reporter, seat, and review metadata.

## REST API Scope

The backend should expose REST endpoints for:

- Authentication: register, login, current user/session, logout if session-based.
- User reservation flow: floors, rooms, seats, available slots, create reservation, cancel reservation, confirm use, list/detail own reservations.
- Violation reports: create report, list/detail own reports.
- Admin management: floor CRUD, room CRUD, seat CRUD, reservation list/detail, report review list/detail/action, occupancy report query.

API acceptance criteria:

- All public API contracts use consistent success and error response shapes.
- All interfaces introduced for the feature set have unit tests.
- Tests cover happy paths, validation failures, permission failures, and key reservation conflict cases.
- Pagination parameters are supported on list endpoints that can grow.

## Frontend Page Scope

### Mini-Program-Style User Pages

- Register/login.
- Floor/room/seat selection.
- Seat availability by time slot.
- Reservation confirmation and result.
- My reservations.
- Violation report submission.
- My reports.

### Admin Pages

- Login or protected admin entry.
- Floor management.
- Room management.
- Seat management.
- Reservation list/detail.
- Violation report review list/detail.
- Occupancy report page.

Frontend acceptance criteria:

- Pages have basic usable layout.
- Forms validate required fields and common formats before submission.
- List pages support pagination.
- Empty, loading, and error states are represented at a basic level.
- The UI does not require advanced visualization or real-time push for the first release.

## Scope Boundaries

In scope:

- Layered front-end/back-end separation.
- Complete database schema for the requested domain.
- REST APIs and API unit tests.
- User registration/login and authorization checks.
- Reservation conflict prevention.
- Timeout auto-release logic.
- Admin CRUD and review workflows.
- Basic occupancy reporting.
- Basic page layout, validation, and pagination.

Out of scope for the first release:

- Payment, deposits, penalties, credits, or blacklists.
- QR code, Bluetooth, GPS, face recognition, or IoT seat sensors.
- Real-time websocket seat maps.
- Multi-campus tenant management.
- Mobile push notifications or SMS/email integrations.
- Advanced charting, export, or BI dashboards.
- Heavy middleware such as distributed queues, search clusters, or complex workflow engines.

## Product Risks and Decisions Needed Later

- Check-in mechanism: this plan assumes a lightweight user confirmation action. If QR or location-based check-in is required, scope and permissions must be revised.
- Reservation rules: maximum daily reservation count, cancellation deadline, and allowed booking window are not specified and should default to simple configurable constants.
- Occupancy definition: implementation should define whether occupancy rate uses confirmed usage only or all non-canceled reservations. Product preference is confirmed/completed usage for use rate and all reservations for reservation volume.
