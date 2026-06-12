"""Tests for the stdlib auth layer: password hashing, user store, tokens."""

from __future__ import annotations

import pytest

from job_sentinel.api.auth import (
    AuthError,
    TokenIssuer,
    User,
    UserStore,
    hash_password,
    verify_password,
)

# ── Password hashing ─────────────────────────────────────────────────────────


def test_hash_roundtrip() -> None:
    stored = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", stored)
    assert not verify_password("wrong", stored)


def test_hashes_are_salted() -> None:
    assert hash_password("same") != hash_password("same")


def test_verify_rejects_malformed_hash() -> None:
    assert not verify_password("x", "not-a-real-hash")


# ── User store ───────────────────────────────────────────────────────────────


@pytest.fixture
def store(tmp_path):
    return UserStore(tmp_path / "users.json")


def test_first_user_must_be_admin(store) -> None:
    with pytest.raises(AuthError, match="admin"):
        store.add_user("alice", "password123")


def test_add_authenticate_and_list(store) -> None:
    store.add_user("Admin", "password123", is_admin=True)
    store.add_user("bob", "hunter2hunter2")

    user = store.authenticate("admin", "password123")  # stored lowercase
    assert user.is_admin is True

    names = [u.username for u in store.list_users()]
    assert names == ["admin", "bob"]


def test_authenticate_rejects_bad_password(store) -> None:
    store.add_user("admin", "password123", is_admin=True)
    with pytest.raises(AuthError):
        store.authenticate("admin", "nope")
    with pytest.raises(AuthError):
        store.authenticate("ghost", "password123")


def test_duplicate_user_rejected(store) -> None:
    store.add_user("admin", "password123", is_admin=True)
    with pytest.raises(AuthError, match="exists"):
        store.add_user("admin", "password456")


def test_remove_user(store) -> None:
    store.add_user("admin", "password123", is_admin=True)
    assert store.remove_user("admin") is True
    assert store.remove_user("admin") is False
    assert store.has_users() is False


# ── Tokens ───────────────────────────────────────────────────────────────────


@pytest.fixture
def issuer(tmp_path):
    return TokenIssuer(tmp_path / "secret")


def test_token_roundtrip(issuer) -> None:
    token = issuer.issue(User(username="harshit", is_admin=True))
    user = issuer.verify(token)
    assert user.username == "harshit"
    assert user.is_admin is True


def test_expired_token_rejected(issuer) -> None:
    token = issuer.issue(User(username="x"), ttl=-1)
    with pytest.raises(AuthError, match="expired"):
        issuer.verify(token)


def test_tampered_token_rejected(issuer) -> None:
    token = issuer.issue(User(username="x"))
    with pytest.raises(AuthError):
        issuer.verify(token[:-4] + "AAAA")


def test_garbage_token_rejected(issuer) -> None:
    with pytest.raises(AuthError):
        issuer.verify("garbage")


def test_secret_persists_across_instances(tmp_path) -> None:
    a = TokenIssuer(tmp_path / "secret")
    token = a.issue(User(username="x"))
    b = TokenIssuer(tmp_path / "secret")  # same file → same key
    assert b.verify(token).username == "x"
