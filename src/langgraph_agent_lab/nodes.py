"""Node implementations for the LangGraph workflow.

Each node returns a partial state update and avoids mutating the input state in place.
"""

from __future__ import annotations

import os
import re

from .state import AgentState, ApprovalDecision, Route, make_event

RISKY_KEYWORDS = {"refund", "delete", "send", "cancel", "remove", "revoke"}
TOOL_KEYWORDS = {"status", "order", "lookup", "check", "track", "find", "search"}
MISSING_INFO_PRONOUNS = {"it", "this", "that", "thing", "issue", "problem"}
ERROR_KEYWORDS = {"timeout", "fail", "failed", "failure", "error", "crash", "unavailable"}


def _tokens(text: str) -> list[str]:
    """Return lower-case word tokens so routing does not depend on punctuation."""
    return re.findall(r"[a-z0-9]+", text.lower())


def intake_node(state: AgentState) -> dict:
    """Normalize raw query into state fields."""
    query = state.get("query", "").strip()
    return {
        "query": query,
        "messages": [f"intake:{query[:40]}"],
        "events": [make_event("intake", "completed", "query normalized")],
    }


def classify_node(state: AgentState) -> dict:
    """Classify the query into a route using deterministic keyword policy."""
    query = state.get("query", "")
    words = _tokens(query)
    word_set = set(words)
    route = Route.SIMPLE
    risk_level = "low"
    reason = "default simple support answer"

    if word_set & RISKY_KEYWORDS:
        route = Route.RISKY
        risk_level = "high"
        reason = "risky action keyword detected"
    elif word_set & TOOL_KEYWORDS:
        route = Route.TOOL
        reason = "tool lookup keyword detected"
    elif len(words) < 5 and word_set & MISSING_INFO_PRONOUNS:
        route = Route.MISSING_INFO
        reason = "short vague request needs clarification"
    elif word_set & ERROR_KEYWORDS:
        route = Route.ERROR
        risk_level = "medium"
        reason = "error or transient failure keyword detected"

    return {
        "route": route.value,
        "risk_level": risk_level,
        "messages": [f"classify:{route.value}"],
        "events": [make_event("classify", "completed", f"route={route.value}", reason=reason)],
    }


def ask_clarification_node(state: AgentState) -> dict:
    """Ask for missing information instead of hallucinating."""
    approval = state.get("approval") or {}
    if approval and not approval.get("approved"):
        question = (
            "I cannot proceed with the requested action without approval. "
            "What safe alternative should I take?"
        )
        event_message = "risky action rejected; safe clarification requested"
    else:
        question = (
            "Can you share the missing details, such as the account, "
            "order id, or exact issue?"
        )
        event_message = "missing information requested"

    return {
        "pending_question": question,
        "final_answer": question,
        "events": [make_event("clarify", "completed", event_message)],
    }


def tool_node(state: AgentState) -> dict:
    """Call a mock tool and simulate transient failures for error-route scenarios."""
    attempt = int(state.get("attempt", 0))
    if state.get("route") == Route.ERROR.value and attempt < 2:
        result = (
            f"ERROR: transient failure attempt={attempt} "
            f"scenario={state.get('scenario_id', 'unknown')}"
        )
    elif state.get("route") == Route.RISKY.value:
        action = state.get("proposed_action") or "approved risky support action"
        result = f"approved-action-result: {action}"
    else:
        result = (
            f"mock-tool-result scenario={state.get('scenario_id', 'unknown')} "
            f"query={state.get('query', '')[:60]}"
        )

    return {
        "tool_results": [result],
        "events": [make_event("tool", "completed", f"tool executed attempt={attempt}")],
    }


def risky_action_node(state: AgentState) -> dict:
    """Prepare a risky action for approval."""
    query = state.get("query", "")
    proposed_action = f"Review and approve external customer action requested by: {query}"
    return {
        "proposed_action": proposed_action,
        "events": [
            make_event(
                "risky_action",
                "pending_approval",
                "approval required",
                risk_level=state.get("risk_level", "high"),
                proposed_action=proposed_action,
            )
        ],
    }


def approval_node(state: AgentState) -> dict:
    """Human approval step with optional LangGraph interrupt()."""
    if os.getenv("LANGGRAPH_INTERRUPT", "").lower() == "true":
        from langgraph.types import interrupt

        value = interrupt(
            {
                "proposed_action": state.get("proposed_action"),
                "risk_level": state.get("risk_level"),
                "query": state.get("query"),
                "scenario_id": state.get("scenario_id"),
            }
        )
        if isinstance(value, dict):
            decision = ApprovalDecision(**value)
        else:
            decision = ApprovalDecision(approved=bool(value))
    else:
        decision = ApprovalDecision(approved=True, comment="mock approval for lab")

    return {
        "approval": decision.model_dump(),
        "events": [make_event("approval", "completed", f"approved={decision.approved}")],
    }


def retry_or_fallback_node(state: AgentState) -> dict:
    """Record a retry attempt or fallback decision."""
    attempt = int(state.get("attempt", 0)) + 1
    max_attempts = int(state.get("max_attempts", 3))
    return {
        "attempt": attempt,
        "errors": [f"transient failure attempt={attempt} of {max_attempts}"],
        "events": [
            make_event(
                "retry",
                "completed",
                "retry attempt recorded",
                attempt=attempt,
                max_attempts=max_attempts,
            )
        ],
    }


def answer_node(state: AgentState) -> dict:
    """Produce a final response grounded in route state."""
    if state.get("tool_results"):
        answer = f"I found: {state['tool_results'][-1]}"
    elif state.get("route") == Route.SIMPLE.value:
        answer = (
            "You can resolve this with the standard support steps. "
            "No external action is needed."
        )
    else:
        answer = "The request has been handled safely."

    return {
        "final_answer": answer,
        "events": [make_event("answer", "completed", "answer generated")],
    }


def evaluate_node(state: AgentState) -> dict:
    """Evaluate tool results: the done check that enables retry loops."""
    tool_results = state.get("tool_results", [])
    latest = tool_results[-1] if tool_results else ""
    if "ERROR" in latest:
        return {
            "evaluation_result": "needs_retry",
            "events": [
                make_event(
                    "evaluate",
                    "completed",
                    "tool result indicates failure, retry needed",
                )
            ],
        }

    return {
        "evaluation_result": "success",
        "events": [make_event("evaluate", "completed", "tool result satisfactory")],
    }


def dead_letter_node(state: AgentState) -> dict:
    """Log unresolvable failures for manual review."""
    attempt = int(state.get("attempt", 0))
    return {
        "final_answer": (
            "Request could not be completed after maximum retry attempts. "
            "Logged for manual review."
        ),
        "errors": [f"dead-lettered after {attempt} attempts"],
        "events": [
            make_event(
                "dead_letter",
                "completed",
                f"max retries exceeded, attempt={attempt}",
            )
        ],
    }


def finalize_node(state: AgentState) -> dict:
    """Finalize the run and emit a final audit event."""
    return {"events": [make_event("finalize", "completed", "workflow finished")]}
