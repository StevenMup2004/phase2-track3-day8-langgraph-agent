"""Streamlit UI for demonstrating the Human in the Loop approval path."""

from __future__ import annotations

import os
import uuid
from typing import Any

import streamlit as st
from langgraph.types import Command

from langgraph_agent_lab.graph import CompiledGraph, build_graph
from langgraph_agent_lab.persistence import build_checkpointer
from langgraph_agent_lab.scenarios import load_scenarios
from langgraph_agent_lab.state import Route, Scenario, initial_state

os.environ["LANGGRAPH_INTERRUPT"] = "true"


@st.cache_resource
def _graph() -> CompiledGraph:
    return build_graph(checkpointer=build_checkpointer("memory"))


@st.cache_data
def _sample_scenarios() -> list[Scenario]:
    return load_scenarios("data/sample/scenarios.jsonl")


def _interrupt_payload(result: dict[str, Any]) -> dict[str, Any] | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0]
    value = getattr(first, "value", None)
    return value if isinstance(value, dict) else {"value": value}


def _run_graph(query: str, expected_route: Route, max_attempts: int = 3) -> dict[str, Any]:
    scenario = Scenario(
        id=f"ui-{uuid.uuid4().hex[:8]}",
        query=query,
        expected_route=expected_route,
        max_attempts=max_attempts,
    )
    state = initial_state(scenario)
    st.session_state.thread_id = state["thread_id"]
    result = _graph().invoke(state, config={"configurable": {"thread_id": state["thread_id"]}})
    st.session_state.result = result
    return result


def _resume_graph(approved: bool) -> dict[str, Any]:
    decision = {
        "approved": approved,
        "reviewer": "streamlit-reviewer",
        "comment": "Approved in UI" if approved else "Rejected in UI",
    }
    result = _graph().invoke(
        Command(resume=decision),
        config={"configurable": {"thread_id": st.session_state.thread_id}},
    )
    st.session_state.result = result
    return result


def _event_trail(result: dict[str, Any]) -> list[dict[str, Any]]:
    return list(result.get("events", []) or [])


st.set_page_config(page_title="LangGraph HITL Demo", layout="wide")
st.title("LangGraph Human in the Loop Demo")

samples = _sample_scenarios()
risky_samples = [item for item in samples if item.expected_route == Route.RISKY]
simple_samples = [item for item in samples if item.expected_route == Route.SIMPLE]
default_query = (
    risky_samples[0].query
    if risky_samples
    else "Refund this customer and send confirmation email"
)

left, right = st.columns([2, 1])

with left:
    sample_options = {
        "Risky sample": {
            "query": default_query,
            "expected_route": Route.RISKY,
            "max_attempts": 3,
        },
        "Simple sample": {
            "query": simple_samples[0].query if simple_samples else "How do I reset my password?",
            "expected_route": Route.SIMPLE,
            "max_attempts": 3,
        },
        "Dead-letter sample": {
            "query": "System failure cannot recover after multiple attempts",
            "expected_route": Route.ERROR,
            "max_attempts": 1,
        },
    }
    selected = st.selectbox("Scenario", list(sample_options))
    sample = sample_options[selected]
    query = st.text_area("Ticket query", value=str(sample["query"]), height=100)
    if st.button("Run graph", type="primary"):
        _run_graph(
            query,
            expected_route=sample["expected_route"],
            max_attempts=int(sample["max_attempts"]),
        )

with right:
    result = st.session_state.get("result")
    if result:
        st.metric("Route", result.get("route") or "paused")
        st.metric("Attempts", int(result.get("attempt", 0) or 0))
        st.metric("Events", len(_event_trail(result)))

result = st.session_state.get("result")
if result:
    payload = _interrupt_payload(result)
    if payload:
        st.subheader("Approval required")
        st.json(payload)
        approve_col, reject_col = st.columns(2)
        with approve_col:
            if st.button("Approve", type="primary"):
                _resume_graph(True)
                st.rerun()
        with reject_col:
            if st.button("Reject"):
                _resume_graph(False)
                st.rerun()

    final_answer = result.get("final_answer") if isinstance(result, dict) else None
    pending_question = result.get("pending_question") if isinstance(result, dict) else None
    if final_answer or pending_question:
        st.subheader("Result")
        st.write(final_answer or pending_question)

    st.subheader("Event trail")
    events = _event_trail(result)
    if events:
        st.dataframe(
            [
                {
                    "node": event.get("node"),
                    "event_type": event.get("event_type"),
                    "message": event.get("message"),
                }
                for event in events
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("The graph is paused before final state events are returned.")
