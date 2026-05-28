from fastapi.testclient import TestClient

from pipeline_simulator.app import app

client = TestClient(app)


def test_pipeline_simulator_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_simulate_event_publish(monkeypatch):
    published = []

    def fake_publish(event):
        published.append(event)

    monkeypatch.setattr("pipeline_simulator.app.publish_event", fake_publish)

    response = client.post("/simulate", json={})
    assert response.status_code == 200
    result = response.json()
    assert result["ok"] is True
    assert result["event"]["event_type"] == "pipeline_run"
    assert published and published[0]["event_type"] == "pipeline_run"


def test_simulate_event_with_override(monkeypatch):
    published = []

    def fake_publish(event):
        published.append(event)

    monkeypatch.setattr("pipeline_simulator.app.publish_event", fake_publish)

    payload = {"status": "success", "dependency": "requests", "version": "2.31.0"}
    response = client.post("/simulate", json=payload)
    assert response.status_code == 200
    event = response.json()["event"]
    assert event["status"] == "success"
    assert event["dependency"] == "requests"
    assert event["version"] == "2.31.0"
    assert published[0]["pipeline_id"] == event["pipeline_id"]
