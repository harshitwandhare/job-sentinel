"""
CORS origin-regex tests.

Verifies that the ``_LOCAL_ORIGIN_REGEX`` allows the expected local and
extension origins and rejects arbitrary remote origins.
"""

from __future__ import annotations

import re

import pytest

from job_sentinel.api.app import _LOCAL_ORIGIN_REGEX


def _match(origin: str) -> bool:
    """Return True when the full origin string matches the CORS regex."""
    return bool(re.fullmatch(_LOCAL_ORIGIN_REGEX, origin))


# ── Origins that MUST be allowed ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "origin",
    [
        # Plain localhost — no port
        "http://localhost",
        "https://localhost",
        # localhost with ports (Next.js picks next free port)
        "http://localhost:3000",
        "http://localhost:3001",
        "https://localhost:8080",
        # 127.0.0.1 variants
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "https://127.0.0.1:3000",
        # Chrome extension — 32 lowercase hex a-p chars
        "chrome-extension://abcdefghijklmnopabcdefghijklmnop",
        # Firefox extension — UUID style
        "moz-extension://12345678-abcd-ef01-2345-6789abcdef01",
        "moz-extension://a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    ],
)
def test_allowed_origins(origin: str) -> None:
    assert _match(origin), f"Expected {origin!r} to be allowed but regex rejected it"


# ── Origins that MUST be rejected ────────────────────────────────────────────


@pytest.mark.parametrize(
    "origin",
    [
        # Random HTTPS domains
        "https://example.com",
        "https://evil.com",
        "https://job-sentinel.io",
        # HTTP external
        "http://example.com",
        # Looks like localhost but isn't
        "http://localhost.evil.com",
        "http://127.0.0.1.attacker.com",
        # Wrong scheme for extension
        "http://chrome-extension://abcdefghijklmnopabcdefghijklmnop",
        # Too short / too long extension ID
        "chrome-extension://abc",
        "chrome-extension://abcdefghijklmnopabcdefghijklmnopXXXX",
        # Invalid chars in Chrome extension ID (must be a-p only)
        "chrome-extension://abcdefghijklmnopabcdefghijklmnoz",
    ],
)
def test_rejected_origins(origin: str) -> None:
    assert not _match(origin), f"Expected {origin!r} to be rejected but regex allowed it"
