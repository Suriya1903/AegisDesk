from datetime import datetime, timezone

from .test_auth_rbac import auth_headers, login


def seed_ticket(app_module, ticket_id="INC999901", user="employee"):
    now = datetime.now(timezone.utc)
    app_module.tickets_collection.insert_one(
        {
            "ticket_id": ticket_id,
            "title": "Test VPN issue",
            "description": "Automated test ticket",
            "category": "Network",
            "subcategory": "VPN",
            "priority": "P3",
            "impact": "Individual",
            "urgency": "Medium",
            "status": "Open",
            "user": user,
            "assignment_group": "Network Support",
            "resolution": None,
            "ai_confidence": 0.94,
            "ai_grounded": True,
            "source": "Automated Test",
            "created_at": now,
            "updated_at": now,
        }
    )
    return ticket_id


def test_employee_can_create_ticket_but_identity_cannot_be_spoofed(client, app_module):
    token = login(client, "employee", "Employee@123")["access_token"]

    response = client.post(
        "/api/tickets",
        headers=auth_headers(token),
        json={
            "title": "Need VPN access",
            "description": "VPN is not connecting.",
            "user": "admin",
            "category": "Network",
            "subcategory": "VPN",
        },
    )
    assert response.status_code == 201, response.text

    ticket = response.json()["ticket"]
    assert ticket["user"] == "employee"
    assert ticket["ticket_id"].startswith("INC")

    audit = app_module.audit_collection.find_one(
        {"ticket_id": ticket["ticket_id"], "event_type": "ticket_created"}
    )
    assert audit["actor"] == "employee"


def test_employee_can_only_see_own_tickets(client, app_module):
    seed_ticket(app_module, "INC999902", "employee")
    source = app_module.tickets_collection.find_one({"ticket_id": "INC999902"})
    source.pop("_id", None)
    source.update({"ticket_id": "INC999903", "user": "other-user"})
    app_module.tickets_collection.insert_one(source)

    token = login(client, "employee", "Employee@123")["access_token"]
    response = client.get("/api/tickets", headers=auth_headers(token))
    assert response.status_code == 200
    ids = {ticket["ticket_id"] for ticket in response.json()["tickets"]}
    assert "INC999902" in ids
    assert "INC999903" not in ids


def test_employee_cannot_update_ticket(client, app_module):
    ticket_id = seed_ticket(app_module, "INC999904", "employee")
    token = login(client, "employee", "Employee@123")["access_token"]

    response = client.patch(
        f"/api/tickets/{ticket_id}",
        headers=auth_headers(token),
        json={"status": "In Progress"},
    )
    assert response.status_code == 403


def test_agent_can_update_ticket_and_audit_change_is_recorded(client, app_module):
    ticket_id = seed_ticket(app_module, "INC999905", "employee")
    token = login(client, "agent", "Agent@123")["access_token"]

    response = client.patch(
        f"/api/tickets/{ticket_id}",
        headers=auth_headers(token),
        json={"status": "In Progress", "resolution": "Investigating."},
    )
    assert response.status_code == 200, response.text

    audit = response.json()["audit"]
    assert audit["event_type"] == "ticket_updated"
    assert audit["actor"] == "agent"
    assert audit["changes"]["status"]["to"] == "In Progress"

    activity = client.get(
        f"/api/tickets/{ticket_id}/activity",
        headers=auth_headers(token),
    )
    assert activity.status_code == 200
    assert activity.json()["count"] == 1


def test_employee_cannot_view_another_users_ticket(client, app_module):
    ticket_id = seed_ticket(app_module, "INC999906", "other-user")
    token = login(client, "employee", "Employee@123")["access_token"]

    response = client.get(
        f"/api/tickets/{ticket_id}",
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_agent_can_view_and_admin_can_view_ticket(client, app_module):
    ticket_id = seed_ticket(app_module, "INC999907", "other-user")

    for username, password in (("agent", "Agent@123"), ("admin", "Admin@123")):
        token = login(client, username, password)["access_token"]
        response = client.get(
            f"/api/tickets/{ticket_id}",
            headers=auth_headers(token),
        )
        assert response.status_code == 200
