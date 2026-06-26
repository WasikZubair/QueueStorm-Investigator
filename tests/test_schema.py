from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

REQUIRED_FIELDS = {
    "ticket_id",
    "relevant_transaction_id",
    "evidence_verdict",
    "case_type",
    "severity",
    "department",
    "agent_summary",
    "recommended_next_action",
    "customer_reply",
    "human_review_required",
}

ENUMS = {
    "evidence_verdict": {"consistent", "inconsistent", "insufficient_data"},
    "case_type": {
        "wrong_transfer",
        "payment_failed",
        "refund_request",
        "duplicate_payment",
        "merchant_settlement_delay",
        "agent_cash_in_issue",
        "phishing_or_social_engineering",
        "other",
    },
    "severity": {"low", "medium", "high", "critical"},
    "department": {
        "customer_support",
        "dispute_resolution",
        "payments_ops",
        "merchant_operations",
        "agent_operations",
        "fraud_risk",
    },
}


def assert_valid_response(body: dict, ticket_id: str) -> None:
    assert REQUIRED_FIELDS.issubset(body)
    assert body["ticket_id"] == ticket_id
    assert body["relevant_transaction_id"] is None or isinstance(
        body["relevant_transaction_id"], str
    )
    assert isinstance(body["human_review_required"], bool)
    assert isinstance(body.get("confidence"), (int, float))
    assert 0 <= body["confidence"] <= 1
    assert isinstance(body.get("reason_codes"), list)
    assert all(isinstance(code, str) for code in body["reason_codes"])
    for field, values in ENUMS.items():
        assert body[field] in values


def test_health_returns_exact_status() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_ticket_response_schema_with_minimal_input() -> None:
    payload = {
        "ticket_id": "TKT-MIN",
        "complaint": "Something is wrong with my money. Please check.",
    }

    response = client.post("/analyze-ticket", json=payload)

    assert response.status_code == 200
    assert_valid_response(response.json(), "TKT-MIN")
