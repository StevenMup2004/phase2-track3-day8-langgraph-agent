from langgraph_agent_lab.nodes import classify_node, dead_letter_node
from langgraph_agent_lab.state import Route


def test_classify_risky_wins_over_tool_keywords() -> None:
    result = classify_node({"query": "Refund and check order status"})
    assert result["route"] == Route.RISKY.value
    assert result["risk_level"] == "high"


def test_classify_missing_info_with_punctuation() -> None:
    result = classify_node({"query": "Can you fix it?!"})
    assert result["route"] == Route.MISSING_INFO.value


def test_classify_error_keywords() -> None:
    result = classify_node({"query": "System failure cannot recover after attempts"})
    assert result["route"] == Route.ERROR.value


def test_dead_letter_appends_error_and_answer() -> None:
    result = dead_letter_node({"attempt": 3})
    assert result["final_answer"]
    assert result["errors"] == ["dead-lettered after 3 attempts"]
