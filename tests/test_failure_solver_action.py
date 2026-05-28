from failure_solver.app import execute_action


def test_execute_action_retry():
    result = execute_action({"action": "retry", "max_attempts": 1, "backoff_seconds": 0})
    assert result["action"] == "retry"
    assert result["result"] == "success"


def test_execute_action_unknown_action():
    result = execute_action({"action": "nonexistent_action"})
    assert result["action"] == "nonexistent_action"
    assert result["result"] == "no_op"
