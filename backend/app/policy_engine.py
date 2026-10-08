from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


# ============================================================
# AegisDesk Safe Automation Policy Engine
# ============================================================
#
# IMPORTANT:
#
# This module DOES NOT execute any IT action.
#
# It only decides whether an AI-recommended request is:
#
#   - APPROVED
#   - HUMAN_REVIEW
#   - BLOCKED
#   - NO_AUTOMATION
#
# The actual action executor will be implemented separately.
#
# The Policy Engine is deterministic.
# The LLM never gets direct authority to execute an action.
#
# ============================================================


POLICY_VERSION = "1.1"


# ============================================================
# Approved low-risk automation workflows
# ============================================================

ALLOWED_ACTIONS = {
    "password_reset": {
        "label": "Password Reset",
        "description": "Initiate the approved password reset workflow.",
        "risk": "low",
        "requires_human": False,
    },
    "account_unlock": {
        "label": "Account Unlock",
        "description": "Initiate the approved account unlock workflow.",
        "risk": "low",
        "requires_human": False,
    },
    "vpn_status_check": {
        "label": "VPN Status Check",
        "description": "Check approved VPN connectivity/status information.",
        "risk": "low",
        "requires_human": False,
    },
    "application_restart": {
        "label": "Application Restart",
        "description": "Restart an approved application through the IT workflow.",
        "risk": "medium",
        "requires_human": False,
    },
}


# ============================================================
# Explicitly blocked actions
# ============================================================

BLOCKED_ACTIONS = {
    "disable_security",
    "disable_endpoint_protection",
    "disable_antivirus",
    "change_firewall",
    "modify_security_policy",
    "delete_user",
    "delete_account",
    "grant_admin_access",
    "grant_privileged_access",
    "change_access_control",
    "execute_shell_command",
    "run_arbitrary_command",
    "install_unapproved_software",
}


# ============================================================
# Minimum thresholds
# ============================================================

MIN_AI_CONFIDENCE = 0.80
MIN_GROUNDING_SIMILARITY = 0.30


# ============================================================
# Enterprise-impact rules
# ============================================================

# Even if an action is normally safe for an individual user,
# enterprise-wide incidents must not be automatically executed.

HIGH_IMPACT_VALUES = {
    "enterprise",
    "organization",
    "company",
    "business",
    "global",
}


# P1 always requires human review.
# P2 requires human review when impact is enterprise-wide
# or when the incident clearly affects multiple users.


@dataclass
class PolicyDecision:
    decision: str
    action: str | None
    action_label: str | None
    reason: str
    requires_human: bool
    policy_version: str
    checks: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ============================================================
# Normalisation helpers
# ============================================================

def _normalise(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip().lower()


def _normalise_action(value: Any) -> str:
    value = _normalise(value)

    replacements = {
        "password reset": "password_reset",
        "reset password": "password_reset",
        "password_reset": "password_reset",

        "account unlock": "account_unlock",
        "unlock account": "account_unlock",
        "account_unlock": "account_unlock",

        "vpn status check": "vpn_status_check",
        "check vpn": "vpn_status_check",
        "vpn_status_check": "vpn_status_check",

        "application restart": "application_restart",
        "restart application": "application_restart",
        "application_restart": "application_restart",
    }

    return replacements.get(value, value)


# ============================================================
# Blocked-request detection
# ============================================================

def _is_blocked_action(action: str) -> bool:
    """
    Check whether an explicitly supplied action is dangerous.
    """

    action = _normalise(action)

    if not action:
        return False

    if action in BLOCKED_ACTIONS:
        return True

    blocked_keywords = (
        "disable security",
        "disable antivirus",
        "disable endpoint",
        "disable endpoint protection",
        "turn off antivirus",
        "turn off security",
        "turn off endpoint protection",
        "disable firewall",
        "turn off firewall",
        "change firewall",
        "modify firewall",
        "security policy",
        "modify security policy",
        "bypass security",
        "bypass endpoint protection",
        "admin access",
        "privileged access",
        "grant administrator",
        "grant admin",
        "arbitrary command",
        "shell command",
        "execute command",
        "run command",
        "unapproved software",
        "install unapproved software",
        "delete account",
        "delete user",
        "remove security control",
    )

    return any(keyword in action for keyword in blocked_keywords)


def _contains_blocked_request(*values: Any) -> bool:
    """
    Detect dangerous intent from the complete request context.

    IMPORTANT:
    We inspect the original user query as well as the AI output.

    This prevents the LLM from accidentally hiding a dangerous
    request behind a generic recommendation such as:
        "Follow approved IT support procedure."
    """

    combined = " ".join(
        _normalise(value)
        for value in values
        if value is not None
    )

    if not combined:
        return False

    # Direct blocked-action phrases.
    blocked_phrases = (
        "disable antivirus",
        "disable the antivirus",
        "turn off antivirus",
        "turn off the antivirus",
        "disable endpoint security",
        "disable endpoint protection",
        "turn off endpoint security",
        "turn off endpoint protection",
        "disable security",
        "turn off security",
        "disable firewall",
        "turn off firewall",
        "change firewall",
        "modify security policy",
        "disable security controls",
        "bypass security controls",
        "bypass endpoint protection",
        "grant admin access",
        "grant administrator access",
        "grant privileged access",
        "delete user",
        "delete account",
        "execute shell command",
        "run arbitrary command",
        "run an arbitrary command",
        "install unapproved software",
        "install unauthorized software",
    )

    if any(phrase in combined for phrase in blocked_phrases):
        return True

    # Compound security-danger patterns.
    security_disable_terms = (
        "disable",
        "turn off",
        "bypass",
        "remove",
    )

    security_targets = (
        "antivirus",
        "endpoint security",
        "endpoint protection",
        "security controls",
        "firewall",
        "security policy",
    )

    if any(term in combined for term in security_disable_terms):
        if any(target in combined for target in security_targets):
            return True

    # Privilege escalation patterns.
    privilege_terms = (
        "admin access",
        "administrator access",
        "privileged access",
        "root access",
        "elevated privileges",
    )

    if any(term in combined for term in privilege_terms):
        if any(
            action_word in combined
            for action_word in (
                "grant",
                "give",
                "enable",
                "request",
                "provide",
            )
        ):
            return True

    return False


# ============================================================
# Approved-action inference
# ============================================================

def _infer_action(analysis: dict[str, Any]) -> str | None:
    """
    Infer an approved automation candidate from structured AI analysis.

    This is deliberately deterministic.

    The LLM does NOT decide what is executable.
    """

    intent = _normalise(analysis.get("intent"))
    category = _normalise(analysis.get("category"))
    subcategory = _normalise(analysis.get("subcategory"))
    query = _normalise(analysis.get("query"))
    recommendation = _normalise(
        analysis.get("recommended_action")
    )

    combined = " ".join(
        [
            intent,
            category,
            subcategory,
            query,
            recommendation,
        ]
    )

    # Password reset
    if "password" in combined and (
        "reset" in combined
        or "expired" in combined
        or "forgot" in combined
    ):
        return "password_reset"

    # Account unlock
    if "account" in combined and (
        "unlock" in combined
        or "locked" in combined
    ):
        return "account_unlock"

    # VPN
    if "vpn" in combined and (
        "status" in combined
        or "connect" in combined
        or "connection" in combined
    ):
        return "vpn_status_check"

    # Application restart
    if "application" in combined and "restart" in combined:
        return "application_restart"

    return None


# ============================================================
# Main Policy Evaluation
# ============================================================

def evaluate_policy(
    analysis: dict[str, Any],
    retrieval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Evaluate an AI analysis against deterministic enterprise policies.

    No external action is executed here.
    """

    retrieval = retrieval or {}

    # --------------------------------------------------------
    # Extract grounding information
    # --------------------------------------------------------

    grounded = bool(
        analysis.get(
            "grounded",
            retrieval.get("grounded", False),
        )
    )

    ai_confidence = float(
        analysis.get(
            "confidence",
            analysis.get("ai_confidence", 0.0),
        )
        or 0.0
    )

    top_similarity = float(
        retrieval.get(
            "top_similarity",
            analysis.get("top_similarity", 0.0),
        )
        or 0.0
    )

    # --------------------------------------------------------
    # Extract classification
    # --------------------------------------------------------

    priority = _normalise(
        analysis.get("priority")
    )

    intent = _normalise(
        analysis.get("intent")
    )

    impact = _normalise(
        analysis.get("impact")
    )

    urgency = _normalise(
        analysis.get("urgency")
    )

    category = _normalise(
        analysis.get("category")
    )

    subcategory = _normalise(
        analysis.get("subcategory")
    )

    query = analysis.get("query", "")

    recommended_action = analysis.get(
        "recommended_action",
        "",
    )

    # --------------------------------------------------------
    # Requested action
    # --------------------------------------------------------

    requested_action = (
        analysis.get("requested_action")
        or analysis.get("action")
        or ""
    )

    normalised_requested_action = _normalise_action(
        requested_action
    )

    # --------------------------------------------------------
    # Checks exposed in API
    # --------------------------------------------------------

    checks = {
        "grounded": grounded,
        "ai_confidence": round(ai_confidence, 4),
        "minimum_ai_confidence": MIN_AI_CONFIDENCE,
        "confidence_passed": (
            ai_confidence >= MIN_AI_CONFIDENCE
        ),
        "top_similarity": round(top_similarity, 4),
        "minimum_grounding_similarity": (
            MIN_GROUNDING_SIMILARITY
        ),
        "grounding_passed": (
            top_similarity >= MIN_GROUNDING_SIMILARITY
        ),
        "priority": priority,
        "intent": intent,
        "impact": impact,
        "urgency": urgency,
    }

    # ========================================================
    # 1. BLOCKED REQUEST DETECTION
    # ========================================================
    #
    # This happens FIRST.
    #
    # We inspect:
    #   - original user query
    #   - requested action
    #   - AI recommendation
    #   - category
    #   - subcategory
    #
    # Therefore a dangerous request cannot be hidden by a
    # generic LLM recommendation.
    # ========================================================

    blocked_request = _contains_blocked_request(
        query,
        requested_action,
        recommended_action,
        category,
        subcategory,
    )

    checks["blocked_request_detected"] = blocked_request

    if blocked_request or _is_blocked_action(
        normalised_requested_action
    ):
        return PolicyDecision(
            decision="BLOCKED",
            action=None,
            action_label=None,
            reason=(
                "The request attempts to perform an action "
                "outside the approved automation allowlist "
                "and may affect security, access control, "
                "or system integrity."
            ),
            requires_human=True,
            policy_version=POLICY_VERSION,
            checks=checks,
        ).to_dict()

    # ========================================================
    # 2. No grounding
    # ========================================================

    if not grounded:
        return PolicyDecision(
            decision="HUMAN_REVIEW",
            action=None,
            action_label=None,
            reason=(
                "The AI response is not sufficiently grounded "
                "in approved enterprise knowledge."
            ),
            requires_human=True,
            policy_version=POLICY_VERSION,
            checks=checks,
        ).to_dict()

    # ========================================================
    # 3. Weak retrieval grounding
    # ========================================================

    if top_similarity < MIN_GROUNDING_SIMILARITY:
        return PolicyDecision(
            decision="HUMAN_REVIEW",
            action=None,
            action_label=None,
            reason=(
                "Retrieved knowledge is below the minimum "
                "grounding threshold required for automation."
            ),
            requires_human=True,
            policy_version=POLICY_VERSION,
            checks=checks,
        ).to_dict()

    # ========================================================
    # 4. Low AI confidence
    # ========================================================

    if ai_confidence < MIN_AI_CONFIDENCE:
        return PolicyDecision(
            decision="HUMAN_REVIEW",
            action=None,
            action_label=None,
            reason=(
                "AI classification confidence is below the "
                "minimum threshold required for automated "
                "processing."
            ),
            requires_human=True,
            policy_version=POLICY_VERSION,
            checks=checks,
        ).to_dict()

    # ========================================================
    # 5. P1 incidents always require human review
    # ========================================================

    if priority == "p1":
        return PolicyDecision(
            decision="HUMAN_REVIEW",
            action=None,
            action_label=None,
            reason=(
                "P1 incidents require human review because "
                "they may represent enterprise-wide or "
                "business-critical impact."
            ),
            requires_human=True,
            policy_version=POLICY_VERSION,
            checks=checks,
        ).to_dict()

    # ========================================================
    # 6. Enterprise-wide P2 incidents require human review
    # ========================================================
    #
    # This fixes the company-wide VPN issue.
    #
    # A VPN status check may be safe for one employee,
    # but the same action must not be automatically approved
    # when the incident affects the entire enterprise.
    # ========================================================

    if (
        priority == "p2"
        and impact in HIGH_IMPACT_VALUES
    ):
        return PolicyDecision(
            decision="HUMAN_REVIEW",
            action=None,
            action_label=None,
            reason=(
                "P2 incidents with enterprise-wide impact "
                "require human review before any automated "
                "workflow is considered."
            ),
            requires_human=True,
            policy_version=POLICY_VERSION,
            checks=checks,
        ).to_dict()

    # ========================================================
    # 7. High urgency + enterprise impact
    # ========================================================

    if (
        urgency == "critical"
        and impact in HIGH_IMPACT_VALUES
    ):
        return PolicyDecision(
            decision="HUMAN_REVIEW",
            action=None,
            action_label=None,
            reason=(
                "Critical-urgency requests with enterprise "
                "impact require human review."
            ),
            requires_human=True,
            policy_version=POLICY_VERSION,
            checks=checks,
        ).to_dict()

    # ========================================================
    # 8. Knowledge questions are not automation requests
    # ========================================================

    if intent == "knowledge question":
        return PolicyDecision(
            decision="NO_AUTOMATION",
            action=None,
            action_label=None,
            reason=(
                "The request is informational. AegisDesk can "
                "provide the grounded answer but should not "
                "execute an IT action."
            ),
            requires_human=False,
            policy_version=POLICY_VERSION,
            checks=checks,
        ).to_dict()

    # ========================================================
    # 9. Determine approved action
    # ========================================================

    inferred_action = _infer_action(analysis)

    if normalised_requested_action in ALLOWED_ACTIONS:
        action = normalised_requested_action
    else:
        action = inferred_action

    # ========================================================
    # 10. No approved automation exists
    # ========================================================

    if not action or action not in ALLOWED_ACTIONS:
        return PolicyDecision(
            decision="HUMAN_REVIEW",
            action=None,
            action_label=None,
            reason=(
                "The request does not map to an approved "
                "automation workflow."
            ),
            requires_human=True,
            policy_version=POLICY_VERSION,
            checks=checks,
        ).to_dict()

    # ========================================================
    # 11. Action-specific human requirement
    # ========================================================

    action_definition = ALLOWED_ACTIONS[action]

    if action_definition["requires_human"]:
        return PolicyDecision(
            decision="HUMAN_REVIEW",
            action=action,
            action_label=action_definition["label"],
            reason=(
                "This workflow is known to AegisDesk but "
                "requires human approval before execution."
            ),
            requires_human=True,
            policy_version=POLICY_VERSION,
            checks=checks,
        ).to_dict()

    # ========================================================
    # 12. Approved low-risk action
    # ========================================================

    return PolicyDecision(
        decision="APPROVED",
        action=action,
        action_label=action_definition["label"],
        reason=(
            "The request is grounded, sufficiently confident, "
            "within the approved impact limits, and maps to "
            "an approved low-risk automation workflow."
        ),
        requires_human=False,
        policy_version=POLICY_VERSION,
        checks=checks,
    ).to_dict()


# ============================================================
# Policy Status
# ============================================================

def policy_status() -> dict[str, Any]:
    return {
        "status": "ready",
        "policy_version": POLICY_VERSION,

        # IMPORTANT:
        # Policy evaluation is active, but actual automation
        # execution remains disabled.
        "automation_enabled": False,
        "execution_enabled": False,

        "minimum_ai_confidence": MIN_AI_CONFIDENCE,
        "minimum_grounding_similarity": (
            MIN_GROUNDING_SIMILARITY
        ),

        "allowed_actions": [
            {
                "id": action_id,
                **definition,
            }
            for action_id, definition
            in ALLOWED_ACTIONS.items()
        ],

        "blocked_action_count": len(
            BLOCKED_ACTIONS
        ),

        "human_review_for_p1": True,
        "human_review_for_enterprise_p2": True,
    }