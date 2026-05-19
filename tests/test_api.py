import json
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.api import create_handler


class ApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "test.sqlite3")
        handler = create_handler(self.db_path, token_secret="test-secret")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base_url = "http://127.0.0.1:{}".format(self.server.server_address[1])

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp_dir.cleanup()

    def request(self, method, path, body=None, token=None, query=None):
        if query:
            path = "{}?{}".format(path, urlencode(query))
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer {}".format(token)
        req = Request(self.base_url + path, data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=5) as response:
                payload = response.read().decode()
                return response.status, json.loads(payload)
        except HTTPError as exc:
            return exc.code, json.loads(exc.read().decode())

    def raw_request(self, method, path, body=None, token=None, query=None):
        if query:
            path = "{}?{}".format(path, urlencode(query))
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer {}".format(token)
        req = Request(self.base_url + path, data=data, headers=headers, method=method)
        return urlopen(req, timeout=5)

    def login_admin(self):
        status, payload = self.request(
            "POST",
            "/auth/login",
            {"username": "admin", "password": "admin123"},
        )
        self.assertEqual(status, 200)
        return payload["token"]

    def register_user(self, username="alice"):
        status, payload = self.request(
            "POST",
            "/auth/register",
            {"username": username, "password": "secret123"},
        )
        self.assertEqual(status, 201)
        return payload["token"], payload["user"]

    def first_seat_id(self):
        status, payload = self.request("GET", "/seats", query={"page_size": 1})
        self.assertEqual(status, 200)
        return payload["items"][0]["id"]

    def first_two_seat_ids(self):
        status, payload = self.request("GET", "/seats", query={"page_size": 2})
        self.assertEqual(status, 200)
        self.assertGreaterEqual(len(payload["items"]), 2)
        return payload["items"][0]["id"], payload["items"][1]["id"]

    def test_health_and_seeded_catalog_with_pagination(self):
        status, payload = self.request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

        status, payload = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload, {"status": "ok"})

        with self.raw_request("OPTIONS", "/api/floors") as response:
            self.assertEqual(response.status, 204)
            self.assertEqual(response.headers["Access-Control-Allow-Origin"], "*")

        status, floors = self.request("GET", "/floors", query={"page": 1, "page_size": 2})
        self.assertEqual(status, 200)
        self.assertEqual(floors["page_size"], 2)
        self.assertEqual(floors["pageSize"], 2)
        self.assertIn("hasNext", floors)
        self.assertGreaterEqual(floors["total"], 3)

        status, rooms = self.request("GET", "/api/rooms", query={"floorId": floors["items"][0]["id"]})
        self.assertEqual(status, 200)
        self.assertGreaterEqual(rooms["total"], 1)

        status, seats = self.request(
            "GET",
            "/api/seats",
            query={"roomId": rooms["items"][0]["id"], "pageSize": 5, "status": "available"},
        )
        self.assertEqual(status, 200)
        self.assertGreaterEqual(seats["total"], 1)
        self.assertIn("roomName", seats["items"][0])
        self.assertIn("floorName", seats["items"][0])

        status, floor_seats = self.request(
            "GET",
            "/api/seats",
            query={"floorId": floors["items"][0]["id"], "pageSize": 5},
        )
        self.assertEqual(status, 200)
        self.assertGreaterEqual(floor_seats["total"], 1)
        self.assertTrue(all(item["floorId"] == floors["items"][0]["id"] for item in floor_seats["items"]))

    def test_register_login_and_admin_authz(self):
        user_token, user = self.register_user()
        self.assertEqual(user["role"], "user")

        status, login = self.request(
            "POST",
            "/auth/login",
            {"username": "alice", "password": "secret123"},
        )
        self.assertEqual(status, 200)
        self.assertIn("token", login)

        status, payload = self.request(
            "POST",
            "/api/admin/floors",
            {"name": "Restricted", "level": 9},
            token=user_token,
        )
        self.assertEqual(status, 403)
        self.assertEqual(payload["error"], "admin role required")

    def test_admin_floor_room_seat_management(self):
        admin_token = self.login_admin()
        status, floor = self.request(
            "POST",
            "/api/admin/floors",
            {"name": "Innovation Floor", "number": 7},
            token=admin_token,
        )
        self.assertEqual(status, 201)

        status, room = self.request(
            "POST",
            "/api/admin/rooms",
            {"floorId": floor["id"], "name": "I-701 Studio"},
            token=admin_token,
        )
        self.assertEqual(status, 201)

        status, room = self.request(
            "PATCH",
            "/admin/rooms/{}".format(room["id"]),
            {"close_time": "23:00"},
            token=admin_token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(room["close_time"], "23:00")

        status, seat = self.request(
            "POST",
            "/api/admin/seats",
            {"roomId": room["id"], "code": "A01", "seat_type": "focus", "has_power": True},
            token=admin_token,
        )
        self.assertEqual(status, 201)
        self.assertEqual(seat["label"], "A01")

        status, disabled_seat = self.request(
            "POST",
            "/api/admin/seats",
            {"roomId": room["id"], "code": "A02", "status": "disabled"},
            token=admin_token,
        )
        self.assertEqual(status, 201)
        self.assertEqual(disabled_seat["active"], 0)

        status, seats = self.request(
            "GET",
            "/api/admin/seats",
            token=admin_token,
            query={"pageSize": 2, "keyword": "A01"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(seats["pageSize"], 2)
        self.assertEqual(seats["total"], 1)

        status, seat = self.request(
            "DELETE",
            "/admin/seats/{}".format(seat["id"]),
            token=admin_token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(seat["active"], 0)

    def test_reservation_conflict_check_in_and_auto_release(self):
        user_token, _ = self.register_user()
        other_token, _ = self.register_user("bob")
        seat_id, second_seat_id = self.first_two_seat_ids()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        start = now - timedelta(minutes=5)
        end = now + timedelta(minutes=55)

        status, reservation = self.request(
            "POST",
            "/api/reservations",
            {
                "seatId": seat_id,
                "startTime": start.isoformat().replace("+00:00", "Z"),
                "endTime": end.isoformat().replace("+00:00", "Z"),
            },
            token=user_token,
        )
        self.assertEqual(status, 201)
        self.assertEqual(reservation["status"], "reserved")

        status, active = self.request(
            "GET",
            "/api/reservations/active",
            token=user_token,
            query={"pageSize": 5},
        )
        self.assertEqual(status, 200)
        self.assertEqual(active["total"], 1)
        self.assertIn("startTime", active["items"][0])

        status, detail = self.request(
            "GET",
            "/api/reservations/{}".format(reservation["id"]),
            token=user_token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(detail["id"], reservation["id"])

        status, available = self.request(
            "GET",
            "/api/seats/availability",
            query={
                "startTime": start.isoformat().replace("+00:00", "Z"),
                "endTime": end.isoformat().replace("+00:00", "Z"),
                "pageSize": 100,
            },
        )
        self.assertEqual(status, 200)
        self.assertNotIn(seat_id, [item["id"] for item in available["items"]])

        status, conflict = self.request(
            "POST",
            "/reservations",
            {
                "seat_id": seat_id,
                "start_time": (now + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
                "end_time": (now + timedelta(minutes=70)).isoformat().replace("+00:00", "Z"),
            },
            token=other_token,
        )
        self.assertEqual(status, 409)
        self.assertIn("reserved", conflict["error"])

        status, checked_in = self.request(
            "POST",
            "/reservations/{}/check-in".format(reservation["id"]),
            token=user_token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(checked_in["status"], "checked_in")

        status, late = self.request(
            "POST",
            "/reservations",
            {
                "seat_id": second_seat_id,
                "start_time": (now - timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
                "end_time": (now + timedelta(minutes=30)).isoformat().replace("+00:00", "Z"),
            },
            token=other_token,
        )
        self.assertEqual(status, 201)
        self.assertEqual(late["status"], "reserved")

        status, expired = self.request(
            "POST",
            "/reservations",
            {
                "seat_id": second_seat_id,
                "start_time": (now - timedelta(hours=2)).isoformat().replace("+00:00", "Z"),
                "end_time": (now - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            },
            token=other_token,
        )
        self.assertEqual(status, 400)
        self.assertIn("expired", expired["error"])

        admin_token = self.login_admin()
        status, released = self.request(
            "POST",
            "/admin/reservations/auto-release",
            token=admin_token,
        )
        self.assertEqual(status, 200)
        self.assertIn(late["id"], released["reservation_ids"])

        status, cancelled = self.request(
            "POST",
            "/api/reservations/{}/cancel".format(reservation["id"]),
            token=user_token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(cancelled["status"], "cancelled")

        status, active = self.request(
            "GET",
            "/api/reservations/active",
            token=user_token,
            query={"pageSize": 5},
        )
        self.assertEqual(status, 200)
        self.assertEqual(active["total"], 0)

    def test_violation_report_review_and_utilization_stats(self):
        user_token, _ = self.register_user()
        admin_token = self.login_admin()
        seat_id = self.first_seat_id()

        status, report = self.request(
            "POST",
            "/api/reports",
            {"seatId": seat_id, "type": "noise", "description": "Loud phone call"},
            token=user_token,
        )
        self.assertEqual(status, 201)
        self.assertEqual(report["status"], "pending")

        status, bad_report = self.request(
            "POST",
            "/api/reports",
            {"seatId": 999999, "type": "noise", "description": "Unknown seat"},
            token=user_token,
        )
        self.assertEqual(status, 404)

        status, reports = self.request(
            "GET",
            "/admin/reports",
            token=admin_token,
            query={"status": "pending"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(reports["total"], 1)

        status, my_reports = self.request(
            "GET",
            "/api/reports",
            token=user_token,
            query={"pageSize": 5},
        )
        self.assertEqual(status, 200)
        self.assertEqual(my_reports["total"], 1)

        status, reviewed = self.request(
            "PATCH",
            "/api/admin/reports/{}".format(report["id"]),
            {"status": "approved", "admin_note": "Warned user"},
            token=admin_token,
        )
        self.assertEqual(status, 200)
        self.assertEqual(reviewed["status"], "approved")

        status, reviewed_again = self.request(
            "PATCH",
            "/api/admin/reports/{}".format(report["id"]),
            {"status": "rejected", "admin_note": "Duplicate review"},
            token=admin_token,
        )
        self.assertEqual(status, 409)

        now = datetime.now(timezone.utc).replace(microsecond=0)
        status, stats = self.request(
            "GET",
            "/api/admin/stats/utilization",
            token=admin_token,
            query={
                "from": (now - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                "to": (now + timedelta(days=1)).isoformat().replace("+00:00", "Z"),
            },
        )
        self.assertEqual(status, 200)
        self.assertIn("utilization_rate", stats)
        self.assertIn("utilizationRate", stats)
        self.assertIn("totalSeats", stats)
        self.assertGreater(len(stats["rooms"]), 0)


if __name__ == "__main__":
    unittest.main()
