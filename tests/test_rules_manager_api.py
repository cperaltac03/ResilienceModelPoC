from fastapi.testclient import TestClient

from rules_manager.app import app

client = TestClient(app)


def test_rules_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_put_and_get_rules():
    rules = [
        {"if": {"branch": "main"}, "then": {"action": "retry"}}
    ]
    response = client.put("/rules", json=rules)
    assert response.status_code == 200
    assert response.json()["count"] == 1

    get_response = client.get("/rules")
    assert get_response.status_code == 200
    assert get_response.json() == rules


def test_append_rule():
    rule = {"if": {"branch": "dev"}, "then": {"action": "clean_cache_and_retry"}}
    response = client.post("/rules", json=rule)
    assert response.status_code == 200
    assert response.json()["count"] >= 1
