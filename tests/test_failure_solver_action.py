from failure_solver.app import execute_action
from failure_solver.actions.cache_clean import clean_cache_action
from failure_solver.actions.dependency_substitution import dependency_substitution_action
from failure_solver.actions.retry import retry_action


def test_execute_action_retry():
    result = execute_action({"action": "retry", "max_attempts": 1, "backoff_seconds": 0})
    assert result["action"] == "retry"
    assert result["result"] == "success"


def test_retry_action_links_attempts_and_backoff():
    result = retry_action({"action": "retry", "max_attempts": 2, "backoff_seconds": 0})

    assert result["attempts"] == 2
    assert result["backoff_seconds"] == 0
    assert result["result"] == "success"


def test_clean_cache_action_marks_cache_cleaned():
    result = clean_cache_action({"action": "clean_cache_and_retry", "max_attempts": 1, "backoff_seconds": 0})

    assert result["action"] == "clean_cache_and_retry"
    assert result["cache_cleaned"] is True
    assert result["result"] == "success"


def test_dependency_substitution_action_uses_pipeline_context():
    result = dependency_substitution_action(
        {"action": "dependency_substitution"},
        {"dependency": "requests", "pipeline_id": "build-1234"},
    )

    assert result["dependency"] == "requests"
    assert result["substitute_dependency"] == "requests-mirror"
    assert result["substituted"] is True


def test_execute_action_unknown_action():
    result = execute_action({"action": "nonexistent_action"})
    assert result["action"] == "nonexistent_action"
    assert result["result"] == "no_op"
