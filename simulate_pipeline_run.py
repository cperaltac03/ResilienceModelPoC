import json
from decision_engine.decision_engine import DecisionContext, DecisionEngine
from failure_classifier.classifier import FailureClassifier
from failure_solver.app import execute_action
from pipeline_simulator.app import build_event

payload = {
    'status': 'failed',
    'dependency': 'requests',
    'version': '2.31.0',
    'error': "ReadTimeoutError: HTTPSConnectionPool(host='pypi.org', port=443): Read timed out."
}

event = build_event(payload)
classifier = FailureClassifier()
classification = classifier.classify(event['error'])
with open('rules_manager/rules.json', 'r', encoding='utf-8') as f:
    rules = json.load(f)
engine = DecisionEngine('http://rules-manager-unused')
decision = engine.decide(
    DecisionContext(category=classification.category, severity=classification.severity, branch=event['branch']),
    rules=rules,
)
outcome = execute_action(decision)

print('event=')
print(json.dumps(event, indent=2))
print()
print('classification=')
print(json.dumps({'category': classification.category, 'severity': classification.severity}, indent=2))
print()
print('decision=')
print(json.dumps(decision, indent=2))
print()
print('outcome=')
print(json.dumps(outcome, indent=2))
