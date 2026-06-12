"""
api/auth.py
────────────
Self-contained authentication for the local API — stdlib only, no services.

Design
──────
- **Users** live in ``data/users.json``: username → PBKDF2-HMAC-SHA256 hash
  (260k iterations, per-user random salt). Created via ``job-sentinel users
  add`` — the first user must be an admin; only admins may create accounts.
- **Tokens** are HMAC-SHA256-signed values ``username:expiry:signature`` keyed
  by ``AUTH_SECRET`` (auto-generated into ``data/auth_secret`` on first use).
  Stateless: no token table, restarting the API keeps sessions alive.
- **Modes** via ``AUTH_MODE`` env:
    off       — no auth at all (default; single-user laptop setup)
    demo      — GET endpoints are public, mutating endpoints need a login
    required  — every /api request needs a login

Threat model: this protects a small self-hosted deployment shared with a few
invited users. It is intentionally not OAuth — no third-party dependency, no
cost, nothing to expire. If the project ever grows real multi-tenancy, swap
this module for an identity provider behind the same FastAPI dependency.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from pathlib import Path

_PBKDF2_ITERATIONS = 260_000
_TOKEN_TTL_SECONDS = 7 * 24 * 3600  # one week

AuthMode = Literal["off", "demo", "required"]


class User(BaseModel):
    username: str
    is_admin: bool = False


class AuthError(ValueError):
    """Bad credentials, unknown user, or malformed token."""


# ─────────────────────────────────────────────────────────────────────────────
# Password hashing
# ─────────────────────────────────────────────────────────────────────────────


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"pbkdf2${_PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _scheme, iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, AttributeError):
        return False


# ─────────────────────────────────────────────────────────────────────────────
# User store (data/users.json)
# ─────────────────────────────────────────────────────────────────────────────


class UserStore:
    """Tiny JSON-file user database with atomic writes."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def _load(self) -> dict[str, dict[str, object]]:
        if not self._path.is_file():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]

    def _save(self, users: dict[str, dict[str, object]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(users, indent=2), encoding="utf-8")
        tmp.replace(self._path)

    def list_users(self) -> list[User]:
        return [
            User(username=name, is_admin=bool(rec.get("is_admin", False)))
            for name, rec in sorted(self._load().items())
        ]

    def add_user(self, username: str, password: str, *, is_admin: bool = False) -> User:
        username = username.strip().lower()
        if not username or not password:
            msg = "Username and password are required."
            raise AuthError(msg)
        users = self._load()
        if username in users:
            msg = f"User {username!r} already exists."
            raise AuthError(msg)
        if not users and not is_admin:
            msg = "The first account must be an admin (pass --admin)."
            raise AuthError(msg)
        users[username] = {"password": hash_password(password), "is_admin": is_admin}
        self._save(users)
        return User(username=username, is_admin=is_admin)

    def remove_user(self, username: str) -> bool:
        users = self._load()
        if users.pop(username.strip().lower(), None) is None:
            return False
        self._save(users)
        return True

    def authenticate(self, username: str, password: str) -> User:
        rec = self._load().get(username.strip().lower())
        if rec is None or not verify_password(password, str(rec.get("password", ""))):
            msg = "Invalid username or password."
            raise AuthError(msg)
        return User(username=username.strip().lower(), is_admin=bool(rec.get("is_admin", False)))

    def has_users(self) -> bool:
        return bool(self._load())


# ─────────────────────────────────────────────────────────────────────────────
# Tokens (stateless, HMAC-signed)
# ─────────────────────────────────────────────────────────────────────────────


def _load_or_create_secret(path: Path) -> bytes:
    if path.is_file():
        return path.read_bytes()
    secret = secrets.token_bytes(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(secret)
    return secret


class TokenIssuer:
    def __init__(self, secret_path: Path) -> None:
        self._secret = _load_or_create_secret(secret_path)

    def issue(self, user: User, ttl: int = _TOKEN_TTL_SECONDS) -> str:
        expiry = int(time.time()) + ttl
        payload = f"{user.username}:{int(user.is_admin)}:{expiry}"
        sig = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
        return base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()

    def verify(self, token: str) -> User:
        try:
            decoded = base64.urlsafe_b64decode(token.encode()).decode()
            username, is_admin, expiry, sig = decoded.rsplit(":", 3)
            payload = f"{username}:{is_admin}:{expiry}"
            expected = hmac.new(self._secret, payload.encode(), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected):
                msg = "Invalid token signature."
                raise AuthError(msg)
            if int(expiry) < time.time():
                msg = "Token expired — log in again."
                raise AuthError(msg)
            return User(username=username, is_admin=is_admin == "1")
        except AuthError:
            raise
        except Exception as exc:
            msg = "Malformed token."
            raise AuthError(msg) from exc
