from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pymongo import DESCENDING


class ServiceNowMockError(RuntimeError):
    """Raised when the mock ServiceNow adapter cannot complete an operation."""


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _next_number(collection, prefix: str, field: str, start: int) -> str:
    latest = collection.find_one(
        {field: {"$regex": rf"^{prefix}\d+$"}},
        sort=[(field, DESCENDING)],
        projection={field: 1},
    )
    if not latest:
        number = start
    else:
        try:
            number = int(str(latest[field])[len(prefix):]) + 1
        except (KeyError, ValueError, TypeError):
            number = start
    return f"{prefix}{number:06d}"


def create_incident(database, ticket: dict) -> dict:
    """Create a ServiceNow-like incident from an AegisDesk ticket."""
    collection = database["servicenow_incidents"]
    created = now_utc()

    incident = {
        "number": _next_number(collection, "INC", "number", 1001),
        "sys_id": None,
        "short_description": ticket.get("title") or ticket.get("description", "")[:160],
        "description": ticket.get("description", ""),
        "category": ticket.get("category", "General"),
        "subcategory": ticket.get("subcategory", "General"),
        "priority": ticket.get("priority", "P3"),
        "impact": ticket.get("impact", "Individual"),
        "urgency": ticket.get("urgency", "Medium"),
        "assignment_group": ticket.get("assignment_group", "Service Desk"),
        "state": "New",
        "caller": ticket.get("user", "Employee"),
        "aegisdesk_ticket_id": ticket.get("ticket_id"),
        "source": "AegisDesk Mock ServiceNow",
        "resolution": None,
        "created_at": created,
        "updated_at": created,
    }

    result = collection.insert_one(incident)
    incident["sys_id"] = str(result.inserted_id)
    collection.update_one(
        {"_id": result.inserted_id},
        {"$set": {"sys_id": incident["sys_id"]}},
    )
    incident.pop("_id", None)
    return incident


def get_incident(database, number: str) -> Optional[dict]:
    collection = database["servicenow_incidents"]
    incident = collection.find_one({"number": number})
    if not incident:
        return None
    incident.pop("_id", None)
    return incident


def update_incident(
    database,
    number: str,
    *,
    state: Optional[str] = None,
    assignment_group: Optional[str] = None,
    resolution: Optional[str] = None,
) -> Optional[dict]:
    collection = database["servicenow_incidents"]
    incident = collection.find_one({"number": number})
    if not incident:
        return None

    changes: dict[str, Any] = {"updated_at": now_utc()}
    if state is not None:
        changes["state"] = state
    if assignment_group is not None:
        changes["assignment_group"] = assignment_group
    if resolution is not None:
        changes["resolution"] = resolution

    collection.update_one({"_id": incident["_id"]}, {"$set": changes})
    return get_incident(database, number)


def create_service_request(database, *, software: str, user: str, description: str) -> dict:
    """Create a ServiceNow-like service request for software provisioning."""
    collection = database["servicenow_requests"]
    created = now_utc()

    request = {
        "number": _next_number(collection, "REQ", "number", 1001),
        "sys_id": None,
        "short_description": f"Software request: {software}",
        "description": description,
        "software": software,
        "requested_for": user,
        "state": "Requested",
        "provisioning_status": "Provisioning",
        "source": "AegisDesk Mock ServiceNow",
        "created_at": created,
        "updated_at": created,
    }

    result = collection.insert_one(request)
    request["sys_id"] = str(result.inserted_id)
    collection.update_one(
        {"_id": result.inserted_id},
        {"$set": {"sys_id": request["sys_id"]}},
    )
    request.pop("_id", None)
    return request


def get_service_request(database, number: str) -> Optional[dict]:
    collection = database["servicenow_requests"]
    request = collection.find_one({"number": number})
    if not request:
        return None
    request.pop("_id", None)
    return request


def update_service_request(
    database,
    number: str,
    *,
    state: Optional[str] = None,
    provisioning_status: Optional[str] = None,
) -> Optional[dict]:
    collection = database["servicenow_requests"]
    request = collection.find_one({"number": number})
    if not request:
        return None

    changes: dict[str, Any] = {"updated_at": now_utc()}
    if state is not None:
        changes["state"] = state
    if provisioning_status is not None:
        changes["provisioning_status"] = provisioning_status

    collection.update_one({"_id": request["_id"]}, {"$set": changes})
    return get_service_request(database, number)
