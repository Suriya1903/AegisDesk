import pytest


def login(client, username, password):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_health_is_public(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_login_success_and_me(client):
    data = login(client, "employee", "Employee@123")
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "employee"
    assert data["user"]["role"] == "employee"

    response = client.get(
        "/api/auth/me",
        headers=auth_headers(data["access_token"]),
    )
    assert response.status_code == 200
    assert response.json()["user"]["username"] == "employee"


def test_invalid_login_is_rejected(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "employee", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_protected_endpoint_requires_authentication(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_employee_cannot_access_agent_or_admin_endpoints(client):
    token = login(client, "employee", "Employee@123")["access_token"]
    headers = auth_headers(token)

    assert client.get("/api/policy/status", headers=headers).status_code == 403
    assert client.get("/api/auth/users", headers=headers).status_code == 403
    assert client.get("/database/info", headers=headers).status_code == 403


def test_agent_can_access_operations_but_not_user_management(client):
    token = login(client, "agent", "Agent@123")["access_token"]
    headers = auth_headers(token)

    assert client.get("/api/policy/status", headers=headers).status_code == 200
    assert client.get("/api/auth/users", headers=headers).status_code == 403


def test_admin_can_access_user_management(client):
    token = login(client, "admin", "Admin@123")["access_token"]
    headers = auth_headers(token)

    response = client.get("/api/auth/users", headers=headers)
    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert {u["username"] for u in response.json()["users"]} == {
        "employee",
        "agent",
        "admin",
    }


def test_admin_can_change_role_and_cannot_remove_own_admin_role(client):
    token = login(client, "admin", "Admin@123")["access_token"]
    headers = auth_headers(token)

    response = client.patch(
        "/api/auth/users/employee/role",
        headers=headers,
        json={"role": "agent"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "agent"

    response = client.patch(
        "/api/auth/users/admin/role",
        headers=headers,
        json={"role": "employee"},
    )
    assert response.status_code == 400


def test_invalid_role_is_rejected(client):
    token = login(client, "admin", "Admin@123")["access_token"]
    response = client.patch(
        "/api/auth/users/employee/role",
        headers=auth_headers(token),
        json={"role": "superuser"},
    )
    assert response.status_code == 400
