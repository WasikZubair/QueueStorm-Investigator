import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_investigate_retry_heavy_case_returns_queue_storm_likely() -> None:
    payload = {
        "case_id": "case-test-001",
        "events": [
            {
                "event_id": "evt-001",
                "queue": "payments.settlement",
                "transaction_id": "txn-123",
                "status": "failed",
            },
            {
                "event_id": "evt-002",
                "queue": "payments.settlement",
                "transaction_id": "txn-123",
                "status": "retry",
            },
            {
                "event_id": "evt-003",
                "queue": "payments.settlement",
                "transaction_id": "txn-123",
                "status": "retry",
            },
            {
                "event_id": "evt-004",
                "queue": "payments.settlement",
                "transaction_id": "txn-123",
                "status": "success",
            },
        ],
    }

    response = client.post("/investigate", json=payload)
    body = response.json()

    assert response.status_code == 200
    assert body["classification"] == "queue_storm_likely"
    assert body["case_id"] == "case-test-001"
    assert "txn-123" in body["matched_transactions"]
    assert body["safety_note"]
