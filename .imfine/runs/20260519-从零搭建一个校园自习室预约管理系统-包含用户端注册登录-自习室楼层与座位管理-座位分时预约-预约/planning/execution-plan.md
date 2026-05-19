# Execution Plan

## Scope

Build a lightweight front/back separated campus study room reservation system from an empty repo.

- Backend: Python stdlib `http.server`, `sqlite3`, `unittest`.
- Frontend: static user mini-program-style pages plus admin pages using HTML/CSS/JS.
- Excluded: heavy third-party middleware, package-manager-only workflows, speculative features.

## Success Criteria

- Users can register, log in, browse floors/seats, reserve time slots, see active bookings, and report seat occupation violations.
- Admins can manage rooms/floors/seats, review reports, and view seat usage statistics.
- Expired or timed-out reservations can be released by backend logic.
- SQLite schema includes complete entities and relationships.
- REST endpoints have backend unit tests.
- Frontend pages include basic layout, form validation, and paginated lists.
- QA, Reviewer, Technical Writer, Project Knowledge Updater, Committer, and Archive gates complete separately.

## Flow

1. `T01` Architect creates skeleton and API contract.
   - Verify: directories and `docs/api.md` exist.
2. `T02` and `T03` Backend implement SQLite and REST API.
   - Verify: API supports required domain workflows.
3. `T04` Backend tests all endpoints.
   - Verify: `python3 -m unittest discover -s backend/tests` passes.
4. `T05` User frontend and `T06` Admin frontend run in parallel from the API contract.
   - Verify: required pages, validation, and pagination exist.
5. `T07` Integration wires frontend to backend.
   - Verify: documented local smoke flow works.
6. `T08` QA gate runs unit tests and manual smoke.
7. `T09` Reviewer gate checks correctness, security, data integrity, and test coverage.
8. `T10` Technical Writer gate updates README/API docs.
9. `T11` Project Knowledge Updater records architecture and commands.
10. `T12` Committer stages intended files and commits.
11. `T13` Archive records final evidence and status.

## Rework Rules

- QA failure returns to the owning dev task, then reruns QA.
- Reviewer blocker returns to the owning dev task, then reruns QA and Reviewer.
- Documentation gap returns to Technical Writer before Knowledge, Committer, or Archive.
