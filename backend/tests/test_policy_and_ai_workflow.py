from .test_auth_rbac import auth_headers, login


def test_policy_engine_blocks_dangerous_request(client):
    token = login(client, "agent", "Agent@123")["access_token"]
    response = client.post(
        "/api/policy/evaluate",
        headers=auth_headers(token),
        json={
            "analysis": {
                "query": "Disable the antivirus and endpoint security",
                "confidence": 0.99,
                "category": "Security",
                "subcategory": "Security Policy",
                "recommended_action": "disable_antivirus",
                "priority": "P3",
                "impact": "Individual",
                "urgency": "Medium",
            },
            "retrieval": {"grounded": True, "top_similarity": 0.8},
        },
    )
    assert response.status_code == 200, response.text
    policy = response.json()["policy"]
    assert policy["decision"] == "BLOCKED"
    assert policy["requires_human"] is True


def test_ai_ticket_workflow_persists_ticket_without_loading_llm(
    client, app_module
):
    token = login(client, "employee", "Employee@123")["access_token"]

    original_analyze = app_module.analyze_request
    original_policy = app_module.evaluate_policy

    app_module.analyze_request = lambda query, top_k=5: {
        "answer": "Restart the approved VPN client and retry authentication.",
        "intent": "Incident",
        "category": "Network",
        "subcategory": "VPN",
        "priority": "P3",
        "impact": "Individual",
        "urgency": "Medium",
        "assignment_group": "Network Support",
        "confidence": 0.94,
        "recommended_action": "vpn_status_check",
        "grounded": True,
        "top_similarity": 0.49,
        "model": "test-model",
    }
    app_module.evaluate_policy = lambda analysis, retrieval: {
        "decision": "APPROVED",
        "action": "vpn_status_check",
        "action_label": "Check VPN status",
        "reason": "Test policy approval.",
        "requires_human": False,
        "policy_version": "1.1",
        "checks": {},
    }

    try:
        response = client.post(
            "/api/tickets/ai",
            headers=auth_headers(token),
            json={
                "query": "My VPN is not connecting",
                "source": "Automated Test",
            },
        )
    finally:
        app_module.analyze_request = original_analyze
        app_module.evaluate_policy = original_policy

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["workflow"]["rag"] == "completed"
    assert body["workflow"]["llm"] == "completed"
    assert body["workflow"]["policy_engine"] == "completed"
    assert body["ticket"]["user"] == "employee"
    assert body["ticket"]["policy_decision"] == "APPROVED"
    assert body["audit"]["actor"] == "employee"

    stored = app_module.tickets_collection.find_one(
        {"ticket_id": body["ticket"]["ticket_id"]}
    )
    assert stored is not None
    assert stored["category"] == "Network"
