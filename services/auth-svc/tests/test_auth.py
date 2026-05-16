"""
Basic auth-svc integration tests.

Run: pytest tests/ -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import create_app
from app.core.database import Base, get_db


# Use in-memory SQLite for tests
TEST_DB_URL = "sqlite:///./test_auth.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


class TestRegister:
    def test_register_success(self, client):
        res = client.post("/api/v1/auth/register", json={
            "username": "testuser",
            "password": "secret123",
            "email": "test@example.com",
            "role": "student",
        })
        assert res.status_code == 201
        assert "testuser" in res.json()["message"]

    def test_register_duplicate(self, client):
        payload = {"username": "dup", "password": "secret123"}
        client.post("/api/v1/auth/register", json=payload)
        res = client.post("/api/v1/auth/register", json=payload)
        assert res.status_code == 409


class TestLogin:
    def _register(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "loginuser",
            "password": "pass1234",
            "role": "student",
        })

    def test_login_success(self, client):
        self._register(client)
        res = client.post("/api/v1/auth/login", json={
            "identifier": "loginuser",
            "password": "pass1234",
        })
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "loginuser"

    def test_login_wrong_password(self, client):
        self._register(client)
        res = client.post("/api/v1/auth/login", json={
            "identifier": "loginuser",
            "password": "wrong",
        })
        assert res.status_code == 401

    def test_login_nonexistent(self, client):
        res = client.post("/api/v1/auth/login", json={
            "identifier": "ghost",
            "password": "nope",
        })
        assert res.status_code == 401


class TestMe:
    def _get_token(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "meuser",
            "password": "pass1234",
        })
        res = client.post("/api/v1/auth/login", json={
            "identifier": "meuser",
            "password": "pass1234",
        })
        return res.json()["access_token"]

    def test_me_success(self, client):
        token = self._get_token(client)
        res = client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}"
        })
        assert res.status_code == 200
        assert res.json()["username"] == "meuser"

    def test_me_no_token(self, client):
        res = client.get("/api/v1/auth/me")
        assert res.status_code in (401, 403)


class TestRefresh:
    def test_refresh_success(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "refuser",
            "password": "pass1234",
        })
        login_res = client.post("/api/v1/auth/login", json={
            "identifier": "refuser",
            "password": "pass1234",
        })
        refresh_token = login_res.json()["refresh_token"]

        res = client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert res.status_code == 200
        assert "access_token" in res.json()
