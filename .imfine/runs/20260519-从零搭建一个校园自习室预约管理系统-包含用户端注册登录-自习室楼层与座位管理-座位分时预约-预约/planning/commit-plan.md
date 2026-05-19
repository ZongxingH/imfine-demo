# Commit Plan

## Strategy

Prefer one final feature commit after QA, review, documentation, and project knowledge gates pass. This keeps the empty-repo implementation atomic and avoids committing partial harness states.

## Pre-Commit Checks

- `python3 -m unittest discover -s backend/tests`
- Manual smoke: start backend, open user pages, register/login, reserve seat, release expired reservation, submit report.
- Manual smoke: open admin pages, manage seats, review report, inspect usage statistics.
- Review `git status --short` and stage only intended source, docs, tests, and approved imfine evidence.

## Commit Content

- `backend/`: stdlib HTTP API, SQLite schema/data access, services, tests.
- `frontend/`: static user and admin pages, shared API helper, styles/scripts.
- `docs/` and `README.md`: setup, run, API, data model, and smoke instructions.
- `.imfine/project/` and run evidence only after gate agents approve those updates.

## Commit Message

```text
Implement campus study room reservation system
```

## Gate Order

1. QA gate passes.
2. Reviewer gate passes with no blockers.
3. Technical Writer gate confirms docs.
4. Project Knowledge Updater gate confirms project facts.
5. Committer gate creates the commit.
6. Archive gate records final evidence.
