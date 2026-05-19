"""SQLite schema and seed data for the study room reservation backend."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


def connect(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('user', 'admin')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS floors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            level INTEGER NOT NULL UNIQUE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            floor_id INTEGER NOT NULL REFERENCES floors(id) ON DELETE CASCADE,
            name TEXT NOT NULL,
            capacity INTEGER NOT NULL DEFAULT 0,
            open_time TEXT NOT NULL DEFAULT '08:00',
            close_time TEXT NOT NULL DEFAULT '22:00',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (floor_id, name)
        );

        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id INTEGER NOT NULL REFERENCES rooms(id) ON DELETE CASCADE,
            label TEXT NOT NULL,
            seat_type TEXT NOT NULL DEFAULT 'standard',
            has_power INTEGER NOT NULL DEFAULT 1,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (room_id, label)
        );

        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            seat_id INTEGER NOT NULL REFERENCES seats(id) ON DELETE CASCADE,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL CHECK (
                status IN ('reserved', 'checked_in', 'completed', 'cancelled', 'released')
            ),
            checked_in_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_reservations_seat_time
            ON reservations(seat_id, start_time, end_time, status);

        CREATE TABLE IF NOT EXISTS violation_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            reservation_id INTEGER REFERENCES reservations(id) ON DELETE SET NULL,
            seat_id INTEGER REFERENCES seats(id) ON DELETE SET NULL,
            reason TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected')),
            admin_note TEXT NOT NULL DEFAULT '',
            reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reviewed_at TEXT
        );
        """
    )
    conn.commit()


def seed(conn: sqlite3.Connection) -> None:
    from backend.security import hash_password

    if conn.execute("SELECT 1 FROM users WHERE username = 'admin'").fetchone() is None:
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
            ("admin", hash_password("admin123")),
        )

    if conn.execute("SELECT COUNT(*) AS count FROM floors").fetchone()["count"] == 0:
        floors = [("Ground Floor", 1), ("Quiet Study Floor", 2), ("Graduate Commons", 3)]
        conn.executemany("INSERT INTO floors (name, level) VALUES (?, ?)", floors)

        rooms = [
            (1, "G-101 Open Study", "08:00", "22:00", 8),
            (1, "G-102 Group Room", "09:00", "21:00", 6),
            (2, "Q-201 Silent Room", "07:30", "23:00", 10),
            (3, "C-301 Research Room", "08:00", "20:00", 4),
        ]
        conn.executemany(
            """
            INSERT INTO rooms (floor_id, name, open_time, close_time, capacity)
            VALUES (?, ?, ?, ?, ?)
            """,
            rooms,
        )

        for room in conn.execute("SELECT id, capacity FROM rooms").fetchall():
            seats = []
            for index in range(1, room["capacity"] + 1):
                seats.append(
                    (
                        room["id"],
                        "S{:02d}".format(index),
                        "window" if index in (1, 2) else "standard",
                        1 if index % 3 != 0 else 0,
                    )
                )
            conn.executemany(
                """
                INSERT INTO seats (room_id, label, seat_type, has_power)
                VALUES (?, ?, ?, ?)
                """,
                seats,
            )
    conn.commit()


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return None if row is None else dict(row)
