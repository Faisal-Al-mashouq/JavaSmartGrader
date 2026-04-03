from __future__ import annotations

from types import SimpleNamespace

import pytest
from db.models import UserRole
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from schemas import UserBase

from api.auth import (
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
    get_current_user,
    require_role,
)
from api.dependencies import get_db


def test_create_access_token_roundtrip() -> None:
    token = create_access_token({"sub": "7", "role": UserRole.student.value})
    decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded["sub"] == "7"
    assert decoded["role"] == UserRole.student.value
    assert "exp" in decoded


def test_get_current_user_success(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.auth as auth_mod

    async def fake_get_user_by_id(session, user_id: int):
        return SimpleNamespace(
            id=user_id,
            username="alice",
            email="alice@example.com",
            role=UserRole.student,
            password_hash="hashed",
        )

    monkeypatch.setattr(auth_mod, "get_user_by_id", fake_get_user_by_id)

    app = FastAPI()

    @app.get("/whoami", response_model=UserBase)
    async def whoami(current: UserBase = Depends(get_current_user)):
        return current

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_db] = fake_get_db

    token = create_access_token({"sub": "99"})
    client = TestClient(app)
    resp = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == 99
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert body["role"] == UserRole.student.value


def test_get_current_user_rejects_bad_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.auth as auth_mod

    async def fake_get_user_by_id(session, user_id: int):
        raise AssertionError("should not lookup user for bad token")

    monkeypatch.setattr(auth_mod, "get_user_by_id", fake_get_user_by_id)

    app = FastAPI()

    @app.get("/whoami")
    async def whoami(_current: UserBase = Depends(get_current_user)):
        return {"ok": True}

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    resp = client.get("/whoami", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


def test_get_current_user_unknown_sub(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.auth as auth_mod

    async def fake_get_user_by_id(session, user_id: int):
        return None

    monkeypatch.setattr(auth_mod, "get_user_by_id", fake_get_user_by_id)

    app = FastAPI()

    @app.get("/whoami")
    async def whoami(_current: UserBase = Depends(get_current_user)):
        return {"ok": True}

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_db] = fake_get_db

    token = create_access_token({"sub": "12345"})
    client = TestClient(app)
    resp = client.get("/whoami", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_require_role_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    import api.auth as auth_mod

    async def fake_get_user_by_id(session, user_id: int):
        return SimpleNamespace(
            id=user_id,
            username="bob",
            email="bob@example.com",
            role=UserRole.student,
            password_hash="hashed",
        )

    monkeypatch.setattr(auth_mod, "get_user_by_id", fake_get_user_by_id)

    app = FastAPI()

    @app.get("/instructor-only")
    async def instructor_route(_=Depends(require_role(UserRole.instructor))):
        return {"ok": True}

    async def fake_get_db():
        yield None

    app.dependency_overrides[get_db] = fake_get_db

    token = create_access_token({"sub": "1"})
    client = TestClient(app)
    resp = client.get("/instructor-only", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
