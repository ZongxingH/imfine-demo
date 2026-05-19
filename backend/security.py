"""Password hashing and signed token helpers using only the standard library."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any


_PBKDF2_ROUNDS = 200_000


def hash_password(password: str) -> str:
    if len(password) < 6:
        raise ValueError("password must be at least 6 characters")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ROUNDS)
    return "pbkdf2_sha256${}${}${}".format(
        _PBKDF2_ROUNDS,
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode(),
    )


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, rounds, salt_b64, digest_b64 = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_token(
    user: dict[str, Any],
    secret: bytes | str,
    expires_in: int = 24 * 60 * 60,
) -> str:
    secret_bytes = _secret_bytes(secret)
    payload = {
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"],
        "exp": int(time.time()) + expires_in,
        "nonce": secrets.token_hex(8),
    }
    payload_b64 = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _sign(payload_b64.encode(), secret_bytes)
    return "{}.{}".format(payload_b64, signature)


def verify_token(token: str, secret: bytes | str) -> dict[str, Any] | None:
    secret_bytes = _secret_bytes(secret)
    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError:
        return None
    expected = _sign(payload_b64.encode(), secret_bytes)
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = json.loads(_b64decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def default_secret() -> str:
    return os.environ.get("STUDY_ROOM_TOKEN_SECRET", "dev-study-room-secret")


def _secret_bytes(secret: bytes | str) -> bytes:
    return secret if isinstance(secret, bytes) else secret.encode()


def _sign(data: bytes, secret: bytes) -> str:
    return _b64encode(hmac.new(secret, data, hashlib.sha256).digest())


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode())

