"""Safe, deterministic self-heal actions for AegisDesk.

This module intentionally does not execute arbitrary shell commands, touch the
host OS, change security controls, or expose credentials.  Each supported
operation is a bounded demo/automation workflow that returns a structured
result suitable for an enterprise ITSM demo.
"""

from datetime import datetime, timezone
from typing import Any


ALLOWED_SELF_HEAL_ACTIONS = {
    "password_reset": {
        "label": "Password Reset",
        "description": "Reset the employee password through the approved identity workflow.",
    },
    "account_unlock": {
        "label": "Account Unlock",
        "description": "Unlock the employee account through the approved identity workflow.",
    },
    "vpn_status_check": {
        "label": "VPN Status Check",
        "description": "Run the approved VPN health/status workflow.",
    },
    "application_restart": {
        "label": "Application Restart",
        "description": "Restart an approved application through the bounded application workflow.",
    },
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def available_actions() -> list[dict[str, str]]:
    return [
        {
            "action": action,
            "label": details["label"],
            "description": details["description"],
        }
        for action, details in ALLOWED_SELF_HEAL_ACTIONS.items()
    ]


def execute_self_heal_action(
    action: str,
    *,
    ticket: dict[str, Any],
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute one explicitly allow-listed self-heal workflow.

    The operations are intentionally simulated/bounded.  No arbitrary command
    execution is performed.  This keeps the demo safe while preserving the
    architecture of an agentic IT automation workflow.
    """

    normalized_action = str(action or "").strip().lower()
    if normalized_action not in ALLOWED_SELF_HEAL_ACTIONS:
        raise ValueError(
            f"Unsupported self-heal action: {normalized_action or 'empty'}. "
            f"Allowed actions: {', '.join(sorted(ALLOWED_SELF_HEAL_ACTIONS))}."
        )

    ticket_id = str(ticket.get("ticket_id", ""))
    user = str(ticket.get("user", "employee"))
    started_at = _now()

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "action": normalized_action,
            "action_label": ALLOWED_SELF_HEAL_ACTIONS[normalized_action]["label"],
            "ticket_id": ticket_id,
            "user": user,
            "result": "Validation passed. No automation side effect was executed.",
            "started_at": started_at.isoformat(),
            "completed_at": _now().isoformat(),
        }

    results = {
        "password_reset": (
            "Approved password reset workflow completed successfully. "
            "No password or credential value is exposed by AegisDesk."
        ),
        "account_unlock": (
            "Approved account unlock workflow completed successfully."
        ),
        "vpn_status_check": (
            "Approved VPN status workflow completed successfully. "
            "The VPN troubleshooting workflow is healthy enough to resolve the ticket."
        ),
        "application_restart": (
            "Approved application restart workflow completed successfully."
        ),
    }

    return {
        "success": True,
        "dry_run": False,
        "action": normalized_action,
        "action_label": ALLOWED_SELF_HEAL_ACTIONS[normalized_action]["label"],
        "ticket_id": ticket_id,
        "user": user,
        "result": results[normalized_action],
        "started_at": started_at.isoformat(),
        "completed_at": _now().isoformat(),
    }
