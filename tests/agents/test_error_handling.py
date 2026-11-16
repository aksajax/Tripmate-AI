
"""Tests for TripMate AI graph error handling."""

from app.graph.error_handling import safe_node


def test_safe_node_returns_normal_result():
    def successful_node(state):
        return {"current_step": "example"}

    wrapped = safe_node("example", successful_node)

    result = wrapped({})

    assert result == {"current_step": "example"}


def test_safe_node_records_unexpected_error():
    def failing_node(state):
        raise RuntimeError("Test failure")

    wrapped = safe_node("example", failing_node)

    result = wrapped({})

    assert result["current_step"] == "example"
    assert result["workflow_status"] == "failed"
    assert len(result["errors"]) == 1
    assert result["errors"][0]["node"] == "example"
    assert result["errors"][0]["error_type"] == "RuntimeError"
    assert result["errors"][0]["message"] == "Test failure"
