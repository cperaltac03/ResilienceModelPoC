import json

from decision_engine.decision_engine import DecisionContext, DecisionEngine
from failure_classifier.classifier import FailureClassifier
from failure_solver.app import execute_action
from pipeline_simulator.app import build_event


def test_timeout_failure_selects_timeout_recovery_action():
    timeout_error = "ReadTimeoutError: HTTPSConnectionPool(host='pypi.org', port=443): Read timed out."

    event = build_event(
        {
            "status": "failed",
            "dependency": "requests",
            "version": "2.31.0",
            "error": timeout_error,
        }
    )

    classifier = FailureClassifier()
    classification = classifier.classify(event["error"])

    assert classification.category == "Timeout"
    assert classification.severity == "MEDIUM"

    with open("rules_manager/rules.json", encoding="utf-8") as handle:
        rules = json.load(handle)

    engine = DecisionEngine("http://rules-manager-unused")
    decision = engine.decide(
        DecisionContext(
            category=classification.category,
            severity=classification.severity,
            branch=event["branch"],
        ),
        rules=rules,
    )

    assert decision["action"] == "increase_timeout_and_retry"
    assert decision["max_attempts"] == 3
    assert decision["backoff_seconds"] == 5

    outcome = execute_action(decision)

    assert outcome["action"] == "increase_timeout_and_retry"
    assert outcome["result"] == "success"