"""Business services for study room reservations."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend import database
from backend.security import hash_password, verify_password


class ServiceError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


class StudyRoomService:
    def __init__(self, db_path: str | Path):
        self.db_path = db_path
        with database.connect(self.db_path) as conn:
            database.initialize(conn)
            database.seed(conn)

    def register(self, username: str, password: str) -> dict[str, Any]:
        username = _require_text(username, "username")
        password = _require_text(password, "password")
        try:
            password_hash = hash_password(password)
        except ValueError as exc:
            raise ServiceError(400, str(exc)) from exc
        with database.connect(self.db_path) as conn:
            try:
                cur = conn.execute(
                    """
                    INSERT INTO users (username, password_hash, role)
                    VALUES (?, ?, 'user')
                    """,
                    (username, password_hash),
                )
                conn.commit()
            except Exception as exc:
                raise ServiceError(409, "username already exists") from exc
            return self._get_user(conn, cur.lastrowid)

    def authenticate(self, username: str, password: str) -> dict[str, Any]:
        with database.connect(self.db_path) as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE username = ?",
                (_require_text(username, "username"),),
            ).fetchone()
            if user is None or not verify_password(password, user["password_hash"]):
                raise ServiceError(401, "invalid username or password")
            return _public_user(dict(user))

    def list_floors(self, page: int, page_size: int) -> dict[str, Any]:
        return self._paginate(
            "SELECT * FROM floors ORDER BY level",
            "SELECT COUNT(*) AS count FROM floors",
            (),
            page,
            page_size,
        )

    def list_rooms(self, page: int, page_size: int, floor_id: int | None = None) -> dict[str, Any]:
        where = "WHERE r.active = 1"
        params: tuple[Any, ...] = ()
        if floor_id is not None:
            where += " AND r.floor_id = ?"
            params = (_as_int(floor_id, "floor_id"),)
        return self._paginate(
            """
            SELECT r.*, f.name AS floor_name, f.name AS floorName, f.level AS floor_level, f.level AS floorLevel
            FROM rooms r JOIN floors f ON f.id = r.floor_id
            {}
            ORDER BY f.level, r.name
            """.format(where),
            "SELECT COUNT(*) AS count FROM rooms r {}".format(where),
            params,
            page,
            page_size,
        )

    def list_seats(
        self,
        page: int,
        page_size: int,
        room_id: int | None = None,
        floor_id: int | None = None,
        status: str | None = None,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        where = "WHERE r.active = 1"
        params: list[Any] = []
        if room_id is not None:
            where += " AND s.room_id = ?"
            params.append(_as_int(room_id, "room_id"))
        if floor_id is not None:
            where += " AND r.floor_id = ?"
            params.append(_as_int(floor_id, "floor_id"))
        if status in {None, "", "available"}:
            where += " AND s.active = 1"
        elif status in {"disabled", "inactive"}:
            where += " AND s.active = 0"
        elif status == "reserved":
            where += """
              AND s.active = 1
              AND EXISTS (
                SELECT 1 FROM reservations rv
                WHERE rv.seat_id = s.id
                  AND rv.status IN ('reserved', 'checked_in')
                  AND rv.start_time <= ?
                  AND rv.end_time > ?
              )
            """
            now = _time_str(_utcnow())
            params.extend([now, now])
        else:
            raise ServiceError(400, "unsupported seat status filter")
        if keyword:
            where += " AND (s.label LIKE ? OR r.name LIKE ? OR f.name LIKE ?)"
            pattern = "%{}%".format(str(keyword).strip())
            params.extend([pattern, pattern, pattern])
        return self._paginate(
            """
            SELECT
                s.*,
                s.label AS code,
                r.id AS roomId,
                r.name AS room_name,
                r.name AS roomName,
                f.id AS floorId,
                f.name AS floor_name,
                f.name AS floorName,
                CASE WHEN s.active = 1 THEN 'available' ELSE 'inactive' END AS status,
                CASE WHEN s.active = 1 THEN 1 ELSE 0 END AS available
            FROM seats s
            JOIN rooms r ON r.id = s.room_id
            JOIN floors f ON f.id = r.floor_id
            {}
            ORDER BY f.level, r.name, s.label
            """.format(where),
            """
            SELECT COUNT(*) AS count
            FROM seats s
            JOIN rooms r ON r.id = s.room_id
            JOIN floors f ON f.id = r.floor_id
            {}
            """.format(where),
            tuple(params),
            page,
            page_size,
        )

    def create_floor(self, data: dict[str, Any]) -> dict[str, Any]:
        name = _require_text(data.get("name"), "name")
        level = _as_int(data.get("level"), "level")
        with database.connect(self.db_path) as conn:
            try:
                cur = conn.execute("INSERT INTO floors (name, level) VALUES (?, ?)", (name, level))
                conn.commit()
            except Exception as exc:
                raise ServiceError(409, "floor level already exists") from exc
            return dict(conn.execute("SELECT * FROM floors WHERE id = ?", (cur.lastrowid,)).fetchone())

    def update_floor(self, floor_id: int, data: dict[str, Any]) -> dict[str, Any]:
        updates, params = _updates(data, {"name": str, "level": int})
        if not updates:
            raise ServiceError(400, "no floor fields to update")
        params.append(_as_int(floor_id, "floor_id"))
        with database.connect(self.db_path) as conn:
            conn.execute("UPDATE floors SET {} WHERE id = ?".format(", ".join(updates)), params)
            conn.commit()
            return self._require_row(conn, "SELECT * FROM floors WHERE id = ?", (floor_id,), "floor not found")

    def create_room(self, data: dict[str, Any]) -> dict[str, Any]:
        floor_id = _as_int(data.get("floor_id"), "floor_id")
        name = _require_text(data.get("name"), "name")
        open_time = data.get("open_time", "08:00")
        close_time = data.get("close_time", "22:00")
        with database.connect(self.db_path) as conn:
            self._require_row(conn, "SELECT * FROM floors WHERE id = ?", (floor_id,), "floor not found")
            try:
                cur = conn.execute(
                    """
                    INSERT INTO rooms (floor_id, name, open_time, close_time, capacity)
                    VALUES (?, ?, ?, ?, 0)
                    """,
                    (floor_id, name, open_time, close_time),
                )
                conn.commit()
            except Exception as exc:
                raise ServiceError(409, "room already exists on this floor") from exc
            return self._room(conn, cur.lastrowid)

    def update_room(self, room_id: int, data: dict[str, Any]) -> dict[str, Any]:
        updates, params = _updates(
            data,
            {"floor_id": int, "name": str, "open_time": str, "close_time": str, "active": int},
        )
        if not updates:
            raise ServiceError(400, "no room fields to update")
        params.append(_as_int(room_id, "room_id"))
        with database.connect(self.db_path) as conn:
            conn.execute("UPDATE rooms SET {} WHERE id = ?".format(", ".join(updates)), params)
            conn.commit()
            return self._room(conn, room_id)

    def deactivate_room(self, room_id: int) -> dict[str, Any]:
        with database.connect(self.db_path) as conn:
            conn.execute("UPDATE rooms SET active = 0 WHERE id = ?", (_as_int(room_id, "room_id"),))
            conn.commit()
            return self._room(conn, room_id)

    def create_seat(self, data: dict[str, Any]) -> dict[str, Any]:
        room_id = _as_int(data.get("room_id"), "room_id")
        label = _require_text(data.get("label"), "label")
        seat_type = _require_text(data.get("seat_type", "standard"), "seat_type")
        has_power = 1 if bool(data.get("has_power", True)) else 0
        active = 1 if data.get("active", 1) else 0
        with database.connect(self.db_path) as conn:
            self._require_row(conn, "SELECT * FROM rooms WHERE id = ?", (room_id,), "room not found")
            try:
                cur = conn.execute(
                    """
                    INSERT INTO seats (room_id, label, seat_type, has_power, active)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (room_id, label, seat_type, has_power, active),
                )
                if active:
                    conn.execute("UPDATE rooms SET capacity = capacity + 1 WHERE id = ?", (room_id,))
                conn.commit()
            except Exception as exc:
                raise ServiceError(409, "seat already exists in this room") from exc
            return self._seat(conn, cur.lastrowid)

    def update_seat(self, seat_id: int, data: dict[str, Any]) -> dict[str, Any]:
        updates, params = _updates(
            data,
            {"room_id": int, "label": str, "seat_type": str, "has_power": int, "active": int},
        )
        if not updates:
            raise ServiceError(400, "no seat fields to update")
        params.append(_as_int(seat_id, "seat_id"))
        with database.connect(self.db_path) as conn:
            conn.execute("UPDATE seats SET {} WHERE id = ?".format(", ".join(updates)), params)
            conn.commit()
            return self._seat(conn, seat_id)

    def deactivate_seat(self, seat_id: int) -> dict[str, Any]:
        with database.connect(self.db_path) as conn:
            row = self._seat(conn, seat_id)
            conn.execute("UPDATE seats SET active = 0 WHERE id = ?", (_as_int(seat_id, "seat_id"),))
            conn.execute("UPDATE rooms SET capacity = MAX(capacity - 1, 0) WHERE id = ?", (row["room_id"],))
            conn.commit()
            return self._seat(conn, seat_id)

    def create_reservation(self, user_id: int, data: dict[str, Any]) -> dict[str, Any]:
        seat_id = _as_int(data.get("seat_id"), "seat_id")
        start_time = _parse_time(data.get("start_time"), "start_time")
        end_time = _parse_time(data.get("end_time"), "end_time")
        if end_time <= start_time:
            raise ServiceError(400, "end_time must be after start_time")
        if end_time <= _utcnow():
            raise ServiceError(400, "reservation time slot has already expired")
        with database.connect(self.db_path) as conn:
            self.auto_release_overdue(conn=conn)
            seat = conn.execute(
                """
                SELECT s.*
                FROM seats s JOIN rooms r ON r.id = s.room_id
                WHERE s.id = ? AND s.active = 1 AND r.active = 1
                """,
                (seat_id,),
            ).fetchone()
            if seat is None:
                raise ServiceError(404, "seat not found")
            conflict = conn.execute(
                """
                SELECT id FROM reservations
                WHERE seat_id = ?
                  AND status IN ('reserved', 'checked_in')
                  AND start_time < ?
                  AND end_time > ?
                LIMIT 1
                """,
                (seat_id, _time_str(end_time), _time_str(start_time)),
            ).fetchone()
            if conflict is not None:
                raise ServiceError(409, "seat is already reserved for that time")
            cur = conn.execute(
                """
                INSERT INTO reservations (user_id, seat_id, start_time, end_time, status)
                VALUES (?, ?, ?, ?, 'reserved')
                """,
                (user_id, seat_id, _time_str(start_time), _time_str(end_time)),
            )
            conn.commit()
            return self._reservation(conn, cur.lastrowid)

    def available_seats(
        self,
        page: int,
        page_size: int,
        start_value: str | None,
        end_value: str | None,
        room_id: int | None = None,
        floor_id: int | None = None,
        keyword: str | None = None,
    ) -> dict[str, Any]:
        start_time = _parse_time(start_value, "start_time")
        end_time = _parse_time(end_value, "end_time")
        if end_time <= start_time:
            raise ServiceError(400, "end_time must be after start_time")
        if end_time <= _utcnow():
            raise ServiceError(400, "reservation time slot has already expired")
        where = "WHERE s.active = 1 AND r.active = 1"
        params: list[Any] = []
        if room_id is not None:
            where += " AND s.room_id = ?"
            params.append(_as_int(room_id, "room_id"))
        if floor_id is not None:
            where += " AND r.floor_id = ?"
            params.append(_as_int(floor_id, "floor_id"))
        if keyword:
            where += " AND (s.label LIKE ? OR r.name LIKE ? OR f.name LIKE ?)"
            pattern = "%{}%".format(str(keyword).strip())
            params.extend([pattern, pattern, pattern])
        params.extend([_time_str(end_time), _time_str(start_time)])
        return self._paginate(
            """
            SELECT
                s.*,
                s.label AS code,
                r.id AS roomId,
                r.name AS room_name,
                r.name AS roomName,
                f.id AS floorId,
                f.name AS floor_name,
                f.name AS floorName,
                'available' AS status,
                1 AS available
            FROM seats s
            JOIN rooms r ON r.id = s.room_id
            JOIN floors f ON f.id = r.floor_id
            {}
              AND NOT EXISTS (
                SELECT 1 FROM reservations rv
                WHERE rv.seat_id = s.id
                  AND rv.status IN ('reserved', 'checked_in')
                  AND rv.start_time < ?
                  AND rv.end_time > ?
              )
            ORDER BY f.level, r.name, s.label
            """.format(where),
            """
            SELECT COUNT(*) AS count
            FROM seats s JOIN rooms r ON r.id = s.room_id
            {}
              AND NOT EXISTS (
                SELECT 1 FROM reservations rv
                WHERE rv.seat_id = s.id
                  AND rv.status IN ('reserved', 'checked_in')
                  AND rv.start_time < ?
                  AND rv.end_time > ?
              )
            """.format(where),
            tuple(params),
            page,
            page_size,
        )

    def list_reservations(
        self,
        user_id: int,
        role: str,
        page: int,
        page_size: int,
        active_only: bool = False,
    ) -> dict[str, Any]:
        where = ""
        params: list[Any] = []
        if role != "admin":
            where = "WHERE rv.user_id = ?"
            params.append(_as_int(user_id, "user_id"))
        if active_only:
            where += " AND" if where else "WHERE"
            where += " rv.status IN ('reserved', 'checked_in')"
        return self._paginate(
            """
            SELECT
                rv.*,
                rv.seat_id AS seatId,
                rv.start_time AS startTime,
                rv.end_time AS endTime,
                s.label AS seat_label,
                s.label AS seatCode,
                r.name AS room_name,
                r.name AS roomName
            FROM reservations rv
            JOIN seats s ON s.id = rv.seat_id
            JOIN rooms r ON r.id = s.room_id
            {}
            ORDER BY rv.start_time DESC
            """.format(where),
            "SELECT COUNT(*) AS count FROM reservations rv {}".format(where),
            tuple(params),
            page,
            page_size,
        )

    def get_reservation(self, reservation_id: int, user_id: int, role: str) -> dict[str, Any]:
        with database.connect(self.db_path) as conn:
            reservation = self._reservation(conn, reservation_id)
            if role != "admin" and reservation["user_id"] != user_id:
                raise ServiceError(403, "reservation does not belong to user")
            return reservation

    def cancel_reservation(self, reservation_id: int, user_id: int, role: str) -> dict[str, Any]:
        with database.connect(self.db_path) as conn:
            reservation = self._reservation(conn, reservation_id)
            if role != "admin" and reservation["user_id"] != user_id:
                raise ServiceError(403, "reservation does not belong to user")
            if reservation["status"] not in {"reserved", "checked_in"}:
                raise ServiceError(409, "reservation cannot be cancelled")
            conn.execute(
                """
                UPDATE reservations
                SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (_as_int(reservation_id, "reservation_id"),),
            )
            conn.commit()
            return self._reservation(conn, reservation_id)

    def check_in(self, reservation_id: int, user_id: int, role: str) -> dict[str, Any]:
        now = _utcnow()
        with database.connect(self.db_path) as conn:
            self.auto_release_overdue(conn=conn, now=now)
            reservation = self._reservation(conn, reservation_id)
            if role != "admin" and reservation["user_id"] != user_id:
                raise ServiceError(403, "reservation does not belong to user")
            if reservation["status"] != "reserved":
                raise ServiceError(409, "reservation is not available for check-in")
            start_time = _parse_time(reservation["start_time"], "start_time")
            end_time = _parse_time(reservation["end_time"], "end_time")
            if now > start_time + timedelta(minutes=15) or now >= end_time:
                raise ServiceError(409, "reservation check-in window has closed")
            conn.execute(
                """
                UPDATE reservations
                SET status = 'checked_in', checked_in_at = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (_time_str(now), reservation_id),
            )
            conn.commit()
            return self._reservation(conn, reservation_id)

    def auto_release_overdue(
        self,
        grace_minutes: int = 15,
        conn: Any | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        owns_conn = conn is None
        active_conn = database.connect(self.db_path) if conn is None else conn
        try:
            cutoff = (now or _utcnow()) - timedelta(minutes=grace_minutes)
            rows = active_conn.execute(
                """
                SELECT id FROM reservations
                WHERE status = 'reserved' AND start_time < ?
                """,
                (_time_str(cutoff),),
            ).fetchall()
            ids = [row["id"] for row in rows]
            if ids:
                active_conn.executemany(
                    """
                    UPDATE reservations
                    SET status = 'released', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    [(reservation_id,) for reservation_id in ids],
                )
            if owns_conn:
                active_conn.commit()
            return {"released": len(ids), "reservation_ids": ids}
        finally:
            if owns_conn:
                active_conn.close()

    def create_report(self, reporter_id: int, data: dict[str, Any]) -> dict[str, Any]:
        reservation_id = data.get("reservation_id")
        seat_id = data.get("seat_id")
        reason = _require_text(data.get("reason"), "reason")
        details = str(data.get("details", ""))
        if reservation_id is None and seat_id is None:
            raise ServiceError(400, "reservation_id or seat_id is required")
        reservation_id = None if reservation_id is None else _as_int(reservation_id, "reservation_id")
        seat_id = None if seat_id is None else _as_int(seat_id, "seat_id")
        with database.connect(self.db_path) as conn:
            if reservation_id is not None:
                reservation = self._reservation(conn, reservation_id)
                if seat_id is not None and reservation["seat_id"] != seat_id:
                    raise ServiceError(400, "reservation_id and seat_id do not match")
                seat_id = reservation["seat_id"]
            if seat_id is not None:
                self._seat(conn, seat_id)
            cur = conn.execute(
                """
                INSERT INTO violation_reports
                    (reporter_id, reservation_id, seat_id, reason, details, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                """,
                (reporter_id, reservation_id, seat_id, reason, details),
            )
            conn.commit()
            return self._report(conn, cur.lastrowid)

    def list_user_reports(self, reporter_id: int, page: int, page_size: int) -> dict[str, Any]:
        return self._paginate(
            """
            SELECT
                vr.*,
                vr.seat_id AS seatId,
                vr.reason AS type,
                vr.details AS description,
                s.label AS seatCode
            FROM violation_reports vr
            LEFT JOIN seats s ON s.id = vr.seat_id
            WHERE vr.reporter_id = ?
            ORDER BY vr.created_at DESC, vr.id DESC
            """,
            "SELECT COUNT(*) AS count FROM violation_reports vr WHERE vr.reporter_id = ?",
            (_as_int(reporter_id, "reporter_id"),),
            page,
            page_size,
        )

    def get_report(self, report_id: int, user_id: int, role: str) -> dict[str, Any]:
        with database.connect(self.db_path) as conn:
            report = self._report(conn, report_id)
            if role != "admin" and report["reporter_id"] != user_id:
                raise ServiceError(403, "report does not belong to user")
            return report

    def list_reports(self, page: int, page_size: int, status: str | None = None) -> dict[str, Any]:
        where = ""
        params: tuple[Any, ...] = ()
        if status:
            where = "WHERE vr.status = ?"
            params = (status,)
        return self._paginate(
            """
            SELECT
                vr.*,
                vr.seat_id AS seatId,
                vr.reason AS type,
                vr.details AS description,
                s.label AS seatCode,
                u.username AS reporter_username,
                u.username AS reporterUsername
            FROM violation_reports vr
            JOIN users u ON u.id = vr.reporter_id
            LEFT JOIN seats s ON s.id = vr.seat_id
            {}
            ORDER BY vr.created_at DESC, vr.id DESC
            """.format(where),
            "SELECT COUNT(*) AS count FROM violation_reports vr {}".format(where),
            params,
            page,
            page_size,
        )

    def review_report(self, report_id: int, reviewer_id: int, data: dict[str, Any]) -> dict[str, Any]:
        status = data.get("status")
        if status not in {"approved", "rejected"}:
            raise ServiceError(400, "status must be approved or rejected")
        admin_note = str(data.get("admin_note", ""))
        with database.connect(self.db_path) as conn:
            report = self._report(conn, report_id)
            if report["status"] != "pending":
                raise ServiceError(409, "report has already been reviewed")
            conn.execute(
                """
                UPDATE violation_reports
                SET status = ?, admin_note = ?, reviewed_by = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (status, admin_note, reviewer_id, report_id),
            )
            conn.commit()
            return self._report(conn, report_id)

    def utilization(self, start_value: str | None, end_value: str | None) -> dict[str, Any]:
        end_time = _parse_time(end_value, "to") if end_value else _utcnow()
        start_time = _parse_time(start_value, "from") if start_value else end_time - timedelta(days=7)
        if end_time <= start_time:
            raise ServiceError(400, "to must be after from")
        total_minutes = int((end_time - start_time).total_seconds() // 60)
        with database.connect(self.db_path) as conn:
            rooms = conn.execute(
                """
                SELECT r.id, r.name, COUNT(s.id) AS seats
                FROM rooms r
                LEFT JOIN seats s ON s.room_id = r.id AND s.active = 1
                WHERE r.active = 1
                GROUP BY r.id
                ORDER BY r.id
                """
            ).fetchall()
            room_stats = []
            total_capacity = 0
            total_reserved = 0
            for room in rooms:
                reserved = self._reserved_minutes_for_room(conn, room["id"], start_time, end_time)
                capacity = int(room["seats"]) * total_minutes
                total_capacity += capacity
                total_reserved += reserved
                room_stats.append(
                    {
                        "room_id": room["id"],
                        "room_name": room["name"],
                        "seats": room["seats"],
                        "reserved_minutes": reserved,
                        "reservedMinutes": reserved,
                        "capacity_minutes": capacity,
                        "capacityMinutes": capacity,
                        "utilization_rate": _rate(reserved, capacity),
                        "utilizationRate": round(_rate(reserved, capacity) * 100, 2),
                        "roomName": room["name"],
                    }
                )
            return {
                "from": _time_str(start_time),
                "to": _time_str(end_time),
                "reserved_minutes": total_reserved,
                "reservedMinutes": total_reserved,
                "capacity_minutes": total_capacity,
                "capacityMinutes": total_capacity,
                "utilization_rate": _rate(total_reserved, total_capacity),
                "utilizationRate": round(_rate(total_reserved, total_capacity) * 100, 2),
                "totalSeats": sum(int(room["seats"]) for room in rooms),
                "reservedSeats": total_reserved,
                "rooms": room_stats,
            }

    def _paginate(
        self,
        query: str,
        count_query: str,
        params: tuple[Any, ...],
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        page = max(_as_int(page, "page"), 1)
        page_size = min(max(_as_int(page_size, "page_size"), 1), 100)
        offset = (page - 1) * page_size
        with database.connect(self.db_path) as conn:
            total = conn.execute(count_query, params).fetchone()["count"]
            rows = conn.execute(query + " LIMIT ? OFFSET ?", params + (page_size, offset)).fetchall()
            return {
                "items": [dict(row) for row in rows],
                "page": page,
                "page_size": page_size,
                "pageSize": page_size,
                "total": total,
                "hasNext": page * page_size < total,
            }

    def _reserved_minutes_for_room(
        self,
        conn: Any,
        room_id: int,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        rows = conn.execute(
            """
            SELECT rv.start_time, rv.end_time
            FROM reservations rv
            JOIN seats s ON s.id = rv.seat_id
            WHERE s.room_id = ?
              AND rv.status IN ('reserved', 'checked_in', 'completed')
              AND rv.start_time < ?
              AND rv.end_time > ?
            """,
            (room_id, _time_str(end_time), _time_str(start_time)),
        ).fetchall()
        minutes = 0
        for row in rows:
            overlap_start = max(start_time, _parse_time(row["start_time"], "start_time"))
            overlap_end = min(end_time, _parse_time(row["end_time"], "end_time"))
            minutes += max(int((overlap_end - overlap_start).total_seconds() // 60), 0)
        return minutes

    def _get_user(self, conn: Any, user_id: int) -> dict[str, Any]:
        user = self._require_row(conn, "SELECT * FROM users WHERE id = ?", (user_id,), "user not found")
        return _public_user(user)

    def _room(self, conn: Any, room_id: int) -> dict[str, Any]:
        return self._require_row(conn, "SELECT * FROM rooms WHERE id = ?", (room_id,), "room not found")

    def _seat(self, conn: Any, seat_id: int) -> dict[str, Any]:
        return self._require_row(conn, "SELECT * FROM seats WHERE id = ?", (seat_id,), "seat not found")

    def _reservation(self, conn: Any, reservation_id: int) -> dict[str, Any]:
        return self._require_row(
            conn,
            "SELECT * FROM reservations WHERE id = ?",
            (_as_int(reservation_id, "reservation_id"),),
            "reservation not found",
        )

    def _report(self, conn: Any, report_id: int) -> dict[str, Any]:
        return self._require_row(
            conn,
            "SELECT * FROM violation_reports WHERE id = ?",
            (_as_int(report_id, "report_id"),),
            "report not found",
        )

    def _require_row(self, conn: Any, query: str, params: tuple[Any, ...], message: str) -> dict[str, Any]:
        row = conn.execute(query, params).fetchone()
        if row is None:
            raise ServiceError(404, message)
        return dict(row)


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "created_at": user["created_at"],
    }


def _updates(data: dict[str, Any], allowed: dict[str, type]) -> tuple[list[str], list[Any]]:
    updates = []
    params: list[Any] = []
    for field, field_type in allowed.items():
        if field in data:
            value = data[field]
            if field_type is int:
                value = 1 if isinstance(value, bool) and value else _as_int(value, field)
            elif field_type is str:
                value = _require_text(value, field)
            updates.append("{} = ?".format(field))
            params.append(value)
    return updates, params


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ServiceError(400, "{} is required".format(field))
    return value.strip()


def _as_int(value: Any, field: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ServiceError(400, "{} must be an integer".format(field)) from exc


def _parse_time(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ServiceError(400, "{} is required".format(field))
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ServiceError(400, "{} must be an ISO timestamp".format(field)) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _time_str(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0
