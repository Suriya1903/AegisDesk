from __future__ import annotations

import json
import os
import re
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.rag_service import search_knowledge


load_dotenv()


# =========================================================
# CONFIGURATION
# =========================================================

MODEL_NAME = os.getenv(
    "HF_MODEL_NAME",
    "Qwen/Qwen2.5-0.5B-Instruct",
)

MAX_NEW_TOKENS = int(
    os.getenv(
        "AI_MAX_NEW_TOKENS",
        "350",
    )
)

MIN_GROUNDING_SIMILARITY = float(
    os.getenv(
        "AI_MIN_GROUNDING_SIMILARITY",
        "0.25",
    )
)


# =========================================================
# MODEL STATE
# =========================================================

_tokenizer = None
_model = None
_device = None


# =========================================================
# RESPONSE MODEL
# =========================================================

class AIAnalysis(BaseModel):
    answer: str
    intent: str
    category: str
    subcategory: str
    priority: str
    impact: str
    urgency: str
    assignment_group: str
    confidence: float = Field(ge=0.0, le=1.0)
    recommended_action: str
    grounded: bool = False
    model: str
    retrieval: dict[str, Any]
    sources: list[dict[str, Any]]
    llm_error: str | None = None


# =========================================================
# MODEL LOADING
# =========================================================

def _load_model() -> None:
    global _tokenizer, _model, _device

    if _model is not None and _tokenizer is not None:
        return

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "AI dependencies are missing. Install transformers, torch, "
            "accelerate and sentencepiece."
        ) from exc

    _device = "cuda" if torch.cuda.is_available() else "cpu"

    print(
        f"[AegisDesk AI] Loading model: {MODEL_NAME}"
    )
    print(
        f"[AegisDesk AI] Device: {_device}"
    )

    _tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME,
        trust_remote_code=True,
    )

    dtype = (
        torch.float16
        if _device == "cuda"
        else torch.float32
    )

    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=dtype,
        trust_remote_code=True,
    )

    _model.to(_device)
    _model.eval()

    print("[AegisDesk AI] Hugging Face model loaded.")


# =========================================================
# STATUS
# =========================================================

def ai_status() -> dict[str, Any]:
    return {
        "status": (
            "loaded"
            if _model is not None
            else "not_loaded"
        ),
        "model": MODEL_NAME,
        "device": _device,
        "loaded": _model is not None,
    }


# =========================================================
# HELPERS
# =========================================================

def _normalise(value: Any) -> str:
    if value is None:
        return ""

    return (
        str(value)
        .strip()
        .lower()
    )


def _clamp_confidence(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0

    return max(
        0.0,
        min(1.0, number),
    )


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned,
    )

    try:
        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    match = re.search(
        r"\{.*\}",
        cleaned,
        flags=re.DOTALL,
    )

    if match:
        parsed = json.loads(match.group(0))

        if isinstance(parsed, dict):
            return parsed

    raise ValueError(
        "The LLM did not return valid JSON."
    )


def _top_similarity(results: list[dict[str, Any]]) -> float:
    if not results:
        return 0.0

    try:
        return float(
            results[0].get(
                "similarity",
                results[0].get(
                    "confidence",
                    0.0,
                ),
            )
            or 0.0
        )
    except (TypeError, ValueError):
        return 0.0


def _grounded_sources(
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        item
        for item in results
        if float(
            item.get(
                "similarity",
                0.0,
            )
            or 0.0
        ) >= MIN_GROUNDING_SIMILARITY
    ]


def _format_sources(
    results: list[dict[str, Any]],
) -> str:
    parts: list[str] = []

    for index, item in enumerate(results, start=1):
        parts.append(
            "\n".join(
                [
                    f"SOURCE {index}",
                    f"Article: {item.get('title', '')}",
                    f"Category: {item.get('category', '')}",
                    f"Similarity: {item.get('similarity', 0.0)}",
                    f"Content: {item.get('text', '')}",
                ]
            )
        )

    return "\n\n".join(parts)


# =========================================================
# DETERMINISTIC ITSM NORMALISATION
# =========================================================
#
# Qwen is responsible for language understanding.
# Deterministic rules then protect important ITSM fields.
#
# This prevents a small local model from returning:
#   VPN -> General
#   VPN -> Knowledge Question
#   confidence -> 0.0
#
# The policy engine remains the final safety gate.
# =========================================================

def _rule_based_classification(
    query: str,
    results: list[dict[str, Any]],
) -> dict[str, Any] | None:

    text = _normalise(query)

    has_vpn = (
        "vpn" in text
        or "virtual private network" in text
    )

    has_password = (
        "password" in text
        or "passcode" in text
    )

    has_account = (
        "account" in text
        or "login" in text
        or "sign in" in text
        or "signin" in text
    )

    has_outlook = (
        "outlook" in text
        or "email" in text
        or "mail" in text
    )

    has_restart = (
        "restart" in text
        or "reopen" in text
        or "relaunch" in text
    )

    dangerous = any(
        phrase in text
        for phrase in (
            "disable antivirus",
            "disable endpoint",
            "disable security",
            "turn off antivirus",
            "turn off security",
            "change firewall",
            "modify security policy",
            "give me admin",
            "grant admin",
            "admin access",
            "privileged access",
            "run shell command",
            "arbitrary command",
            "install unapproved software",
            "delete account",
            "delete user",
        )
    )

    if dangerous:
        return {
            "intent": "Service Request",
            "category": "Security",
            "subcategory": "Security Policy",
            "priority": "P2",
            "impact": "Individual",
            "urgency": "High",
            "assignment_group": "Security Operations",
            "confidence": 0.99,
            "recommended_action": (
                "Do not perform the requested security or privileged "
                "change. Route the request to human security support."
            ),
        }

    if has_vpn:
        widespread = any(
            phrase in text
            for phrase in (
                "everyone",
                "all users",
                "whole team",
                "entire team",
                "company",
                "organization",
                "outage",
                "multiple users",
            )
        )

        return {
            "intent": "Incident",
            "category": "Network",
            "subcategory": "VPN",
            "priority": "P2" if widespread else "P3",
            "impact": "Enterprise" if widespread else "Individual",
            "urgency": "High" if widespread else "Medium",
            "assignment_group": "Network Support",
            "confidence": 0.94,
            "recommended_action": (
                "Verify internet connectivity and the approved VPN "
                "client, re-authenticate after a password change, "
                "restart the approved VPN client, and escalate to "
                "Network Support if the approved troubleshooting steps "
                "do not resolve the issue."
            ),
        }

    if has_password:
        reset = any(
            phrase in text
            for phrase in (
                "reset",
                "forgot",
                "forgotten",
                "expired",
                "change my password",
            )
        )

        if reset:
            return {
                "intent": "Service Request",
                "category": "Account",
                "subcategory": "Password Reset",
                "priority": "P3",
                "impact": "Individual",
                "urgency": "Medium",
                "assignment_group": "Service Desk",
                "confidence": 0.96,
                "recommended_action": (
                    "Initiate the approved password reset workflow."
                ),
            }

    if has_account and any(
        phrase in text
        for phrase in (
            "locked",
            "unlock",
            "lockout",
        )
    ):
        return {
            "intent": "Incident",
            "category": "Account",
            "subcategory": "Account Unlock",
            "priority": "P3",
            "impact": "Individual",
            "urgency": "High",
            "assignment_group": "Service Desk",
            "confidence": 0.96,
            "recommended_action": (
                "Initiate the approved account unlock workflow."
            ),
        }

    if has_outlook:
        return {
            "intent": "Incident",
            "category": "Email",
            "subcategory": "Outlook",
            "priority": "P3",
            "impact": "Individual",
            "urgency": "Medium",
            "assignment_group": "Service Desk",
            "confidence": 0.91,
            "recommended_action": (
                "Follow the approved Outlook synchronization "
                "troubleshooting procedure and escalate if unresolved."
            ),
        }

    if has_restart:
        return {
            "intent": "Incident",
            "category": "Software",
            "subcategory": "Application Restart",
            "priority": "P3",
            "impact": "Individual",
            "urgency": "Medium",
            "assignment_group": "Service Desk",
            "confidence": 0.90,
            "recommended_action": (
                "Restart the affected approved application through "
                "the IT workflow."
            ),
        }

    # Only override the model if a strong RAG category exists.
    if results:
        category = str(
            results[0].get(
                "category",
                "General",
            )
        )

        title = str(
            results[0].get(
                "title",
                "",
            )
        )

        if category and category != "General":
            return {
                "intent": "Incident",
                "category": category,
                "subcategory": title,
                "priority": "P3",
                "impact": "Individual",
                "urgency": "Medium",
                "assignment_group": "Service Desk",
                "confidence": 0.82,
                "recommended_action": (
                    "Follow the approved troubleshooting guidance "
                    "from the retrieved enterprise knowledge."
                ),
            }

    return None


# =========================================================
# PROMPT
# =========================================================

def _build_prompt(
    query: str,
    sources: list[dict[str, Any]],
) -> str:

    knowledge = _format_sources(sources)

    return f"""
You are the ITSM analysis component of AegisDesk.

User request:
{query}

Approved enterprise knowledge:
{knowledge}

Rules:
1. Use only the supplied enterprise knowledge as factual grounding.
2. Never invent company policies, system state, credentials, or procedures.
3. Never claim that an action was executed.
4. Do not recommend disabling antivirus, endpoint protection,
   firewall/security controls, granting privileged access, deleting
   accounts, or running arbitrary commands.
5. Classify the user's actual request, not merely the knowledge article.
6. A user reporting that VPN is not connecting is an Incident,
   category Network, subcategory VPN.
7. A request to reset a forgotten/expired password is a Service Request.
8. A locked account is an Incident with Account Unlock as the subcategory.
9. Output ONLY valid JSON.
10. confidence must be between 0.0 and 1.0.

Required JSON:
{{
  "answer": "short helpful grounded answer",
  "intent": "Knowledge Question | Incident | Service Request | Automatable Issue",
  "category": "Network | Account | Email | Hardware | Software | Security | General",
  "subcategory": "specific ITSM subcategory",
  "priority": "P1 | P2 | P3 | P4",
  "impact": "Individual | Team | Department | Enterprise",
  "urgency": "Low | Medium | High | Critical",
  "assignment_group": "appropriate support group",
  "confidence": 0.0,
  "recommended_action": "safe recommended next step"
}}
""".strip()


# =========================================================
# LLM CALL
# =========================================================

def _call_llm(
    prompt: str,
) -> dict[str, Any]:

    import torch

    _load_model()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a strict enterprise ITSM classification "
                "assistant. Return JSON only."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    if hasattr(
        _tokenizer,
        "apply_chat_template",
    ):
        inputs = _tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        )
    else:
        text = (
            "SYSTEM:\n"
            + messages[0]["content"]
            + "\nUSER:\n"
            + messages[1]["content"]
        )

        inputs = _tokenizer(
            text,
            return_tensors="pt",
        )["input_ids"]

    inputs = inputs.to(_device)

    with torch.no_grad():
        generated = _model.generate(
            inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=False,
            pad_token_id=(
                _tokenizer.eos_token_id
                if _tokenizer.eos_token_id is not None
                else None
            ),
        )

    generated_tokens = generated[
        0,
        inputs.shape[-1]:,
    ]

    output_text = _tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True,
    )

    return _extract_json(output_text)


# =========================================================
# MAIN ANALYSIS
# =========================================================

def analyze_request(
    query: str,
    top_k: int = 5,
) -> dict[str, Any]:

    query = query.strip()

    if not query:
        raise ValueError(
            "Query cannot be empty."
        )

    results = search_knowledge(
        query,
        top_k=top_k,
    )

    top_similarity = _top_similarity(results)

    grounded_sources = _grounded_sources(
        results
    )

    grounded = bool(
        grounded_sources
        and top_similarity >= MIN_GROUNDING_SIMILARITY
    )

    retrieval = {
        "count": len(results),
        "grounded_count": len(grounded_sources),
        "top_similarity": round(
            top_similarity,
            4,
        ),
    }

    if not grounded:
        return {
            "query": query,
            "grounded": False,
            "model": MODEL_NAME,
            "retrieval": retrieval,
            "sources": results,
            "analysis": {
                "answer": (
                    "I could not find enough approved enterprise "
                    "knowledge to safely answer this request. "
                    "Please contact the Service Desk."
                ),
                "intent": "Incident",
                "category": "General",
                "subcategory": "General",
                "priority": "P3",
                "impact": "Individual",
                "urgency": "Medium",
                "assignment_group": "Service Desk",
                "confidence": 0.0,
                "recommended_action": (
                    "Human review is required because the request "
                    "is not sufficiently grounded in approved "
                    "enterprise knowledge."
                ),
            },
        }

    prompt = _build_prompt(
        query,
        grounded_sources,
    )

    llm_error = None
    llm_result: dict[str, Any] = {}

    try:
        llm_result = _call_llm(prompt)

    except Exception as exc:
        llm_error = str(exc)

    rule_result = _rule_based_classification(
        query,
        grounded_sources,
    )

    # Strong deterministic ITSM patterns take precedence over
    # unreliable small-model classification. This is still safe
    # because the Policy Engine remains the final gate.
    if rule_result is not None:
        structured = rule_result
    else:
        structured = llm_result

    if not structured:
        structured = {
            "answer": (
                "The request is grounded in approved knowledge, "
                "but the AI classification could not be completed."
            ),
            "intent": "Incident",
            "category": "General",
            "subcategory": "General",
            "priority": "P3",
            "impact": "Individual",
            "urgency": "Medium",
            "assignment_group": "Service Desk",
            "confidence": 0.0,
            "recommended_action": (
                "Human review is required."
            ),
        }

    confidence = _clamp_confidence(
        structured.get(
            "confidence",
            0.0,
        )
    )

    analysis = {
        "answer": str(
            structured.get(
                "answer",
                "Please follow the approved IT support procedure.",
            )
        ),
        "intent": str(
            structured.get(
                "intent",
                "Incident",
            )
        ),
        "category": str(
            structured.get(
                "category",
                "General",
            )
        ),
        "subcategory": str(
            structured.get(
                "subcategory",
                "General",
            )
        ),
        "priority": str(
            structured.get(
                "priority",
                "P3",
            )
        ),
        "impact": str(
            structured.get(
                "impact",
                "Individual",
            )
        ),
        "urgency": str(
            structured.get(
                "urgency",
                "Medium",
            )
        ),
        "assignment_group": str(
            structured.get(
                "assignment_group",
                "Service Desk",
            )
        ),
        "confidence": confidence,
        "recommended_action": str(
            structured.get(
                "recommended_action",
                "Human review is recommended.",
            )
        ),
    }

    # Keep the answer grounded even when Qwen produces a weak
    # generic answer.
    if rule_result is not None:
        analysis["answer"] = (
            analysis["answer"]
            if analysis["answer"]
            and "firewall rules" not in _normalise(
                analysis["answer"]
            )
            else rule_result["recommended_action"]
        )

    # Expose the structured classification at the top level as well.
    # The Policy Engine consumes this top-level contract:
    # confidence, intent, priority, grounded, recommended_action, etc.
    # Keeping "analysis" preserves the frontend/API response contract.
    return {
        "query": query,
        "grounded": grounded,
        "model": MODEL_NAME,
        "retrieval": retrieval,
        "sources": results,

        # Policy Engine contract
        "answer": analysis["answer"],
        "intent": analysis["intent"],
        "category": analysis["category"],
        "subcategory": analysis["subcategory"],
        "priority": analysis["priority"],
        "impact": analysis["impact"],
        "urgency": analysis["urgency"],
        "assignment_group": analysis["assignment_group"],
        "confidence": analysis["confidence"],
        "recommended_action": analysis["recommended_action"],
        "top_similarity": top_similarity,

        # Existing structured response preserved
        "analysis": analysis,

        **(
            {"llm_error": llm_error}
            if llm_error
            else {}
        ),
    }
