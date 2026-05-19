# Product

Status: updated after implementation.

Product domain: campus study room reservation management.

Primary users:

- Students: register/login, browse study rooms and seats, reserve time slots, check in, cancel active reservations, and submit violation reports.
- Administrators: manage floors, rooms, and seats; review violation reports; view utilization statistics.
- System process: releases overdue reservations when auto-release is triggered or reservation services run lazy cleanup.

Explicitly out of scope for this version: payment, IoT seat sensors, QR/GPS/human-face verification, push notifications, blacklists, multi-campus support, realtime WebSocket maps, and complex BI.

Evidence: `.imfine/runs/20260519-从零搭建一个校园自习室预约管理系统-包含用户端注册登录-自习室楼层与座位管理-座位分时预约-预约/product/product-plan.md`, `README.md`, `frontend/`, `backend/`.
