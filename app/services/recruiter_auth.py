"""Recruiter session tokens. Credentials come from environment settings."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from app.config.settings import Settings, get_settings

TOKEN_TTL_SECONDS = 12 * 60 * 60


class RecruiterAuthError(Exception):
    """Base recruiter authentication error."""


class RecruiterAuthNotConfiguredError(RecruiterAuthError):
    """Raised when recruiter username, password, or session secret is missing."""


class InvalidRecruiterCredentialsError(RecruiterAuthError):
    """Raised when the login does not match configured credentials."""


@dataclass(frozen=True)
class RecruiterSession:
    username: str
    expires_at: int


class RecruiterAuth:
    def __init__(
        self,
        username: str | None,
        password: str | None,
        session_secret: str | None,
        *,
        ttl_seconds: int = TOKEN_TTL_SECONDS,
    ) -> None:
        self._username = (username or "").strip() or None
        self._password = password or None
        self._secret = (session_secret or "").strip() or None
        self._ttl_seconds = ttl_seconds

    @classmethod
    def from_settings(cls, settings: Settings | None = None) -> RecruiterAuth:
        loaded = settings or get_settings()
        return cls(
            loaded.recruiter_username,
            loaded.recruiter_password,
            loaded.recruiter_session_secret,
        )

    @property
    def configured(self) -> bool:
        return bool(self._username and self._password and self._secret)

    def login(self, username: str, password: str) -> str:
        if not self.configured or self._username is None or self._password is None:
            raise RecruiterAuthNotConfiguredError(
                "Recruiter login is not configured. Set RECRUITER_USERNAME, "
                "RECRUITER_PASSWORD, and RECRUITER_SESSION_SECRET."
            )
        if not _digest_equal(username.strip(), self._username) or not _digest_equal(
            password, self._password
        ):
            raise InvalidRecruiterCredentialsError("Invalid username or password")
        return self.issue_token(self._username)

    def issue_token(self, username: str) -> str:
        if not self._secret:
            raise RecruiterAuthNotConfiguredError("RECRUITER_SESSION_SECRET is not set")
        expires_at = int(time.time()) + self._ttl_seconds
        payload = json.dumps(
            {"u": username, "exp": expires_at}, separators=(",", ":")
        )
        body = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
        signature = hmac.new(
            self._secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256
        ).hexdigest()
        return f"{body}.{signature}"

    def verify_token(self, token: str) -> RecruiterSession | None:
        if not self.configured or not self._secret:
            return None
        try:
            body, signature = token.split(".", 1)
        except ValueError:
            return None
        expected = hmac.new(
            self._secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256
        ).hexdigest()
        if not _digest_equal(signature, expected):
            return None
        try:
            payload = json.loads(base64.urlsafe_b64decode(body.encode("ascii")))
            username = str(payload["u"])
            expires_at = int(payload["exp"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None
        if expires_at < int(time.time()):
            return None
        if username != self._username:
            return None
        return RecruiterSession(username=username, expires_at=expires_at)


def get_recruiter_auth() -> RecruiterAuth:
    return RecruiterAuth.from_settings()


def _digest_equal(left: str, right: str) -> bool:
    left_b = left.encode("utf-8")
    right_b = right.encode("utf-8")
    if len(left_b) != len(right_b):
        hmac.compare_digest(left_b, left_b)
        return False
    return hmac.compare_digest(left_b, right_b)
