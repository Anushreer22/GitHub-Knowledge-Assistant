import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    register_user,
    authenticate_user
)
from backend.app.services.retrieval_service import RetrievalService


@pytest.fixture(scope="module")
def client():
    RetrievalService.get_instance()
    with TestClient(app) as c:
        yield c


def test_password_hashing():
    pwd = "SecretPassword123!"
    h = hash_password(pwd)
    assert h.startswith("pbkdf2_sha256$100000$")
    assert verify_password(pwd, h) is True
    assert verify_password("WrongPassword", h) is False

    with pytest.raises(ValueError):
        hash_password("short")


def test_jwt_token_creation_and_verification():
    token = create_access_token("u_123", "alice", expires_delta_hours=2)
    assert isinstance(token, str)
    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == "u_123"
    assert payload["username"] == "alice"

    # Invalid token tampering
    tampered = token[:-5] + "XXXXX"
    assert decode_access_token(tampered) is None
    assert decode_access_token("invalid.token.here") is None


def test_user_registration_and_login(client):
    username = f"dev_user_{id(client)}"
    email = f"{username}@example.com"
    pwd = "ValidPass123!"

    # 1. Register
    reg_res = client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": pwd
    })
    assert reg_res.status_code == 200
    reg_data = reg_res.json()
    assert "token" in reg_data
    assert reg_data["user"]["username"] == username
    token = reg_data["token"]

    # 2. Duplicate registration rejected
    dup_res = client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": pwd
    })
    assert dup_res.status_code == 400
    assert "already taken" in dup_res.json()["detail"] or "already registered" in dup_res.json()["detail"]

    # 3. Login
    login_res = client.post("/api/auth/login", json={
        "username": username,
        "password": pwd
    })
    assert login_res.status_code == 200
    assert "token" in login_res.json()

    # 4. Wrong password login
    bad_login = client.post("/api/auth/login", json={
        "username": username,
        "password": "WrongPassword999!"
    })
    assert bad_login.status_code == 401

    # 5. Access /api/auth/me with Bearer token
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == username

    # 6. Unauthenticated access to /api/auth/me rejected
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 401


def test_user_saved_repositories_and_history(client):
    username = f"col_user_{id(client)}"
    email = f"{username}@example.com"
    pwd = "CollectionPass123!"

    reg = client.post("/api/auth/register", json={
        "username": username,
        "email": email,
        "password": pwd
    })
    token = reg.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Save repository
    save_res = client.post(
        "/api/user/saved-repositories",
        json={"repo_id": "pallets__werkzeug"},
        headers=headers
    )
    assert save_res.status_code == 200
    assert "pallets__werkzeug" in save_res.json()

    # Get saved
    get_res = client.get("/api/user/saved-repositories", headers=headers)
    assert get_res.status_code == 200
    assert "pallets__werkzeug" in get_res.json()

    # Authenticated search records history
    search_res = client.post(
        "/api/search",
        json={"query": "test_auth_history_query", "mode": "bm25", "top_k": 2},
        headers=headers
    )
    assert search_res.status_code == 200

    # Retrieve history
    hist_res = client.get("/api/user/search-history", headers=headers)
    assert hist_res.status_code == 200
    history_items = hist_res.json()
    assert len(history_items) > 0
    assert history_items[0]["query"] == "test_auth_history_query"

    # Delete saved repository
    del_res = client.delete("/api/user/saved-repositories/pallets__werkzeug", headers=headers)
    assert del_res.status_code == 200
    assert "pallets__werkzeug" not in del_res.json()
