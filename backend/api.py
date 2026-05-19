"""HTTP REST API layer for the study room backend."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, urlparse

from backend.security import create_token, default_secret, verify_token
from backend.services import ServiceError, StudyRoomService


def create_handler(db_path: str, token_secret: str | bytes | None = None) -> type[BaseHTTPRequestHandler]:
    service = StudyRoomService(db_path)
    secret = token_secret or default_secret()

    class StudyRoomHandler(BaseHTTPRequestHandler):
        server_version = "StudyRoomHTTP/1.0"

        def do_GET(self) -> None:
            self._dispatch("GET")

        def do_POST(self) -> None:
            self._dispatch("POST")

        def do_PATCH(self) -> None:
            self._dispatch("PATCH")

        def do_DELETE(self) -> None:
            self._dispatch("DELETE")

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self._cors_headers()
            self.end_headers()

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _dispatch(self, method: str) -> None:
            parsed = urlparse(self.path)
            path = _normalize_path(parsed.path.rstrip("/") or "/")
            query = parse_qs(parsed.query)
            try:
                response, status = self._route(method, path, query)
                self._json(status, response)
            except ServiceError as exc:
                self._json(exc.status, {"error": exc.message})
            except json.JSONDecodeError:
                self._json(400, {"error": "invalid JSON body"})
            except Exception:
                self._json(500, {"error": "internal server error"})

        def _route(
            self,
            method: str,
            path: str,
            query: dict[str, list[str]],
        ) -> tuple[dict[str, Any], int]:
            if method == "GET" and path == "/health":
                return {"status": "ok"}, 200

            if method == "POST" and path == "/auth/register":
                body = _normalize_body(self._body())
                user = service.register(body.get("username"), body.get("password"))
                return {"user": user, "token": create_token(user, secret)}, 201

            if method == "POST" and path == "/auth/login":
                body = _normalize_body(self._body())
                user = service.authenticate(body.get("username"), body.get("password"))
                return {"user": user, "token": create_token(user, secret)}, 200

            if method == "GET" and path == "/floors":
                return service.list_floors(_page(query), _page_size(query)), 200

            if method == "GET" and path == "/rooms":
                return (
                    service.list_rooms(
                        _page(query),
                        _page_size(query),
                        _query_int(query, "floor_id", "floorId"),
                    ),
                    200,
                )

            if method == "GET" and path == "/seats":
                return (
                    service.list_seats(
                        _page(query),
                        _page_size(query),
                        _query_int(query, "room_id", "roomId"),
                        _query_int(query, "floor_id", "floorId"),
                        _query_one(query, "status"),
                        _query_one(query, "keyword"),
                    ),
                    200,
                )

            if method == "GET" and path == "/seats/availability":
                return (
                    service.available_seats(
                        _page(query),
                        _page_size(query),
                        _query_one(query, "start_time", "startTime"),
                        _query_one(query, "end_time", "endTime"),
                        _query_int(query, "room_id", "roomId"),
                        _query_int(query, "floor_id", "floorId"),
                        _query_one(query, "keyword"),
                    ),
                    200,
                )

            if method == "GET" and path in {"/reservations", "/reservations/active"}:
                user = self._require_user()
                return (
                    service.list_reservations(
                        user["user_id"],
                        user["role"],
                        _page(query),
                        _page_size(query),
                        active_only=path.endswith("/active"),
                    ),
                    200,
                )

            if method == "POST" and path == "/reservations":
                user = self._require_user()
                return service.create_reservation(user["user_id"], _normalize_body(self._body())), 201

            if method == "GET" and path.startswith("/reservations/"):
                user = self._require_user()
                return service.get_reservation(_path_id(path, 1), user["user_id"], user["role"]), 200

            if method == "POST" and path.startswith("/reservations/") and path.endswith("/check-in"):
                user = self._require_user()
                reservation_id = _path_id(path, 1)
                return (
                    service.check_in(reservation_id, user["user_id"], user["role"]),
                    200,
                )

            if method == "POST" and path.startswith("/reservations/") and path.endswith("/cancel"):
                user = self._require_user()
                return service.cancel_reservation(_path_id(path, 1), user["user_id"], user["role"]), 200

            if method == "GET" and path == "/reports":
                user = self._require_user()
                return service.list_user_reports(user["user_id"], _page(query), _page_size(query)), 200

            if method == "GET" and path.startswith("/reports/"):
                user = self._require_user()
                return service.get_report(_path_id(path, 1), user["user_id"], user["role"]), 200

            if method == "POST" and path == "/reports":
                user = self._require_user()
                return service.create_report(user["user_id"], _normalize_body(self._body())), 201

            admin = None
            if path.startswith("/admin/"):
                admin = self._require_admin()

            if method == "POST" and path == "/admin/floors":
                return service.create_floor(_normalize_body(self._body())), 201
            if method == "PATCH" and path.startswith("/admin/floors/"):
                return service.update_floor(_path_id(path, 2), _normalize_body(self._body())), 200
            if method == "DELETE" and path.startswith("/admin/floors/"):
                raise ServiceError(405, "floors cannot be deleted after setup")

            if method == "POST" and path == "/admin/rooms":
                return service.create_room(_normalize_body(self._body())), 201
            if method == "PATCH" and path.startswith("/admin/rooms/"):
                return service.update_room(_path_id(path, 2), _normalize_body(self._body())), 200
            if method == "DELETE" and path.startswith("/admin/rooms/"):
                return service.deactivate_room(_path_id(path, 2)), 200

            if method == "GET" and path == "/admin/seats":
                return (
                    service.list_seats(
                        _page(query),
                        _page_size(query),
                        _query_int(query, "room_id", "roomId"),
                        _query_int(query, "floor_id", "floorId"),
                        _query_one(query, "status"),
                        _query_one(query, "keyword"),
                    ),
                    200,
                )
            if method == "POST" and path == "/admin/seats":
                return service.create_seat(_normalize_body(self._body())), 201
            if method == "PATCH" and path.startswith("/admin/seats/"):
                return service.update_seat(_path_id(path, 2), _normalize_body(self._body())), 200
            if method == "DELETE" and path.startswith("/admin/seats/"):
                return service.deactivate_seat(_path_id(path, 2)), 200

            if method == "POST" and path == "/admin/reservations/auto-release":
                grace = _query_int(query, "grace_minutes")
                return service.auto_release_overdue(grace or 15), 200

            if method == "GET" and path == "/admin/reservations":
                return service.list_reservations(admin["user_id"], admin["role"], _page(query), _page_size(query)), 200

            if method == "GET" and path.startswith("/admin/reservations/"):
                return service.get_reservation(_path_id(path, 2), admin["user_id"], admin["role"]), 200

            if method == "GET" and path == "/admin/reports":
                return (
                    service.list_reports(_page(query), _page_size(query), _status_query(query)),
                    200,
                )
            if method == "PATCH" and path.startswith("/admin/reports/"):
                return service.review_report(_path_id(path, 2), admin["user_id"], _normalize_body(self._body())), 200

            if method == "GET" and path in {"/admin/statistics/utilization", "/admin/stats/utilization"}:
                return (
                    service.utilization(_query_one(query, "from"), _query_one(query, "to")),
                    200,
                )

            raise ServiceError(404, "endpoint not found")

        def _body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0"))
            if length == 0:
                return {}
            if length > 1_000_000:
                raise ServiceError(413, "request body too large")
            data = json.loads(self.rfile.read(length).decode())
            if not isinstance(data, dict):
                raise ServiceError(400, "JSON body must be an object")
            return data

        def _require_user(self) -> dict[str, Any]:
            header = self.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                raise ServiceError(401, "missing bearer token")
            payload = verify_token(header.removeprefix("Bearer ").strip(), secret)
            if payload is None:
                raise ServiceError(401, "invalid bearer token")
            return payload

        def _require_admin(self) -> dict[str, Any]:
            user = self._require_user()
            if user.get("role") != "admin":
                raise ServiceError(403, "admin role required")
            return user

        def _json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self._cors_headers()
            self.end_headers()
            self.wfile.write(body)

        def _cors_headers(self) -> None:
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")

    return StudyRoomHandler


def _normalize_path(path: str) -> str:
    if path == "/api":
        return "/"
    if path.startswith("/api/"):
        return path[4:]
    return path


def _normalize_body(data: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "email": "username",
        "seatId": "seat_id",
        "reservationId": "reservation_id",
        "startTime": "start_time",
        "endTime": "end_time",
        "floorId": "floor_id",
        "roomId": "room_id",
        "number": "level",
        "code": "label",
        "type": "reason",
        "description": "details",
    }
    normalized = dict(data)
    for source, target in aliases.items():
        if source in normalized and target not in normalized:
            normalized[target] = normalized[source]
    if normalized.get("status") == "reviewed":
        normalized["status"] = "approved"
    if "status" in normalized and "active" not in normalized:
        if normalized["status"] in {"inactive", "maintenance", "disabled"}:
            normalized["active"] = 0
        elif normalized["status"] in {"available", "active"}:
            normalized["active"] = 1
    return normalized


def _query_one(query: dict[str, list[str]], name: str, *aliases: str) -> str | None:
    for key in (name,) + aliases:
        values = query.get(key)
        if values:
            return values[0]
    return None


def _query_int(query: dict[str, list[str]], name: str, *aliases: str) -> int | None:
    value = _query_one(query, name, *aliases)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ServiceError(400, "{} must be an integer".format(name)) from exc


def _status_query(query: dict[str, list[str]]) -> str | None:
    status = _query_one(query, "status")
    return "approved" if status == "reviewed" else status


def _page(query: dict[str, list[str]]) -> int:
    return _query_int(query, "page") or 1


def _page_size(query: dict[str, list[str]]) -> int:
    return _query_int(query, "page_size", "pageSize") or 20


def _path_id(path: str, index: int) -> int:
    parts = path.strip("/").split("/")
    try:
        return int(parts[index])
    except (IndexError, ValueError) as exc:
        raise ServiceError(404, "resource id not found") from exc
