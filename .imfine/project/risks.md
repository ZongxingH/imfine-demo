# Risks

Status: updated after implementation.

Known residual risks:

- API tests bind an ephemeral localhost port; sandboxed environments may require permission to run them.
- No browser automation or visual regression tests are present for the static frontends.
- Reservation conflict prevention is covered sequentially; high-concurrency double-booking stress tests are not implemented.
- The default admin credentials are for local/demo use and must be changed before any real deployment.

Evidence: `tests/test_api.py`, `.imfine/runs/20260519-从零搭建一个校园自习室预约管理系统-包含用户端注册登录-自习室楼层与座位管理-座位分时预约-预约/review/recheck-report.md`, `README.md`.
